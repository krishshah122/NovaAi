"""
Semantic Chunker & Schema Validator
Splits large text content into semantically meaningful 200-400 token chunks with overlap,
and validates all items against the production KBRecord Pydantic schema.
"""

import re
from typing import List, Dict, Optional
try:
    import tiktoken
    ENCODER = tiktoken.get_encoding("cl100k_base")
except ImportError:
    ENCODER = None

from knowledge_base.schema import KBRecord, KBCategory, KBSource


class SemanticChunker:
    """
    Chunks textual knowledge base records while preserving context and metadata.
    Ensures every resulting chunk is a validated KBRecord object.
    """

    def __init__(self, target_chunk_tokens: int = 300, overlap_tokens: int = 50):
        self.target_tokens = target_chunk_tokens
        self.overlap_tokens = overlap_tokens

    def count_tokens(self, text: str) -> int:
        """Calculate exact token count via tiktoken, with approximation fallback."""
        if not text:
            return 0
        if ENCODER:
            return len(ENCODER.encode(text))
        # Fallback: approximation (approx 4 chars or 0.75 words per token)
        return len(text.split()) * 4 // 3

    def split_into_paragraphs(self, text: str) -> List[str]:
        """Split text by natural paragraph or section boundaries."""
        # Split by double linebreaks or bullet lists
        paragraphs = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]
        if not paragraphs and text.strip():
            paragraphs = [text.strip()]
        return paragraphs

    def chunk_text(self, text: str) -> List[str]:
        """
        Group paragraphs into target chunk lengths with specified token overlap.
        If a single paragraph exceeds target tokens, split by sentence boundaries.
        """
        if not text:
            return []

        total_tokens = self.count_tokens(text)
        if total_tokens <= self.target_tokens:
            return [text]

        paragraphs = self.split_into_paragraphs(text)
        chunks: List[str] = []
        current_chunk: List[str] = []
        current_tokens: int = 0

        for para in paragraphs:
            para_tokens = self.count_tokens(para)
            
            # If a single paragraph exceeds target size, break it down by sentences
            if para_tokens > self.target_tokens:
                sentences = [s.strip() + "." for s in para.split(".") if s.strip()]
                for sent in sentences:
                    sent_tokens = self.count_tokens(sent)
                    if current_tokens + sent_tokens > self.target_tokens and current_chunk:
                        chunks.append("\n\n".join(current_chunk))
                        # Keep overlap from the tail of current_chunk
                        current_chunk, current_tokens = self._extract_overlap(current_chunk)
                    current_chunk.append(sent)
                    current_tokens += sent_tokens
                continue

            if current_tokens + para_tokens > self.target_tokens and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk, current_tokens = self._extract_overlap(current_chunk)

            current_chunk.append(para)
            current_tokens += para_tokens

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks

    def _extract_overlap(self, chunk_paragraphs: List[str]) -> tuple[List[str], int]:
        """Retain tail paragraphs to fulfill token overlap requirement."""
        overlap_list = []
        overlap_tokens = 0
        for p in reversed(chunk_paragraphs):
            p_tokens = self.count_tokens(p)
            if overlap_tokens + p_tokens <= self.overlap_tokens:
                overlap_list.insert(0, p)
                overlap_tokens += p_tokens
            else:
                break
        return overlap_list, overlap_tokens

    def _safe_map_enum(self, enum_cls, value, default):
        """Helper to gracefully match string inputs to Pydantic Enums."""
        if value is None:
            return default
        try:
            return enum_cls(str(value).lower())
        except ValueError:
            # Fallback matching by substring
            val_str = str(value).lower()
            for item in enum_cls:
                if val_str in item.value or item.value in val_str:
                    return item
            return default

    def process(self, records: List[Dict]) -> List[KBRecord]:
        """
        Take cleaned dictionary records, apply chunking if content is large,
        and validate into KBRecord Pydantic models.
        """
        validated_records: List[KBRecord] = []

        for item in records:
            raw_id = item.get("id") or item.get("record_id") or "kb_item"
            title = item.get("title", "Health Insurance Knowledge")
            content = item.get("content", "")
            category = self._safe_map_enum(KBCategory, item.get("category"), KBCategory.FAQ)
            source = self._safe_map_enum(KBSource, item.get("source"), KBSource.MANUAL_ENTRY)
            
            tags = item.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]

            chunks = self.chunk_text(content)
            if not chunks:
                continue

            # If it remained as 1 chunk, create single record without chunk index
            if len(chunks) == 1:
                rec = KBRecord(
                    record_id=raw_id if not str(raw_id).startswith("kb_") else raw_id,
                    title=title,
                    content=chunks[0],
                    category=category,
                    subcategory=item.get("subcategory"),
                    source=source,
                    source_url=item.get("source_url"),
                    version=str(item.get("version", "1.0")),
                    pii_flag=bool(item.get("pii_flag", False)),
                    tags=tags,
                    chunk_index=None,
                    parent_id=None
                )
                validated_records.append(rec)
            else:
                # Create parent-child relationship across generated chunks
                for idx, chunk_str in enumerate(chunks, 1):
                    rec = KBRecord(
                        record_id=f"{raw_id}_c{idx}",
                        title=f"{title} (Part {idx})",
                        content=chunk_str,
                        category=category,
                        subcategory=item.get("subcategory"),
                        source=source,
                        source_url=item.get("source_url"),
                        version=str(item.get("version", "1.0")),
                        pii_flag=bool(item.get("pii_flag", False)),
                        tags=tags,
                        chunk_index=idx,
                        parent_id=raw_id
                    )
                    validated_records.append(rec)

        print(f"[CHUNKER] Converted {len(records)} items into {len(validated_records)} validated KBRecord chunks.")
        return validated_records


if __name__ == "__main__":
    from knowledge_base.schema import KBCategory, KBSource
    sample_data = [{
        "id": "test_001",
        "title": "Extended Deductibles Explanation",
        "content": ("Deductibles represent your out-of-pocket obligation before insurance kicks in.\n\n" * 15),
        "category": "costs_pricing",
        "source": "healthcare.gov"
    }]
    chunker = SemanticChunker(target_chunk_tokens=50, overlap_tokens=15)
    records = chunker.process(sample_data)
    for r in records:
        print(f"ID: {r.record_id} | Index: {r.chunk_index} | Parent: {r.parent_id} | Tokens: {chunker.count_tokens(r.content)}")
