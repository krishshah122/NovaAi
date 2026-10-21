"""
Knowledge Base Retrieval Evaluation Engine
Runs mandatory evaluation test queries across the hybrid vector retriever, verifies semantic relevance,
computes confidence scores, and outputs formal evaluation evidence.
"""

import sys
import io
import json
import statistics
import time
from pathlib import Path
from typing import Any, Dict, List

# Ensure UTF-8 stdout encoding on Windows consoles
if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from knowledge_base.schema import KBQueryRequest
from knowledge_base.retriever import HybridRetriever


def _percentile(values: List[float], percentile: float) -> float:
    """Return a linearly interpolated percentile for a non-empty sample."""
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]

    index = (len(ordered) - 1) * percentile
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = index - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def run_retrieval_tests() -> List[Dict[str, Any]]:
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
            "expected_record_id": "health_product_platinum_plus",
            "expected_source": "manual_entry",
            "explanation": "Properly retrieves specific product pricing data for the newly added Platinum Health Plus plan."
        },
        {
            "query": "What happens if I miss my premium payment and I get tax credits? How long is the grace period before termination?",
            "expected_record_id": "health_policy_grace_period",
            "expected_source": "healthcare.gov",
            "explanation": "Retrieves the exact newly added policy regarding grace periods for APTC recipients."
        },
        {
            "query": "Can I sign up for health insurance coverage right now outside of the standard Open Enrollment period if I recently got married or moved?",
            "expected_record_id": "supp_eligibility_marketplace_c1",
            "expected_source": "healthcare.gov",
            "expected_source_url": "https://www.healthcare.gov/quick-guide/eligibility/",
            "explanation": "Retrieves Special Enrollment Period (SEP) qualification rules governing qualifying life events like marriage."
        },
        {
            "query": "Does standard Bronze or Silver marketplace health insurance cover adult dental and vision care?",
            "expected_record_id": "health_faq_dental_vision",
            "expected_source": "healthcare.gov",
            "explanation": "Accurately finds the FAQ explaining that adult dental/vision requires separate plans but pediatric is included."
        },
        {
            "query": "Why should I bother paying for health insurance? I am young, healthy, and don't need it.",
            "expected_record_id": "supp_objections_c1",
            "expected_source": "manual_entry",
            "explanation": "Successfully links natural conversation pushback to our new Objection Handling records for healthy callers."
        }
    ]

    evaluation_results: List[Dict[str, Any]] = []
    query_latencies_ms: List[float] = []

    print("\n[EVALUATION] Running exact-record and citation checks on 5 policy queries...\n")

    for idx, scenario in enumerate(test_scenarios, 1):
        query_text = scenario["query"]
        req = KBQueryRequest(question=query_text, top_k=2, min_score=0.20)

        start_time = time.perf_counter()
        matches = retriever.query(req)
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        query_latencies_ms.append(elapsed_ms)

        expected_id = scenario["expected_record_id"]
        top_match = matches[0] if matches else None
        top1_correct = bool(top_match and top_match.record.record_id == expected_id)
        expected_retrieved = any(result.record.record_id == expected_id for result in matches)
        citation_correct = bool(
            top1_correct
            and top_match
            and f"Source: {scenario['expected_source']}" in top_match.citation
            and (
                not scenario.get("expected_source_url")
                or scenario["expected_source_url"] in top_match.citation
            )
        )
        verdict = (
            "correct" if top1_correct and citation_correct
            else "partially_correct" if expected_retrieved
            else "incorrect"
        )
        source_ref = top_match.citation if top_match else "None Retrieved"

        evaluation_results.append({
            "query": query_text,
            "expected_record_id": expected_id,
            "retrieved_record_ids": [result.record.record_id for result in matches],
            "retrieved_records": [result.model_dump() for result in matches],
            "source_reference": source_ref,
            "expected_source": scenario["expected_source"],
            "top1_correct": top1_correct,
            "expected_record_in_top_k": expected_retrieved,
            "citation_correct": citation_correct,
            "elapsed_ms": elapsed_ms,
            "relevance_explanation": scenario["explanation"],
            "verdict": verdict,
        })

        print(f"[TEST {idx}/5] {verdict.upper()} | top-1={top1_correct} | citation={citation_correct} | {elapsed_ms} ms")
        print(f"         Expected: {expected_id} | Retrieved: {[result.record.record_id for result in matches]}")
        print("-" * 70)

    total_tests = len(evaluation_results)
    top1_hits = sum(result["top1_correct"] for result in evaluation_results)
    top_k_hits = sum(result["expected_record_in_top_k"] for result in evaluation_results)
    citation_hits = sum(result["citation_correct"] for result in evaluation_results)
    warm_latencies_ms = query_latencies_ms[1:]
    summary = {
        "query_count": total_tests,
        "top1_accuracy_percent": round(top1_hits / total_tests * 100, 1),
        "recall_at_2_percent": round(top_k_hits / total_tests * 100, 1),
        "citation_accuracy_percent": round(citation_hits / total_tests * 100, 1),
        "latency_ms": {
            "cold_first_query": query_latencies_ms[0],
            "warm_median": round(statistics.median(warm_latencies_ms), 2) if warm_latencies_ms else None,
            "warm_p95": round(_percentile(warm_latencies_ms, 0.95), 2) if warm_latencies_ms else None,
            "all_queries": query_latencies_ms,
            "scope": "HybridRetriever.query only; excludes Vapi, speech recognition, LLM response generation, and text-to-speech.",
        },
    }

    print(
        f"\n[EVALUATION] Top-1: {summary['top1_accuracy_percent']}% | "
        f"Recall@2: {summary['recall_at_2_percent']}% | "
        f"Citation: {summary['citation_accuracy_percent']}%"
    )
    print(
        f"[LATENCY] Cold first query: {summary['latency_ms']['cold_first_query']} ms | "
        f"Warm median: {summary['latency_ms']['warm_median']} ms | "
        f"Warm p95: {summary['latency_ms']['warm_p95']} ms"
    )

    output_report = project_root / "knowledge_base" / "data" / "processed" / "retrieval_evaluation_report.json"
    output_report.parent.mkdir(parents=True, exist_ok=True)
    with open(output_report, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": evaluation_results}, f, indent=2, ensure_ascii=False)
    print(f"[SAVE] Evaluation report saved to: {output_report}")

    print("=" * 70 + "\n")
    return evaluation_results


if __name__ == "__main__":
    run_retrieval_tests()
