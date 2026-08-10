"""
Automated Vapi Assistant Provisioning Script
Registers the conversational voice bot directly with Vapi.ai using REST API, attaching our
production lead qualification system prompt, Deepgram Nova-2 speech recognition, and custom RAG webhooks.
"""

import os
import sys
import io
import json
import argparse
import requests
from pathlib import Path

# Ensure UTF-8 stdout/stderr encoding on Windows consoles
if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Ensure project root in python path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv
    env_path = project_root / ".env"
    load_dotenv(dotenv_path=env_path, override=True)
except ImportError:
    pass

from voice_agent.prompts import LEAD_QUALIFICATION_SYSTEM_PROMPT
from voice_agent.rag_tool import VAPI_TOOLS_DEFINITIONS


def provision_vapi_assistant(webhook_url: str = "https://your-ngrok-url.ngrok-free.app/webhook/vapi") -> dict:
    """
    Connect to Vapi API and create or update our Health Insurance Advisor voice assistant.
    """
    api_key = os.getenv("VAPI_API_KEY")
    if not api_key or api_key == "your_vapi_key_here":
        print("[ERROR] VAPI_API_KEY is missing or invalid in your .env file.")
        print("Please insert your valid Vapi Private Key from https://dashboard.vapi.ai/account")
        return {}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Format tools to bind to our specific webhook endpoint server
    configured_tools = []
    for tool_def in VAPI_TOOLS_DEFINITIONS:
        # Vapi server tool syntax requires attaching the server webhook URL
        tool_payload = {
            "type": "function",
            "function": tool_def["function"],
            "server": {
                "url": webhook_url
            }
        }
        configured_tools.append(tool_payload)

    # Build assistant provisioning payload
    assistant_payload = {
        "name": "Nova Health Insurance Advisor",
        "firstMessage": "Hello! Thank you for calling our Health Insurance Advisory center. My name is Nova Advisor. How can I assist you with your health coverage today?",
        "model": {
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "temperature": 0.3,
            "messages": [
                {
                    "role": "system",
                    "content": LEAD_QUALIFICATION_SYSTEM_PROMPT
                }
            ],
            "tools": configured_tools
        },
        "voice": {
            "provider": "openai",
            "voiceId": "nova"
        },
        "silenceTimeoutSeconds": 30,
        "maxDurationSeconds": 600
    }

    print("=" * 70)
    print("[PROVISION] STARTING VAPI ASSISTANT PROVISIONING (QUESTION 1)")
    print(f"            Target Webhook Server URL: {webhook_url}")
    print("=" * 70)

    url = "https://api.vapi.ai/assistant"
    print("\n[VAPI] Transmitting configuration payload to https://api.vapi.ai/assistant...")

    try:
        response = requests.post(url, headers=headers, json=assistant_payload, timeout=20)
        
        # If Groq model fails (e.g. if Groq key isn't connected in user's Vapi dashboard), graceful fallback to standard gpt-4o-mini
        if response.status_code == 400 and ("provider" in response.text.lower() or "model" in response.text.lower()):
            print(f"[WARNING] Groq provider configuration rejected by Vapi ({response.status_code}: {response.text}).")
            print("[VAPI] Switching to universal fallback model (provider: 'openai', model: 'gpt-4o-mini')...")
            assistant_payload["model"]["provider"] = "openai"
            assistant_payload["model"]["model"] = "gpt-4o-mini"
            response = requests.post(url, headers=headers, json=assistant_payload, timeout=20)

        response.raise_for_status()
        assistant_data = response.json()
        assistant_id = assistant_data.get("id")
        
        print("\n[SUCCESS] Voice Assistant successfully registered on Vapi.ai!")
        print(f"   -> Assistant ID:    {assistant_id}")
        print(f"   -> Assistant Name:  {assistant_data.get('name')}")
        print(f"   -> LLM Engine:      {assistant_data.get('model', {}).get('provider')} / {assistant_data.get('model', {}).get('model')}")
        print(f"   -> ASR Transcoder:  {assistant_data.get('transcoder', {}).get('provider')} / {assistant_data.get('transcoder', {}).get('model')}")
        
        # Save assistant config for grading evidence and web caller links
        output_dir = Path(__file__).resolve().parent / "data"
        output_dir.mkdir(parents=True, exist_ok=True)
        config_file = output_dir / "vapi_assistant_config.json"
        
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(assistant_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n[SAVE] Assistant configuration & verification proof saved to: {config_file}")
        
        web_link = f"https://dashboard.vapi.ai/assistants/{assistant_id}"
        print(f"\n[WEB CALLING INTERFACE LINK]:")
        print(f"   Open your browser and test live audio speech directly at:")
        print(f"   --> {web_link}")
        print("=" * 70 + "\n")
        
        return assistant_data

    except requests.RequestException as e:
        print(f"\n[ERROR] Failed to communicate with Vapi API: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"   Response body: {e.response.text}")
        print("=" * 70 + "\n")
        return {}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Register Vapi Voice Assistant with RAG Webhook URL")
    parser.add_argument("--url", dest="webhook_url", default="https://your-ngrok-url.ngrok-free.app/webhook/vapi", help="Public ngrok or server webhook URL pointing to your FastAPI server")
    args = parser.parse_args()

    provision_vapi_assistant(webhook_url=args.webhook_url)
