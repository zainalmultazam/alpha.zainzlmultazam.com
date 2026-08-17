import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.config import settings
from app.engine.strategy import calculate_lot_size

async def send_telegram_message(message: str) -> bool:
    """Mengirim pesan teks ke Telegram pribadi / channel."""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return False
        
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload, timeout=12.0)
            return res.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

async def notify_super_digest(picks: List[Dict[str, Any]], climate: Optional[Dict[str, Any]] = None) -> bool:
    """Mengirimkan Super-Bot Digest (HANYA TOP 3 TERBAIK) dengan parameter order GTC presisi dan alokasi lot otomatis."""
    if not picks:
        return False

    now_str = datetime.now().strftime("%d %b %Y, %H:%M WIB")
    
    # 1. Header & Market Climate Banner
    regime_title = climate.get("title", "Risk-On") if climate else "Risk-On"
    regime_status = climate.get("regime", "BULLISH") if climate else "BULLISH"
    ihsg_price = climate.get("price", 0) if climate else 0
    ihsg_change = climate.get("change_pct", 0) if climate else 0
    sign = "+" if ihsg_change >= 0 else ""
    
    if regime_status == "BULLISH":
        climate_icon = "🟢"
        exposure_text = "100% Modal Aktif (Pasar Sehat)"
    elif regime_status == "NEUTRAL":
        climate_icon = "🟡"
        exposure_text = "50% Alokasi Lot (Konsolidasi/Pullback)"
    else:
        climate_icon = "🔴"
        exposure_text = "DEFENSIVE / CASH IS KING (IHSG < EMA200)"

    msg = f"⚡ <b>ALPHASWING SUPER-DIGEST (TOP 3)</b>\n"
    msg += f"📅 <i>{now_str} • {settings.APP_DOMAIN}</i>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"{climate_icon} <b>IHSG CLIMATE:</b> {regime_title}\n"
    msg += f"• Indeks: <b>{ihsg_price:,.0f} ({sign}{ihsg_change}%)</b>\n"
    msg += f"• Rekomendasi: <i>{exposure_text}</i>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━\n\n"

    # 2. Top 3 Picks Details
    top_3 = picks[:3]
    for i, p in enumerate(top_3, 1):
        plan = p["plan"]
        entry = plan["entry_price"]
        sl = plan["stop_loss"]
        tp1 = plan["tp1"]
        tp2 = plan["tp2"]

        # Hitung alokasi lot otomatis berbasis 1% risk dari default capital
        sizing = calculate_lot_size(settings.DEFAULT_CAPITAL, settings.DEFAULT_MAX_RISK_PCT, entry, sl)
        lots = sizing["lots"]
        shares = sizing["shares"]
        cost_idr = sizing["total_cost"]
        risk_idr = sizing["max_risk_idr"]

        weekly_tag = "🟢 Weekly Confirmed" if p.get("weekly_confirmed") else "🟡 Daily Setup"

        msg += f"<b>#{i} 🎯 {p['symbol']} ({p['name']})</b>\n"
        msg += f"• Setup: <code>{p['primary_setup']}</code> (Skor: <b>{p['score']} PTS</b>)\n"
        msg += f"• Status: <i>{weekly_tag}</i> | Turnover: Rp {p['turnover_bio']}B\n"
        msg += f"• 🟢 <b>BUY STOP / ENTRY:</b> Rp {entry:,}\n"
        msg += f"• 🔴 <b>STOP LOSS:</b> Rp {sl:,} (-{plan['risk_pct']}%)\n"
        msg += f"• 🎯 <b>TP 1 (2R):</b> Rp {tp1:,} (+{plan['tp1_gain_pct']}%)\n"
        msg += f"• 🚀 <b>TP 2 (Runner):</b> Rp {tp2:,} (+{plan['tp2_gain_pct']}%)\n"
        msg += f"• 🧮 <b>ALOKASI AMAN:</b> <b>{lots} Lot</b> ({shares:,} lbr)\n"
        msg += f"   <i>Modal Beli: Rp {cost_idr:,} | Max Risiko: Rp {risk_idr:,} (1%)</i>\n\n"

    # 3. Action Call to Trader
    msg += "━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "📌 <b>INSTRUKSI EKSEKUSI:</b>\n"
    msg += "1. Buka aplikasi sekuritas Anda (Stockbit/IPOT/Mirae/MOST/Ajaib).\n"
    msg += "2. Pasang <b>Auto-Order GTC Buy Stop</b> pada harga Entry di atas.\n"
    msg += "3. Pasang <b>Auto Stop Loss (OCO)</b> untuk proteksi modal otomatis.\n"
    msg += "4. Selesai! Tidak perlu menatap layar saat jam bursa.\n"
    msg += f"🔗 <i>Web Terminal: https://{settings.APP_DOMAIN}</i>"

    return await send_telegram_message(msg)

# Alias for backward compatibility
notify_top_picks = notify_super_digest
