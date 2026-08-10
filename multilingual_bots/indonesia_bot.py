"""
Indonesia Native Voice Agent Module (Bahasa Indonesia Multifinance & Installment Financing)

Implements authentic conversational Bahasa Indonesia, regional Jakartan dialect naturalness, financial terminology
(Angsuran, Tenor, DP, IDR calculation), respectful etiquette (Pak / Ibu), and zero-hallucination boundaries.
"""
from typing import Dict, Any, List

# ---------------------------------------------------------------------------
# 1. INDONESIA MULTIFINANCE KNOWLEDGE REPOSITORY (LOCALIZED IDR PRICING)
# ---------------------------------------------------------------------------

INDONESIA_MULTIFINANCE_KB: List[Dict[str, Any]] = [
    {
        "id": "idr_multi_oto_pro",
        "title": "Nova OtoPro Multifinance 2026",
        "content": (
            "Nova OtoPro adalah solusi pembiayaan kendaraan bermotor (Multifinance) unggulan untuk pribadi dan operasional usaha.\n\n"
            "• Minimum Down Payment (DP): Mulai dari 15% dari harga OTR (On-The-Road) kendaraan.\n"
            "• Angsuran Bulanan (Installment): Sangat terjangkau, mulai dari Rp 2.850.000 / bulan untuk tenor 48 bulan (4 tahun).\n"
            "• Suku Bunga (Interest Rate): Bunga kompetitif tetap (fixed rate) 6,8% per tahun, bebas risiko fluktuasi inflasi.\n"
            "• Keuntungan Khusus: Include asuransi All-Risk penuh selama masa tenor dan gratis servis perawatan berkala di bengkel resmi."
        ),
        "tags": ["otopro", "multifinance", "kendaraan", "angsuran", "dp 15%", "bunga", "tenor"]
    },
    {
        "id": "idr_multi_modal_kerja",
        "title": "Nova Modal Usaha Cepat (Working Capital)",
        "content": (
            "Fasilitas pembiayaan tunai jaminan BPKB kendaraan untuk ekspansi modal kerja UMKM dan bisnis modern di Indonesia.\n\n"
            "• Plafon Pinjaman: Mulai dari Rp 50.000.000 hingga Rp 500.000.000 cair dalam 24 jam.\n"
            "• Tenor Fleksibel: Pilihan tenor mulai dari 12, 24, hingga 36 bulan sesuai arus kas usaha.\n"
            "• Persyaratan Simple: Cukup KTP, NPWP, dan rekening koran 3 bulan terakhir."
        ),
        "tags": ["modal kerja", "bpkb", "umkm", "50 juta", "tenor fleksibel"]
    },
    {
        "id": "idr_objection_handling",
        "title": "Bahasa Objection Handling Guidelines",
        "content": (
            "Jika calon nasabah menyatakan 'Bunganya kemahalan Pak' atau 'DP-nya bisa kurang lagi nggak?':\n"
            "• Strategi Empati: Gunakan bahasa santai dan santun bergaya profesional ('Paham banget Pak/Bu, pastinya kita cari cicilan yang paling nyaman buat cash flow keluarga ya').\n"
            "• Edukasi Nilai Plus: Jelaskan bahwa angsuran Rp 2.850.000/bulan sudah INCLUDE asuransi All-Risk full protection. Jadi kalau terjadi musibah atau dicucuk di jalan, kendaraan diproteksi 100% tanpa biaya tambahan.\n"
            "• Solusi Fleksibel (Fallback): Jika berat di bulanan, tawarkan opsi penambahan DP sedikit ke 25% untuk menjatuhkan cicilan bulanan hingga Rp 2.100.000 saja."
        ),
        "tags": ["kemahalan", "bunga mahal", "dp kurang", "objection", "cicilan ringan", "all-risk"]
    }
]


def query_indonesia_kb(question: str) -> str:
    """Localized similarity match for Indonesia Multifinance using live Pinecone HybridRetriever RAG."""
    from voice_agent.rag_tool import execute_query_knowledge_base
    return execute_query_knowledge_base(question)


# ---------------------------------------------------------------------------
# 2. BAHASA INDONESIA SYSTEM PROMPT & REGIONAL JAKARTAN RULES
# ---------------------------------------------------------------------------

INDONESIA_BAHASA_PROMPT = """You are 'Budi', a professional, friendly, and solution-oriented Senior Multifinance Advisor representing Nova AI Jakarta.

# YOUR CORE LINGUISTIC IDENTITY (BAHASA INDONESIA WITH REGIONAL JAKARTAN EMPATHY):
You MUST communicate in natural, highly conversational **Bahasa Indonesia** suitable for formal financing consultations yet infused with accessible regional Jakartan friendliness.
- **Politeness Honorifics:** Regularly address the customer respectfully as **"Pak"** (Bapak) or **"Bu"** (Ibu).
- **Financial Vocabulary:** Utilize proper regional financing terms: *Angsuran (monthly installments), Tenor (duration), DP (Down Payment), BPKB (title deed), Plafon (loan ceiling), Asuransi All-Risk*.
- **Conversational Tone:** Avoid rigid robotic translations. Use natural conversational connectors ("Paham banget Pak...", "Jadi begini Bu...").

# VOICE OUTPUT FORMATTING (CRITICAL FOR TTS SMOOTHNESS & ASR TOLERANCE):
- **Concise Responses:** Keep your answers brief, punchy, and under 3 sentences. Do NOT monologue or give overly long explanations.
- **Fluid Conversational Flow:** Speak in natural, fluid sentences. Avoid bullet points or special formatting.
- **Pronunciation Safety:** Write out numbers cleanly (e.g., "dua juta delapan ratus lima puluh ribu rupiah") if it helps the speech engine sound more natural.

# YOUR MISSION & DIALOGUE RULES:
1. **Consult & Qualify:** Greet the caller warmly in Bahasa. Inquire whether they need motor vehicle financing or working capital expansion.
2. **Concrete Quoting (Zero Hallucination):** If a user asks for a quote or simulation, IMMEDIATELY provide the concrete figures (e.g., Rp 2.850.000 for 48 months) from the retrieved knowledge. Do not endlessly ask questions without providing the math. Never guess figures.
3. **Handle Rate Objections Gracefully:** If a customer feels interest rates are too high, acknowledge their sensitivity, emphasize that installments include full All-Risk vehicle insurance, and propose adjustable DP fallback options.
4. **Human Escalation:** If the user asks to "connect to a human", "speak to a manager", or makes a request you cannot fulfill, immediately respond with: "Certainly, Pak/Bu. I'll connect you with one of our financing specialists." Do NOT try to handle the request yourself after an escalation request.
"""

def get_indonesia_assistant_config(ngrok_url: str = "") -> Dict[str, Any]:
    """Return complete JSON payload for initializing the Indonesia Bahasa Voice Agent in Vapi."""
    return {
        "name": "Nova Indonesia - Bahasa Multifinance Advisor (Budi)",
        "model": {
            "provider": "groq",
            "model": "llama-3.1-70b-versatile",
            "temperature": 0.3,
            "messages": [{"role": "system", "content": INDONESIA_BAHASA_PROMPT}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "query_knowledge_base",
                        "description": "Query Indonesia multifinance knowledge base in IDR currency for vehicle loans and rate objection handling.",
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
            "voiceId": "VR6AewLTigWG4xSOukaG",  # Professional confident male voice suitable for Indonesian articulation
            "stability": 0.60,
            "similarityBoost": 0.85
        }
    }
