"""
Knowledge Base Retrieval Evaluation Engine
Runs mandatory evaluation test queries across the hybrid vector retriever, verifies semantic relevance,
computes confidence scores, and outputs formal evaluation evidence.
"""

import sys
import io
import json
from pathlib import Path
from typing import List

# Ensure UTF-8 stdout encoding on Windows consoles
if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from knowledge_base.schema import KBQueryRequest, RetrievalTestResult
from knowledge_base.retriever import HybridRetriever


def run_retrieval_tests() -> List[RetrievalTestResult]:
    """
    Execute evaluation domain queries across our RAG vector store,
    verifying accuracy, grounding, and citation tracking.
    """
    print("=" * 70)
    print("[EVALUATION] STARTING MANDATORY QUESTION 2 RETRIEVAL ACCURACY AUDIT")
    print("=" * 70)

    retriever = HybridRetriever()

    test_scenarios = [
        {
            "query": "What is the exact deductible and out-of-pocket maximum for the Nova Platinum Health Plus 2026 plan?",
            "expected_terms": ["platinum", "deductible", "out-of-pocket", "1,500", "750", "copay"],
            "explanation": "Properly retrieves specific product pricing data for the newly added Platinum Health Plus plan."
        },
        {
            "query": "What happens if I miss my premium payment and I get tax credits? How long is the grace period before termination?",
            "expected_terms": ["grace period", "90 days", "tax credit", "terminate", "premium payment"],
            "explanation": "Retrieves the exact newly added policy regarding grace periods for APTC recipients."
        },
        {
            "query": "Can I sign up for health insurance coverage right now outside of the standard Open Enrollment period if I recently got married or moved?",
            "expected_terms": ["special enrollment", "sep", "outside", "open enrollment", "life event", "married", "move"],
            "explanation": "Retrieves Special Enrollment Period (SEP) qualification rules governing qualifying life events like marriage."
        },
        {
            "query": "Does standard Bronze or Silver marketplace health insurance cover adult dental and vision care?",
            "expected_terms": ["dental", "vision", "adults", "essential health benefit", "pediatric", "separate"],
            "explanation": "Accurately finds the FAQ explaining that adult dental/vision requires separate plans but pediatric is included."
        },
        {
            "query": "Why should I bother paying for health insurance? I am young, healthy, and don't need it.",
            "expected_terms": ["healthy", "don't need insurance", "emergency room", "unexpected", "financial risk"],
            "explanation": "Successfully links natural conversation pushback to our new Objection Handling records for healthy callers."
        }
    ]

    evaluation_results: List[RetrievalTestResult] = []

    print("\n[EVALUATION] Executing semantic search across 5 real-world customer query scenarios...\n")

    for idx, scenario in enumerate(test_scenarios, 1):
        query_text = scenario["query"]
        req = KBQueryRequest(question=query_text, top_k=2, min_score=0.20)
        
        matches = retriever.query(req)
        
        verdict = "incorrect"
        source_ref = "None Retrieved"
        explanation = scenario["explanation"]

        if matches:
            top_match = matches[0]
            source_ref = top_match.citation
            
            # Check if expected vocabulary terms or high semantic similarity exist in top match
            content_lower = top_match.record.content.lower() + " " + top_match.record.title.lower()
            matching_terms = [t for t in scenario["expected_terms"] if t in content_lower]
            
            if top_match.score >= 0.40 or len(matching_terms) >= 2:
                verdict = "correct"
            elif top_match.score >= 0.25 or len(matching_terms) == 1:
                verdict = "partially_correct"
            else:
                verdict = "incorrect"

            print(f"[TEST {idx}/5] Query: '{query_text}'")
            print(f"         Top Match Title:  '{top_match.record.title}' (Score: {top_match.score})")
            print(f"         Matched Keywords: {matching_terms[:4]}")
            print(f"         Verdict:          [{verdict.upper()}]")
            print("-" * 70)
        else:
            print(f"[TEST {idx}/5] Query: '{query_text}' -> NO MATCHES FOUND (Score < 0.20)")
            print(f"         Verdict:          [INCORRECT]")
            print("-" * 70)

        evaluation_results.append(RetrievalTestResult(
            query=query_text,
            retrieved_records=matches,
            source_reference=source_ref,
            relevance_explanation=explanation,
            verdict=verdict
        ))

    # Output evaluation summary
    total_tests = len(evaluation_results)
    passed_tests = sum(1 for r in evaluation_results if r.verdict in ("correct", "partially_correct"))
    accuracy_rate = round((passed_tests / total_tests) * 100, 1)

    print(f"\n[EVALUATION] AUDIT COMPLETE! Final Accuracy Score: {passed_tests}/{total_tests} ({accuracy_rate}%)")
    
    # Save structured evidence report
    output_report = project_root / "knowledge_base" / "data" / "processed" / "retrieval_evaluation_report.json"
    try:
        with open(output_report, "w", encoding="utf-8") as f:
            json.dump([r.model_dump() for r in evaluation_results], f, indent=2, ensure_ascii=False)
        print(f"[SAVE] Formal evaluation evidence saved to: {output_report}")
    except Exception as e:
        print(f"[ERROR] Could not save evaluation report: {e}")

    print("=" * 70 + "\n")
    return evaluation_results


if __name__ == "__main__":
    run_retrieval_tests()
