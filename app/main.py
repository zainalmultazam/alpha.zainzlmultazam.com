import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

from app.config import settings
from app.engine.journal import init_db, get_open_trades, get_journal_stats
from app.engine.capital import init_capital_db
from app.engine.tracker import init_tracker_db, record_signal_snapshot, update_tracked_signals
from app.services.market_data import get_market_climate, get_global_macro_data
from app.services.telegram import notify_super_digest, notify_morning_briefing, notify_evening_wrap
from app.services.telegram_bot import telegram_polling_worker, sentinel_scheduler_worker

# Import Routers
from app.routers import pages, market, screener, tracker, journal, capital, auth, telegram, forecaster, ai
from app.routers.screener import execute_market_scan, cached_scan_results

app = FastAPI(title=settings.APP_NAME)

@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME}

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Scheduler untuk automasi pasar (Morning Briefing, Evening Wrap, EOD Scan) ──
scheduler = AsyncIOScheduler()

async def run_scheduled_morning_briefing():
    """Jadwal Otomatis 08:45 WIB: Kirim Morning Pre-Market Briefing & Top 3 Picks (IDX)."""
    global cached_scan_results
    try:
        if not cached_scan_results.get("IDX"):
            cached_scan_results["IDX"] = await execute_market_scan(market="IDX")
        climate = get_market_climate(market="IDX")
        macro = get_global_macro_data()
        regime = climate.get("regime", "BULLISH") if isinstance(climate, dict) else "BULLISH"
        record_signal_snapshot(cached_scan_results["IDX"][:10], climate=regime, market="IDX")
        await notify_morning_briefing(cached_scan_results["IDX"][:3], climate=climate, macro=macro, market="IDX")
    except Exception as e:
        print(f"Error in morning briefing cron: {e}")

async def run_scheduled_evening_wrap():
    """Jadwal Otomatis 16:15 WIB: Kirim Evening Market & Portfolio Wrap (IDX)."""
    try:
        climate = get_market_climate(market="IDX")
        macro = get_global_macro_data()
        open_trades = get_open_trades(market="IDX")
        stats = get_journal_stats(market="IDX")
        update_tracked_signals(market="IDX")
        await notify_evening_wrap(climate=climate, macro=macro, open_trades=open_trades, stats=stats, market="IDX")
    except Exception as e:
        print(f"Error in evening wrap cron: {e}")

async def run_daily_scheduled_scan():
    """Jadwal Otomatis 17:00 WIB: Scan EOD Kompas100, update sinyal, & sinkronisasi tracker."""
    global cached_scan_results
    try:
        print("[CRON] Running daily EOD market scan...")
        cached_scan_results["IDX"] = await execute_market_scan(market="IDX", force=True)
        update_tracked_signals(market="IDX")
        print("[CRON] Daily EOD scan & signal tracking completed.")
    except Exception as e:
        print(f"Error in daily scheduled scan: {e}")

async def run_scheduled_premarket_us():
    """Jadwal Otomatis 20:00 WIB: Kirim Wall Street Pre-Market Briefing & Top 3 Picks."""
    global cached_scan_results
    try:
        if not cached_scan_results.get("US"):
            cached_scan_results["US"] = await execute_market_scan(market="US")
        climate = get_market_climate(market="US")
        regime = climate.get("regime", "BULLISH") if isinstance(climate, dict) else "BULLISH"
        record_signal_snapshot(cached_scan_results["US"][:10], climate=regime, market="US")
        await notify_morning_briefing(cached_scan_results["US"][:3], climate=climate, macro={}, market="US")
    except Exception as e:
        print(f"Error in US premarket briefing cron: {e}")

async def run_scheduled_postmarket_us():
    """Jadwal Otomatis 06:00 WIB: Kirim Wall Street Post-Market Wrap & Status Portofolio US."""
    try:
        climate = get_market_climate(market="US")
        open_trades = get_open_trades(market="US")
        stats = get_journal_stats(market="US")
        update_tracked_signals(market="US")
        await notify_evening_wrap(climate=climate, open_trades=open_trades, stats=stats, market="US")
    except Exception as e:
        print(f"Error in US postmarket wrap cron: {e}")

@app.on_event("startup")
async def startup_event():
    init_db()
    init_tracker_db()
    init_capital_db()
    
    # 1. Jadwalkan bot cron otomatis
    try:
        # [IDX] Pukul 08:45 WIB: Morning Pre-Market Briefing (Senin-Jumat)
        scheduler.add_job(run_scheduled_morning_briefing, "cron", day_of_week="mon-fri", hour=8, minute=45, timezone="Asia/Jakarta")
        # [IDX] Pukul 16:15 WIB: Evening Market & Portfolio Wrap (Senin-Jumat)
        scheduler.add_job(run_scheduled_evening_wrap, "cron", day_of_week="mon-fri", hour=16, minute=15, timezone="Asia/Jakarta")
        # [IDX] Pukul 17:00 WIB: EOD Full Database Refresh Scan (Senin-Jumat)
        scheduler.add_job(run_daily_scheduled_scan, "cron", day_of_week="mon-fri", hour=17, minute=0, timezone="Asia/Jakarta")
        # [IDX AI Learner] Pukul 17:15 WIB: Autonomous External Learning & Calibration (Senin-Jumat)
        from app.engine.external_learner import run_nightly_external_learning_idx, run_nightly_external_learning_us
        scheduler.add_job(run_nightly_external_learning_idx, "cron", day_of_week="mon-fri", hour=17, minute=15, timezone="Asia/Jakarta")
        
        # [US Wall Street] Pukul 20:00 WIB: Wall Street Pre-Market Briefing & Top 3 Picks (Senin-Jumat)
        scheduler.add_job(run_scheduled_premarket_us, "cron", day_of_week="mon-fri", hour=20, minute=0, timezone="Asia/Jakarta")
        # [US Wall Street] Pukul 06:00 WIB: Wall Street Post-Market Wrap (Selasa-Sabtu)
        scheduler.add_job(run_scheduled_postmarket_us, "cron", day_of_week="tue-sat", hour=6, minute=0, timezone="Asia/Jakarta")
        # [US AI Learner] Pukul 06:15 WIB: Autonomous External Learning & Calibration (Selasa-Sabtu)
        scheduler.add_job(run_nightly_external_learning_us, "cron", day_of_week="tue-sat", hour=6, minute=15, timezone="Asia/Jakarta")
        
        scheduler.start()
    except Exception as e:
        print(f"Scheduler start warning: {e}")
    
    # 2. Jalankan background worker Telegram Polling & Safety Sentinel
    asyncio.create_task(telegram_polling_worker())
    asyncio.create_task(sentinel_scheduler_worker())

# ── Mount All Routers ────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(market.router)
app.include_router(screener.router)
app.include_router(tracker.router)
app.include_router(forecaster.router)
app.include_router(journal.router)
app.include_router(capital.router)
app.include_router(telegram.router)
app.include_router(ai.router)
app.include_router(pages.router)  # Pages router mounted last to allow specific API paths first
