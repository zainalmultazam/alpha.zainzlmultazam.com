from fastapi import APIRouter
from app.config import settings
from app.services.telegram import send_telegram_message, notify_morning_briefing, notify_evening_wrap
from app.services.market_data import get_market_climate, get_global_macro_data
from app.engine.journal import get_open_trades, get_journal_stats
from app.services.telegram_bot import run_safety_sentinel_check
from app.routers.screener import execute_market_scan, cached_scan_results

router = APIRouter(prefix="/api/telegram", tags=["Telegram"])

@router.get("/status")
async def api_telegram_status():
    open_trades = get_open_trades()
    return {
        "status": "success",
        "bot_configured": bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID),
        "chat_id": str(settings.TELEGRAM_CHAT_ID)[:4] + "****" if settings.TELEGRAM_CHAT_ID else None,
        "schedules": [
            {"time": "08:45 WIB", "title": "Morning Pre-Market Briefing & Top 3 Picks", "active": True},
            {"time": "Jam Bursa (3 Menit)", "title": "Safety Sentinel Live SL / TP Alerts", "active": True},
            {"time": "16:15 WIB", "title": "Evening Market & Portfolio Wrap", "active": True},
            {"time": "17:00 WIB", "title": "EOD Full Database Scan Refresh", "active": True}
        ],
        "open_trades_monitored": len(open_trades)
    }

@router.post("/test")
async def api_telegram_test():
    test_msg = f"🔔 <b>ALPHA GLOBAL TELEGRAM BOT AKTIF</b>\n"
    test_msg += f"━━━━━━━━━━━━━━━━━━\n"
    test_msg += f"• Domain  : <code>{settings.APP_DOMAIN}</code>\n"
    test_msg += f"• Status  : 🟢 <b>Terkoneksi Sempurna</b>\n"
    test_msg += f"• Pasar   : 🇮🇩 IDX Indonesia & 🇺🇸 US Wall Street\n"
    test_msg += f"━━━━━━━━━━━━━━━━━━\n"
    test_msg += f"<i>Robot siap mengawal portofolio global Anda!</i>"
    
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "🌐 Buka Alpha", "url": f"https://{settings.APP_DOMAIN}"}
            ]
        ]
    }
    ok = await send_telegram_message(test_msg, reply_markup=reply_markup)
    return {"status": "success" if ok else "failed", "connected": ok}

@router.post("/send-digest")
async def api_telegram_send_digest(market: str = "IDX"):
    m_clean = (market or "IDX").upper().strip()
    if not cached_scan_results.get(m_clean):
        cached_scan_results[m_clean] = await execute_market_scan(market=m_clean)
    climate = get_market_climate(market=m_clean)
    macro = get_global_macro_data() if m_clean == "IDX" else None
    ok = await notify_morning_briefing(cached_scan_results[m_clean][:3], climate=climate, macro=macro, market=m_clean)
    return {"status": "success" if ok else "failed", "sent": ok, "market": m_clean, "top_count": min(3, len(cached_scan_results[m_clean]))}

@router.post("/send-evening-wrap")
async def api_telegram_send_evening_wrap():
    climate = get_market_climate(market="IDX")
    open_trades = get_open_trades(market="IDX")
    stats = get_journal_stats(market="IDX")
    ok = await notify_evening_wrap(climate=climate, open_trades=open_trades, stats=stats)
    return {"status": "success" if ok else "failed", "sent": ok, "open_trades_count": len(open_trades)}

@router.post("/check-sentinel")
async def api_check_sentinel():
    res = await run_safety_sentinel_check()
    return {"status": "success", "data": res, "message": "Safety Sentinel check executed"}
