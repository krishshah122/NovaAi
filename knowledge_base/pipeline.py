"""
Knowledge Base Data Pipeline Orchestrator
Connects collection, cleaning, semantic chunking, embedding generation, and vector indexing
into an automated, reproducible workflow.
"""

import sys
import io
import json
import time
from pathlib import Path
from typing import List, Dict

# Ensure UTF-8 stdout encoding on Windows consoles to prevent UnicodeEncodeError
if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Ensure repository root is available in Python path when executed directly
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from knowledge_base.scraper import load_curated_content, HealthInsuranceScraper
from knowledge_base.cleaner import DataCleaner
from knowledge_base.chunker import SemanticChunker
from knowledge_base.embedder import VectorEmbedder
from knowledge_base.indexer import PineconeIndexer
from knowledge_base.schema import KBRecord


class KBPipeline:
    """
    End-to-End processing pipeline for unstructured and curated business content.
    Transforms raw text into searchable, traceable vector embeddings for production RAG and Voice Agents.
    """

    def __init__(self, processed_dir: str = "knowledge_base/data/processed"):
        self.processed_dir = Path(processed_dir)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

        self.cleaner = DataCleaner()
        self.chunker = SemanticChunker(target_chunk_tokens=300, overlap_tokens=50)
        self.embedder = VectorEmbedder()
        self.indexer = PineconeIndexer()

    def run(self, include_live_scrape: bool = False) -> List[KBRecord]:
        """
        Execute full knowledge base ingestion pipeline.
        
        Args:
            include_live_scrape: Whether to actively scrape public government URLs before processing.
        """
        start_time = time.time()
        print("\n" + "=" * 65)
        print("[START] STARTING PRODUCTION KNOWLEDGE BASE INGESTION PIPELINE")
        print("=" * 65)

        # ---------------------------------------------------------
        # PHASE 1: Data Collection & Extraction
        # ---------------------------------------------------------
        print("\n[PHASE 1] Data Collection & Extraction...")
        raw_records: List[Dict] = load_curated_content()

        if include_live_scrape:
            print("[INFO] Executing live scraper for public domain US Government sources...")
            scraper = HealthInsuranceScraper()
            scraped = scraper.scrape_all()
            raw_records.extend(scraped)
        
        print(f"[OK] Total input source documents gathered: {len(raw_records)}")
        if not raw_records:
            print("[ERROR] No input content detected. Halting pipeline.")
            return []

        # ---------------------------------------------------------
        # PHASE 2: Data Cleaning & PII Protection
        # ---------------------------------------------------------
        print("\n[PHASE 2] Data Cleaning & PII Protection...")
        cleaned_records = self.cleaner.process(raw_records)
        
        # ---------------------------------------------------------
        # PHASE 3: Semantic Chunking & Schema Validation
        # ---------------------------------------------------------
        print("\n[PHASE 3] Semantic Chunking & Pydantic Schema Validation...")
        validated_records: List[KBRecord] = self.chunker.process(cleaned_records)

        # Persist intermediate clean record structures
        records_dump_path = self.processed_dir / "kb_records.json"
        with open(records_dump_path, "w", encoding="utf-8") as f:
            json.dump([r.model_dump() for r in validated_records], f, indent=2, ensure_ascii=False)
        print(f"[SAVE] Structured schema records saved to: {records_dump_path}")

        # ---------------------------------------------------------
        # PHASE 4: Local 384-Dim Vector Embedding Generation
        # ---------------------------------------------------------
        print("\n[PHASE 4] Local 384-Dim Vector Embedding Generation...")
        vector_payloads = self.embedder.embed_records(validated_records)

        # ---------------------------------------------------------
        # PHASE 5: Serverless Index Ingestion & Caching
        # ---------------------------------------------------------
        print("\n[PHASE 5] Serverless Index Ingestion & Offline Backup...")
        indexed_count = self.indexer.index_vectors(vector_payloads)

        elapsed = round(time.time() - start_time, 2)
        print("\n" + "=" * 65)
        print(f"[DONE] PIPELINE EXECUTION COMPLETE in {elapsed}s!")
        print(f"       Processed Documents: {len(raw_records)} -> Unique Vectors: {len(vector_payloads)}")
        print(f"       Indexed Vectors:     {indexed_count}")
        print("=" * 65 + "\n")

        return validated_records


if __name__ == "__main__":
    # Allow optional flag `--scrape` from command line
    scrape_arg = "--scrape" in sys.argv
    pipeline = KBPipeline()
    pipeline.run(include_live_scrape=scrape_arg)
