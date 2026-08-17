from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os
import asyncio
import pandas as pd
from typing import Optional

from app.config import settings
from app.engine.universe import get_universe
from app.services.market_data import fetch_stock_df, clear_cache, get_market_climate, get_idx_market_status
from app.engine.scanner import scan_stock
from app.engine.strategy import calculate_lot_size
from app.engine.journal import log_trade, get_all_trades, close_trade, get_journal_stats, init_db
from app.services.telegram import send_telegram_message, notify_super_digest
from app.services.telegram_bot import telegram_polling_worker, sentinel_scheduler_worker, run_safety_sentinel_check

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# Scheduler untuk scan otomatis setiap sore pukul 17:00 WIB
scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup_event():
    init_db()
    # 1. Jadwalkan scan otomatis sore hari
    scheduler.add_job(run_daily_scheduled_scan, "cron", hour=17, minute=0, timezone="Asia/Jakarta")
    scheduler.start()
    
    # 2. Jalankan background worker Telegram Polling & Safety Sentinel
    asyncio.create_task(telegram_polling_worker())
    asyncio.create_task(sentinel_scheduler_worker())

cached_scan_results = []

async def execute_market_scan() -> list:
    """Melakukan scan seluruh universe saham secara asinkron."""
    universe = get_universe()
    loop = asyncio.get_event_loop()
    
    def scan_single(item):
        df = fetch_stock_df(item["ticker"])
        return scan_stock(item, df)

    # Menjalankan pemindaian dengan thread pool agar non-blocking
    tasks = [loop.run_in_executor(None, scan_single, item) for item in universe]
    scanned = await asyncio.gather(*tasks)
    
    results = [res for res in scanned if res is not None]
    results.sort(key=lambda x: x["score"], reverse=True)
    return results

async def run_daily_scheduled_scan():
    global cached_scan_results
    results = await execute_market_scan()
    cached_scan_results = results
    if settings.ENABLE_TELEGRAM_ALERTS:
        climate = get_market_climate()
        await notify_super_digest(results[:3], climate)

@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "domain": settings.APP_DOMAIN}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    climate = get_market_climate()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "domain": settings.APP_DOMAIN,
            "default_capital": settings.DEFAULT_CAPITAL,
            "default_risk_pct": settings.DEFAULT_MAX_RISK_PCT,
            "app_name": settings.APP_NAME,
            "climate": climate
        }
    )

@app.post("/api/auth/verify-pin")
async def api_verify_pin(pin: str = Form(...)):
    if str(pin).strip() == str(settings.ACCESS_PIN).strip():
        response = JSONResponse(content={"status": "success", "authenticated": True, "token": "pin_ok"})
        response.set_cookie(key="alpha_pin_auth", value="authenticated", max_age=2592000, httponly=False, samesite="lax")
        return response
    return JSONResponse(status_code=401, content={"status": "error", "message": "PIN Salah. Silakan coba lagi."})

@app.get("/api/auth/status")
async def api_auth_status(request: Request):
    auth_cookie = request.cookies.get("alpha_pin_auth")
    return {"status": "success", "authenticated": auth_cookie == "authenticated"}

@app.post("/api/auth/logout")
async def api_auth_logout():
    response = JSONResponse(content={"status": "success", "authenticated": False})
    response.delete_cookie("alpha_pin_auth")
    return response

@app.get("/api/market-climate")
async def api_market_climate():
    return {"status": "success", "data": get_market_climate()}

@app.get("/api/market-status")
async def api_market_status():
    return {"status": "success", "data": get_idx_market_status()}

@app.get("/api/scan")
async def api_scan(force: bool = False):
    global cached_scan_results
    if not cached_scan_results or force:
        if force:
            clear_cache()
        cached_scan_results = await execute_market_scan()
    climate = get_market_climate()
    return {
        "status": "success", 
        "total": len(cached_scan_results), 
        "climate": climate,
        "data": cached_scan_results
    }

@app.post("/api/calculate-size")
async def api_calculate_size(
    capital: float = Form(...),
    risk_pct: float = Form(1.0),
    entry_price: float = Form(...),
    stop_loss: float = Form(...)
):
    result = calculate_lot_size(capital, risk_pct, entry_price, stop_loss)
    return {"status": "success", "data": result}

@app.get("/api/chart/{ticker}")
async def api_chart(ticker: str):
    full_ticker = ticker if ticker.endswith(".JK") else f"{ticker}.JK"
    loop = asyncio.get_event_loop()
    df = await loop.run_in_executor(None, fetch_stock_df, full_ticker)
    
    if df is None or df.empty:
        return JSONResponse(status_code=404, content={"error": "Data not found"})
    
    # Format untuk TradingView Lightweight Charts
    candles = []
    volumes = []
    for idx, row in df.iterrows():
        time_str = idx.strftime("%Y-%m-%d")
        open_val = round(float(row["Open"]), 2)
        close_val = round(float(row["Close"]), 2)
        high_val = round(float(row["High"]), 2)
        low_val = round(float(row["Low"]), 2)
        vol_val = int(row["Volume"]) if pd.notnull(row["Volume"]) else 0
        
        candles.append({
            "time": time_str,
            "open": open_val,
            "high": high_val,
            "low": low_val,
            "close": close_val,
        })
        volumes.append({
            "time": time_str,
            "value": vol_val,
            "color": "rgba(16, 185, 129, 0.4)" if close_val >= open_val else "rgba(239, 68, 68, 0.4)"
        })
        
    return {"ticker": ticker, "candles": candles[-150:], "volumes": volumes[-150:]}

@app.get("/api/journal")
async def api_get_journal():
    return {"status": "success", "trades": get_all_trades(), "stats": get_journal_stats()}

@app.get("/api/journal/stats")
async def api_journal_stats():
    return {"status": "success", "data": get_journal_stats()}

@app.post("/api/journal/log")
async def api_log_trade(
    ticker: str = Form(...),
    entry_price: float = Form(...),
    stop_loss: float = Form(...),
    target_price: float = Form(...),
    lots: int = Form(...),
    setup_name: str = Form("Alpha Setup")
):
    trade_id = log_trade(ticker, entry_price, stop_loss, target_price, lots, setup_name)
    return {"status": "success", "trade_id": trade_id}

@app.post("/api/journal/close")
async def api_close_trade(
    trade_id: int = Form(...),
    exit_price: float = Form(...),
    notes: Optional[str] = Form("")
):
    ok = close_trade(trade_id, exit_price, notes or "")
    return {"status": "success" if ok else "error"}

@app.get("/api/journal/check-safety")
async def api_check_safety():
    await run_safety_sentinel_check()
    return {"status": "success", "message": "Safety Sentinel check executed"}

@app.post("/api/telegram/test")
async def api_telegram_test():
    ok = await send_telegram_message(f"🔔 <b>AlphaSwing IDX Test Alert</b>\nKoneksi Telegram berhasil terhubung ke sistem {settings.APP_DOMAIN}!")
    return {"status": "success" if ok else "failed", "connected": ok}

@app.post("/api/telegram/send-digest")
async def api_telegram_send_digest():
    global cached_scan_results
    if not cached_scan_results:
        cached_scan_results = await execute_market_scan()
    climate = get_market_climate()
    ok = await notify_super_digest(cached_scan_results[:3], climate)
    return {"status": "success" if ok else "failed", "sent": ok, "top_count": min(3, len(cached_scan_results))}
