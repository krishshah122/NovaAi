"""
Voice Agent RAG and CRM Tools
Defines tool JSON schemas for Vapi assistant declaration and executes back-end function implementations
connecting live voice calls to the Pinecone vector database and business CRM lead persistence.
"""

import os
import json
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from knowledge_base.retriever import HybridRetriever
from knowledge_base.schema import KBQueryRequest

# Initialize singleton retriever instance for high-speed low-latency tool execution
_retriever_instance: Optional[HybridRetriever] = None


def get_retriever() -> HybridRetriever:
    """Lazy initialization of singleton HybridRetriever."""
    global _retriever_instance
    if _retriever_instance is None:
        print("[RAG TOOL] Initializing singleton HybridRetriever for voice agent webhooks...")
        _retriever_instance = HybridRetriever()
    return _retriever_instance


# ---------------------------------------------------------------------------
# 1. TOOL EXECUTION LOGIC (Backend Webhook Functions)
# ---------------------------------------------------------------------------

def execute_query_knowledge_base(question: str) -> str:
    """
    Execute semantic similarity query against our knowledge base.
    Returns formatted RAG passages with citations for Groq/Llama-3 voice consumption.
    """
    if not question or len(question.strip()) < 3:
        return "ERROR: Question text too short. Please ask a clearer insurance policy question."

    print(f"\n[WEBHOOK TOOL] Executing query_knowledge_base(question='{question}')")
    retriever = get_retriever()
    
    req = KBQueryRequest(question=question, top_k=2, min_score=0.20)
    results = retriever.query(req)
    
    formatted_output = retriever.format_context_for_rag(results)
    print(f"[WEBHOOK TOOL] Retrieved {len(results)} high-confidence policy chunks to feed voice bot.")
    return formatted_output


def execute_submit_lead_to_crm(
    caller_name: str = "Anonymous Caller",
    email_or_phone: str = "Not Provided",
    household_size: int = 1,
    interested_plan_type: str = "Undetermined",
    notes: str = "Standard consultation",
    needs_human_escalation: bool = False
) -> str:
    """
    Persist qualified caller profile and lead details into business CRM database.
    """
    crm_dir = Path(__file__).resolve().parent / "data"
    crm_dir.mkdir(parents=True, exist_ok=True)
    leads_file = crm_dir / "leads.json"

    lead_record = {
        "lead_id": f"lead_{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.utcnow().isoformat(),
        "caller_name": str(caller_name),
        "contact_info": str(email_or_phone),
        "household_size": int(household_size) if str(household_size).isdigit() else 1,
        "interested_plan_type": str(interested_plan_type),
        "consultation_notes": str(notes),
        "status": "REQUIRES_HUMAN_ESCALATION" if needs_human_escalation else "QUALIFIED_LEAD",
        "assigned_agent": "Human Onboarding Specialist" if needs_human_escalation else "Automated Nudge System"
    }

    existing_leads: List[Dict] = []
    if leads_file.exists():
        try:
            with open(leads_file, "r", encoding="utf-8") as f:
                existing_leads = json.load(f)
        except Exception as e:
            print(f"[WARNING] Could not read existing leads database: {e}")

    existing_leads.append(lead_record)

    try:
        with open(leads_file, "w", encoding="utf-8") as f:
            json.dump(existing_leads, f, indent=2, ensure_ascii=False)
        
        status_tag = "🔴 [ESCALATION ALERT]" if needs_human_escalation else "🟢 [NEW LEVERAGED LEAD]"
        print(f"\n{status_tag} CRM Record Created! Saved to: {leads_file}")
        print(f"   -> Lead ID: {lead_record['lead_id']} | Name: {caller_name} | Plan: {interested_plan_type}")
        
        if needs_human_escalation:
            return f"SUCCESS: Lead recorded under ticket {lead_record['lead_id']}. High priority human escalation alert triggered to licensed agent team."
        else:
            return f"SUCCESS: Qualified lead profile successfully created under ID {lead_record['lead_id']}."
    except Exception as e:
        print(f"[ERROR] Failed writing lead to CRM disk: {e}")
        return f"ERROR: Could not persist lead record: {e}"


# ---------------------------------------------------------------------------
# 2. VAPI ASSISTANT TOOL SCHEMAS (JSON Structure for Voice Engine Setup)
# ---------------------------------------------------------------------------

VAPI_TOOLS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "query_knowledge_base",
            "description": "Query the verified health insurance knowledge base to retrieve accurate deductibles, coverage rules, Medicare eligibility, subsidy thresholds, ACA laws, and objection handling responses. ALWAYS use this tool instead of guessing policy details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The explicit insurance policy question, comparison query, or customer objection to check against official documentation."
                    }
                },
                "required": ["question"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "submit_lead_to_crm",
            "description": "Submit a qualified customer lead profile or human escalation request into our enterprise CRM system at the conclusion of a consultation or when an out-of-scope/complex situation requires transfer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "caller_name": {
                        "type": "string",
                        "description": "Full name of the caller if shared, otherwise default to Anonymous Caller."
                    },
                    "email_or_phone": {
                        "type": "string",
                        "description": "Contact phone number or email address."
                    },
                    "household_size": {
                        "type": "integer",
                        "description": "Total number of individuals in the family requiring coverage."
                    },
                    "interested_plan_type": {
                        "type": "string",
                        "description": "Target metal plan or program of interest (e.g., Bronze, Silver, Gold, Medicaid, SEP)."
                    },
                    "notes": {
                        "type": "string",
                        "description": "Brief conversational summary of key needs, objections handled, or questions answered."
                    },
                    "needs_human_escalation": {
                        "type": "boolean",
                        "description": "Set to True ONLY if the customer requested a human agent, became frustrated, or presented complex unresolvable legal claims."
                    }
                },
                "required": ["caller_name", "needs_human_escalation"]
            }
        }
    }
]
