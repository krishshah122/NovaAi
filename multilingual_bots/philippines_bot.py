"""
Philippines Native Voice Agent Module (Taglish Bancassurance & Family Protection)

Implements authentic Taglish code-switching, local financial terminology (Bancassurance, VUL, PHP pricing),
regional cultural honorifics (Po/Opo, Sir/Ma'am), and strict zero-hallucination boundaries.
"""
from typing import Dict, Any, List

# ---------------------------------------------------------------------------
# 1. PHILIPPINES BANCASSURANCE KNOWLEDGE REPOSITORY (LOCALIZED PHP PRICING)
# ---------------------------------------------------------------------------

PHILIPPINES_BANCASSURANCE_KB: List[Dict[str, Any]] = [
    {
        "id": "php_banca_pampeled_shield",
        "title": "Nova Pamiliya Secure Shield 2026",
        "content": (
            "Ang Nova Pamiliya Secure Shield ay ang aming premier Bancassurance package para sa pamilyang Pilipino. "
            "It combines life insurance protection na may educational funding at Critical Illness rider.\n\n"
            "• Monthly Premium: ₱2,450 per month (fixed rate for 5 years, zero price hikes).\n"
            "• Annual Deductible / Out-of-Pocket Cap: ₱15,000 lamang per year para sa hospitalization.\n"
            "• Hospital Copay / Checkups: ₱250 flat fee kada checkup sa top accredited networks (St. Luke's, Makati Med, The Medical City).\n"
            "• Special Benefit: 100% full reimbursement para sa annual family checkups at zero-waiting period sa dengue at pneumonia coverage!"
        ),
        "tags": ["pamiliya shield", "bancassurance", "2450 premium", "15000 deductible", "dengue", "pneumonia"]
    },
    {
        "id": "php_banca_vul_builder",
        "title": "Nova Kabuhayan Wealth Builder (VUL)",
        "content": (
            "Ang Kabuhayan Wealth Builder ay isang Variable Universal Life (VUL) insurance plan na pinagsasama ang life coverage at investment fund growth.\n\n"
            "• Minimum Monthly Contribution: ₱3,500 monthly auto-deduct sa ATM bank account.\n"
            "• Allocation: 60% ng premium ay nakatutok sa local equity index funds (PSEi) para sa retirement o college tuition fund ng anak.\n"
            "• Life Benefit: Guaranteed sum assured na ₱2,000,000 in case of unexpected accidental death or disability."
        ),
        "tags": ["vul", "wealth builder", "investment", "3500 monthly", "2 million sum assured"]
    },
    {
        "id": "php_objection_handling",
        "title": "Taglish Objection Handling Guidelines",
        "content": (
            "Kung sabihin ng customer na 'Mahal naman' o 'Walang budget ngayon':\n"
            "• Response Strategy: Acknowledge politely using cultural honorifics ('Naiintindihan ko po Sir/Ma'am, importante talaga ang budgeting ngayon'). "
            "• Value Transition: Explain na ang ₱2,450 a month ay parang ₱80 lang araw-araw (mas mura pa sa isang kape), pero sagrado na ang future ng buong pamilya laban sa emergency hospital bills.\n"
            "• Downward Fallback Option: Alukin ang 'Kabuhayan Basic Starter' na ₱1,200/month lang na focus sa terminal accident & ICU coverage."
        ),
        "tags": ["mahal", "budget", "objection", "kape comparison", "starter fallback"]
    }
]


def query_philippines_kb(question: str) -> str:
    """Localized similarity match for Philippines Bancassurance using live Pinecone HybridRetriever RAG."""
    from voice_agent.rag_tool import execute_query_knowledge_base
    return execute_query_knowledge_base(question)


# ---------------------------------------------------------------------------
# 2. TAGLISH SYSTEM PROMPT & CODE-SWITCHING RULES
# ---------------------------------------------------------------------------

PHILIPPINES_TAGLISH_PROMPT = """You are 'Mika', a warm, highly expert, and empathetic Senior Bancassurance Advisor representing Nova AI Manila.

# YOUR CORE LINGUISTIC IDENTITY (TAGLISH CODE-SWITCHING):
You MUST speak in fluent, natural **Taglish** (the conversational blend of Tagalog and English utilized in Philippine business and banking consultations).
- **Sentence Flow:** Utilize Tagalog for emotional rapport and family-oriented discussions.
- **Financial Terminology:** Keep standard English financial terms (Premium, Deductible, Bancassurance, Copay).
- **Cultural Honorifics:** Use "po" and "opo" naturally but sparingly to avoid robotic repetition. Address the caller as "Sir or Ma'am" (DO NOT use a slash "Sir/Ma'am" as the speech engine will mispronounce it).

# VOICE OUTPUT FORMATTING (CRITICAL FOR TTS SMOOTHNESS):
- **Fluid Conversational Flow:** Do NOT split your responses into many tiny, choppy sentences. Speak in natural, fluid paragraphs.
- **No Formatting:** Do NOT use asterisks, bullet points, slashes, or special characters. Use commas and periods for natural pacing. 
- **Pronunciation Safety:** Write out numbers and symbols cleanly. Write "pesos" instead of "PHP" or "₱" if it helps the speech engine sound more natural.

# YOUR MISSION & DIALOGUE RULES:
1. **Proactive Qualification (DON'T JUST QUOTE):** Before quoting a plan, always ask clarifying questions! Ask whether they are looking for individual or family coverage, how many family members they have, and what their comfortable budget range is.
2. **Strict Grounding (Zero Hallucination):** When discussing premiums or deductibles, base statements strictly on retrieved local knowledge records. Do not guess dollar amounts.
3. **Budget Empathy & Sales Pivot:** If a customer mentions a "tight budget" or says a plan is "mahal" (expensive), DO NOT just acknowledge it and stop. Be a strong sales advisor: immediately pivot and suggest lower-coverage, affordable options like the 'Kabuhayan Basic Starter' plan to save the sale.
4. **Corporate Identity:** You are strictly an employee of Nova AI Manila. Never associate yourself with external vendor models.
"""

def get_philippines_assistant_config(ngrok_url: str = "") -> Dict[str, Any]:
    """Return complete JSON payload for initializing the Philippine Taglish Voice Agent in Vapi."""
    return {
        "name": "Nova Philippines - Taglish Bancassurance Advisor (Mika)",
        "model": {
            "provider": "groq",
            "model": "llama-3.1-70b-versatile",
            "temperature": 0.3,
            "messages": [{"role": "system", "content": PHILIPPINES_TAGLISH_PROMPT}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "query_knowledge_base",
                        "description": "Query Philippines bancassurance knowledge base in PHP currency for family plans and objection handling.",
                        "parameters": {
                            "type": "object",
                            "properties": {"question": {"type": "string"}},
                            "required": ["question"]
                        }
                    },
                    "server": {"url": ngrok_url or "http://localhost:8000/webhook/vapi"}
                }
            ]
        },
        "voice": {
            "provider": "11labs",
            "voiceId": "21m00Tcm4TlvDq8ikWAM",  # Warm conversational female voice suited for Southeast Asian accent tuning
            "stability": 0.55,
            "similarityBoost": 0.8
        }
    }
