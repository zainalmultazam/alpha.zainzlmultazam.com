import httpx
from typing import List, Dict, Any
from app.config import settings

async def send_telegram_message(message: str) -> bool:
    """Mengirim pesan teks ke Telegram pribadi."""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return False
        
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload, timeout=10.0)
            return res.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

async def notify_top_picks(picks: List[Dict[str, Any]]):
    """Mengirimkan ringkasan Top 5 Alpha Picks harian ke Telegram."""
    if not picks:
        return
        
    msg = f"🚀 <b>ALPHASWING IDX: TOP PICKS HARI INI</b>\n"
    msg += f"<i>{settings.APP_DOMAIN}</i>\n\n"
    
    for i, p in enumerate(picks[:5], 1):
        plan = p["plan"]
        msg += f"<b>{i}. {p['symbol']} ({p['name']})</b>\n"
        msg += f"• Setup: <code>{p['primary_setup']}</code> (Skor: {p['score']})\n"
        msg += f"• 🟢 <b>Entry Zone:</b> Rp {plan['entry_price']:,}\n"
        msg += f"• 🔴 <b>Stop Loss:</b> Rp {plan['stop_loss']:,} (-{plan['risk_pct']}%)\n"
        msg += f"• 🎯 <b>Target TP1:</b> Rp {plan['tp1']:,} (+{plan['tp1_gain_pct']}% | R:R {plan['rr_ratio']})\n"
        msg += f"• 🎯 <b>Target TP2:</b> Rp {plan['tp2']:,} (+{plan['tp2_gain_pct']}%)\n\n"
        
    msg += "⚠️ <i>Gunakan Auto Order / GTC di sekuritas Anda. Batasi risiko max 1% per trade.</i>"
    await send_telegram_message(msg)
