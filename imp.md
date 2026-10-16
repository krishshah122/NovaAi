# Nova AI Interview Prep – Senior AI Engineer Questions and Answers

This document is a draft interview prep guide for the Nova AI project. It is designed for a senior-level AI/ML engineering discussion and covers architecture, technology choices, technical trade-offs, production constraints, and business reasoning.

---

## 1) Project Overview

### Q1. What is Nova AI, and what problem does it solve?
**Answer:** Nova AI is a real-time voice assistant and RAG platform built for insurance advisory calls. The key problem it solves is giving accurate, grounded answers during live calls while preventing AI hallucinations. The system combines voice orchestration, retrieval-augmented generation, and real-time live agent assistance in one workflow.

### Q2. Why is the project important in the healthcare/insurance domain?
**Answer:** Insurance and healthcare questions are sensitive, compliance-heavy, and often require exact policy details. A model that guesses can cause legal or financial risk. The project solves this by grounding answers in a curated knowledge base and forcing tool-based retrieval before responding.

### Q3. What is the main difference between a normal chatbot and this voice AI platform?
**Answer:** A normal chatbot works in a text interface and can take time to answer. This system operates in real time over voice calls, must handle ASR noise, multilingual speech, low-latency responses, and policy-grounded answers with tool calls and compliance escalation.

### Q4. How would you describe the business value of this project?
**Answer:** It reduces human agent workload, improves lead qualification, shortens call time, and increases conversion. At the same time, it protects the business from inaccurate answers and compliance problems by routing uncertain questions to a human specialist.

### Q5. What are the three biggest product goals of Nova AI?
**Answer:** First, accurate and grounded insurance answers. Second, low-latency live call support. Third, real-time human agent assistance through transcript analysis and lead capture.

---

## 2) Architecture and System Design

### Q6. Can you walk me through the end-to-end flow of a call?
**Answer:** A caller enters the UI, connects to Vapi through WebRTC, and speaks. Vapi uses Deepgram for ASR and handles the voice pipeline. If the user asks a policy question, the model triggers a webhook to the FastAPI backend. The backend queries Pinecone for relevant policy chunks and returns the answer. At the same time, the frontend sends transcript updates to the nudge engine for real-time sentiment and business signal analysis.

### Q7. Why is the architecture split into Vapi, FastAPI, and the nudge engine?
**Answer:** Separation of concerns is critical. Vapi handles the audio layer, FastAPI handles business logic and retrieval, and the nudge engine focuses on transcript analysis. This ensures voice latency is not blocked by heavy AI analysis and allows each component to scale independently.

### Q8. Why use a separate backend if Vapi already handles LLM logic?
**Answer:** Vapi orchestrates the conversation, but the backend is where the business-critical logic lives: retrieval, validation, compliance checks, lead capture, and knowledge-base querying. This is the control plane that makes the system reliable and auditable.

### Q9. What is the role of the frontend in this architecture?
**Answer:** The frontend acts as the caller UI and streaming dashboard. It triggers the call, captures live transcript frames, and sends them to the nudge engine for compliance and sales signal detection. It also provides the user’s multilingual interface.

### Q10. Why is FastAPI a strong choice here?
**Answer:** FastAPI is asynchronous, fast, and easy to integrate with Pydantic validation. It is well-suited for webhook triggers, concurrent requests, and real-time voice integrations. It also works naturally with Python ML tooling used in the project.

### Q11. Why not build everything inside Vapi directly?
**Answer:** Vapi is excellent for orchestration but not ideal for custom retrieval pipelines, local vector search logic, compliance workflows, and internal business process management. A custom backend gives us control over safety, data flow, and debugging.

### Q12. How does the RAG flow actually work in this project?
**Answer:** The model identifies that a user asks a factual question. It triggers a tool call or webhook to the backend. The backend searches Pinecone using embeddings from the question and retrieves the most relevant chunks. Those chunks are used to answer grounded questions and avoid hallucination.

### Q13. Why is the architecture designed with strict tool forcing?
**Answer:** This reduces hallucinations by making the model use a retrieval tool before answering policy facts. It turns the LLM from a free-form reasoner into a controlled policy assistant.

---

## 3) Knowledge Base and Retrieval Design

### Q14. What is the purpose of the knowledge base in this project?
**Answer:** The knowledge base stores curated insurance and health policy information in vector form so the AI can retrieve factual policy answers quickly and reliably during live calls.

### Q15. How is the knowledge base built?
**Answer:** It begins with raw documents, cleans and filters them, splits them into logical chunks, embeds them into vectors, and then indexes them into Pinecone. Each stage is designed to preserve context and reduce noise.

### Q16. Why use semantic chunking instead of random chunking?
**Answer:** Insurance policies are context-heavy. If a deductible is split away from its plan description, the model may answer with incomplete or incorrect information. Semantic chunking keeps related sections together, which improves retrieval quality.

### Q17. Why not use a simple 500-token chunk split?
**Answer:** Fixed-size chunking can break logical units. A plan summary and its deductible may be separated. That leads to retrieval of incomplete facts and bad answers. Semantic and section-aware chunking is safer for compliance-sensitive content.

### Q18. What is the role of the Pydantic schema?
**Answer:** It ensures all knowledge base records conform to a strict structure. That helps with validation, data quality, filtering, and consistent indexing.

### Q19. What happens if the same policy file is ingested twice?
**Answer:** The system detects duplicates using controlled identifiers and hashing so identical or near-identical records do not pollute the vector index. This improves precision and reduces retrieval noise.

### Q20. How do you handle PII before indexing data?
**Answer:** The cleaner removes or masks phone numbers, emails, SSNs, and other sensitive patterns using regex. This prevents sensitive personal data from being embedded or sent to third-party services.

---

### 🔍 Deep Dive: How Regex, MD5 Hashing, and Jaccard Similarity Work in the Data Pipeline

The `cleaner.py` module uses three distinct techniques to protect data and eliminate duplicates. Below is an in-depth walkthrough of each technique, how it works internally, and the order they execute.

#### Technique 1: Regex (Regular Expressions) — PII Detection & Redaction

Regex is a pattern-matching language built into Python. The cleaner defines four regex patterns to find and replace sensitive personal information before any text reaches the embedding or indexing stages.

**The Four PII Patterns Used:**

| PII Type | Regex Pattern | What It Detects | Example Match |
|----------|--------------|-----------------|---------------|
| Email | `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z\|a-z]{2,7}\b` | Any email address format | `john.doe@example.com` |
| Phone | `\b(?:\+?1[-. ]?)?\(?([0-9]{3})\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})\b` | US phone numbers in any format (parentheses, dashes, dots, spaces) | `(800) 555-0199`, `800.555.0199`, `+1-800-555-0199` |
| SSN | `\b\d{3}[- ]?\d{2}[- ]?\d{4}\b` | Social Security Numbers with or without separators | `123-45-6789`, `123 45 6789`, `123456789` |
| Credit Card | `\b(?:\d[ -]*?){13,16}\b` | 13 to 16 digit card numbers with optional separators | `4111-2222-3333-4444` |

**How a Regex Pattern Works (SSN Example Breakdown):**

```
Pattern:  \b\d{3}[- ]?\d{2}[- ]?\d{4}\b

Symbol-by-symbol:
  \b      →  Word boundary (match must start/end at a word edge, not mid-word)
  \d{3}   →  Exactly 3 digits (0-9)
  [- ]?   →  Optionally one dash or one space (the ? means "0 or 1 times")
  \d{2}   →  Exactly 2 digits
  [- ]?   →  Optionally one dash or one space
  \d{4}   →  Exactly 4 digits
  \b      →  Word boundary

Result: Matches "123-45-6789", "123 45 6789", and "123456789"
        Does NOT match "12345" (too short) or "hello" (not digits)
```

**What Happens When a Match Is Found:**

```
Input:    "Call me at 800-555-0199 about my Gold plan policy"
Process:  PHONE regex matches "800-555-0199"
          pattern.sub("[PII_REDACTED_PHONE]", text) replaces it
Output:   "Call me at [PII_REDACTED_PHONE] about my Gold plan policy"
```

The method returns a tuple: `(redacted_text, had_pii)` — the boolean flag is stored in the record's `pii_flag` field so auditors know which records originally contained sensitive data.

**Credit Card False-Positive Protection:**  
The cleaner includes an extra safety check for credit cards. Since the broad pattern `(?:\d[ -]*?){13,16}` could accidentally match short numbers like years (2024), it strips all non-digit characters and only flags the match if the clean digit count is genuinely between 13 and 16.

---

#### Technique 2: MD5 Hashing — Exact Duplicate Detection

MD5 (Message Digest Algorithm 5) is a one-way hash function that converts any input text into a fixed 32-character hexadecimal fingerprint. The same input always produces the same output, but different inputs produce different outputs.

**The Formula Used:**

```python
text_hash = hashlib.md5(text.strip().lower().encode('utf-8')).hexdigest()
```

**Step-by-Step Breakdown:**

```
Input:      "Bronze plans have LOW premiums  "

Step 1 — .strip()         →  "Bronze plans have LOW premiums"     (removes trailing spaces)
Step 2 — .lower()         →  "bronze plans have low premiums"     (case-insensitive comparison)
Step 3 — .encode('utf-8') →  b'bronze plans have low premiums'    (converts string to bytes)
Step 4 — hashlib.md5(...) →  applies the MD5 algorithm internally
Step 5 — .hexdigest()     →  "a3f2b8c9e1d4f7a2b3c8d9e0f1a2b3c4"  (32-char unique fingerprint)
```

**How Duplicate Detection Works:**

The cleaner maintains a `seen_hashes` set. For each new record:

```
Record 1: "Bronze plans have low premiums"  →  hash: "a3f2b8c9..."
          Check: Is "a3f2b8c9..." in seen_hashes?  NO → Add to set, KEEP record ✅

Record 2: "Silver plans have mid premiums"  →  hash: "f7e1d2a0..."
          Check: Is "f7e1d2a0..." in seen_hashes?  NO → Add to set, KEEP record ✅

Record 3: "Bronze plans have low premiums"  →  hash: "a3f2b8c9..."  (same as Record 1!)
          Check: Is "a3f2b8c9..." in seen_hashes?  YES → SKIP record 🚫 (exact duplicate)
```

**Why MD5 and Not Direct String Comparison?**  
Comparing full text strings is expensive for large documents. MD5 reduces any text (even a 10,000-word document) to a fixed 32-character fingerprint, making comparison instant regardless of document size. It also provides a clean way to store "seen" records in a memory-efficient set.

---

#### Technique 3: Jaccard Similarity — Near-Duplicate Detection

MD5 only catches exact duplicates. If someone slightly rewords a record ("Bronze plans have lower premiums" vs. "Bronze plans feature low premiums"), the MD5 hashes will be completely different. Jaccard similarity solves this by measuring how much word overlap two texts share.

**The Formula:**

```
Jaccard Similarity = |A ∩ B| / |A ∪ B|

Where:
  A = set of unique words in Text A
  B = set of unique words in Text B
  A ∩ B = words that appear in BOTH texts (intersection)
  A ∪ B = all unique words from BOTH texts combined (union)
```

**Worked Example:**

```
Text A: "bronze plans have low premiums"
Text B: "bronze plans feature low premiums"

Word Set A: {bronze, plans, have, low, premiums}         → 5 unique words
Word Set B: {bronze, plans, feature, low, premiums}       → 5 unique words

Intersection (A ∩ B): {bronze, plans, low, premiums}      → 4 shared words
Union (A ∪ B): {bronze, plans, have, feature, low, premiums} → 6 total unique words

Jaccard = 4 / 6 = 0.667 (66.7% similar)
```

**The Threshold:**  
The cleaner uses a threshold of `0.85` (85%). If Jaccard similarity between a new record and any previously accepted record is ≥ 85%, the new record is considered a near-duplicate and is skipped. In the example above, 66.7% is below 85%, so both records would be kept.

**A Near-Duplicate Example That Would Be Caught:**

```
Text A: "The bronze plan has lower monthly premiums but higher deductibles when you need care"
Text B: "The bronze plan has lower monthly premiums but higher deductibles when you get care"

Only one word differs ("need" vs "get"), so Jaccard ≈ 0.93 (93%)
93% ≥ 85% threshold → Text B is SKIPPED as a near-duplicate 🚫
```

**Performance Note:**  
Each new record is compared against ALL previously accepted records. For Record N, the cleaner runs N-1 Jaccard comparisons. This is acceptable because the knowledge base typically has dozens of records (not millions). At enterprise scale, techniques like MinHash or SimHash would replace brute-force Jaccard.

---

#### Processing Order and Why It Matters

The cleaner executes all three techniques in a specific order on every record. This order is intentional for efficiency:

```
For each record in the input list:
│
├─ Step 1: NORMALIZE TEXT (fix whitespace, standardize terms)
│   Always runs. Ensures consistent comparison for all subsequent steps.
│
├─ Step 2: MD5 HASH CHECK (exact duplicate?)
│   Instant O(1) lookup in the hash set.
│   If duplicate → SKIP immediately (no further processing)
│
├─ Step 3: JACCARD SIMILARITY CHECK (near-duplicate?)
│   More expensive: compares word sets against every previous record.
│   Only runs if MD5 passed (no point doing expensive check on exact dupes).
│   If near-duplicate (≥ 85%) → SKIP immediately
│
└─ Step 4: REGEX PII SCAN (all 4 patterns)
    Only runs if the record survived both dedup checks.
    No point redacting PII in a record that will be thrown away.
    Scans all 4 patterns (Email, Phone, SSN, Credit Card).
    Replaces matches with [PII_REDACTED_TYPE] tags.
    Sets pii_flag = True on the record.
```

**Why cheapest checks first?**  
MD5 hashing is nearly instantaneous (O(1) set lookup). Jaccard requires iterating over word sets of every previously accepted record. Regex scanning requires multiple pattern passes over the full text. By putting MD5 first, exact duplicates are eliminated before any expensive computation runs.

---

### Q21. Why is a local backup like vector_store.json useful?
**Answer:** It acts as a fallback in case Pinecone is unavailable or slow. In production, this helps maintain continuity and resilience without dropping the whole service.

### Q22. What is the main challenge of a vector database in this type of project?
**Answer:** The challenge is not only retrieval speed but also retrieval accuracy. The model must retrieve the right policy clause and not a semantically similar but wrong document. Data quality and chunk boundaries are critical.

---

## 4) Model and Library Choices

### Q23. Why did you choose fastembed instead of sentence-transformers with PyTorch?
**Answer:** The original setup caused heavy memory usage. PyTorch footprints are large, and this became a problem in constrained cloud environments. fastembed uses ONNX and is much lighter, which reduces RAM usage and removes OOM risks.

### Q24. Why is ONNX important in this project?
**Answer:** ONNX is optimized for fast CPU inference and lower memory overhead. It allows embedding generation to run efficiently in a constrained environment without sacrificing much performance.

### Q25. Why use Pinecone instead of ChromaDB or pgvector?
**Answer:** Pinecone is a managed, serverless vector database with low-latency search and lower operational burden. For a real-time voice application, that is a strong trade-off compared with managing self-hosted vector infrastructure.

### Q26. Why not use OpenAI embeddings instead of local embeddings?
**Answer:** Cloud embeddings add latency, cost, and external API dependency. Local embedding generation is faster, cheaper, and more reliable for repeated policy lookups in a live call environment.

### Q27. Why choose Groq for the nudge engine?
**Answer:** Groq provides low-latency inference for structured JSON output, which matches the requirement of a live transcript analysis engine. It is much better suited to this use case than a slower general-purpose LLM service.

### Q28. Why is Groq better than OpenAI GPT-4o for this specific task?
**Answer:** The nudge engine needs under a second of response time. OpenAI models may be more capable in general, but Groq is designed for faster inference and lower latency, which is the decisive factor in this workflow.

### Q29. Why use Vapi instead of building your own WebRTC agent system?
**Answer:** Building raw audio handling, barge-in detection, ASR routing, and TTS orchestration is extremely complex. Vapi simplifies that infrastructure and lets the team focus on business logic and retrieval accuracy.

### Q30. What is the role of Deepgram in your architecture?
**Answer:** Deepgram provides streaming transcription that is fast enough for live voice interactions. This is critical because the system has to process speech quickly and keep call flow natural.

### Q31. What is the role of ElevenLabs in this stack?
**Answer:** ElevenLabs handles lifelike TTS generation so the system can speak responses back to users naturally. It is used to make the voice experience sound realistic and clear.

### Q32. Why is BeautifulSoup and PyMuPDF included in the stack?
**Answer:** They help extract clean text from web pages and PDFs. This is important because a lot of policy information is embedded in web-based or PDF-based sources.

### Q33. How does tiktoken help in the chunking strategy?
**Answer:** It helps estimate token usage precisely when splitting documents. This is important because the retrieval and generation flow must respect token budgets and maintain consistent chunk quality.

---

## 5) Real-Time Voice and Nudge Engine

### Q34. What is the live nudge engine, and why is it important?
**Answer:** The nudge engine analyzes transcript windows in real time to detect frustration, compliance signals, and cross-sell opportunities. This helps a human agent intervene at the right moment during a live call.

### Q35. What is the sliding-window technique?
**Answer:** It looks at only the most recent transcript segment instead of the whole conversation. This keeps analysis focused and low latency while still capturing the latest context.

### Q36. Why is the nudge engine required to return JSON output?
**Answer:** It enables structured downstream processing. The dashboard or app can reliably parse fields like signal type, confidence, and recommended action without fragile text parsing.

### Q37. What are the biggest risks in a real-time nudge engine?
**Answer:** Noisy audio, ASR errors, outdated context, and token saturation. If the conversation drifts too far, the important signal may fall out of the sliding window and be missed.

### Q38. How do you deal with multilingual voice issues in this project?
**Answer:** The project uses localized prompts, culturally adapted phrasing, and explicit formatting for numbers and currency. This helps reduce ASR errors and makes TTS more natural in Taglish and Bahasa Indonesian contexts.

---

## 6) Safety, Compliance, and Production Trade-offs

### Q39. How do you prevent the model from hallucinating policy answers?
**Answer:** The project enforces tool-based retrieval, strict system prompts, and fallback escalation when no trusted answer exists. The model is instructed not to guess and to rely on the knowledge base for factual questions.

### Q40. What is your safety strategy when the system is unsure?
**Answer:** If the retrieval score is low or the answer is outside policy scope, the system should avoid answering directly and instead escalate to a human specialist or a compliant fallback message.

### Q41. What is the role of human escalation in this design?
**Answer:** Human escalation is a safety net. It protects the business and the customer by sending ambiguous, high-risk, or complex scenarios to a licensed human specialist.

### Q42. Why is a lead engine important in a voice AI product?
**Answer:** It converts live conversations into structured opportunities. It allows the system to capture potential customer intent, budget, and relevant details and push them into a CRM or database.

### Q43. How do you think about cost and scaling in this architecture?
**Answer:** The system is built with low-latency APIs and optimized embedding inference because the cost of waiting is high in a live call environment. The architecture balances speed, safety, and economics by using efficient models and selective third-party services.

### Q44. What would be your biggest concern in production at scale?
**Answer:** Scaling bottlenecks around real-time transcript analysis, API rate limits, and ensuring compliance under noisy call conditions. At larger scale, smaller specialized models and internal inference would likely replace heavy third-party calls.

---

## 7) Product and Engineering Judgment

### Q45. If you had to improve this system next, what would you change first?
**Answer:** I would focus on evaluation and observability: better retrieval scoring, logging of every tool call, call-level analytics, and more robust fallback metrics. I would also add automated regression tests around policy retrieval quality and multilingual transcripts.

### Q46. Why are retrieval tests important here?
**Answer:** Because the whole system depends on answering accurate policy questions. Without retrieval validation, the project might appear to work but still fail on factual accuracy.

### Q47. What makes this project a strong AI engineering portfolio piece?
**Answer:** It combines multiple advanced AI patterns: RAG, embeddings, vector search, live analytics, multilingual prompts, lower-latency design, and production safety. It is not just a toy demo but an end-to-end applied AI product.

### Q48. How would you explain this project in one sentence to a hiring manager?
**Answer:** Nova AI is a real-time voice and RAG system that combines policy-grounded retrieval, multilingual voice orchestration, and live compliance nudging to create a safe and scalable insurance advisory assistant.

---

## Short Interview-Friendly Summary

If you need a compact version for speaking:  
- This project uses Vapi for voice orchestration, FastAPI for the backend control plane, Pinecone for vector retrieval, and Groq for low-latency nudge analysis.  
- The knowledge base is cleaned, chunked, embedded, and indexed using a custom pipeline.  
- The main design goal is safe, grounded answers under real-time constraints.  
- The project trades off latency, cost, and operational simplicity while emphasizing compliance and reliability.

---

## Final Tip for Interview Preparation

When answering questions, always explain three things clearly:
1. What the technology is.
2. Why it was chosen for this problem.
3. What trade-off or risk it solved.

That structure sounds strong and senior-level because it shows engineering judgment, not just technical familiarity.
