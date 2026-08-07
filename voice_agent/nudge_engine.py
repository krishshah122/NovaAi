import os
import json
import time
from typing import List, Dict, Any, Optional
from groq import Groq

# In-memory cooldown cache: {session_id: {signal_type: last_timestamp}}
NUDGE_COOLDOWNS: Dict[str, Dict[str, float]] = {}
COOLDOWN_SECONDS = 30.0

NUDGE_SYSTEM_PROMPT = """You are a Real-Time Agent Assist AI listening to a live call between a Customer and an AI Agent.
Your job is to analyze the recent conversation transcript and generate an actionable 'Nudge' if a critical business signal is detected.

SIGNALS TO WATCH FOR:
1. "frustration": The customer sounds annoyed, frustrated, repeats themselves, or says "too expensive", "tight budget", "too high". 
   - Nudge Action: Advise the agent to show empathy and pivot to a lower-cost scalable plan (e.g., Starter Plan).
2. "cross_sell": The customer mentions family, a spouse, kids, or a second vehicle, but the agent hasn't explicitly offered family/multi-vehicle coverage. 
   - Nudge Action: Advise the agent to suggest pitching the family plan or multi-vehicle bundle.
3. "compliance": The customer asks for medical advice, legal advice, or asks to speak to a human manager. 
   - Nudge Action: Remind the agent to state "I am not a doctor" or explicitly confirm the human escalation.

RULES:
- ONLY output a Nudge if a signal is clearly present in the most recent messages.
- If the conversation is normal/cooperative, output an empty nudge object.
- DO NOT hallucinate nudges for normal cooperative questions.
- Keep the nudge message under 12 words (it flashes on a screen for an agent).

You must respond ONLY with a raw JSON object (no markdown, no backticks).
Format:
{
  "detected": true/false,
  "signal_type": "frustration" | "cross_sell" | "compliance" | "none",
  "nudge_message": "Actionable advice for the agent here"
}
"""

def generate_nudge(session_id: str, transcript_buffer: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Analyzes the recent transcript buffer and returns a nudge if a signal is found.
    Returns: {"nudge": {"type": ..., "message": ...}, "latency_ms": 120} or {"nudge": None}
    """
    start_time = time.time()
    
    if not transcript_buffer:
        return {"nudge": None, "latency_ms": 0}
        
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    # Format the transcript buffer into a readable string (last 6 messages max for speed)
    recent_msgs = transcript_buffer[-6:]
    convo_text = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in recent_msgs])
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": NUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": f"RECENT TRANSCRIPT:\n{convo_text}"}
            ],
            temperature=0.0,
            max_tokens=150,
            response_format={"type": "json_object"}
        )
        
        response_text = completion.choices[0].message.content
        result = json.loads(response_text)
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        if result.get("detected") and result.get("signal_type") and result.get("signal_type") != "none":
            signal_type = result["signal_type"]
            
            # Check Cooldown suppression
            now = time.time()
            if session_id not in NUDGE_COOLDOWNS:
                NUDGE_COOLDOWNS[session_id] = {}
                
            last_fired = NUDGE_COOLDOWNS[session_id].get(signal_type, 0)
            if (now - last_fired) < COOLDOWN_SECONDS:
                # Suppressed due to cooldown to prevent spamming
                print(f"[NUDGE ENGINE] Suppressed '{signal_type}' nudge due to {COOLDOWN_SECONDS}s cooldown.")
                return {"nudge": None, "latency_ms": latency_ms, "suppressed": True}
                
            # Fire nudge and update cooldown cache
            NUDGE_COOLDOWNS[session_id][signal_type] = now
            print(f"[NUDGE ENGINE] FIRED: {signal_type} -> {result.get('nudge_message')}")
            return {
                "nudge": {
                    "type": signal_type,
                    "message": result.get("nudge_message", "Attention required.")
                },
                "latency_ms": latency_ms
            }
            
        return {"nudge": None, "latency_ms": latency_ms}
        
    except Exception as e:
        print(f"[NUDGE ENGINE ERROR]: {str(e)}")
        return {"nudge": None, "latency_ms": int((time.time() - start_time) * 1000), "error": str(e)}
