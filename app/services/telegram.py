import httpx
import html
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.config import settings
from app.engine.strategy import calculate_lot_size

async def send_telegram_message(message: str) -> bool:
    """Mengirim pesan teks ke Telegram pribadi / grup / channel."""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return False
        
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": str(settings.TELEGRAM_CHAT_ID),
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload, timeout=12.0)
            if res.status_code != 200:
                print(f"Telegram API response error: {res.status_code} - {res.text}")
            return res.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

async def notify_super_digest(picks: List[Dict[str, Any]], climate: Optional[Dict[str, Any]] = None) -> bool:
    """Mengirimkan Super-Bot Digest (HANYA TOP 3 TERBAIK) yang disesuaikan khusus untuk Stockbit Auto Order."""
    if not picks:
        return False

    now_str = datetime.now().strftime("%d %b %Y, %H:%M WIB")
    
    # 1. Header & Market Climate Banner
    regime_title = html.escape(str(climate.get("title", "Risk-On") if climate else "Risk-On"))
    regime_status = climate.get("regime", "BULLISH") if climate else "BULLISH"
    ihsg_price = climate.get("price", 0) if climate else 0
    ihsg_change = climate.get("change_pct", 0) if climate else 0
    sign = "+" if ihsg_change >= 0 else ""
    
    if regime_status == "BULLISH":
        exposure_text = "100% Modal Aktif (Pasar Sehat)"
    elif regime_status == "NEUTRAL":
        exposure_text = "50% Alokasi Lot (Konsolidasi/Pullback)"
    else:
        exposure_text = "DEFENSIVE / CASH IS KING (IHSG < EMA200)"

    msg = f"<b>[ALPHASWING x STOCKBIT] TOP 3 PICKS</b>\n"
    msg += f"<i>{now_str} • {settings.APP_DOMAIN}</i>\n"
    msg += "────────────\n"
    
    # Status Operasional Bursa
    market_status = climate.get("market_status") if climate else None
    if market_status:
        status_title = html.escape(str(market_status.get("title", "")))
        msg += f"<b>STATUS BURSA:</b> {status_title}\n"
    
    msg += f"<b>IHSG CLIMATE:</b> {regime_title}\n"
    msg += f"• Indeks: <b>{ihsg_price:,.0f} ({sign}{ihsg_change}%)</b>\n"
    msg += f"• Rekomendasi: <i>{html.escape(exposure_text)}</i>\n"
    msg += "────────────\n\n"

    # 2. Top 3 Picks Details (Disesuaikan Menu Stockbit)
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
        half_lots = max(1, lots // 2)
        runner_lots = lots - half_lots
        cost_idr = sizing["total_cost"]
        risk_idr = sizing["max_risk_idr"]

        weekly_tag = "[Weekly Confirmed]" if p.get("weekly_confirmed") else "[Daily Setup]"
        safe_name = html.escape(str(p.get("name", "")))
        safe_setup = html.escape(str(p.get("primary_setup", "")))

        msg += f"<b>#{i} {p['symbol']} - {safe_name}</b>\n"
        msg += f"• Setup: <code>{safe_setup}</code> (Skor: <b>{p['score']} PTS</b>)\n"
        msg += f"• Validasi: <i>{weekly_tag}</i> | Turnover: Rp {p['turnover_bio']}B\n"
        msg += f"• [AUTO BUY GTC]: <b>Last Price &gt;= Rp {entry:,}</b> (Order {lots} Lot)\n"
        msg += f"• [AUTO SL CUT]: <b>Last Price &lt;= Rp {sl:,}</b> (-{plan['risk_pct']}%)\n"
        msg += f"• [TAKE PROFIT 1]: <b>Last Price &gt;= Rp {tp1:,}</b> (+{plan['tp1_gain_pct']}% | Jual {half_lots} Lot)\n"
        msg += f"• [TAKE PROFIT 2]: <b>Last Price &gt;= Rp {tp2:,}</b> (+{plan['tp2_gain_pct']}% | Jual {runner_lots} Lot)\n"
        msg += f"• [ALOKASI MODAL]: <b>{lots} Lot</b> ({shares:,} lembar)\n"
        msg += f"   <i>Total Beli: Rp {cost_idr:,} | Max Risiko: Rp {risk_idr:,} (1%)</i>\n"
        msg += f"• <i>Stockbit Link: https://stockbit.com/#/symbol/{p['symbol']}</i>\n\n"

    # 3. Panduan Khusus Aplikasi Stockbit
    msg += "────────────\n"
    msg += "<b>PANDUAN SETTING DI APLIKASI STOCKBIT:</b>\n"
    msg += "1. Buka Stockbit → Cari Saham → Tekan 'Auto Order'.\n"
    msg += "2. Pilih Tab 'BUY', pilih kondisi: <code>Price &gt;= Rp [Entry]</code>.\n"
    msg += "3. Set Expiry 'GTC' dan masukkan jumlah Lot di atas.\n"
    msg += "4. Pasang Auto Order 'SELL' Cut Loss: <code>Price &lt;= Rp [SL]</code>.\n"
    msg += f"Terminal: https://{settings.APP_DOMAIN}"

    return await send_telegram_message(msg)

# Alias for backward compatibility
notify_top_picks = notify_super_digest
