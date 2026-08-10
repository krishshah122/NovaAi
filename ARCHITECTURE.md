# System Architecture

This document provides a high-level overview of the Nova AI Advisor system architecture, detailing how the Voice Agent, Knowledge Base, and Real-Time Nudge Engine interact.

## High-Level Architecture Diagram

```mermaid
graph TD
    %% Define Styles
    classDef frontend fill:#3b82f6,stroke:#1e3a8a,stroke-width:2px,color:#fff;
    classDef backend fill:#10b981,stroke:#065f46,stroke-width:2px,color:#fff;
    classDef vapi fill:#8b5cf6,stroke:#4c1d95,stroke-width:2px,color:#fff;
    classDef db fill:#f59e0b,stroke:#b45309,stroke-width:2px,color:#fff;
    classDef groq fill:#ef4444,stroke:#991b1b,stroke-width:2px,color:#fff;

    %% Nodes
    User(("User Voice")):::frontend
    Browser["Web Caller UI<br/>(HTML/JS)"]:::frontend
    Vapi["Vapi AI Cloud<br/>Voice Agent Orchestrator"]:::vapi
    FastAPI["FastAPI Webhook Server<br/>(Nova Backend)"]:::backend
    Pinecone[("Pinecone Vector DB<br/>RAG Knowledge")]:::db
    GroqLLM["Groq Llama-3<br/>Nudge Engine"]:::groq
    CRM[("Mock CRM<br/>leads.json")]:::db

    %% Connections
    User <-->|Mic / Speaker| Browser
    Browser <-->|WebRTC Audio| Vapi
    
    %% Vapi Backend integrations
    Vapi -->|"Server URL Webhooks<br/>Tool Calls"| FastAPI
    FastAPI -->|"Tool Results<br/>(Query/Submit)"| Vapi

    %% Database integrations
    FastAPI <-->|Similarity Search| Pinecone
    FastAPI -->|Append Lead| CRM

    %% Live Dashboard Nudges
    Browser -->|Live Transcripts| FastAPI
    FastAPI <-->|Signal Extraction| GroqLLM
    FastAPI -.->|Return JSON Nudge| Browser
```

## Key Components

### 1. Frontend Web Caller (`web_caller.html`)
- Built using Vapi's Web SDK.
- Handles WebRTC audio connections with the Vapi Cloud.
- Dynamically intercepts `transcript` and `function-call` events to power the Live Agent Dashboard.
- Submits live transcripts to the Nudge Engine.

### 2. Vapi AI Orchestrator
- Handles Speech-to-Text (ASR) via Deepgram Nova-2.
- Handles LLM planning and dialogue generation.
- Handles Text-to-Speech (TTS) via ElevenLabs and Cartesia.
- Emits Webhook requests to our FastAPI server whenever the AI decides it needs to use a tool.

### 3. FastAPI Backend (`server.py`)
- **`POST /webhook/vapi`**: The core bridge. It catches tool calls from Vapi, routes them to local Python functions (`execute_query_knowledge_base`, `execute_submit_lead_to_crm`), and returns the results.
- **`POST /api/analyze_transcript`**: The Nudge Engine endpoint. Receives transcript buffers from the frontend.

### 4. Knowledge Base (`pinecone`)
- Populated by `cleaner.py` and `indexer.py`.
- Stores strictly curated, public-domain health and multifinance policies encoded into dense vectors using `all-MiniLM-L6-v2`.

### 5. Groq Nudge Engine (`nudge_engine.py`)
- Powered by `llama-3.3-70b-versatile` for ultra-low latency (< 600ms).
- Semantically extracts business signals (frustration, cross-sell, compliance) from a sliding conversation window without relying on brittle Regex rules.
