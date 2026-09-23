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

def format_id_date(dt: Optional[datetime] = None, include_time: bool = True, include_day: bool = True) -> str:
    """Format tanggal Indonesia (misal: Selasa, 18 Agu 2026, 17:00 WIB atau 18 Agu 2026, 17:00)."""
    if dt is None:
        dt = datetime.now()
    days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    months = ["", "Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
    day_name = days[dt.weekday()]
    month_name = months[dt.month]
    day_prefix = f"{day_name}, " if include_day else ""
    time_suffix = f", {dt.strftime('%H:%M')} WIB" if include_time else ""
    return f"{day_prefix}{dt.day} {month_name} {dt.year}{time_suffix}"

async def notify_morning_briefing(picks: List[Dict[str, Any]], climate: Optional[Dict[str, Any]] = None, macro: Optional[Dict[str, Any]] = None, market: str = "IDX") -> bool:
    """Mengirimkan Morning Pre-Market Briefing (08:45 WIB untuk IDX / 20:00 WIB untuk Wall Street) dengan Iklim Pasar, Radar Makro, dan Top 3 Picks."""
    now_str = format_id_date(datetime.now())
    clean_m = (market or "IDX").upper().strip()
    is_us = (clean_m == "US")
    
    # 1. Header & Market Climate Banner
    regime_status = climate.get("regime", "BULLISH") if climate else "BULLISH"
    index_name = "S&P 500" if is_us else "IHSG"
    idx_price = climate.get("price", 0) if climate else 0
    idx_change = climate.get("change_pct", 0) if climate else 0
    sign = "+" if idx_change >= 0 else ""
    exposure = climate.get("exposure_pct", 50) if climate else 50
    
    if regime_status == "BULLISH":
        climate_badge = f"🟢 <b>BULLISH ({exposure}% Modal Aktif)</b>"
    elif regime_status == "NEUTRAL":
        climate_badge = f"🟡 <b>CAUTION ({exposure}% Modal Aktif)</b>"
    else:
        climate_badge = f"🔴 <b>DEFENSIVE ({exposure}% Modal Aktif)</b>"

    header_title = "🇺🇸 🌆 <b>WALL STREET PRE-MARKET BRIEFING</b>" if is_us else "🇮🇩 🌅 <b>MORNING PRE-MARKET BRIEFING</b>"
    price_str = f"${idx_price:,.2f}" if is_us else f"{idx_price:,.2f}"

    msg = f"{header_title}\n"
    msg += f"<i>{now_str}</i>\n"
    msg += "━━━━━━━━━━━━━━━━━━\n"
    
    msg += f"📊 <b>{index_name}:</b> <code>{price_str}</code> ({sign}{idx_change}%)\n"
    msg += f"🧭 <b>Rezim:</b> {climate_badge}\n"
    if climate and climate.get("advice"):
        msg += f"💡 <i>{climate['advice']}</i>\n"
    msg += "━━━━━━━━━━━━━━━━━━\n"

    # 2. Global Macro Radar Highlights (hanya untuk briefing pagi IDX)
    if not is_us and macro and macro.get("items"):
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
        open_trades = get_open_trades(market=clean_m)
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
        picks_title = "🎯 <b>TOP 3 US MOMENTUM PICKS (PLUANG):</b>\n\n" if is_us else "🎯 <b>TOP 3 REKOMENDASI HARI INI:</b>\n\n"
        msg += picks_title
        
        # Filter blackout stocks for US market so user is protected from gap-down risk
        if is_us:
            safe_picks = [p for p in picks if not p.get("is_earnings_blackout")]
            top_3 = safe_picks[:3] if safe_picks else picks[:3]
        else:
            top_3 = picks[:3]

        inline_keyboard = []
        base_capital = 5000.0 if is_us else settings.DEFAULT_CAPITAL

        for i, p in enumerate(top_3, 1):
            plan = p.get("plan", {})
            entry = float(plan.get("entry_price", p.get("close", 0)))
            sl = float(plan.get("stop_loss", entry * 0.96))
            tp1 = float(plan.get("tp1", entry * 1.08))
            tp2 = float(plan.get("tp2", entry * 1.15))

            # Hitung alokasi lot/shares otomatis berbasis 1% risk dari default capital
            sizing = calculate_lot_size(base_capital, settings.DEFAULT_MAX_RISK_PCT, entry, sl, market=clean_m)
            lots = sizing["lots"]
            shares = sizing.get("shares", lots)
            unit_name = "Shares" if is_us else "Lot"
            qty_val = shares if is_us else lots
            half_qty = max(1, qty_val // 2) if not is_us else round(qty_val / 2, 2)
            
            cost_str = f"${sizing['total_cost']:,.2f}" if is_us else format_rupiah_short(sizing["total_cost"])
            risk_str = f"${sizing['max_risk_amount']:,.2f}" if is_us else format_rupiah_short(sizing["max_risk_idr"])

            entry_str = f"${entry:,.2f}" if is_us else f"{int(entry):,}"
            sl_str = f"${sl:,.2f}" if is_us else f"{int(sl):,}"
            tp1_str = f"${tp1:,.2f}" if is_us else f"{int(tp1):,}"
            tp2_str = f"${tp2:,.2f}" if is_us else f"{int(tp2):,}"

            weekly_tag = "Weekly Confirmed" if p.get("weekly_confirmed") else "Daily Setup"
            safe_name = html.escape(str(p.get("name", p.get("symbol", ""))))
            safe_setup = html.escape(str(p.get("primary_setup", "Breakout")))
            earnings_tag = f" | {p.get('earnings_badge')}" if p.get("earnings_badge") else ""

            turnover_unit = f"${p.get('turnover_bio', 0)}M" if is_us else f"Rp {p.get('turnover_bio', 0)}B"

            msg += f"<b>#{i} {p['symbol']} - {safe_name}</b>\n"
            msg += f"• Setup: <code>{safe_setup}</code> (Skor: <b>{p.get('score', 90)} PTS</b>{earnings_tag})\n"
            msg += f"• Validasi: <i>{weekly_tag}</i> | Turnover: {turnover_unit}\n\n"
            
            # Angka kunci format code agar tap-to-copy
            msg += f"🟢 <b>BUY (GTC) :</b> <code>{entry_str}</code> → <b>{qty_val} {unit_name}</b> ({cost_str})\n"
            msg += f"🔴 <b>STOP LOSS :</b> <code>{sl_str}</code> (-{plan.get('risk_pct', 4.0)}% | Risk {risk_str})\n"
            msg += f"🎯 <b>TARGET TP1:</b> <code>{tp1_str}</code> (+{plan.get('tp1_gain_pct', 8.0)}% | Jual {half_qty} {unit_name})\n"
            msg += f"🚀 <b>TARGET TP2:</b> <code>{tp2_str}</code> (+{plan.get('tp2_gain_pct', 15.0)}%)\n\n"
            
            if is_us:
                msg += f"• <a href=\"https://app.pluang.com\">Buka {p['symbol']} di Pluang</a>\n"
            else:
                msg += f"• <a href=\"https://stockbit.com/#/symbol/{p['symbol']}\">Buka {p['symbol']} di Stockbit</a>\n"
            
            if i < len(top_3):
                msg += "──────────────────\n\n"

            inline_keyboard.append([
                {
                    "text": f"🛒 Catat Beli {p['symbol']} ({qty_val} {unit_name})",
                    "callback_data": f"picklot:{p['symbol']}:{qty_val}:{entry}:{sl}:{tp1}"
                }
            ])

        reply_markup = {"inline_keyboard": inline_keyboard} if inline_keyboard else None
    else:
        msg += "<i>Belum ada setup dengan skor tinggi yang lolos filter likuiditas. Disiplin tunggu konfirmasi pasar!</i>\n"
        reply_markup = None

    return await send_telegram_message(msg.strip(), reply_markup=reply_markup)

async def notify_super_digest(picks: List[Dict[str, Any]], climate: Optional[Dict[str, Any]] = None, market: str = "IDX") -> bool:
    """Mengirimkan Super-Bot Digest (HANYA TOP 3 TERBAIK) dengan tombol interaktif 1-Click Buy."""
    return await notify_morning_briefing(picks, climate=climate, market=market)

async def notify_evening_wrap(climate: Optional[Dict[str, Any]] = None, open_trades: Optional[List[Dict[str, Any]]] = None, stats: Optional[Dict[str, Any]] = None, market: str = "IDX") -> bool:
    """Mengirimkan Evening Market & Portfolio Wrap (16:15 WIB untuk IDX / 06:00 WIB untuk Wall Street)."""
    now_str = format_id_date(datetime.now())
    clean_m = (market or "IDX").upper().strip()
    is_us = (clean_m == "US")
    
    index_name = "S&P 500" if is_us else "IHSG"
    idx_price = climate.get("price", 0) if climate else 0
    idx_change = climate.get("change_pct", 0) if climate else 0
    sign = "+" if idx_change >= 0 else ""
    regime = climate.get("regime", "BULLISH") if climate else "BULLISH"

    header_title = "🇺🇸 🌅 <b>WALL STREET POST-MARKET WRAP</b>" if is_us else "🇮🇩 🌆 <b>MARKET CLOSE & PORTFOLIO WRAP</b>"
    price_str = f"${idx_price:,.2f}" if is_us else f"{idx_price:,.2f}"

    msg = f"{header_title}\n"
    msg += f"<i>{now_str}</i>\n"
    msg += "━━━━━━━━━━━━━━━━━━\n"
    msg += f"📊 <b>{index_name} Tutup:</b> <code>{price_str}</code> ({sign}{idx_change}%) • <b>{regime}</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━\n\n"

    # Status Open Trades
    unit_name = "Shares" if is_us else "Lot"
    if open_trades and len(open_trades) > 0:
        msg += f"💼 <b>POSISI TERBUKA AKTIF ({len(open_trades)} Saham):</b>\n"
        for t in open_trades:
            ticker = t.get("ticker", "")
            entry = float(t.get("entry_price", 0))
            sl = float(t.get("stop_loss", 0))
            lots = int(t.get("lots", 0))
            entry_fmt = f"${entry:,.2f}" if is_us else f"Rp {entry:,.0f}"
            sl_fmt = f"${sl:,.2f}" if is_us else f"Rp {sl:,.0f}"
            msg += f"• <b>{ticker}</b> ({lots} {unit_name}) — Entry: {entry_fmt} | SL: {sl_fmt}\n"
        msg += "\n"
    else:
        cash_type = "USD" if is_us else "RDN"
        msg += f"💼 <b>Posisi Terbuka:</b> 0 Saham (100% Cash {cash_type} Aman)\n\n"

    # Performance Stats
    if stats:
        win_rate = stats.get("win_rate", 0.0)
        pnl = stats.get("total_realized_pnl", 0.0)
        pnl_sign = "+" if pnl >= 0 else ""
        pnl_fmt = f"{pnl_sign}${pnl:,.2f}" if is_us else f"{pnl_sign}Rp {pnl:,.0f}"
        closed_count = stats.get("closed_trades_count", 0)
        msg += "📈 <b>RINGKASAN KINERJA JURNAL:</b>\n"
        msg += f"• Win Rate        : <b>{win_rate:.1f}%</b>\n"
        msg += f"• Total Realized  : <b>{pnl_fmt}</b>\n"
        msg += f"• Transaksi Selesai: <b>{closed_count} Trade</b>\n"
    
    app_url = f"https://{settings.APP_DOMAIN}/{clean_m.lower()}/screener"
    msg += "\n────────────\n"
    msg += f"🌐 <a href=\"{app_url}\">Buka Alpha ({clean_m})</a>"

    return await send_telegram_message(msg.strip())

# Alias for backward compatibility
notify_top_picks = notify_super_digest
