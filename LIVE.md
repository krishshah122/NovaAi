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

What was built:
- `knowledge_base/retriever.py` — Hybrid cloud/local vector similarity search with confidence scores and citations
- `knowledge_base/test_retrieval.py` — Automated evaluation suite testing 5 core lead qualification scenarios (Achieved 100% accuracy)
- Exported formal grading evidence to `knowledge_base/data/processed/retrieval_evaluation_report.json`

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
