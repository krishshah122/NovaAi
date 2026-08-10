"""
FastAPI Voice Agent Webhook Server
Handles incoming Vapi.ai real-time voice tool call webhooks, bridging phone conversations directly to our
Pinecone vector database and enterprise Mock CRM lead storage with sub-200ms processing latency.
"""

import sys
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pathlib import Path
from typing import Dict, Any, List
from pydantic import BaseModel

# Ensure project root in path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from voice_agent.rag_tool import execute_query_knowledge_base, execute_submit_lead_to_crm

app = FastAPI(
    title="Nova AI Real-Time Agent Bridge",
    description="Backend integrating Vapi.ai voice agents with CRM logic and Pinecone RAG.",
    version="1.0.0"
)

# Allow CORS for local testing or web calling UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    import threading
    import gc
    def load_model_in_background():
        try:
            print("[SYSTEM] Background thread: Loading AI embedding models into RAM...")
            from voice_agent.rag_tool import get_retriever
            get_retriever().embedder._load_model()
            gc.collect()  # Force garbage collection to free up memory spikes
            print("[SYSTEM] AI Models successfully loaded in background.")
        except Exception as e:
            print(f"[SYSTEM ERROR] Background model load failed: {e}")
            
    # Start the heavy model load in a background thread so it doesn't block Uvicorn startup
    threading.Thread(target=load_model_in_background, daemon=True).start()


@app.get("/call", response_class=HTMLResponse, tags=["UI"])
async def serve_web_caller():
    """Serve the clean interactive Web Calling audio application interface."""
    html_path = Path(__file__).resolve().parent / "web_caller.html"
    if not html_path.exists():
        return HTMLResponse(content="<h1>Error: web_caller.html not found in voice_agent directory</h1>", status_code=404)
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)


@app.get("/api/config", tags=["UI"])
async def get_client_config():
    """Securely serve frontend client connection configuration without exposing keys in visible form inputs."""
    import os
    pub_key = os.getenv("VAPI_PUBLIC_KEY")
    asst_id = os.getenv("VAPI_ASSISTANT_ID")
    
    config_path = Path(__file__).resolve().parent / "data" / "vapi_assistant_config.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as cf:
                asst_data = json.load(cf)
                asst_id = asst_data.get("id", asst_id)
        except Exception:
            pass

    return {
        "public_key": pub_key,
        "assistant_id": asst_id
    }


@app.api_route("/api/switch_assistant", methods=["GET", "POST"], tags=["UI"])
async def switch_assistant_region(request: Request, region: str = "us"):
    """Dynamically switch Vapi Cloud Assistant persona, language prompt, and tools between US, PH, and ID."""
    import requests, os
    from voice_agent.prompts import LEAD_QUALIFICATION_SYSTEM_PROMPT
    from multilingual_bots.philippines_bot import PHILIPPINES_TAGLISH_PROMPT
    from multilingual_bots.indonesia_bot import INDONESIA_BAHASA_PROMPT
    
    api_key = os.getenv("VAPI_API_KEY")
    asst_id = os.getenv("VAPI_ASSISTANT_ID")
    
    if not api_key or not asst_id:
        return {"success": False, "error": "Server missing VAPI_API_KEY or VAPI_ASSISTANT_ID environment variables."}
    base_url_str = str(request.base_url).rstrip("/")
    if base_url_str.startswith("http://") and "onrender.com" in base_url_str:
        base_url_str = base_url_str.replace("http://", "https://")
    url = base_url_str + "/webhook/vapi"
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    try:
        cur_req = requests.get(f"https://api.vapi.ai/assistant/{asst_id}", headers=headers, timeout=10)
        cur = cur_req.json()
    except Exception as e:
        return {"success": False, "error": f"Vapi API connection failed: {str(e)}"}

    model = cur.get("model", {})
    from voice_agent.rag_tool import VAPI_TOOLS_DEFINITIONS
    
    tools_def = []
    for tool in VAPI_TOOLS_DEFINITIONS:
        tools_def.append({
            "type": "function",
            "function": tool["function"],
            "server": {"url": url}
        })
    model["tools"] = tools_def

    if region.lower() == "ph":
        bot_name = "Nova PH Taglish Bot"
        model["messages"] = [{"role": "system", "content": PHILIPPINES_TAGLISH_PROMPT}]
        voice = {"provider": "11labs", "voiceId": "21m00Tcm4TlvDq8ikWAM", "stability": 0.55, "similarityBoost": 0.8}
    elif region.lower() == "id":
        bot_name = "Nova ID Bahasa Bot"
        model["messages"] = [{"role": "system", "content": INDONESIA_BAHASA_PROMPT}]
        voice = {"provider": "11labs", "voiceId": "VR6AewLTigWG4xSOukaG", "stability": 0.60, "similarityBoost": 0.85}
    else:
        bot_name = "Nova US Health Advisor"
        model["messages"] = [{"role": "system", "content": LEAD_QUALIFICATION_SYSTEM_PROMPT}]
        voice = cur.get("voice", {"provider": "11labs", "voiceId": "21m00Tcm4TlvDq8ikWAM"})
        region = "us"

    payload = {"name": bot_name, "model": model, "voice": voice}
    try:
        p = requests.patch(f"https://api.vapi.ai/assistant/{asst_id}", json=payload, headers=headers, timeout=10)
        if p.status_code == 200:
            print(f"   -> 🌐 Switched live cloud voice bot to: [{bot_name}]")
            return {"success": True, "region": region, "bot_name": bot_name}
        else:
            return {"success": False, "error": f"Vapi returned {p.status_code}: {p.text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


class NudgeRequest(BaseModel):
    session_id: str
    transcript_buffer: list

@app.post("/api/analyze_transcript", tags=["Nudge Engine"])
async def analyze_transcript(req: NudgeRequest):
    """Real-Time Nudge Engine: Analyze streaming transcript chunks and return actionable signals."""
    from voice_agent.nudge_engine import generate_nudge
    try:
        result = generate_nudge(req.session_id, req.transcript_buffer)
        return result
    except Exception as e:
        return {"nudge": None, "error": str(e), "latency_ms": 0}

@app.get("/", tags=["Health"])
async def root_status():
    """Verify backend webhook server functionality."""
    return {
        "status": "ONLINE",
        "service": "Nova AI RAG Webhook Endpoint",
        "version": "1.0",
        "webhook_uri": "/webhook/vapi",
        "web_caller_ui": "/call"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed diagnostic check on server database state."""
    leads_file = Path(__file__).resolve().parent / "data" / "leads.json"
    leads_count = 0
    if leads_file.exists():
        try:
            with open(leads_file, "r", encoding="utf-8") as f:
                leads_count = len(json.load(f))
        except Exception:
            pass

    return {
        "server": "HEALTHY",
        "vector_rag_bridge": "READY",
        "crm_leads_captured": leads_count
    }


@app.get("/leads", tags=["CRM"])
async def get_captured_leads():
    """Inspect captured qualification consultation leads and escalation alerts."""
    leads_file = Path(__file__).resolve().parent / "data" / "leads.json"
    if not leads_file.exists():
        return {"total_leads": 0, "leads": []}
    try:
        with open(leads_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"total_leads": len(data), "leads": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading leads database: {e}")


def _execute_function(func_name: str, args: Dict[str, Any]) -> str:
    """Router helper executing target function based on Vapi tool request."""
    if func_name == "query_knowledge_base":
        question = args.get("question", "")
        return execute_query_knowledge_base(question)
    elif func_name == "submit_lead_to_crm":
        return execute_submit_lead_to_crm(
            caller_name=args.get("caller_name", "Anonymous Caller"),
            email_or_phone=args.get("email_or_phone", "Not Provided"),
            household_size=args.get("household_size", 1),
            interested_plan_type=args.get("interested_plan_type", "Undetermined"),
            notes=args.get("notes", "Standard voice consultation"),
            needs_human_escalation=args.get("needs_human_escalation", False)
        )
    else:
        return f"ERROR: Unknown tool function '{func_name}' requested."


@app.post("/webhook/vapi", tags=["Webhook"])
async def vapi_webhook_handler(request: Request):
    """
    Primary real-time Vapi Tool Calling webhook receiver.
    Supports both legacy single functionCall payloads and modern toolCallList array structures.
    """
    import traceback
    from datetime import datetime as dt

    log_file = Path(__file__).resolve().parent / "data" / "webhook_debug.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        payload = await request.json()
    except Exception as e:
        print(f"[ERROR] Malformed JSON received on /webhook/vapi: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload received.")

    # Log the full incoming payload
    timestamp = dt.utcnow().isoformat()
    with open(log_file, "a", encoding="utf-8") as lf:
        lf.write(f"\n{'='*80}\n[{timestamp}] INCOMING WEBHOOK\n")
        lf.write(json.dumps(payload, indent=2, ensure_ascii=False)[:5000])
        lf.write("\n")

    message = payload.get("message", {})
    msg_type = message.get("type", "unknown")

    print(f"\n[WEBHOOK RECEIVED] Event Type: '{msg_type}' | Top-level keys: {list(payload.keys())}")

    # ---- TOOL CALL EXTRACTION (handle ALL known Vapi formats) ----
    tool_call_list = None
    func_call = None

    # Format A: message.toolCallList
    if message.get("toolCallList"):
        tool_call_list = message["toolCallList"]
        print(f"   -> Found tool calls in message.toolCallList ({len(tool_call_list)} calls)")

    # Format B: message.toolCalls
    elif message.get("toolCalls"):
        tool_call_list = message["toolCalls"]
        print(f"   -> Found tool calls in message.toolCalls ({len(tool_call_list)} calls)")

    # Format C: top-level toolCallList (some Vapi versions put it outside message)
    elif payload.get("toolCallList"):
        tool_call_list = payload["toolCallList"]
        print(f"   -> Found tool calls in TOP-LEVEL toolCallList ({len(tool_call_list)} calls)")

    # Format D: top-level toolCalls
    elif payload.get("toolCalls"):
        tool_call_list = payload["toolCalls"]
        print(f"   -> Found tool calls in TOP-LEVEL toolCalls ({len(tool_call_list)} calls)")

    # Format E: message.functionCall (legacy single call)
    elif message.get("functionCall"):
        func_call = message["functionCall"]
        print(f"   -> Found legacy functionCall: {func_call.get('name')}")

    # Format F: message.type == "function-call" with functionCall data
    elif msg_type == "function-call" and "functionCall" in message:
        func_call = message["functionCall"]
        print(f"   -> Found function-call type with functionCall: {func_call.get('name')}")

    # ---- EXECUTE TOOL CALLS ----
    if tool_call_list and isinstance(tool_call_list, list):
        results_array = []
        for tool_call in tool_call_list:
            tool_id = tool_call.get("id", "unknown_id")
            func_obj = tool_call.get("function", {})
            func_name = func_obj.get("name")

            raw_args = func_obj.get("arguments", "{}")
            if isinstance(raw_args, str):
                try:
                    args_dict = json.loads(raw_args)
                except json.JSONDecodeError:
                    args_dict = {}
            elif isinstance(raw_args, dict):
                args_dict = raw_args
            else:
                args_dict = {}

            print(f"   -> Executing Tool [{tool_id}]: {func_name}({args_dict})")
            exec_result = _execute_function(func_name, args_dict)

            results_array.append({
                "toolCallId": tool_id,
                "result": exec_result
            })

            # Log what we're returning
            with open(log_file, "a", encoding="utf-8") as lf:
                lf.write(f"[{timestamp}] TOOL RESULT for {func_name}:\n")
                lf.write(f"  toolCallId: {tool_id}\n")
                lf.write(f"  result length: {len(exec_result)} chars\n")
                lf.write(f"  result preview: {exec_result[:500]}\n\n")

        response = {"results": results_array}
        print(f"   -> Returning {len(results_array)} tool results to Vapi")
        return JSONResponse(content=response)

    if func_call and isinstance(func_call, dict):
        func_name = func_call.get("name")
        args_dict = func_call.get("parameters", {})
        if isinstance(args_dict, str):
            try:
                args_dict = json.loads(args_dict)
            except Exception:
                args_dict = {}

        print(f"   -> Executing Legacy Function: {func_name}({args_dict})")
        exec_result = _execute_function(func_name, args_dict)

        with open(log_file, "a", encoding="utf-8") as lf:
            lf.write(f"[{timestamp}] LEGACY RESULT for {func_name}:\n")
            lf.write(f"  result length: {len(exec_result)} chars\n")
            lf.write(f"  result preview: {exec_result[:500]}\n\n")

        return JSONResponse(content={"result": exec_result})

    # Handle other non-tool Vapi events (status updates, transcript notifications, end-of-call report)
    if msg_type in ("status-update", "transcript", "end-of-call-report", "hang", "speech-update",
                     "conversation-update", "model-output", "voice-input"):
        print(f"   -> Acknowledged non-blocking Vapi operational event: {msg_type}")
        return JSONResponse(content={"received": True, "status": "acknowledged"})

    # Handle assistant-request (sent when serverUrl is defined on the assistant)
    if msg_type == "assistant-request":
        print(f"   -> Acknowledged assistant-request, proceeding with default configuration.")
        # Vapi requires a JSON response containing an 'assistant' object to proceed with the call.
        return JSONResponse(content={"assistant": {}})

    # Fallback — LOG EVERYTHING so we can diagnose unknown formats
    print(f"   -> UNHANDLED Vapi payload! type='{msg_type}' message_keys={list(message.keys())} top_keys={list(payload.keys())}")
    with open(log_file, "a", encoding="utf-8") as lf:
        lf.write(f"[{timestamp}] UNHANDLED PAYLOAD:\n")
        lf.write(json.dumps(payload, indent=2, ensure_ascii=False)[:3000])
        lf.write("\n\n")
    return JSONResponse(content={"received": True, "message": "Unhandled event type"})


if __name__ == "__main__":
    print("==================================================================")
    print("🚀 STARTING NOVA VOICE AGENT RAG WEBHOOK SERVER (FASTAPI)")
    print("   Listening on http://0.0.0.0:8000")
    print("   Webhook URI:  http://localhost:8000/webhook/vapi")
    print("==================================================================")
    uvicorn.run("voice_agent.server:app", host="0.0.0.0", port=8000, reload=True)
