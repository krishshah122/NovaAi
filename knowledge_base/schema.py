"""
Knowledge Base Record Schema
Defines the structure for all KB records with validation, metadata, and taxonomy.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid


class KBCategory(str, Enum):
    """Product/policy taxonomy categories."""
    PRODUCT_PLANS = "product_plans"
    ELIGIBILITY = "eligibility"
    COVERAGE = "coverage"
    COSTS_PRICING = "costs_pricing"
    CLAIMS = "claims"
    ENROLLMENT = "enrollment"
    FAQ = "faq"
    OBJECTION_HANDLING = "objection_handling"
    QUALIFICATION_RULES = "qualification_rules"
    COMPLIANCE = "compliance"
    GLOSSARY = "glossary"
    PREVENTIVE_CARE = "preventive_care"
    NETWORK_PROVIDERS = "network_providers"


class KBSource(str, Enum):
    """Data source tracking — US Government public domain sources only."""
    HEALTHCARE_GOV = "healthcare.gov"
    MEDICARE_GOV = "medicare.gov"
    CMS_GOV = "cms.gov"
    NAIC = "naic.org"
    MANUAL_ENTRY = "manual_entry"


class KBRecord(BaseModel):
    """
    Single knowledge base record.
    
    Schema matches the assessment requirement:
    record_id, title, content, category, source, version, pii_flag
    """
    record_id: str = Field(
        default_factory=lambda: f"kb_{uuid.uuid4().hex[:8]}",
        description="Unique identifier for this KB record"
    )
    title: str = Field(
        ...,
        min_length=5,
        max_length=200,
        description="Descriptive title for the record"
    )
    content: str = Field(
        ...,
        min_length=10,
        description="The actual knowledge content"
    )
    category: KBCategory = Field(
        ...,
        description="Primary category from the taxonomy"
    )
    subcategory: Optional[str] = Field(
        default=None,
        description="Optional subcategory for finer classification"
    )
    source: KBSource = Field(
        ...,
        description="Where this data was sourced from"
    )
    source_url: Optional[str] = Field(
        default=None,
        description="Original URL of the source"
    )
    version: str = Field(
        default="1.0",
        description="Version of this record"
    )
    pii_flag: bool = Field(
        default=False,
        description="Whether this record contains or had PII (redacted)"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Searchable tags for retrieval"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO timestamp of record creation"
    )
    chunk_index: Optional[int] = Field(
        default=None,
        description="If chunked, the index of this chunk from the parent"
    )
    parent_id: Optional[str] = Field(
        default=None,
        description="If chunked, reference to the parent record"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "record_id": "kb_prod_001",
                "title": "Health Insurance Plan Categories - Bronze",
                "content": "Bronze plans have the lowest monthly premiums but highest costs when you get care. They cover 60% of costs on average. Good for healthy people who want protection from worst-case scenarios.",
                "category": "product_plans",
                "subcategory": "bronze_plan",
                "source": "healthcare.gov",
                "source_url": "https://www.healthcare.gov/choose-a-plan/plan-categories/",
                "version": "1.0",
                "pii_flag": False,
                "tags": ["bronze", "plan", "premium", "costs", "coverage"],
                "created_at": "2024-01-15T10:00:00",
                "chunk_index": None,
                "parent_id": None
            }
        }


class KBQueryResult(BaseModel):
    """Result from a knowledge base query."""
    record: KBRecord
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Similarity score (0-1)"
    )
    citation: str = Field(
        ...,
        description="Formatted citation string"
    )

    def format_for_voice(self) -> str:
        """Format this result for voice agent consumption."""
        return (
            f"[Source: {self.record.source.value} | "
            f"Category: {self.record.category.value}]\n"
            f"{self.record.content}"
        )


class KBQueryRequest(BaseModel):
    """Request to query the knowledge base."""
    question: str = Field(..., min_length=3)
    top_k: int = Field(default=3, ge=1, le=10)
    category_filter: Optional[KBCategory] = None
    min_score: float = Field(default=0.3, ge=0.0, le=1.0)


class RetrievalTestResult(BaseModel):
    """Result of a retrieval test for assessment evidence."""
    query: str
    retrieved_records: List[KBQueryResult]
    source_reference: str
    relevance_explanation: str
    verdict: str = Field(
        ...,
        pattern="^(correct|partially_correct|incorrect)$"
    )
