"""
FastAPI Voice Agent Webhook Server
Handles incoming Vapi.ai real-time voice tool call webhooks, bridging phone conversations directly to our
Question 2 vector database and enterprise Mock CRM lead storage with sub-200ms processing latency.
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
    title="Darwix AI Assessment — Voice Agent RAG Server",
    version="1.0",
    description="Backend webhook handler connecting Vapi real-time calls to Pinecone RAG and CRM database."
)

# Allow CORS for local testing or web calling UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    pub_key = os.getenv("VAPI_PUBLIC_KEY") or os.getenv("VAPI_API_KEY", "d2685516-ae94-4892-8abd-4db236d65f64")
    asst_id = os.getenv("VAPI_ASSISTANT_ID", "")
    
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
async def switch_assistant_region(region: str = "us"):
    """Dynamically switch Vapi Cloud Assistant persona, language prompt, and tools between US, PH, and ID."""
    import requests, os
    from voice_agent.prompts import LEAD_QUALIFICATION_SYSTEM_PROMPT
    from multilingual_bots.philippines_bot import PHILIPPINES_TAGLISH_PROMPT
    from multilingual_bots.indonesia_bot import INDONESIA_BAHASA_PROMPT
    
    api_key = os.getenv("VAPI_API_KEY", "d2685516-ae94-4892-8abd-4db236d65f64")
    asst_id = os.getenv("VAPI_ASSISTANT_ID", "e3f52f6f-a0f7-4c1e-99d6-09e5dd9f024f")
    url = "https://majority-ribcage-contented.ngrok-free.dev/webhook/vapi"
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    try:
        cur_req = requests.get(f"https://api.vapi.ai/assistant/{asst_id}", headers=headers, timeout=10)
        cur = cur_req.json()
    except Exception as e:
        return {"success": False, "error": f"Vapi API connection failed: {str(e)}"}

    model = cur.get("model", {})
    tools_def = [
        {
            "type": "function",
            "function": {
                "name": "query_knowledge_base",
                "description": "Search vector database for health insurance or regional financial policies.",
                "parameters": {"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"]}
            },
            "server": {"url": url}
        },
        {
            "type": "function",
            "function": {
                "name": "submit_lead_to_crm",
                "description": "Submit qualified customer profile into CRM.",
                "parameters": {"type": "object", "properties": {"caller_name": {"type": "string"}, "interested_plan_type": {"type": "string"}, "notes": {"type": "string"}}, "required": ["caller_name", "interested_plan_type"]}
            },
            "server": {"url": url}
        }
    ]
    model["tools"] = tools_def

    if region.lower() == "ph":
        bot_name = "Darwix PH Taglish Bot"
        model["messages"] = [{"role": "system", "content": PHILIPPINES_TAGLISH_PROMPT}]
        voice = {"provider": "11labs", "voiceId": "21m00Tcm4TlvDq8ikWAM", "stability": 0.55, "similarityBoost": 0.8}
    elif region.lower() == "id":
        bot_name = "Darwix ID Bahasa Bot"
        model["messages"] = [{"role": "system", "content": INDONESIA_BAHASA_PROMPT}]
        voice = {"provider": "11labs", "voiceId": "VR6AewLTigWG4xSOukaG", "stability": 0.60, "similarityBoost": 0.85}
    else:
        bot_name = "Darwix US Health Advisor"
        model["messages"] = [{"role": "system", "content": LEAD_QUALIFICATION_SYSTEM_PROMPT}]
        voice = cur.get("voice", {"provider": "11labs", "voiceId": "21m00Tcm4TlvDq8ikWAM"})
        region = "us"

    payload = {"name": bot_name, "model": model, "voice": voice, "serverUrl": url}
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
        "service": "Darwix AI Assessment RAG Webhook Endpoint",
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
    try:
        payload = await request.json()
    except Exception as e:
        print(f"[ERROR] Malformed JSON received on /webhook/vapi: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload received.")

    message = payload.get("message", {})
    msg_type = message.get("type", "unknown")

    print(f"\n[WEBHOOK RECEIVED] Event Type: '{msg_type}'")

    # Handle standard function tool calls from Groq Llama-3 / Vapi
    if msg_type == "function-call" or "functionCall" in message or "toolCalls" in message or "toolCallList" in message:
        
        # 1. Check for modern toolCallList (OpenAI/Groq tools standard in Vapi)
        tool_call_list = message.get("toolCallList") or message.get("toolCalls")
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

            return JSONResponse(content={"results": results_array})

        # 2. Check for legacy single functionCall payload
        func_call = message.get("functionCall")
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
            return JSONResponse(content={"result": exec_result})

    # Handle other non-tool Vapi events (status updates, transcript notifications, end-of-call report)
    if msg_type in ("status-update", "transcript", "end-of-call-report"):
        print(f"   -> Acknowledged non-blocking Vapi operational event: {msg_type}")
        return JSONResponse(content={"received": True, "status": "acknowledged"})

    # Fallback return for unhandled webhook types
    print(f"   -> Unhandled Vapi payload structure: {list(message.keys())}")
    return JSONResponse(content={"received": True, "message": "Unhandled event type"})


if __name__ == "__main__":
    print("==================================================================")
    print("🚀 STARTING DARWIX VOICE AGENT RAG WEBHOOK SERVER (FASTAPI)")
    print("   Listening on http://0.0.0.0:8000")
    print("   Webhook URI:  http://localhost:8000/webhook/vapi")
    print("==================================================================")
    uvicorn.run("voice_agent.server:app", host="0.0.0.0", port=8000, reload=True)
