import httpx
import html
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.config import settings
from app.engine.strategy import calculate_lot_size

async def send_telegram_message(message: str, reply_markup: Optional[Dict[str, Any]] = None) -> bool:
    """Mengirim pesan teks ke Telegram pribadi / grup / channel dengan opsional inline keyboard buttons."""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return False
        
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": str(settings.TELEGRAM_CHAT_ID),
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload, timeout=12.0)
            if res.status_code != 200:
                print(f"Telegram API response error: {res.status_code} - {res.text}")
            return res.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

async def answer_callback_query(callback_query_id: str, text: str = "", show_alert: bool = False) -> bool:
    """Menjawab callback query untuk menampilkan notifikasi pop-up di Telegram."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return False
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    payload = {
        "callback_query_id": callback_query_id,
        "text": text,
        "show_alert": show_alert
    }
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload, timeout=8.0)
            return res.status_code == 200
    except Exception as e:
        print(f"Callback answer error: {e}")
        return False

def format_rupiah_short(amount: float) -> str:
    """Format angka rupiah ringkas (misal 12.8 Jt / 496 Rb)."""
    if amount >= 1_000_000_000:
        return f"Rp {amount / 1_000_000_000:.2f} M"
    elif amount >= 1_000_000:
        return f"Rp {amount / 1_000_000:.1f} Jt"
    elif amount >= 1_000:
        return f"Rp {amount / 1_000:.0f} Rb"
    else:
        return f"Rp {amount:,.0f}"

def format_id_date(dt: datetime) -> str:
    """Format tanggal Indonesia (misal: Senin, 17 Agu 2026 • 17:00 WIB)."""
    days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    months = ["", "Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
    day_name = days[dt.weekday()]
    month_name = months[dt.month]
    return f"{day_name}, {dt.day} {month_name} {dt.year} • {dt.strftime('%H:%M')} WIB"

async def notify_super_digest(picks: List[Dict[str, Any]], climate: Optional[Dict[str, Any]] = None) -> bool:
    """Mengirimkan Super-Bot Digest (HANYA TOP 3 TERBAIK) dengan tombol interaktif 1-Click Buy & Stockbit."""
    if not picks:
        return False

    now_str = format_id_date(datetime.now())
    
    # 1. Header & Market Climate Banner
    regime_title = html.escape(str(climate.get("title", "Risk-On") if climate else "Risk-On"))
    regime_status = climate.get("regime", "BULLISH") if climate else "BULLISH"
    ihsg_price = climate.get("price", 0) if climate else 0
    ihsg_change = climate.get("change_pct", 0) if climate else 0
    sign = "+" if ihsg_change >= 0 else ""
    
    if regime_status == "BULLISH":
        climate_badge = "🟢 <b>BULLISH (Risk-On)</b>"
    elif regime_status == "NEUTRAL":
        climate_badge = "🟡 <b>CAUTION (50% Lot)</b>"
    else:
        climate_badge = "🔴 <b>DEFENSIVE (Cash is King)</b>"

    msg = f"<b>TOP 3 PICKS</b>\n"
    msg += f"<i>{now_str}</i>\n"
    msg += "────────────\n"
    
    # Status Operasional Bursa
    market_status = climate.get("market_status") if climate else None
    if market_status:
        status_title = html.escape(str(market_status.get("title", "")))
        msg += f"🏛️ <b>Bursa:</b> {status_title}\n"
    
    msg += f"🌦️ <b>IHSG:</b> {ihsg_price:,.0f} ({sign}{ihsg_change}%) • {climate_badge}\n"
    msg += "────────────\n\n"

    # 2. Top 3 Picks Details (Format Kartu Bersih & Tap to Copy)
    top_3 = picks[:3]
    inline_keyboard = []

    for i, p in enumerate(top_3, 1):
        plan = p["plan"]
        entry = int(plan["entry_price"])
        sl = int(plan["stop_loss"])
        tp1 = int(plan["tp1"])
        tp2 = int(plan["tp2"])

        # Hitung alokasi lot otomatis berbasis 1% risk dari default capital
        sizing = calculate_lot_size(settings.DEFAULT_CAPITAL, settings.DEFAULT_MAX_RISK_PCT, entry, sl)
        lots = sizing["lots"]
        half_lots = max(1, lots // 2)
        runner_lots = lots - half_lots
        cost_str = format_rupiah_short(sizing["total_cost"])
        risk_str = format_rupiah_short(sizing["max_risk_idr"])

        weekly_tag = "Weekly Confirmed" if p.get("weekly_confirmed") else "Daily Setup"
        safe_name = html.escape(str(p.get("name", "")))
        safe_setup = html.escape(str(p.get("primary_setup", "")))

        msg += f"<b>#{i} {p['symbol']} - {safe_name}</b>\n"
        msg += f"• Setup: <code>{safe_setup}</code> (Skor: <b>{p['score']} PTS</b>)\n"
        msg += f"• Validasi: <i>{weekly_tag}</i> | Turnover: Rp {p['turnover_bio']}B\n\n"
        
        # Angka kunci dengan format <code> agar bisa di-tap to copy di HP
        msg += f"🟢 <b>BUY (GTC) :</b> <code>{entry}</code> → <b>{lots} Lot</b>\n"
        msg += f"🔴 <b>CUT LOSS  :</b> <code>{sl}</code> (-{plan['risk_pct']}%)\n"
        msg += f"🎯 <b>TARGET 1  :</b> <code>{tp1}</code> (+{plan['tp1_gain_pct']}% | Jual {half_lots} Lot)\n"
        msg += f"🚀 <b>TARGET 2  :</b> <code>{tp2}</code> (+{plan['tp2_gain_pct']}% | Jual {runner_lots} Lot)\n\n"
        
        msg += f"• Modal: <b>{cost_str}</b> | Max Risiko: <b>{risk_str}</b> (1%)\n"
        msg += f"• <a href=\"https://stockbit.com/#/symbol/{p['symbol']}\">Buka {p['symbol']} di Stockbit</a>\n"
        if i < len(top_3):
            msg += "────────────\n\n"

        # Buat Baris Tombol Interaktif untuk setiap saham
        inline_keyboard.append([
            {
                "text": f"🛒 Beli & Catat {lots} Lot {p['symbol']}",
                "callback_data": f"buy:{p['symbol']}:{lots}:{entry}:{sl}:{tp1}"
            },
            {
                "text": f"📱 {p['symbol']} Stockbit",
                "url": f"https://stockbit.com/#/symbol/{p['symbol']}"
            }
        ])

    reply_markup = {"inline_keyboard": inline_keyboard}
    return await send_telegram_message(msg.strip(), reply_markup=reply_markup)

# Alias for backward compatibility
notify_top_picks = notify_super_digest
