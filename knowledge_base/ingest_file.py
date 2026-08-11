"""
Universal File Ingestor for Knowledge Base
Accepts PDF, TXT, or JSON files and automatically converts them into
curated_content.json schema entries for the RAG pipeline.

Usage:
    python knowledge_base/ingest_file.py <file_path> [--category <category>] [--source <label>]

Examples:
    python knowledge_base/ingest_file.py docs/policy_handbook.pdf
    python knowledge_base/ingest_file.py notes.txt --category coverage
    python knowledge_base/ingest_file.py extra_plans.json
"""

import sys
import io
import json
import re
import os
import uuid
import argparse
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# Ensure UTF-8 stdout on Windows
if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Ensure project root is in path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


CURATED_PATH = Path(__file__).resolve().parent / "data" / "raw" / "curated_content.json"

# Valid categories from schema.py KBCategory enum
VALID_CATEGORIES = [
    "product_plans", "eligibility", "coverage", "costs_pricing", "claims",
    "enrollment", "faq", "objection_handling", "qualification_rules",
    "compliance", "glossary", "preventive_care", "network_providers"
]


def extract_text_from_pdf(filepath: Path) -> str:
    """Extract all text from a PDF file, including table content."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("[ERROR] PyMuPDF is not installed. Run: pip install PyMuPDF")
        sys.exit(1)

    doc = fitz.open(str(filepath))
    all_text = []

    for page_num, page in enumerate(doc, start=1):
        # Extract regular text
        text = page.get_text("text")
        if text.strip():
            all_text.append(text.strip())

        # Extract tables if present
        try:
            tables = page.find_tables()
            for table in tables:
                extracted = table.extract()
                if extracted:
                    # Convert table rows into readable text
                    for row in extracted:
                        clean_row = [str(cell).strip() if cell else "" for cell in row]
                        if any(clean_row):
                            all_text.append(" | ".join(clean_row))
        except Exception:
            pass  # Some pages may not have tables

    doc.close()
    return "\n\n".join(all_text)


def extract_text_from_txt(filepath: Path) -> str:
    """Read plain text file."""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return f.read().strip()


def load_json_records(filepath: Path) -> List[Dict]:
    """
    Load JSON file. Supports two formats:
    1. A list of objects with at least 'content' or 'text' field
    2. A single object with 'content' or 'text' field
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        return [data]
    else:
        print(f"[ERROR] Unsupported JSON structure in {filepath}")
        return []


def generate_title_from_content(content: str, max_len: int = 80) -> str:
    """Auto-generate a title from the first meaningful line of content."""
    lines = content.strip().split("\n")
    for line in lines:
        clean = line.strip().lstrip("#•-* ")
        if len(clean) >= 10:
            return clean[:max_len]
    return f"Ingested Document {uuid.uuid4().hex[:6]}"


def generate_tags_from_content(content: str) -> List[str]:
    """Auto-extract simple keyword tags from content."""
    # Common insurance keywords to look for
    keywords = [
        "premium", "deductible", "copay", "coinsurance", "coverage", "plan",
        "bronze", "silver", "gold", "platinum", "medicaid", "medicare",
        "enrollment", "subsidy", "eligibility", "claims", "network",
        "prescription", "emergency", "preventive", "ACA", "marketplace",
        "family", "individual", "out-of-pocket", "HSA", "HMO", "PPO"
    ]
    content_lower = content.lower()
    found = [kw for kw in keywords if kw.lower() in content_lower]
    return found[:8]  # Limit to 8 tags


def auto_detect_category(content: str) -> str:
    """Try to auto-detect the best category from content keywords."""
    content_lower = content.lower()
    category_signals = {
        "product_plans": ["plan", "bronze", "silver", "gold", "platinum", "hmo", "ppo"],
        "eligibility": ["eligible", "eligibility", "qualify", "qualifying", "enrollment period"],
        "coverage": ["coverage", "covered", "benefits", "essential health"],
        "costs_pricing": ["premium", "deductible", "copay", "coinsurance", "cost", "price", "pricing"],
        "claims": ["claim", "denied", "appeal", "reimbursement"],
        "enrollment": ["enroll", "sign up", "open enrollment", "marketplace", "application"],
        "faq": ["frequently asked", "faq", "question", "answer"],
        "objection_handling": ["objection", "too expensive", "don't need", "healthy"],
        "compliance": ["compliance", "hipaa", "regulation", "legal", "law"],
        "glossary": ["glossary", "definition", "term", "means"],
        "preventive_care": ["preventive", "screening", "vaccine", "wellness", "checkup"],
        "network_providers": ["network", "provider", "doctor", "hospital", "in-network"],
    }

    scores = {}
    for cat, signals in category_signals.items():
        scores[cat] = sum(1 for s in signals if s in content_lower)

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "faq"


def convert_to_curated_entry(
    content: str,
    title: str = None,
    category: str = None,
    source_label: str = "manual_entry",
    source_file: str = None,
    tags: List[str] = None,
    record_id: str = None
) -> Dict:
    """Convert extracted text into a curated_content.json compatible entry."""

    if not title:
        title = generate_title_from_content(content)
    if not category:
        category = auto_detect_category(content)
    if not tags:
        tags = generate_tags_from_content(content)
    if not record_id:
        record_id = f"ingested_{uuid.uuid4().hex[:8]}"

    return {
        "id": record_id,
        "title": title,
        "content": content,
        "category": category,
        "source": source_label,
        "source_url": source_file or "uploaded_file",
        "tags": tags
    }


def append_to_curated(new_entries: List[Dict]) -> int:
    """Append new entries to curated_content.json."""
    existing = []
    if CURATED_PATH.exists():
        with open(CURATED_PATH, "r", encoding="utf-8") as f:
            existing = json.load(f)

    # Check for duplicate IDs
    existing_ids = {entry.get("id") for entry in existing}
    added = 0
    for entry in new_entries:
        if entry["id"] in existing_ids:
            print(f"  ⚠ Skipping duplicate ID: {entry['id']}")
            continue
        existing.append(entry)
        existing_ids.add(entry["id"])
        added += 1

    with open(CURATED_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    return added


def ingest_file(filepath: str, category: str = None, source_label: str = None) -> int:
    """
    Main ingestion function. Accepts a file path and converts it into
    curated_content.json entries.

    Returns the number of new entries added.
    """
    path = Path(filepath).resolve()
    if not path.exists():
        print(f"[ERROR] File not found: {path}")
        return 0

    ext = path.suffix.lower()
    filename = path.name
    src = source_label or "manual_entry"

    print(f"\n{'=' * 60}")
    print(f"[INGEST] Processing: {filename}")
    print(f"         Type: {ext.upper()} | Source: {src}")
    print(f"{'=' * 60}")

    new_entries = []

    # ── PDF ──
    if ext == ".pdf":
        content = extract_text_from_pdf(path)
        if not content or len(content) < 20:
            print("[ERROR] No readable text extracted from PDF.")
            return 0
        print(f"  📄 Extracted {len(content)} characters from PDF ({path.stat().st_size // 1024} KB)")

        # Split very long PDFs into separate entries per ~2000 chars
        if len(content) > 3000:
            chunks = split_into_sections(content, max_chars=2000)
            for i, chunk in enumerate(chunks):
                entry = convert_to_curated_entry(
                    content=chunk,
                    category=category,
                    source_label=src,
                    source_file=filename,
                    record_id=f"pdf_{path.stem}_{i}"
                )
                entry["title"] = f"{generate_title_from_content(chunk)} (Section {i+1})"
                new_entries.append(entry)
            print(f"  📑 Split into {len(chunks)} sections for optimal RAG chunking")
        else:
            new_entries.append(convert_to_curated_entry(
                content=content,
                category=category,
                source_label=src,
                source_file=filename,
                record_id=f"pdf_{path.stem}"
            ))

    # ── TXT ──
    elif ext == ".txt":
        content = extract_text_from_txt(path)
        if not content or len(content) < 20:
            print("[ERROR] TXT file is empty or too short.")
            return 0
        print(f"  📝 Read {len(content)} characters from TXT file")

        if len(content) > 3000:
            chunks = split_into_sections(content, max_chars=2000)
            for i, chunk in enumerate(chunks):
                entry = convert_to_curated_entry(
                    content=chunk,
                    category=category,
                    source_label=src,
                    source_file=filename,
                    record_id=f"txt_{path.stem}_{i}"
                )
                entry["title"] = f"{generate_title_from_content(chunk)} (Section {i+1})"
                new_entries.append(entry)
            print(f"  📑 Split into {len(chunks)} sections")
        else:
            new_entries.append(convert_to_curated_entry(
                content=content,
                category=category,
                source_label=src,
                source_file=filename,
                record_id=f"txt_{path.stem}"
            ))

    # ── JSON ──
    elif ext == ".json":
        records = load_json_records(path)
        print(f"  📦 Loaded {len(records)} records from JSON")

        for i, record in enumerate(records):
            # Support multiple content field names
            content = (
                record.get("content") or
                record.get("text") or
                record.get("body") or
                record.get("description") or
                ""
            )
            if not content or len(content) < 20:
                print(f"  ⚠ Skipping record {i}: no usable content field found")
                continue

            title = record.get("title") or record.get("name") or None
            cat = category or record.get("category") or None
            tags = record.get("tags") or None
            rid = record.get("id") or f"json_{path.stem}_{i}"

            new_entries.append(convert_to_curated_entry(
                content=content,
                title=title,
                category=cat,
                source_label=src,
                source_file=filename,
                tags=tags,
                record_id=rid
            ))

    else:
        print(f"[ERROR] Unsupported file type: {ext}")
        print(f"        Supported: .pdf, .txt, .json")
        return 0

    if not new_entries:
        print("[WARNING] No valid entries were generated from the file.")
        return 0

    # Append to curated_content.json
    added = append_to_curated(new_entries)

    print(f"\n{'=' * 60}")
    print(f"[DONE] Successfully added {added} new entries to curated_content.json")
    print(f"       Total entries now: {len(json.load(open(CURATED_PATH, 'r', encoding='utf-8')))}")
    print(f"\n💡 Next step: Run the pipeline to push these to Pinecone:")
    print(f"   python knowledge_base/pipeline.py")
    print(f"{'=' * 60}\n")

    return added


def split_into_sections(text: str, max_chars: int = 2000) -> List[str]:
    """Split long text into sections, preferring to break at paragraph boundaries."""
    paragraphs = re.split(r'\n\s*\n', text)
    sections = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current) + len(para) + 2 > max_chars and current:
            sections.append(current.strip())
            current = para
        else:
            current += "\n\n" + para if current else para

    if current.strip():
        sections.append(current.strip())

    return sections


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest PDF, TXT, or JSON files into the Knowledge Base"
    )
    parser.add_argument("file", help="Path to the file to ingest (.pdf, .txt, or .json)")
    parser.add_argument(
        "--category", "-c",
        choices=VALID_CATEGORIES,
        default=None,
        help="Force a specific category (auto-detected if not provided)"
    )
    parser.add_argument(
        "--source", "-s",
        default="manual_entry",
        help="Source label for traceability (e.g., 'internal_handbook', 'partner_doc')"
    )

    args = parser.parse_args()
    ingest_file(args.file, category=args.category, source_label=args.source)
