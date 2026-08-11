# Nova AI - Deep Dive Technical Interview

This document serves as a comprehensive "interview-style" deep dive into the Nova AI project. It breaks down the system's architecture, key features, technology choices, and implementation details.

---

## 1. Project Overview

**Interviewer: What is Nova AI, and what problem does it solve?**

**Engineer:** Nova AI is an end-to-end, real-time Voice AI platform designed for health insurance advisory. The core problem it solves is automating complex, compliance-heavy customer service phone calls without risking AI hallucinations. It goes beyond a simple voice bot by incorporating two enterprise-grade features: 
1. **Real-Time Voice RAG (Retrieval-Augmented Generation):** It grounds the voice agent's answers in a strictly curated Pinecone vector database.
2. **Live Nudge Engine:** It silently "listens" to the transcript and flashes actionable signals (like frustration or cross-sell opportunities) to a human agent dashboard in under 600ms.

---

## 2. Architecture & Flow

**Interviewer: Can you walk me through the architecture and the data flow when a user makes a call?**

**Engineer:** The architecture is split between the frontend (Web Caller UI), the voice orchestrator (Vapi.ai), and the backend logic (FastAPI).

1. **Audio Ingestion:** The user clicks "Call" on the browser, opening a WebRTC connection to Vapi.ai.
2. **ASR (Speech-to-Text):** Vapi uses Deepgram Nova-2 to transcribe the user's speech in real-time.
3. **Dialogue Logic & RAG Trigger:** Vapi passes the transcript to our core LLM. If the user asks a factual policy question (e.g., "What's the deductible on the Platinum plan?"), the LLM suspends generating a verbal response and fires a Webhook to our FastAPI backend (`/webhook/vapi`).
4. **Vector Retrieval:** The backend processes the webhook, executes `query_knowledge_base`, and searches our Pinecone vector database using `fastembed` (all-MiniLM-L6-v2) for exact policy details. It returns this text to Vapi.
5. **TTS (Text-to-Speech):** Vapi synthesizes the highly accurate response using ElevenLabs and streams the audio back to the user.
6. **Parallel Nudge Engine:** Simultaneously, the frontend intercepts the live text transcripts via websockets and POSTs them to our `/api/analyze_transcript` endpoint. The Groq-powered Nudge Engine evaluates the last 6 sentences and returns actionable JSON nudges to the UI dashboard.

---

## 3. Key Implementations & Technology Choices

**Interviewer: How is the Knowledge Base constructed and ingested?**

**Engineer:** We built a custom, automated data pipeline (`pipeline.py`). We extract text from federal public domain sources (Healthcare.gov, Medicare.gov) and custom files (PDFs/TXTs) using our **Universal File Ingestor**. 
1. The `cleaner.py` script sanitizes the text, removes PII (Phone, SSN, Email) using Regex, and deduplicates using MD5 hashing.
2. The `chunker.py` script splits documents semantically by paragraph and validates them against a strict Pydantic schema.
3. The `embedder.py` script generates dense 384-dimensional vectors.
4. Finally, `indexer.py` UPSERTs these into a Pinecone serverless index.

**Interviewer: I see you migrated from PyTorch to `fastembed`. Why was this critical?**

**Engineer:** Memory constraints. Initially, we used the standard `sentence-transformers` library backed by PyTorch to generate embeddings. However, loading PyTorch immediately consumed over 600MB of RAM. Since our backend is hosted on Render's Free Tier (which strictly caps RAM at 512MB), this caused persistent `Out Of Memory (OOM)` crashes and CrashLoopBackOff states.
We refactored the embedder to use `fastembed`, which runs the exact same `all-MiniLM-L6-v2` model weights but operates on the highly optimized **ONNX** runtime instead of PyTorch. This slashed our memory footprint by 75% down to ~150MB, completely solving the server crashes while maintaining identical RAG retrieval accuracy.

**Interviewer: How does the Nudge Engine achieve such low latency?**

**Engineer:** In a live call environment, if a nudge takes 3 seconds to generate, the conversation has already moved on. We built the Nudge Engine using the `llama-3.3-70b-versatile` model hosted on **Groq**. Groq utilizes specialized LPU (Language Processing Unit) hardware rather than traditional GPUs. 
By sending a tightly constrained sliding window (only the last 6 messages) to Groq and requesting a strict JSON object output, we achieve complete semantic extraction in **under 600 milliseconds**. This allows the UI to flash "Frustration Detected" almost instantly without relying on brittle regex keyword matching.

**Interviewer: What steps did you take to handle Multilingual calls like Taglish and Bahasa Indonesia?**

**Engineer:** Non-English Voice AI is notoriously difficult due to ASR hallucination and poor code-switching (mixing languages). 
- For **Taglish (Philippines)**, we explicitly instructed the LLM in the system prompt to use local conversational connectors ("po/opo") and framed concepts locally (e.g., comparing premiums to the "cost of a daily coffee"). 
- For **Bahasa Indonesia**, we used specific honorifics ("Pak / Bu") and Jakarta-centric finance terminology.
- To prevent the English-biased Deepgram ASR from mistranscribing foreign words (like mistaking "Halo Budi" for "Hello Buddhists"), we instructed the LLM to output cleanly formatted, fully spelled-out numbers and punctuation, which helps the ElevenLabs TTS engine pronounce the foreign text much more naturally.

---

## 4. Business Value & Security

**Interviewer: How does the system handle lead generation?**

**Engineer:** When a caller completes a consultation or requests human escalation (e.g., due to extreme frustration or complex compliance questions), the LLM executes the `submit_lead_to_crm` tool. This captures the user's inferred details (household size, budget, name) and posts it to the backend via webhook. The backend generates a unique `lead_id` and persists it into our mock CRM database (`leads.json`). We even expose an API endpoint (`/leads`) so administrators can monitor these incoming leads in real-time.

**Interviewer: How do you prevent the AI from giving illegal medical or legal advice?**

**Engineer:** Zero-hallucination compliance is our top priority. We implement this through:
1. **Strict Prompting:** The system prompt explicitly forbids guessing rates or Medicaid income cutoffs.
2. **Forced RAG:** If asked a policy question, the LLM is instructed that it *must* trigger the `query_knowledge_base` tool.
3. **Safe Fallback:** If the vector database returns no relevant chunks, the LLM is programmed to trigger a fallback script: *"I do not have exact details on that subject... let me connect you directly with one of our licensed human insurance specialists."* It then fires the CRM tool to escalate the call.
