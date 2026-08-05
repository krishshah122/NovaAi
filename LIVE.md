# 📋 LIVE.md — Build Progress & Changelog

> This file tracks what's been built, what data sources are used, and what's coming next.
> Updated after each build phase.

---

## 🔧 Current Status: **Question 2 Complete (Parts 1-3) — Ready to Build Question 1 Voice Agent (Part 4)**

---

## ✅ Part 1: Project Foundation + KB Data (DONE)

### What was created

| File | Purpose |
|------|---------|
| `requirements.txt` | Python dependencies — FastAPI, sentence-transformers, Pinecone, Groq, Deepgram, etc. |
| `.env.example` | API key template — copy to `.env` and fill in your keys |
| `.gitignore` | Ignore secrets, venv, cache, audio files |
| `knowledge_base/schema.py` | Pydantic models for KB records (record_id, title, content, category, source, version, pii_flag) |
| `knowledge_base/scraper.py` | Web scraper for US government public domain sources only |
| `knowledge_base/data/raw/curated_content.json` | 14 detailed health insurance records written from public info |
| `LIVE.md` | This file — tracks build progress |

### Where data comes from

| Source | Legal Status | What We Get |
|--------|-------------|-------------|
| **Healthcare.gov** | ✅ Public domain (US federal govt, 17 U.S.C. § 105) | Glossary, plan categories, enrollment, costs, preventive care, coverage, FAQs |
| **Medicare.gov** | ✅ Public domain (US federal govt) | Eligibility rules, coverage details, cost breakdowns |
| **Curated content** | ✅ Original (written based on publicly available info) | Plans, qualification rules, objection handling, compliance, glossary |

### What was intentionally excluded
- ❌ **BCBS** — private company, copyrighted content, ToS may prohibit scraping
- ❌ **UnitedHealthcare** — same
- ❌ **Aetna** — same
- ❌ **No synthetic/fake data** — all content is real or based on real public information

### Design decisions
- **Scraper separated from data**: `scraper.py` only scrapes. Curated content lives in `curated_content.json`
- **Schema-first**: KB records have a defined Pydantic schema before any data is processed
- **robots.txt checked**: Scraper checks robots.txt and rate-limits (2s delay between requests)

---

## ✅ Part 2: Data Pipeline (DONE)

What was built:
- `knowledge_base/cleaner.py` — PII detection/redaction (regex), deduplication (MD5 & Jaccard similarity), text normalization
- `knowledge_base/chunker.py` — Semantic chunking (200-400 tokens via tiktoken), 50-token overlap, Pydantic schema validation
- `knowledge_base/embedder.py` — Local embeddings via `sentence-transformers/all-MiniLM-L6-v2` (384-dim, zero API cost)
- `knowledge_base/indexer.py` — Pinecone Serverless indexer (`health-insurance-kb`, cosine) + local JSON offline cache
- `knowledge_base/pipeline.py` — CLI orchestrator combining extraction, cleaning, chunking, embedding, and indexing

---

## ✅ Part 3: KB Retriever & Retrieval Testing (DONE — Completes Question 2)

What was built & how it aligns with **`q.txt` (Question 2 Assessment Spec)**:
- `knowledge_base/retriever.py` — Hybrid Cloud/Offline similarity search engine (`HybridRetriever`) that connects Question 2 to Question 1.
- `knowledge_base/test_retrieval.py` — Automated verification suite running the 5 mandatory assessment query types (Achieved 100% accuracy).

### 🔍 What the Retriever Queries (100% Coverage of `q.txt` Requirements)
The retrieval evaluation tests explicitly demonstrate accurate vector search across the **5 mandatory domain question types** required by Question 2:
1. **Product Query**: *"What are the deductibles, premiums, and coverage cost differences between Bronze and Silver health plans?"* (Score: `0.8010` -> ✅ **Correct**)
2. **Qualification Query**: *"Am I eligible for Medicare, Medicaid, or premium tax credit subsidies to lower costs if my income recently dropped?"* (Score: `0.4924` -> ✅ **Correct**)
3. **Objection Query**: *"Why should I bother paying for health insurance? I am young and healthy and never visit the hospital."* (Score: `0.6761` -> ✅ **Correct**)
4. **Policy Query**: *"What benefits are guaranteed as Essential Health Benefits (EHB) and pre-existing conditions under the Affordable Care Act (ACA)?"* (Score: `0.7369` -> ✅ **Correct**)
5. **FAQ Query**: *"Can I sign up for health insurance coverage right now outside of the standard Open Enrollment period if I recently got married or moved?"* (Score: `0.6706` -> ✅ **Correct**)

### 📤 What the Retriever Returns as Output (Strict Assessment Field Schema)
Whenever queried, the retrieval engine produces structured `KBQueryResult` objects that output exact assessment grading proof:
- **Mandatory Schema Fields**: Returns `record_id`, `title`, `content`, `category`, `source`, `version` (`1.0`), and `pii_flag` (`False`/`True`) directly adhering to the exact table field format specified in `q.txt`.
- **Confidence Score (`score`)**: Floating point vector similarity ranking (0.0 to 1.0) with automatic cutoffs (`min_score = 0.20-0.30`) so the system safely states when information is unavailable instead of hallucinating.
- **Source Reference (`citation`)**: Formatted attribution string (`Policy Document: '...' | Category: '...' | Source: '...' | Version: 1.0`) directly consumed by the Question 1 voice bot.
- **Auditable Grading Evidence**: Automatically generates and stores `query`, `retrieved_records`, `source_reference`, `relevance_explanation`, and grading `verdict` (`correct` / `partially_correct` / `incorrect`) to `knowledge_base/data/processed/retrieval_evaluation_report.json`.

### 🗄️ Database Storage Schema & RAG I/O Reference (Full Examples)

#### 1. How Pinecone Stores Records (Vector Database Schema)
In Pinecone serverless Cloud DB (and our offline backup cache), each knowledge item is stored as a vector object containing 3 core root fields:
- **`id`**: Unique primary identifier string (e.g., `"kb_prod_001_c1"`).
- **`values`**: An array of exactly **384 floating-point numbers** generated by `sentence-transformers/all-MiniLM-L6-v2` representing semantic meaning.
- **`metadata`**: Key-value dictionary containing the clean scalars from our Pydantic schema:
```json
{
  "id": "kb_prod_001_c1",
  "values": [0.0342, -0.1294, 0.0051, 0.0821, "... (384 floats total)"],
  "metadata": {
    "record_id": "kb_prod_001_c1",
    "title": "Bronze Health Insurance Plan",
    "content": "Bronze plans have the lowest monthly premiums but highest costs when you get care. They cover 60% of costs on average. Good for healthy people who want protection from worst-case scenarios.",
    "category": "product_plans",
    "source": "healthcare.gov",
    "source_url": "https://www.healthcare.gov/choose-a-plan/plan-categories/",
    "version": "1.0",
    "pii_flag": false,
    "tags": ["bronze", "plan", "premium", "costs"],
    "chunk_index": 1,
    "parent_id": "kb_prod_001"
  }
}
```

#### 2. Input Query Schema & Full Example (`KBQueryRequest`)
When the Question 1 Voice Agent (or test script) sends a query to the retrieval engine, it passes this exact JSON payload:
```json
{
  "question": "What are the deductibles and coverage cost differences between Bronze and Silver health plans?",
  "top_k": 2,
  "category_filter": "product_plans",
  "min_score": 0.20
}
```

#### 3. Output Result Schema & Full Example (`List[KBQueryResult]`)
The `HybridRetriever` searches the vector space, applies confidence filtering, and returns an array of validated results with exact citations and Pydantic schema reconstruction:
```json
[
  {
    "record": {
      "record_id": "kb_prod_001_c1",
      "title": "Bronze Health Insurance Plan",
      "content": "Bronze plans have the lowest monthly premiums but highest costs when you get care. They cover 60% of costs on average. Good for healthy people who want protection from worst-case scenarios.",
      "category": "product_plans",
      "subcategory": "bronze_plan",
      "source": "healthcare.gov",
      "source_url": "https://www.healthcare.gov/choose-a-plan/plan-categories/",
      "version": "1.0",
      "pii_flag": false,
      "tags": ["bronze", "deductible", "premium", "cost", "coverage"],
      "created_at": "2026-08-05T13:40:00",
      "chunk_index": 1,
      "parent_id": "kb_prod_001"
    },
    "score": 0.801,
    "citation": "Policy Document: 'Bronze Health Insurance Plan' | Category: product_plans | Source: healthcare.gov (https://www.healthcare.gov/choose-a-plan/plan-categories/) | Version: 1.0"
  }
]
```

---

## 🔜 Part 4: Voice Agent FastAPI Server & RAG Tools (NEXT — Question 1)

What will be built next:
- `voice_agent/server.py` — FastAPI server handling Vapi audio webhooks and dynamic RAG execution
- `voice_agent/rag_tool.py` — Webhook function bridging voice AI to our `HybridRetriever`
- `voice_agent/prompts.py` — Production conversation prompt for Health Insurance Lead Qualification

---

## 📅 Full Build Roadmap

| Part | What | Status |
|------|------|--------|
| **Part 1** | Project setup + KB data sources + schema | ✅ Done |
| **Part 2** | Cleaner → Chunker → Embedder → Pinecone Indexer | ✅ Done |
| **Part 3** | KB Retriever + 5 retrieval tests (completes Q2) | ✅ Done |
| **Part 4** | Voice agent server + tools + system prompt (Q1) | ⏳ Next |
| **Part 5** | Vapi assistant setup + qualification flow (Q1) | ⬜ Pending |
| **Part 6** | Philippines Taglish bot (Q3) | ⬜ Pending |
| **Part 7** | Indonesia Bahasa bot (Q3) | ⬜ Pending |
| **Part 8** | Real-time ASR pipeline + signal detector (Q4) | ⬜ Pending |
| **Part 9** | Nudge engine + WebSocket dashboard (Q4) | ⬜ Pending |
| **Part 10** | Documentation, README, architecture diagram | ⬜ Pending |
