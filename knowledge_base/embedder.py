"""
Vector Embedder
Generates 384-dimensional embeddings locally using sentence-transformers/all-MiniLM-L6-v2.
Formats output vectors and sanitized metadata for serverless vector DB ingestion.
"""

from typing import List, Dict, Any
from knowledge_base.schema import KBRecord

try:
    from fastembed import TextEmbedding
    EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
except ImportError:
    TextEmbedding = None
    EMBEDDING_MODEL_NAME = "mock"


class VectorEmbedder:
    """
    Handles local embedding generation for knowledge base records without external API fees or latency.
    Produces vectors compatible with Pinecone Serverless indices (dim=384, metric=cosine).
    """

    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME, batch_size: int = 32):
        self.model_name = model_name
        self.batch_size = batch_size
        self.model = None

    def _load_model(self):
        """Lazy loader for ONNX embedding model to avoid startup memory spikes. Consumes only ~150MB RAM."""
        if self.model is None and TextEmbedding is not None:
            print(f"[EMBED] Loading fastembed model '{self.model_name}'...")
            self.model = TextEmbedding(model_name=self.model_name)
            print("[EMBED] Model successfully initialized.")
        elif TextEmbedding is None:
            print("[WARNING] fastembed not installed. Fallback to zero-vector mock embeddings.")

    def sanitize_metadata(self, record: KBRecord) -> Dict[str, Any]:
        """
        Convert KBRecord properties into Pinecone-compliant metadata types:
        strings, numbers, booleans, or lists of strings. Excludes None values.
        """
        raw_dict = record.model_dump()
        clean_meta = {}
        for k, v in raw_dict.items():
            if v is None:
                continue
            # Enum conversion
            if hasattr(v, "value"):
                clean_meta[k] = str(v.value)
            elif isinstance(v, (str, int, float, bool)):
                clean_meta[k] = v
            elif isinstance(v, list):
                clean_meta[k] = [str(x) for x in v if x is not None]
            else:
                clean_meta[k] = str(v)
        return clean_meta

    def embed_records(self, records: List[KBRecord]) -> List[Dict[str, Any]]:
        """
        Embed content texts in batches and format for Vector DB indexing.
        Returns a list of payload dicts containing: 'id', 'values', 'metadata'.
        """
        if not records:
            return []

        self._load_model()
        texts = [rec.content for rec in records]
        
        print(f"[EMBED] Generating vector embeddings for {len(records)} records...")
        
        if self.model:
            # Generate real 384-dimensional embeddings (TextEmbedding.embed returns a generator of numpy arrays)
            vectors_generator = self.model.embed(texts)
            embeddings_list = [v.tolist() for v in vectors_generator]
        else:
            # Fallback 384-dimensional zero-vector for testing environments without fastembed
            embeddings_list = [[0.0] * 384 for _ in texts]
            
        payloads = []
        for idx, record in enumerate(records):
            payloads.append({
                "id": record.record_id,
                "values": embeddings_list[idx],
                "metadata": self.sanitize_metadata(record)
            })

        print(f"[EMBED] Summary: Generated 384-dim vector representations for {len(payloads)} chunks.")
        return payloads


if __name__ == "__main__":
    from knowledge_base.schema import KBRecord, KBCategory, KBSource
    test_rec = KBRecord(
        record_id="test_embed",
        title="Bronze Plan Cost Analysis",
        content="Bronze plans feature lower premiums accompanied by higher deductibles.",
        category=KBCategory.COSTS_PRICING,
        source=KBSource.HEALTHCARE_GOV
    )
    embedder = VectorEmbedder()
    payload = embedder.embed_records([test_rec])
    print("Payload generated successfully. Vector len:", len(payload[0]["values"]), "Metadata keys:", payload[0]["metadata"].keys())
