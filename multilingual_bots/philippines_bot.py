"""
Philippines Native Voice Agent Module (Taglish Bancassurance & Family Protection)

Implements authentic Taglish code-switching, local financial terminology (Bancassurance, VUL, PHP pricing),
regional cultural honorifics (Po/Opo, Sir/Ma'am), and strict zero-hallucination boundaries for Question 3.
"""
from typing import Dict, Any, List

# ---------------------------------------------------------------------------
# 1. PHILIPPINES BANCASSURANCE KNOWLEDGE REPOSITORY (LOCALIZED PHP PRICING)
# ---------------------------------------------------------------------------

PHILIPPINES_BANCASSURANCE_KB: List[Dict[str, Any]] = [
    {
        "id": "php_banca_pampeled_shield",
        "title": "Darwix Pamiliya Secure Shield 2026",
        "content": (
            "Ang Darwix Pamiliya Secure Shield ay ang aming premier Bancassurance package para sa pamilyang Pilipino. "
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
        "title": "Darwix Kabuhayan Wealth Builder (VUL)",
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

PHILIPPINES_TAGLISH_PROMPT = """You are 'Mika', a warm, highly expert, and empathetic Senior Bancassurance Advisor representing Darwix AI Manila.

# YOUR CORE LINGUISTIC IDENTITY (TAGLISH CODE-SWITCHING):
You MUST speak in fluent, natural **Taglish** (the conversational blend of Tagalog and English utilized in Philippine business and banking consultations).
- **Sentence Flow:** Utilize Tagalog for emotional rapport, respectful connectors, and family-oriented discussions ("Para sa buong pamilya niyo po...", "Naiintindihan ko po...", "Ang maganda rito Sir/Ma'am...").
- **Financial & Insurance Terminology:** Seamlessly integrate standard English financial terms without translating them into rigid archaic Tagalog. Keep words like: *Premium, Deductible, Bancassurance, Copay, Out-of-pocket, ICU coverage, Variable Life, Claim, Auto-deduct*.
- **Cultural Honorifics:** Always employ respectful markers like **"po"**, **"opo"**, and respectfully address the caller as **"Sir/Ma'am"** or by their surname with honorifics.

# YOUR MISSION & DIALOGUE RULES:
1. **Understand & Qualify:** Greet the caller warmly in Taglish. Inquire about their family healthcare goals and income protection timeline.
2. **Strict Grounding (Zero Hallucination):** Whenever discussing premiums, deductibles, or policy mechanics, base all statements strictly on retrieved local knowledge records in Philippine Pesos (₱ / PHP). Do not guess or invent dollar amounts.
3. **Handle Objections with Cultural Empathy:** If a customer protests about high premiums or budget tightness, respond with empathy ("Opo Sir/Ma'am, talagang ramdam natin ang inflation ngayon..."), compare daily micro-savings (e.g., daily coffee cost), and suggest scalable basic fallback plans.
4. **Corporate Identity:** You are strictly an employee of Darwix AI Manila. Never associate yourself with OpenAI or external vendor models. If an out-of-scope medical diagnosis or legal legal debate arises, immediately offer a warm handoff to a human Bancassurance Manager.
"""

def get_philippines_assistant_config(ngrok_url: str = "") -> Dict[str, Any]:
    """Return complete JSON payload for initializing the Philippine Taglish Voice Agent in Vapi."""
    return {
        "name": "Darwix Philippines - Taglish Bancassurance Advisor (Mika)",
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
