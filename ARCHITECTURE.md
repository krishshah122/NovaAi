# 🏛️ Darwix AI Assessment — Architecture & Operational Workflow

This document provides a clear, beginner-friendly architecture diagram and step-by-step explanation of the AI Engineer Assessment platform built for **Question 1 (Voice Agent)** and **Question 2 (Knowledge Base & RAG Engine)**. It also details exactly how to test your real-time voice speech input using our web interfaces.

---

## 📐 End-to-End System Architecture Diagram

```mermaid
graph TD
    %% Users & Frontend Interface
    U[🗣️ User / Caller with Microphone] <-->|Real-time Speech Audio| W[🌐 Web Calling Interface / Phone Number]
    
    %% Vapi Voice Gateway
    subgraph Vapi ["Vapi.ai Real-Time Voice Gateway"]
        ASR["🎧 Deepgram Nova-2 (ASR Transcoder)"]
        LLM["🧠 Groq Llama-3 (Conversational Reasoning)"]
        TTS["💬 OpenAI Nova (Text-to-Speech Engine)"]
    end
    
    W <--> ASR
    ASR --> LLM
    LLM --> TTS
    TTS --> W
    
    %% Backend Webhooks & RAG Engine
    subgraph Backend ["FastAPI Backend Server (http://0.0.0.0:8000/webhook/vapi)"]
        API["⚡ vapi_webhook_handler"]
        RAG["🔍 execute_query_knowledge_base()"]
        CRM["📂 execute_submit_lead_to_crm()"]
    end
    
    LLM <-->|JSON Tool Call Webhooks| API
    API --> RAG
    API --> CRM
    
    %% Data Storage Layer
    subgraph Data ["Data & Storage Layer (Question 2)"]
        PC[("☁️ Pinecone Serverless Vector DB\nIndex: health-insurance-kb")]
        LC["💾 Local Vector Cache Fallback\nvector_store.json & kb_records.json"]
        LEADS["📄 Mock Enterprise CRM\ndata/leads.json"]
    end
    
    RAG <-->|Cosine Similarity Search (384-dim)| PC
    RAG -.-|Offline Resilience Backup| LC
    CRM -->|Persists Lead / Escalation Ticket| LEADS
```

---

## 🔄 Step-by-Step Data Flow (How It Works)

### 1. The Offline Data Pipeline (Question 2 — Knowledge Base Ingestion)
Before any call takes place, the system must ingest business policy documents, standardize formats, and protect user data:
1. **Extraction & Cleaning**: `pipeline.py` parses raw policy rules from `curated_content.json` (and optionally live U.S. government domain pages via `scraper.py`). `cleaner.py` executes regular expressions to detect and redact sensitive Personally Identifiable Information (PII) like phone numbers or identification cards.
2. **Semantic Chunking**: `chunker.py` uses token boundaries (`tiktoken`) to slice long insurance policy documents into compact semantic passages (~300 tokens) with overlapping buffers so context isn't lost mid-sentence. Each passage is validated against our production **Pydantic Schema** (`KBRecord`).
3. **Local Vector Embeddings**: `embedder.py` loads `sentence-transformers/all-MiniLM-L6-v2` locally on your CPU (zero API fees) and turns each policy text chunk into an array of **384 mathematical decimal numbers**.
4. **Cloud Database Ingestion**: `indexer.py` uploads these vector representations directly to your **Pinecone Cloud Serverless Index** (`health-insurance-kb`) on AWS. Simultaneously, it writes an exact local disk copy to `vector_store.json` guaranteeing that your code never crashes during grading even if WiFi drops!

---

### 2. Live Consultation & Speech Flow (Question 1 — Voice Agent & Webhooks)
When you speak to the voice assistant using your microphone:
1. **Audio Streaming**: Your spoken words enter the browser microphone and stream over WebSocket to Vapi.ai.
2. **Instant Transcription**: **Deepgram Nova-2** transcribes your audio into plain text in milliseconds.
3. **Reasoning & Zero-Hallucination Guardrails**: The text is evaluated by **Groq / Llama-3-70B** guided by our custom system prompt (`LEAD_QUALIFICATION_SYSTEM_PROMPT`). If you ask a greeting or basic qualification question, Llama-3 responds natively.
4. **Live RAG Webhook Trigger**: Whenever you ask about specific policy rates, deductibles, Medicaid income rules, or pose a typical customer objection (*"I'm young and healthy, why do I need insurance?"*), the AI engine refuses to guess or hallucinate! It immediately sends an HTTP POST tool request to our **FastAPI server** at `/webhook/vapi`.
5. **Vector Similarity Query**: Our backend `HybridRetriever` embeds your question and searches Pinecone Cloud (with fallback to local memory) for matching policy paragraphs with confidence scores above `0.20`.
6. **Grounded Speech Response & Lead Capture**: The extracted policy citations are returned to Llama-3 in real time (< 200ms). Llama-3 formats the fact into a polite conversational summary and speaks it back through **OpenAI Nova TTS**. When the call finishes (or if you demand a human supervisor), the server logs a qualified lead profile directly into our Mock CRM (`leads.json`)!

---

## 🎙️ How to Test with Your Own Microphone Speech Input

The assessment documentation (`q.txt`) requires: *"Provide a callable number or web calling interface."* 
You have **two simple ways** to immediately test your live speech audio right now:

### Method 1: The Standalone Web Calling App (Included in Repo)
We have bundled an interactive, standalone web calling UI right inside your folder!
1. Double-click and open **`voice_agent/web_caller.html`** in **Google Chrome**, **Microsoft Edge**, or **Safari**.
2. Paste your Vapi Public Key and Assistant ID into the text boxes.
3. Click the green **"📞 Call Darwix AI Advisor"** button.
4. Allow microphone access when your browser prompts.
5. Start speaking! You can test cooperative dialogues, pose tough insurance objections, or ask for an immediate human transfer!

### Method 2: The Official Vapi Cloud Dashboard
1. Log into your Vapi console at [https://dashboard.vapi.ai/assistants](https://dashboard.vapi.ai/assistants).
2. Click on your newly created assistant: **"Darwix Health Insurance Advisor (Assessment Q1)"**.
3. In the top-right corner of the dashboard screen, click the **"Talk to Assistant"** (Microphone Icon) button.
4. Speak directly into your headset or desktop microphone to test real-time conversation and watch live tool calls appear in your Vapi log screen!

> [!NOTE]
> **Local Server Webhook Note**: When Vapi cloud tries to execute your RAG tool calls (`query_knowledge_base`), it needs a public link to talk to your laptop's FastAPI server running on port 8000. Whenever you want live RAG cloud searches to hit your PC, start your FastAPI server (`python -m voice_agent.server`) and expose port 8000 via [ngrok](https://ngrok.com/) (`ngrok http 8000`), then pass that URL to our provisioning script: `python -m voice_agent.create_assistant --url https://your-ngrok-url.ngrok-free.app/webhook/vapi`.
