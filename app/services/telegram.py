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

async def notify_morning_briefing(picks: List[Dict[str, Any]], climate: Optional[Dict[str, Any]] = None, macro: Optional[Dict[str, Any]] = None) -> bool:
    """Mengirimkan Morning Pre-Market Briefing (08:45 WIB) dengan Iklim IHSG, Radar Makro, dan Top 3 Picks."""
    now_str = format_id_date(datetime.now())
    
    # 1. Header & Market Climate Banner
    regime_status = climate.get("regime", "BULLISH") if climate else "BULLISH"
    ihsg_price = climate.get("price", 0) if climate else 0
    ihsg_change = climate.get("change_pct", 0) if climate else 0
    sign = "+" if ihsg_change >= 0 else ""
    exposure = climate.get("exposure_pct", 50) if climate else 50
    
    if regime_status == "BULLISH":
        climate_badge = f"🟢 <b>BULLISH ({exposure}% Modal Aktif)</b>"
    elif regime_status == "NEUTRAL":
        climate_badge = f"🟡 <b>CAUTION ({exposure}% Modal Aktif)</b>"
    else:
        climate_badge = f"🔴 <b>DEFENSIVE ({exposure}% Modal Aktif)</b>"

    msg = f"🌅 <b>MORNING PRE-MARKET BRIEFING</b>\n"
    msg += f"<i>{now_str}</i>\n"
    msg += "━━━━━━━━━━━━━━━━━━\n"
    
    msg += f"📊 <b>IHSG:</b> <code>{ihsg_price:,.2f}</code> ({sign}{ihsg_change}%)\n"
    msg += f"🧭 <b>Rezim:</b> {climate_badge}\n"
    if climate and climate.get("advice"):
        msg += f"💡 <i>{climate['advice']}</i>\n"
    msg += "━━━━━━━━━━━━━━━━━━\n"

    # 2. Global Macro Radar Highlights
    if macro and macro.get("items"):
        msg += "🌐 <b>RADAR MAKRO GLOBAL:</b>\n"
        for item in macro["items"][:4]:
            m_sign = "+" if item.get("is_positive") else ""
            m_chg = item.get("change_pct", 0)
            icon = "🟢" if item.get("is_positive") else "🔴"
            rel = "/".join(item.get("related_tickers", [])[:2])
            rel_str = f" → {rel}" if rel else ""
            msg += f"• {icon} <b>{item.get('name')}:</b> {item.get('display_price')} (<code>{m_sign}{m_chg}%</code>){rel_str}\n"
        msg += "━━━━━━━━━━━━━━━━━━\n\n"

    # Check for stagnant trades in Journal (Time-Stop Evaluation)
    try:
        from app.engine.journal import get_open_trades
        open_trades = get_open_trades()
        stagnant_trades = [t for t in open_trades if t.get("is_stagnant")]
        if stagnant_trades:
            msg += "⏱️ <b>EVALUASI TIME-STOP (SAHAM STAGNAN):</b>\n"
            for st in stagnant_trades[:3]:
                pnl = float(st.get("pnl_pct") or 0.0)
                pnl_str = f"+{pnl:.1f}%" if pnl >= 0 else f"{pnl:.1f}%"
                days = st.get("holding_days", 8)
                msg += f"• ⚠️ <b>{st['ticker']}:</b> Sudah {days} hari bursa (Floating: <code>{pnl_str}</code>)\n"
                msg += f"  <i>Saran: Pertimbangkan geser SL ke BEP (impas) atau evaluasi rotasi modal.</i>\n"
            msg += "━━━━━━━━━━━━━━━━━━\n\n"
    except Exception as e:
        logger.warning(f"Error checking stagnant trades in morning briefing: {e}")

    # 3. Top 3 Picks Details
    if picks:
        msg += "🎯 <b>TOP 3 REKOMENDASI HARI INI:</b>\n\n"
        top_3 = picks[:3]
        inline_keyboard = []

        for i, p in enumerate(top_3, 1):
            plan = p.get("plan", {})
            entry = int(plan.get("entry_price", p.get("close", 0)))
            sl = int(plan.get("stop_loss", entry * 0.96))
            tp1 = int(plan.get("tp1", entry * 1.08))
            tp2 = int(plan.get("tp2", entry * 1.15))

            # Hitung alokasi lot otomatis berbasis 1% risk dari default capital
            sizing = calculate_lot_size(settings.DEFAULT_CAPITAL, settings.DEFAULT_MAX_RISK_PCT, entry, sl)
            lots = sizing["lots"]
            half_lots = max(1, lots // 2)
            cost_str = format_rupiah_short(sizing["total_cost"])
            risk_str = format_rupiah_short(sizing["max_risk_idr"])

            weekly_tag = "Weekly Confirmed" if p.get("weekly_confirmed") else "Daily Setup"
            safe_name = html.escape(str(p.get("name", p.get("symbol", ""))))
            safe_setup = html.escape(str(p.get("primary_setup", "Breakout")))

            msg += f"<b>#{i} {p['symbol']} - {safe_name}</b>\n"
            msg += f"• Setup: <code>{safe_setup}</code> (Skor: <b>{p.get('score', 90)} PTS</b>)\n"
            msg += f"• Validasi: <i>{weekly_tag}</i> | Turnover: Rp {p.get('turnover_bio', 0)}B\n\n"
            
            # Angka kunci format code agar tap-to-copy
            msg += f"🟢 <b>BUY (GTC) :</b> <code>{entry}</code> → <b>{lots} Lot</b> ({cost_str})\n"
            msg += f"🔴 <b>STOP LOSS :</b> <code>{sl}</code> (-{plan.get('risk_pct', 4.0)}% | Risk {risk_str})\n"
            msg += f"🎯 <b>TARGET TP1:</b> <code>{tp1}</code> (+{plan.get('tp1_gain_pct', 8.0)}% | Jual {half_lots} Lot)\n"
            msg += f"🚀 <b>TARGET TP2:</b> <code>{tp2}</code> (+{plan.get('tp2_gain_pct', 15.0)}%)\n\n"
            msg += f"• <a href=\"https://stockbit.com/#/symbol/{p['symbol']}\">Buka {p['symbol']} di Stockbit</a>\n"
            if i < len(top_3):
                msg += "──────────────────\n\n"

            inline_keyboard.append([
                {
                    "text": f"🛒 Catat Beli {p['symbol']} ({lots} Lot)",
                    "callback_data": f"picklot:{p['symbol']}:{lots}:{entry}:{sl}:{tp1}"
                }
            ])

        reply_markup = {"inline_keyboard": inline_keyboard} if inline_keyboard else None
    else:
        msg += "<i>Belum ada setup dengan skor tinggi yang lolos filter likuiditas pagi ini. Disiplin tunggu konfirmasi pasar!</i>\n"
        reply_markup = None

    return await send_telegram_message(msg.strip(), reply_markup=reply_markup)

async def notify_super_digest(picks: List[Dict[str, Any]], climate: Optional[Dict[str, Any]] = None) -> bool:
    """Mengirimkan Super-Bot Digest (HANYA TOP 3 TERBAIK) dengan tombol interaktif 1-Click Buy."""
    return await notify_morning_briefing(picks, climate=climate)

async def notify_evening_wrap(climate: Optional[Dict[str, Any]] = None, open_trades: Optional[List[Dict[str, Any]]] = None, stats: Optional[Dict[str, Any]] = None) -> bool:
    """Mengirimkan Evening Market & Portfolio Wrap (16:15 WIB)."""
    now_str = format_id_date(datetime.now())
    
    ihsg_price = climate.get("price", 0) if climate else 0
    ihsg_change = climate.get("change_pct", 0) if climate else 0
    sign = "+" if ihsg_change >= 0 else ""
    regime = climate.get("regime", "BULLISH") if climate else "BULLISH"

    msg = f"🌆 <b>MARKET CLOSE & PORTFOLIO WRAP</b>\n"
    msg += f"<i>{now_str}</i>\n"
    msg += "━━━━━━━━━━━━━━━━━━\n"
    msg += f"📊 <b>IHSG Tutup:</b> <code>{ihsg_price:,.2f}</code> ({sign}{ihsg_change}%) • <b>{regime}</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━\n\n"

    # Status Open Trades
    if open_trades and len(open_trades) > 0:
        msg += f"💼 <b>POSISI TERBUKA AKTIF ({len(open_trades)} Saham):</b>\n"
        for t in open_trades:
            ticker = t.get("ticker", "")
            entry = float(t.get("entry_price", 0))
            sl = float(t.get("stop_loss", 0))
            lots = int(t.get("lots", 0))
            msg += f"• <b>{ticker}</b> ({lots} Lot) — Entry: Rp {entry:,.0f} | SL: Rp {sl:,.0f}\n"
        msg += "\n"
    else:
        msg += "💼 <b>Posisi Terbuka:</b> 0 Saham (100% Cash RDN Aman)\n\n"

    # Performance Stats
    if stats:
        win_rate = stats.get("win_rate", 0.0)
        pnl = stats.get("total_realized_pnl", 0.0)
        pnl_sign = "+" if pnl >= 0 else ""
        closed_count = stats.get("closed_trades_count", 0)
        msg += "📈 <b>RINGKASAN KINERJA JURNAL:</b>\n"
        msg += f"• Win Rate        : <b>{win_rate:.1f}%</b>\n"
        msg += f"• Total Realized  : <b>{pnl_sign}Rp {pnl:,.0f}</b>\n"
        msg += f"• Transaksi Selesai: <b>{closed_count} Trade</b>\n"
    
    msg += "\n────────────\n"
    msg += f"🌐 <a href=\"https://{settings.APP_DOMAIN}\">Buka Alpha Terminal</a>"

    return await send_telegram_message(msg.strip())

# Alias for backward compatibility
notify_top_picks = notify_super_digest
