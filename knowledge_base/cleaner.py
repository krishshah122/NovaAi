"""
Data Cleaner & PII Redactor
Standardizes text, redacts Personally Identifiable Information (PII), and eliminates near-duplicate content.
"""

import re
import hashlib
from typing import List, Dict, Set, Tuple


class DataCleaner:
    """
    Cleans raw knowledge base items by:
    1. Standardizing text and normalizing whitespace.
    2. Detecting and redacting PII (phone numbers, emails, SSN, credit cards).
    3. Removing duplicate or near-duplicate items.
    """

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self.seen_hashes: Set[str] = set()
        self.seen_texts: List[str] = []

        # Regular expressions for PII detection
        self.pii_patterns: Dict[str, re.Pattern] = {
            "EMAIL": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'),
            "PHONE": re.compile(r'\b(?:\+?1[-. ]?)?\(?([0-9]{3})\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})\b'),
            "SSN": re.compile(r'\b\d{3}[- ]?\d{2}[- ]?\d{4}\b'),
            "CREDIT_CARD": re.compile(r'\b(?:\d[ -]*?){13,16}\b')
        }

    def normalize_text(self, text: str) -> str:
        """Standardize terminology and collapse redundant whitespace."""
        if not text:
            return ""
        
        # Standardize inconsistent terms if applicable
        replacements = {
            r"\b[A-a]ffordable [C-c]are [A-a]ct\b": "Affordable Care Act (ACA)",
            r"\b[E-e]ssential [H-h]ealth [B-b]enefit[s]?\b": "Essential Health Benefits (EHB)"
        }
        for pat, replacement in replacements.items():
            text = re.sub(pat, replacement, text)

        # Normalize linebreaks and spacing
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()

    def redact_pii(self, text: str) -> Tuple[str, bool]:
        """
        Scan text for PII patterns and replace matches with [PII_REDACTED_<TYPE>].
        Returns (redacted_text, had_pii).
        """
        if not text:
            return text, False

        had_pii = False
        redacted_text = text

        for pii_type, pattern in self.pii_patterns.items():
            matches = pattern.findall(redacted_text)
            if matches:
                # To avoid false positives on simple numbers like years (e.g. 2024), double check credit card lengths
                if pii_type == "CREDIT_CARD":
                    valid_cc_matches = []
                    for match in matches:
                        clean_num = re.sub(r'[^0-9]', '', str(match))
                        if len(clean_num) >= 13 and len(clean_num) <= 16:
                            valid_cc_matches.append(match)
                    if not valid_cc_matches:
                        continue

                had_pii = True
                redacted_text = pattern.sub(f"[PII_REDACTED_{pii_type}]", redacted_text)

        return redacted_text, had_pii

    def _compute_jaccard_similarity(self, text1: str, text2: str) -> float:
        """Compute approximate text similarity using Jaccard index over words."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        return len(intersection) / len(union)

    def is_duplicate(self, text: str) -> bool:
        """Check for exact matches via MD5 hash or near-duplicates via Jaccard similarity."""
        if not text:
            return True

        # Exact hash duplicate check
        text_hash = hashlib.md5(text.strip().lower().encode('utf-8')).hexdigest()
        if text_hash in self.seen_hashes:
            return True
        
        # Near-duplicate check against existing corpus
        for existing_text in self.seen_texts:
            if self._compute_jaccard_similarity(text, existing_text) >= self.similarity_threshold:
                return True

        self.seen_hashes.add(text_hash)
        self.seen_texts.append(text)
        return False

    def process(self, records: List[Dict]) -> List[Dict]:
        """
        Run full cleaning pipeline across all incoming record dictionaries.
        """
        cleaned_records = []
        dupes_removed = 0
        pii_flagged = 0

        for record in records:
            raw_content = record.get("content", "")
            if not raw_content:
                continue

            # 1. Normalize & Standardize
            norm_content = self.normalize_text(raw_content)
            norm_title = self.normalize_text(record.get("title", "Untitled Record"))

            # 2. Duplicate detection
            if self.is_duplicate(norm_content):
                dupes_removed += 1
                continue

            # 3. PII Redaction
            safe_content, content_has_pii = self.redact_pii(norm_content)
            safe_title, title_has_pii = self.redact_pii(norm_title)
            
            has_pii = content_has_pii or title_has_pii or record.get("pii_flag", False)
            if has_pii:
                pii_flagged += 1

            # Update record structure
            cleaned_record = dict(record)
            cleaned_record["title"] = safe_title
            cleaned_record["content"] = safe_content
            cleaned_record["pii_flag"] = has_pii
            cleaned_records.append(cleaned_record)

        print(f"[CLEANER] Processed {len(records)} raw items -> {len(cleaned_records)} unique valid records.")
        print(f"[CLEANER] Removed Duplicates: {dupes_removed} | Flagged/Redacted PII: {pii_flagged}")
        return cleaned_records


if __name__ == "__main__":
    # Test execution on simple sample
    sample_data = [
        {"id": "1", "title": "John Doe Policy", "content": "My phone is 800-555-0199 and email is john.doe@example.com for my Gold plan.", "source": "manual_entry", "category": "product_plans"},
        {"id": "2", "title": "John Doe Policy Duplicate", "content": "My phone is 800-555-0199 and email is john.doe@example.com for my Gold plan.", "source": "manual_entry", "category": "product_plans"}
    ]
    cleaner = DataCleaner()
    results = cleaner.process(sample_data)
    print("Sample cleaned record:", results[0])
