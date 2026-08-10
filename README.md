# Nova AI — Real-Time Voice Agent & RAG Platform

An end-to-end, production-grade Voice AI platform that bridges Vapi.ai's conversational web orchestrator with a high-accuracy Pinecone Vector RAG database and a sub-second Groq Nudge Engine. Built to demonstrate enterprise-level voice assistant architecture with zero-hallucination compliance, multilingual support, and real-time agent assist.

---

## 🏛️ Overall System Flow
1. **The User Interface:** A user accesses the Web Caller UI (`web_caller.html`) and selects a region (US English, Philippines, or Indonesia).
2. **Voice Orchestration:** The browser initiates a WebRTC connection to **Vapi.ai**. Vapi handles raw audio streaming, passing the audio to Deepgram (ASR) for transcription, sending transcripts to the core LLM for logic, and synthesizing the response via ElevenLabs (TTS).
3. **RAG Integration:** If the user asks a factual policy question, Vapi suspends generation and fires a Webhook to our **FastAPI Backend** (`server.py`). 
4. **Vector Retrieval:** The backend processes the webhook, executes `query_knowledge_base`, and searches **Pinecone** to retrieve precise data (e.g., deductible amounts) before returning it to Vapi to read aloud.
5. **Real-Time Nudging:** Simultaneously, the Web Caller UI captures live transcript frames from Vapi and POSTs them to our `/api/analyze_transcript` endpoint. Here, our **Groq Nudge Engine** evaluates a sliding transcript window in under ~600ms, pushing actionable compliance/cross-sell nudges back to the Agent Dashboard.

---

## 🛠️ Tech Stack, APIs, & Design Decisions

| Component / API | Technology Choice | Why this technology? (Design Decision) |
|-----------------|-------------------|----------------------------------------|
| **Voice Orchestrator** | [Vapi.ai](https://vapi.ai/) | Prevents the need to build complex raw WebRTC audio chunking and interruption (barge-in) mechanics from scratch. Vapi handles ultra-low latency ASR/TTS bridging out-of-the-box. |
| **Backend Server** | Python **FastAPI** | Chosen for its native asynchronous capabilities (`async/await`), which is critical for handling simultaneous low-latency webhooks from Vapi and real-time frontend transcript streams. |
| **Vector Database** | **Pinecone** (Serverless) | Fast, cloud-native vector search. Avoids the overhead of managing local pgvector databases while guaranteeing <100ms retrieval latency for Voice RAG constraints. |
| **Embeddings Model** | `fastembed` (ONNX) | A lightweight, fast embedding model that runs using the ONNX runtime. This slashes memory usage to ~150MB compared to PyTorch-based models, allowing for deployment on constrained server environments. |
| **Live Nudge Engine** | **Groq API** (`llama-3.3-70b`) | Traditional LLM APIs (OpenAI/Anthropic) take 1-3 seconds to generate structured JSON. Groq runs on specialized LPU hardware, generating semantic signal extraction JSON in **~500ms**, which is mandatory for real-time agent nudging before a call ends. |
| **Data Cleaning** | Regex & MD5 Hashing | PII is scrubbed using strict Regex patterns before chunking. Duplicate records are dropped using MD5 hashing to ensure the LLM isn't confused by duplicated chunks during retrieval. |

---

## 📦 Project Structure

| Module | Description | Key Files |
|--------|-------------|-----------|
| **Voice Agent** | Vapi-connected voice bot with lead qualification, strict RAG grounding, and human escalation | `voice_agent/`, `web_caller.html` |
| **Knowledge Base** | Production-ready data pipeline — scraping, cleaning, chunking, embedding, and Pinecone indexing | `knowledge_base/`, `RETRIEVAL_TESTS.md` |
| **Multilingual Bots** | Taglish (Philippines) and Bahasa Indonesia voice bots with cultural code-switching and local honorifics | `multilingual_bots/` |
| **Live Nudge Engine** | Groq Llama-3 stream analyzer detecting compliance, frustration, and cross-sell signals in <600ms | `voice_agent/nudge_engine.py` |

---

## 🚀 Quick Start Guide

### 1. Environment Setup
Create a `.env` file in the root directory based on `.env.example`:
```env
PINECONE_API_KEY=your_pinecone_key
GROQ_API_KEY=your_groq_key
VAPI_PRIVATE_API_KEY=your_vapi_key
```

### 2. Install Dependencies
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run the Backend & Web UI
```bash
# Start the FastAPI Webhook Server & Nudge Engine
python -m voice_agent.server
```

Open a web browser and navigate to `http://localhost:8000/call`.
You can toggle between US English, Taglish, and Bahasa Indonesia instantly via the UI tabs!

---

## 🗄️ Knowledge Base Pipeline

Our Knowledge Base (KB) transforms unstructured web data into structured, traceable vectors for the Voice Agent's RAG system.

### How to Add Data & Run the KB Pipeline
If you want to add custom policies or re-index the database from scratch, simply edit the `knowledge_base/data/raw/curated_content.json` file. Then, run the central orchestrator:
```bash
python -m knowledge_base.pipeline
```
This automated pipeline instantly executes:
1. Regex-based PII redaction (masking phone numbers/SSNs) and MD5 hashing deduplication.
2. Semantic chunking (by logical sections) and schema validation.
3. High-speed `all-MiniLM-L6-v2` embedding generation and Pinecone Vector UPSERTing.

### KB Schema & Chunking Strategy
All records adhere to a strict Pydantic schema (`schema.py`):
- **`record_id`**: Unique identifier (e.g., `kb_product_001`).
- **`title` & `content`**: The semantic payload.
- **`category` & `source`**: Taxonomy tags for filtering and traceability (e.g., `healthcare.gov`).
- **`version` & `pii_flag`**: Tracks document updates and confirms redaction passes.

**Chunking:** We use logical document chunking (by section/product) rather than arbitrary token counts (like LangChain's 500-token splitter). This ensures that the LLM receives the entire context of a specific insurance product in a single coherent chunk, preventing deductibles from being separated from premiums across two different chunks.

### How to Test Retrieval
We have compiled test queries, complete with their retrieved chunks, citations, and accuracy verdicts, in the **[RETRIEVAL_TESTS.md](RETRIEVAL_TESTS.md)** file included in this repository.

---

## 🌎 Multilingual Support & Compromises

### ASR (Speech-to-Text) Behavior
Vapi relies heavily on Deepgram Nova-2. While Nova-2 is world-class for English, it struggles natively with heavy regional accents or rapid code-switching without explicit configuration. 
- **The Challenge:** When testing the Indonesian bot, saying *"Halo Budi"* was sometimes mistranscribed as *"Hello, Buddhists"* by the English-first model.
- **Our Solution:** We modified the System Prompt to output strictly formatted, punctuation-clean numbers and words (e.g., spelling out *"dua juta"* instead of *2.000.000*) to aid the TTS engine in recovering gracefully from bad ASR transcripts. 

### TTS (Text-to-Speech) Compromises
- **Taglish:** AI providers do not have a dedicated "Taglish" model. We forced it to sound authentic by using a generic multicultural voice and strictly prompting the LLM to use heavy Filipino conversational connectors (*"po/opo", "sir/ma'am"*) and micro-savings framing (*"cost of a daily coffee"*).
- **Bahasa Indonesia:** We configured the AI to use local honorifics (*"Pak / Bu"*) and regional Jakarta finance terms (*"DP", "Angsuran", "Tenor"*) to avoid sounding like a robotic literal translation.

---

## ⚡ Nudge Engine — Limitations & Scaling Considerations

Our Live Agent Assist Nudge Engine runs on `llama-3.3-70b-versatile` via Groq, achieving ~500ms latency. 

**At 10x scale or in noisy call center environments, the following limitations apply:**

1. **Token Window Saturation:** We currently feed the LLM a sliding window of the last 6 sentences. If a caller goes on a long, rambling 3-minute tangent, the "frustration" signal might fall out of the sliding window before the LLM evaluates it.
2. **ASR Hallucinations (Noisy Audio):** If background noise causes the ASR to transcribe *"I need to pee"* instead of *"I need a fee waiver"*, the semantic Nudge Engine might incorrectly extract an out-of-bounds intent.
3. **Groq Rate Limiting:** While Groq is incredibly fast for single calls, scaling to 10,000 concurrent calls sending transcript chunks every 2 seconds would instantly exhaust standard Groq API rate limits. 
4. **Production Mitigation:** At scale, we would replace the heavy 70B LLM with a highly fine-tuned, localized intent classifier (like a fine-tuned `DistilBERT` or `Llama-3-8B`) deployed on dedicated vLLM infrastructure inside a Kubernetes cluster to evaluate nudges locally without third-party API bottlenecks.
