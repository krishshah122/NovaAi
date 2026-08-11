# Common Defense Questions & Answers

This document contains a list of important and frequently asked questions regarding the technical decisions, architecture, and tool choices of the Nova AI project.

---

### Q1: Why did you choose Pinecone instead of a local vector database like pgvector or ChromaDB?
**Answer:** Pinecone is a fully managed, serverless vector database. Because our Voice AI backend runs in a stateless, ephemeral cloud container (Render), managing local persistent disk state for a database like ChromaDB or Postgres (pgvector) would introduce significant DevOps complexity and risk data loss on server restarts. Pinecone provides sub-100ms retrieval latency via API out of the box, which is strictly required when a user is waiting on a live phone call.

### Q2: Why did you switch from PyTorch `sentence-transformers` to `fastembed`?
**Answer:** Our deployment environment (Render Free Tier) strictly caps memory usage at 512MB. Loading the PyTorch backend to run `sentence-transformers` consumed over 600MB of RAM, causing the server to immediately crash with an `Out Of Memory (OOM)` error. By switching to `fastembed`, we run the exact same embedding model (`all-MiniLM-L6-v2`) but on the highly optimized **ONNX** runtime instead of PyTorch. This reduced our memory footprint to ~150MB, completely solving the crashes while retaining exact RAG accuracy.

### Q3: How do you prevent the AI from hallucinating insurance deductibles?
**Answer:** Zero-hallucination is enforced using three layers:
1. **Strict Prompting:** The LLM is commanded to *never* guess financial figures or rules.
2. **Tool Forcing:** It must execute the `query_knowledge_base` tool whenever a policy question is asked.
3. **Fallback Logic:** If the tool returns no matching vector chunks, the LLM is programmed to immediately pivot to human escalation rather than attempting to guess the answer.

### Q4: Why use Groq for the Nudge Engine instead of OpenAI GPT-4?
**Answer:** The Nudge Engine's purpose is to analyze live transcripts and flash actionable advice (like "Frustration Detected") to a dashboard *while the user is still speaking*. Traditional LLM APIs like OpenAI or Anthropic take 1-3 seconds to generate JSON outputs, which is too slow for real-time live-agent assist. Groq runs on specialized LPU (Language Processing Unit) hardware and returns semantic JSON extractions in under **600 milliseconds**.

### Q5: How do you handle long PDF documents in your Knowledge Base?
**Answer:** We built a custom **Universal File Ingestor** (`ingest_file.py`). Instead of blindly chunking by fixed token lengths (which can cut a sentence in half), the ingestor extracts text and tables (using PyMuPDF) and splits the document intelligently at paragraph boundaries. It automatically auto-generates titles, extracts category tags based on keyword density, and validates the chunks against our strict Pydantic `KBRecord` schema before UPSERTing them to Pinecone.

### Q6: How does the system handle Non-English callers (Taglish / Bahasa Indonesia)?
**Answer:** Multilingual voice bots struggle heavily with ASR (Speech-to-Text) hallucinations, especially when code-switching (mixing English and local dialects). To solve this:
- We crafted hyper-localized system prompts using cultural conversational connectors (e.g., "po/opo" in Taglish, "Pak/Bu" in Bahasa).
- We explicitly instructed the LLM to output cleanly formatted text (e.g., spelling out numbers as words instead of digits) to prevent the Text-to-Speech (TTS) engine from mispronouncing the translated text.

### Q7: If you were to scale this to 10,000 concurrent calls, what would break?
**Answer:** The biggest bottleneck would be the **Groq API rate limits**. Currently, the frontend POSTs a transcript chunk to the Nudge Engine every time a user speaks. At 10,000 concurrent calls, we would instantly exhaust 3rd-party API rate limits. 
**The Fix:** We would replace the heavy 70B Groq model with a highly fine-tuned, localized intent classifier (like a custom 8B model or DistilBERT) deployed on dedicated Kubernetes infrastructure (using vLLM). This would allow us to evaluate nudges locally on our own hardware without any API throttling.

### Q8: How is PII (Personally Identifiable Information) handled?
**Answer:** Before any document is chunked or embedded into the Pinecone database, it runs through `cleaner.py`. This script uses strict Regular Expressions to detect Phone Numbers, Emails, Social Security Numbers, and Credit Cards, replacing them with generic tags like `[PII_REDACTED_SSN]`. This guarantees that no protected health information (PHI) or PII ever leaks into the public vector space.
