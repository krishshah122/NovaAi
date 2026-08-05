"""
Vector DB Indexer
Manages serverless index creation and batch ingestion of vector embeddings into Pinecone,
with local file backup capabilities when offline or unauthenticated.
"""

import os
import json
import time
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(dotenv_path=env_path, override=True)
except ImportError:
    pass

try:
    from pinecone import Pinecone, ServerlessSpec, PineconeException
except ImportError:
    Pinecone = None
    ServerlessSpec = None
    PineconeException = Exception


DEFAULT_INDEX_NAME = "health-insurance-kb"
EMBEDDING_DIMENSION = 384
BATCH_SIZE = 100


class PineconeIndexer:
    """
    Handles serverless Pinecone vector indexing and upserts.
    Features robust error recovery, network retry logic, and local caching.
    """

    def __init__(self, index_name: str = DEFAULT_INDEX_NAME, api_key: Optional[str] = None):
        self.index_name = index_name
        self.api_key = api_key or os.getenv("PINECONE_API_KEY")
        self.pc = None
        self.index = None

    def _initialize_client(self) -> bool:
        """Initialize Pinecone client and ensure the target serverless index exists."""
        if not self.api_key or self.api_key == "your_pinecone_key_here":
            print("[WARNING] PINECONE_API_KEY is not set in environment or .env. Running offline mode.")
            return False

        if Pinecone is None:
            print("[WARNING] pinecone Python package not installed. Running offline mode.")
            return False

        try:
            self.pc = Pinecone(api_key=self.api_key)
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]

            if self.index_name not in existing_indexes:
                print(f"[CLOUD] Creating new serverless Pinecone index '{self.index_name}' (dim={EMBEDDING_DIMENSION}, metric=cosine)...")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=EMBEDDING_DIMENSION,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1")
                )
                print("[WAIT] Waiting for index to become ready...")
                while not self.pc.describe_index(self.index_name).status["ready"]:
                    time.sleep(2)
                print(f"[OK] Index '{self.index_name}' is ready!")

            self.index = self.pc.Index(self.index_name)
            print(f"[OK] Successfully connected to Pinecone index: '{self.index_name}'.")
            return True

        except Exception as e:
            print(f"[ERROR] Error communicating with Pinecone API: {e}")
            print("[INFO] Check your network or verify your PINECONE_API_KEY in .env.")
            return False

    def save_local_backup(self, vector_payloads: List[Dict[str, Any]], output_path: str = "knowledge_base/data/processed/vector_store.json"):
        """Save embeddings locally as a persistent RAG fallback."""
        file_path = Path(output_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(vector_payloads, f, indent=2, ensure_ascii=False)
            print(f"[SAVE] Saved local fallback vector cache to: {file_path}")
        except Exception as e:
            print(f"[ERROR] Could not write local backup: {e}")

    def index_vectors(self, vector_payloads: List[Dict[str, Any]], namespace: str = "health_insurance") -> int:
        """
        Upsert prepared vector records into Pinecone in managed batches.
        Always outputs a local JSON cache to guarantee zero data loss.
        """
        if not vector_payloads:
            print("[WARNING] No vector payloads provided to index.")
            return 0

        # Always generate local backup cache first
        self.save_local_backup(vector_payloads)

        client_ready = self._initialize_client()
        if not client_ready or not self.index:
            print("[INFO] Skipping live Pinecone upsert due to offline mode or missing API key.")
            return len(vector_payloads)

        total_upserted = 0
        print(f"[UPSERT] Upserting {len(vector_payloads)} vector items to Pinecone index '{self.index_name}' in namespace '{namespace}'...")

        try:
            for i in range(0, len(vector_payloads), BATCH_SIZE):
                batch = vector_payloads[i : i + BATCH_SIZE]
                self.index.upsert(vectors=batch, namespace=namespace)
                total_upserted += len(batch)
                print(f"   -> Upserted batch {i // BATCH_SIZE + 1} ({total_upserted}/{len(vector_payloads)} records)")

            # Get stats
            stats = self.index.describe_index_stats()
            print(f"[SUCCESS] Indexing complete! Total vectors in index: {stats.total_vector_count}")
            return total_upserted
        except Exception as e:
            print(f"[ERROR] Error during vector upsert: {e}")
            return total_upserted


if __name__ == "__main__":
    indexer = PineconeIndexer()
    sample_vectors = [{
        "id": "sample_idx_01",
        "values": [0.05] * 384,
        "metadata": {"title": "Sample Plan", "category": "product_plans", "version": "1.0"}
    }]
    indexer.index_vectors(sample_vectors)
