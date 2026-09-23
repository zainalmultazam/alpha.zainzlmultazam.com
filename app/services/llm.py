"""
Universal Multi-Provider LLM Service untuk Platform Alpha.
Mendukung Google Gemini, OpenAI, DeepSeek, Groq, OpenRouter, Custom API,
serta Local Quant Heuristic Reasoning Fallback bila API offline/tanpa token.
Menggunakan standard library Python (urllib.request + asyncio) untuk portabilitas maksimal tanpa dependency issue.
"""

import os
import json
import logging
import asyncio
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

from app.config import settings

logger = logging.getLogger("AlphaLLM")

# System Prompt yang membekali model dengan keahlian institusional trading
ALPHA_SYSTEM_PROMPT = """Kamu adalah 'Alpha AI', rekan analis kuantitatif dan strategi swing trading institusional untuk platform Alpha (IDX & US Wall Street).

GAYA BAHASA & ATURAN JAWABAN:
1. Pakai kata ganti 'kamu'. Gaya bahasa santai tapi tetap profesional, tajam, objektif, dan logis.
2. JANGAN BERTELE-TELE dan JANGAN pakai basa-basi (dilarang pakai salam pembuka 'Halo!', 'Tentu saja...', 'Pertanyaan bagus...'). Langsung to the point ke inti jawaban dan strategi!
3. Format output harus rapi dan enak dibaca:
   - Gunakan tabel markdown jika menampilkan banyak data/saham/angka agar rapi dan terstruktur.
   - Gunakan bullet points ringkas dan tebalkan angka/ticker penting.
4. Kamu terhubung LIVE ke seluruh data Alpha:
   - `user_live_portfolio`: Data saham terbuka riil milik user (Ticker, Entry, Live Price, Floating PnL, Lot, Stop Loss, Status On-Track/Stagnant).
   - `user_capital_and_cash`: Sisa kas siap pakai, modal disetor, NAV total equity, cash ratio.
   - `ai_learning_engine`: Setup unggulan, bobot rezim, winrate historis, optimal exit day.
   - `forward_prediction_scorecard`: Rapor akurasi pelacakan sinyal AI.
   - `sector_rotation_flow`: Rotasi dana sektor (Net Inflow vs Outflow).
   - `market_climate` & `macro_data`: Kondisi IHSG/US market & makro.
   - `active_stock_detail` & `top_market_leaders`: Indikator teknikal (RS Rating, PTS Score, CMF, RVOL, Trade Plan).
5. Jika ditanya soal portofolio/saham aktif: Sebutkan semua saham yang dipegang lengkap dengan statusnya, lalu kasih evaluasi taktis langsung (Hold, Trailing Stop, atau Cut Loss).
6. Jika ditanya soal kas/modal: Sebutkan nominal kas siap pakai dan rasio alokasi saat ini.
7. Disiplin Risk-First: Selalu ingatkan batas risiko 1R dan Stop Loss tanpa bertele-tele.
"""

def get_llm_config() -> Dict[str, str]:
    """Konfigurasi LLM Utama (Tier 1)."""
    provider = (getattr(settings, "LLM_PROVIDER", "gemini") or "gemini").lower().strip()
    api_key = (getattr(settings, "LLM_API_KEY", "") or "").strip()
    model = (getattr(settings, "LLM_MODEL", "gemini-flash-latest") or "gemini-flash-latest").strip()
    base_url = (getattr(settings, "LLM_BASE_URL", "") or "").strip()
    
    return {
        "provider": provider,
        "api_key": api_key,
        "model": model,
        "base_url": base_url
    }

def get_llm_backup_config() -> Dict[str, str]:
    """Konfigurasi LLM Cadangan untuk Auto-Failover (Tier 2)."""
    provider = (getattr(settings, "LLM_BACKUP_PROVIDER", "groq") or "groq").lower().strip()
    api_key = (getattr(settings, "LLM_BACKUP_API_KEY", "") or "").strip()
    model = (getattr(settings, "LLM_BACKUP_MODEL", "qwen/qwen3.8-27b") or "qwen/qwen3.8-27b").strip()
    base_url = (getattr(settings, "LLM_BACKUP_BASE_URL", "") or "").strip()
    
    return {
        "provider": provider,
        "api_key": api_key,
        "model": model,
        "base_url": base_url
    }

def _http_post_sync(url: str, payload: dict, headers: dict) -> Optional[dict]:
    """Eksekusi sync POST HTTP request menggunakan urllib dengan SSL context fallback."""
    try:
        import ssl
        try:
            ctx = ssl.create_default_context()
        except Exception:
            ctx = ssl._create_unverified_context()
            
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            resp_ctx = urllib.request.urlopen(req, context=ctx, timeout=25)
        except urllib.error.URLError:
            ctx_unv = ssl._create_unverified_context()
            resp_ctx = urllib.request.urlopen(req, context=ctx_unv, timeout=25)
            
        with resp_ctx as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="ignore")
        logger.warning(f"HTTP error {e.code} querying LLM: {err_msg}")
        return None
    except Exception as e:
        logger.warning(f"Error querying LLM API: {e}")
        return None

async def query_gemini_api(prompt: str, system_prompt: str, api_key: str, model: str) -> Optional[str]:
    """Panggil Google Gemini REST API dengan system_instruction, X-goog-api-key header & multi-model fallback."""
    candidate_models = [model] if model else []
    for m in ["gemini-3.6-flash", "gemini-flash-latest"]:
        if m not in candidate_models:
            candidate_models.append(m)

    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 2048,
            "topP": 0.95
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": api_key
    }

    for m in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
        data = await asyncio.to_thread(_http_post_sync, url, payload, headers)
        if not data:
            fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
            data = await asyncio.to_thread(_http_post_sync, fallback_url, payload, {"Content-Type": "application/json"})
            
        if data:
            candidates = data.get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                text_parts = [p.get("text", "") for p in parts if p.get("text")]
                if text_parts:
                    return "".join(text_parts).strip()
    return None

async def query_openai_compatible_api(
    prompt: str, 
    system_prompt: str, 
    api_key: str, 
    model: str, 
    provider: str, 
    custom_base_url: str = ""
) -> Optional[str]:
    """Panggil OpenAI Compatible REST API (OpenAI, DeepSeek, Groq, OpenRouter, dll)."""
    if custom_base_url:
        endpoint = custom_base_url.rstrip("/") + "/chat/completions"
    elif provider == "deepseek":
        endpoint = "https://api.deepseek.com/v1/chat/completions"
    elif provider == "groq":
        endpoint = "https://api.groq.com/openai/v1/chat/completions"
    elif provider == "openrouter":
        endpoint = "https://openrouter.ai/api/v1/chat/completions"
    else:
        endpoint = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; AlphaAI/1.0; +https://alpha.zainalmultazam.com)",
        "Accept": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 2000
    }

    data = await asyncio.to_thread(_http_post_sync, endpoint, payload, headers)
    if data:
        choices = data.get("choices", [])
        if choices and "message" in choices[0]:
            return choices[0]["message"].get("content", "")
    return None

async def _execute_llm_call(provider: str, api_key: str, model: str, base_url: str, prompt: str, system_prompt: str) -> Optional[str]:
    """Helper mengeksekusi LLM provider spesifik."""
    if not api_key:
        return None
    if provider == "gemini":
        return await query_gemini_api(prompt, system_prompt, api_key, model)
    else:
        return await query_openai_compatible_api(prompt, system_prompt, api_key, model, provider, base_url)

def generate_local_quant_fallback(prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Mesin Penalaran Quant Lokal jika API Key belum terpasang atau kuota habis di semua provider."""
    p_lower = prompt.lower()
    ctx = context or {}
    stock = ctx.get("stock") or {}
    climate = ctx.get("climate") or {}
    
    ticker = stock.get("symbol") or stock.get("ticker") or ""
    
    # 1. Pertanyaan seputar saham minus tapi skor tinggi
    if any(k in p_lower for k in ["minus", "merah", "turun", "kenapa top", "kenapa skor"]):
        target_name = ticker or "saham ini"
        return f"""### 📊 Analisis Koreksi: Retracement Sehat vs Distribusi

1. **Struktur Tren:**
   Meskipun {target_name} hari ini terkoreksi, struktur jangka menengahnya masih berada di **Stage 2 Uptrend** di atas EMA 50 & EMA 200.

2. **Relative Strength (RS > 80):**
   Kinerjanya mengungguli 80%+ saham lain di bursa saat indeks melemah.

3. **Low Volume Pullback:**
   Penurunan terjadi dengan volume kering (RVOL < 1.0x). Ini adalah fase **retracement sehat** menuju *Entry Zone* dengan **Risk:Reward minimal 1:2**.

💡 **Aksi:** Pasang antrean **Buy Limit di Entry Zone** dan selalu kunci **GTC Stop Loss**."""

    # 2. Pertanyaan seputar IHSG / Iklim Pasar
    if any(k in p_lower for k in ["ihsg", "market", "iklim", "krisis", "turun semua", "bearish"]):
        regime = climate.get("regime", "NEUTRAL")
        return f"""### 🛡️ Kondisi Pasar & Strategi Alpha

* **Status Iklim Saat Ini:** {regime} (Defensif / Selektif).
* **Strategi Alokasi Modal:**
  - Batasi eksposur risiko maksimal **0.5% - 0.75% per trade** saat pasar belum *Confirmed Uptrend*.
  - Fokus hanya pada saham **Stage 2 Leader** dengan *Relative Strength (RS) > 85*.
  - Sektor Hedging yang bisa kamu perhatikan: Emas (`BRMS`, `PSAB`, `ANTM`), Komoditas USD (`ITMG`, `MEDC`), atau US Inverse ETF (`SH`, `SQQQ`).
* Hindari transaksi impulsif di 15 menit pertama (09:00 - 09:15 WIB)."""

    # 3. Pertanyaan seputar Lot / Sizing Modal / Portofolio
    if any(k in p_lower for k in ["modal", "lot", "sizing", "beli berapa", "alokasi"]):
        return """### 🧮 Alokasi Modal & Batas Risiko (Alpha 1R Rule)

1. **Batas Risiko 1R (Maksimal 1% Modal):**
   Jika modal kamu Rp 25.000.000, maka risiko maksimal per transaksi adalah Rp 250.000.
2. **Formula Lot:**
   $$\\text{Jumlah Lot} = \\frac{\\text{Batas Risiko (Rp)}}{(\\text{Harga Entry} - \\text{Stop Loss}) \\times 100}$$
3. **Porsi Portofolio Ideal:**
   - **Top 2 Saham (50% per posisi)** untuk modal terfokus pada saham terbaik.
   - **Top 3 Saham (33% per posisi)** untuk diversifikasi seimbang.

Gunakan fitur **Kalkulator Presisi** di Alpha untuk kalkulasi lot otomatis sesuai harga terkini."""

    # 4. Respon Default Analis
    return """### 🤖 Alpha Quant Insight

Berikut prinsip manajemen risiko utama Alpha untuk kamu:

* **Sistem SEPA & VCP:** Kita menyaring saham berdasarkan kontraksi volatilitas, volume akumulasi Big Money, dan breakout pivot presisi.
* **Manajemen Risiko:** Pastikan setiap posisi kamu punya batas Stop Loss terukur (R:R minimal 1:2) dan jangan kejar harga yang sudah naik >5% dari pivot.
* **Evaluasi Rutin:** Saham yang stagnan >10 hari sebaiknya dievaluasi untuk dialihkan modalnya ke setup yang lebih aktif."""

async def ask_alpha_ai(message: str, context: Optional[Dict[str, Any]] = None, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    """
    Fungsi utama untuk memproses chat dari trader.
    Menggunakan Smart Auto-Failover Multi-Tier:
      - Tier 1: Primary LLM (Default: Google Gemini)
      - Tier 2: Secondary LLM (Default: Groq qwen/qwen3.8-27b) jika Tier 1 429 quota / error / timeout
      - Tier 3: Local Quant Engine jika seluruh provider eksternal tidak dapat dihubungi
    """
    primary = get_llm_config()
    backup = get_llm_backup_config()
    
    # Susun prompt dengan konteks data saham/pasar
    ctx_str = ""
    if context:
        ctx_str = f"\n[Konteks Pasar & Emiten]:\n{json.dumps(context, ensure_ascii=False, indent=2)}\n"
        
    full_prompt = f"{ctx_str}\nPertanyaan Pengguna:\n{message}"
    
    reply = None
    used_provider = "local_quant_engine"
    
    # --- TIER 1: PRIMARY LLM ---
    if primary["api_key"]:
        try:
            reply = await _execute_llm_call(
                primary["provider"],
                primary["api_key"],
                primary["model"],
                primary["base_url"],
                full_prompt,
                ALPHA_SYSTEM_PROMPT
            )
            if reply:
                used_provider = f"{primary['provider'].capitalize()} ({primary['model']})"
        except Exception as e:
            logger.warning(f"Tier 1 LLM ({primary['provider']}) failed: {e}")
            reply = None

    # --- TIER 2: SMART AUTO-FAILOVER (SECONDARY LLM) ---
    # Terpicu otomatis jika Tier 1 gagal (error 429 limit kuota, timeout, atau unavailable)
    if not reply and backup["api_key"]:
        try:
            logger.info(f"Auto-Failover terpicu -> Mengalihkan ke Tier 2: {backup['provider']} ({backup['model']})")
            reply = await _execute_llm_call(
                backup["provider"],
                backup["api_key"],
                backup["model"],
                backup["base_url"],
                full_prompt,
                ALPHA_SYSTEM_PROMPT
            )
            if reply:
                used_provider = f"{backup['provider'].capitalize()} ({backup['model']}) [Auto-Failover]"
        except Exception as e:
            logger.warning(f"Tier 2 LLM ({backup['provider']}) failed: {e}")
            reply = None

    # --- TIER 3: LOCAL QUANT ENGINE FALLBACK ---
    if not reply:
        reply = generate_local_quant_fallback(message, context)
        used_provider = "Alpha Local Quant Engine"

    return {
        "reply": reply,
        "provider": used_provider,
        "status": "success"
    }

async def generate_stock_audit_narrative(ticker: str, metrics: Dict[str, Any], market: str = "IDX") -> str:
    """Membuat audit narasi komprehensif 3-paragraf untuk halaman detail emiten."""
    prompt = f"Berikan audit narasi institusional 3 paragraf untuk saham {ticker} ({market}) berdasarkan metrik berikut:\n{json.dumps(metrics, ensure_ascii=False)}"
    res = await ask_alpha_ai(prompt, context={"stock": metrics, "market": market})
    return res.get("reply", "")
