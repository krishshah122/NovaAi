# Darwix AI — Real-Time Voice Agent & RAG Assessment

An end-to-end Voice AI implementation addressing all 4 questions of the AI Engineer Assessment. This repository bridges Vapi.ai's conversational web orchestrator with a highly accurate Pinecone Vector RAG database and a sub-second Groq Nudge Engine.

## Assessment Matrix
| Question | Implementation Highlights | Artifacts |
|----------|---------------------------|-----------|
| **Q1: Knowledge-Grounded Voice Agent** | Connected Vapi to a local FastAPI backend. Strict prompting rules prevent hallucination. Lead qualification tool appends to CRM. | `voice_agent/`, `web_caller.html` |
| **Q2: Production-Ready Knowledge Base** | Scraped Healthcare.gov, cleaned text via regex, deduplicated via MD5, chunked, and embedded into Pinecone. | `knowledge_base/`, `Q2_RETRIEVAL_TESTS.md` |
| **Q3: Native-Language Voice Bots** | Taglish (Mika) and Bahasa (Budi) bots. See *Multilingual Evaluation* section below. | `multilingual_bots/` |
| **Q4: Live Insights & Nudges** | Groq Llama-3 stream analyzer evaluating transcript buffers in <600ms to detect compliance, frustration, and cross-sell signals. | `voice_agent/nudge_engine.py` |

---

## 🚀 Quick Start Guide

### 1. Environment Setup
Create a `.env` file in the root directory based on `.env.example`:
```env
PINECONE_API_KEY=your_key
GROQ_API_KEY=your_key
VAPI_PRIVATE_API_KEY=your_key
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

## 🌎 Question 3: Multilingual Evaluation & Compromises

### ASR (Speech-to-Text) Behavior
Vapi relies heavily on Deepgram Nova-2. While Nova-2 is world-class for English, it struggles natively with heavy regional accents or rapid code-switching without explicit configuration. 
- **The Challenge:** When testing the Indonesian bot, saying *"Halo Budi"* was sometimes mistranscribed as *"Hello, Buddhists"*.
- **Our Solution:** We modified the System Prompt to output strictly formatted, punctuation-clean numbers and words (e.g., spelling out *"dua juta"* instead of *2.000.000*) to aid the TTS engine in recovering from bad ASR transcripts. 

### TTS (Text-to-Speech) Compromises
- **Taglish:** ElevenLabs does not have a dedicated "Tagalog" model. We forced it to sound authentic by using a generic multicultural voice and strictly prompting the LLM to use heavy Filipino conversational connectors (*"po/opo", "sir/ma'am"*).
- **Bahasa Indonesia:** We configured the AI to use local honorifics (*"Pak / Bu"*) and regional Jakarta finance terms (*"DP", "Angsuran", "Tenor"*) to avoid sounding like a robotic literal translation.

---

## ⚡ Question 4: Nudge Engine Limitations & 10x Scale

Our Live Agent Assist Nudge Engine runs on `llama-3.3-70b-versatile` via Groq, achieving stunning ~500ms latency. 

**However, at 10x scale or in extremely noisy call center environments, the following limitations apply:**

1. **Token Window Saturation:** We currently feed the LLM a sliding window of the last 6 sentences. If a caller goes on a long, rambling 3-minute tangent, the "frustration" signal might fall out of the sliding window before the LLM evaluates it.
2. **ASR Hallucinations (Noisy Audio):** If background noise causes the ASR to transcribe *"I need to pee"* instead of *"I need a fee waiver"*, the semantic Nudge Engine might misinterpret the intent.
3. **Groq Rate Limiting:** While Groq is incredibly fast for single calls, scaling to 10,000 concurrent calls sending transcript chunks every 2 seconds would instantly exhaust standard Groq API rate limits. 
4. **Production Mitigation:** At scale, we would replace the heavy 70B LLM with a highly fine-tuned, localized classifier (like a fine-tuned `DistilBERT` or `Llama-3-8B`) deployed on dedicated vLLM infrastructure to evaluate nudges locally without API bottlenecks.
