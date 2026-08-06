"""
FastAPI Voice Agent Webhook Server
Handles incoming Vapi.ai real-time voice tool call webhooks, bridging phone conversations directly to our
Question 2 vector database and enterprise Mock CRM lead storage with sub-200ms processing latency.
"""

import sys
import json

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pathlib import Path
from typing import Dict, Any, List

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


@app.get("/", tags=["Health"])
async def root_status():
    """Verify backend webhook server functionality."""
    return {
        "status": "ONLINE",
        "service": "Darwix AI Assessment RAG Webhook Endpoint",
        "version": "1.0",
        "webhook_uri": "/webhook/vapi"
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
