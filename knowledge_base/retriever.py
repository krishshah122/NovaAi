"""
Hybrid Knowledge Base Retriever
Executes vector similarity search against Pinecone Cloud vector database with
automatic local file cache fallback and Pydantic schema reconstruction.
"""

import os
import sys
import json
import math
from typing import List, Dict, Optional, Any
from pathlib import Path

# Ensure project root in python path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv
    env_path = project_root / ".env"
    load_dotenv(dotenv_path=env_path, override=True)
except ImportError:
    pass

try:
    from pinecone import Pinecone
except ImportError:
    Pinecone = None

from knowledge_base.schema import (
    KBRecord, KBQueryResult, KBQueryRequest, KBCategory, KBSource
)
from knowledge_base.embedder import VectorEmbedder


class HybridRetriever:
    """
    Production retrieval engine supporting real-time similarity query search.
    Queries Pinecone vector DB primarily, switching to local cosine math if disconnected.
    """

    def __init__(self, index_name: str = "health-insurance-kb", processed_dir: str = "knowledge_base/data/processed"):
        self.index_name = index_name
        self.processed_dir = Path(processed_dir)
        self.embedder = VectorEmbedder()
        
        # Connect to Pinecone if available
        self.index = None
        api_key = os.getenv("PINECONE_API_KEY")
        if Pinecone and api_key and api_key != "your_pinecone_key_here":
            try:
                pc = Pinecone(api_key=api_key)
                self.index = pc.Index(self.index_name)
                print(f"[RETRIEVER] Connected to Pinecone cloud index: '{self.index_name}'")
            except Exception as e:
                print(f"[WARNING] Could not connect to Pinecone index: {e}. Switching to offline mode.")
        
        # Load local schema records and embeddings for backup resilience
        self.local_records_map: Dict[str, KBRecord] = {}
        self.local_vectors: List[Dict[str, Any]] = []
        self._load_local_cache()

    def _load_local_cache(self):
        """Load offline vector store and schema dictionary from local disk cache."""
        records_file = self.processed_dir / "kb_records.json"
        vectors_file = self.processed_dir / "vector_store.json"
        
        if records_file.exists():
            try:
                with open(records_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        rec = KBRecord(**item)
                        self.local_records_map[rec.record_id] = rec
                print(f"[RETRIEVER] Loaded {len(self.local_records_map)} structured schema items into local memory.")
            except Exception as e:
                print(f"[ERROR] Failed loading local records cache: {e}")

        if vectors_file.exists():
            try:
                with open(vectors_file, "r", encoding="utf-8") as f:
                    self.local_vectors = json.load(f)
                print(f"[RETRIEVER] Loaded {len(self.local_vectors)} local fallback vectors.")
            except Exception as e:
                print(f"[ERROR] Failed loading vector store backup: {e}")

    def _reconstruct_record(self, match_id: str, metadata: Dict[str, Any]) -> Optional[KBRecord]:
        """Reconstruct validated KBRecord from local memory cache or Pinecone metadata."""
        if match_id in self.local_records_map:
            return self.local_records_map[match_id]
        
        if not metadata:
            return None

        try:
            # Reconstruct from metadata scalar dictionary
            category_val = metadata.get("category", KBCategory.FAQ.value)
            source_val = metadata.get("source", KBSource.MANUAL_ENTRY.value)
            
            # Convert string booleans/ints back if needed
            pii = metadata.get("pii_flag", False)
            if isinstance(pii, str):
                pii = pii.lower() == "true"

            chunk_idx = metadata.get("chunk_index", None)
            if chunk_idx and isinstance(chunk_idx, str):
                chunk_idx = int(chunk_idx) if chunk_idx.isdigit() else None
                
            tags = metadata.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]

            return KBRecord(
                record_id=match_id,
                title=str(metadata.get("title", "Health Policy Record")),
                content=str(metadata.get("content", "")),
                category=KBCategory(category_val) if category_val in [c.value for c in KBCategory] else KBCategory.FAQ,
                subcategory=metadata.get("subcategory"),
                source=KBSource(source_val) if source_val in [s.value for s in KBSource] else KBSource.MANUAL_ENTRY,
                source_url=metadata.get("source_url"),
                version=str(metadata.get("version", "1.0")),
                pii_flag=pii,
                tags=tags,
                chunk_index=chunk_idx,
                parent_id=metadata.get("parent_id")
            )
        except Exception as e:
            print(f"[ERROR] Could not reconstruct KBRecord for id '{match_id}': {e}")
            return None

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two numeric vectors."""
        if len(vec1) != len(vec2) or not vec1:
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def _search_local_fallback(self, query_vector: List[float], top_k: int, category_filter: Optional[str]) -> List[Dict]:
        """Perform exactly verified mathematical cosine vector search locally."""
        scores = []
        for item in self.local_vectors:
            vec_id = item["id"]
            vec_values = item["values"]
            metadata = item.get("metadata", {})
            
            if category_filter and str(metadata.get("category")) != category_filter:
                continue

            score = self._cosine_similarity(query_vector, vec_values)
            scores.append({
                "id": vec_id,
                "score": score,
                "metadata": metadata
            })

        # Sort descending by score and slice top_k
        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:top_k]

    def query(self, request: KBQueryRequest) -> List[KBQueryResult]:
        """
        Execute similarity retrieval search for an incoming question.
        Returns sorted List of validated KBQueryResult items with citations.
        """
        self.embedder._load_model()
        if not self.embedder.model:
            print("[ERROR] No embedding model loaded. Cannot execute vector search.")
            return []

        # 1. Generate dense vector embedding for query question
        vectors_generator = self.embedder.model.embed([request.question])
        query_vector = next(vectors_generator).tolist()

        matches_data = []
        category_filter_str = request.category_filter.value if request.category_filter else None

        # 2. Try Cloud Pinecone Index Query First
        if self.index:
            try:
                filter_dict = {"category": category_filter_str} if category_filter_str else None
                resp = self.index.query(
                    vector=query_vector,
                    top_k=request.top_k,
                    include_metadata=True,
                    namespace="health_insurance",
                    filter=filter_dict
                )
                matches_data = resp.get("matches", [])
            except Exception as e:
                print(f"[WARNING] Pinecone live query error: {e}. Switching to offline local vector search.")
                matches_data = []

        # 3. Fallback to offline local vector store if Cloud failed or empty
        if not matches_data:
            matches_data = self._search_local_fallback(query_vector, request.top_k, category_filter_str)

        # 4. Filter by minimum confidence score and construct output results
        results: List[KBQueryResult] = []
        for m in matches_data:
            score = round(float(m["score"]), 4)
            if score < request.min_score:
                continue

            match_id = m["id"]
            metadata = m.get("metadata", {})
            record = self._reconstruct_record(match_id, metadata)
            if not record:
                continue

            # Generate formal citation string
            source_desc = f"{record.source.value}"
            if record.source_url:
                source_desc += f" ({record.source_url})"
            citation = f"Policy Document: '{record.title}' | Category: {record.category.value} | Source: {source_desc} | Version: {record.version}"

            results.append(KBQueryResult(
                record=record,
                score=score,
                citation=citation
            ))

        print(f"[RETRIEVER] Query: '{request.question}' -> Found {len(results)} qualifying chunks (min_score={request.min_score})")
        return results

    def format_context_for_rag(self, results: List[KBQueryResult]) -> str:
        """
        Format retrieved passages into a strictly structured prompt block
        for voice agent LLM (Groq/Llama-3) consumption.
        """
        if not results:
            return "NO RELEVANT POLICY DOCUMENTATION FOUND. INSTRUCT AGENT TO OFFER SPECIALIST TRANSFER."

        sections = []
        for idx, res in enumerate(results, 1):
            sec = (
                f"--- [RELEVANT POLICY EXCERPT #{idx} | Confidence Score: {res.score}] ---\n"
                f"CITATION: {res.citation}\n"
                f"CONTENT:\n{res.record.content}\n"
            )
            sections.append(sec)

        return "\n".join(sections)


if __name__ == "__main__":
    retriever = HybridRetriever()
    test_req = KBQueryRequest(
        question="What is the difference in deductibles between Bronze and Silver plans?",
        top_k=3,
        min_score=0.25
    )
    res = retriever.query(test_req)
    print("\nFormatted RAG Context Output:")
    print(retriever.format_context_for_rag(res))
