from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os
import asyncio
import time
import json
import pandas as pd
from typing import Optional

from app.config import settings
from app.engine.universe import get_universe
from app.services.market_data import fetch_stock_df, batch_fetch_stock_dfs, clear_cache, get_market_climate, get_idx_market_status
from app.engine.scanner import scan_stock
from app.engine.strategy import calculate_lot_size
from app.engine.journal import log_trade, get_all_trades, close_trade, delete_trade, get_journal_stats, get_performance_metrics, init_db
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

FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <linearGradient id="zapGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#60A5FA"/>
      <stop offset="50%" stop-color="#3B82F6"/>
      <stop offset="100%" stop-color="#1D4ED8"/>
    </linearGradient>
    <linearGradient id="borderGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#3B82F6" stop-opacity="0.8"/>
      <stop offset="100%" stop-color="#06B6D4" stop-opacity="0.35"/>
    </linearGradient>
    <filter id="neonGlow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="2.5" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  <rect width="64" height="64" rx="16" fill="#070913"/>
  <rect x="1.5" y="1.5" width="61" height="61" rx="14.5" fill="none" stroke="url(#borderGrad)" stroke-width="1.5"/>
  <path d="M35 8 L15 36 L30 36 L25 56 L49 26 L34 26 Z" fill="url(#zapGrad)" filter="url(#neonGlow)"/>
</svg>"""

@app.get("/favicon.svg")
@app.get("/favicon.ico")
@app.get("/apple-touch-icon.png")
@app.get("/apple-touch-icon-precomposed.png")
@app.get("/icon-192.svg")
@app.get("/icon-512.svg")
@app.get("/icon-192.png")
@app.get("/icon-512.png")
async def get_favicon():
    return Response(content=FAVICON_SVG, media_type="image/svg+xml", headers={"Cache-Control": "no-cache, must-revalidate"})

PWA_MANIFEST = {
    "name": "Alpha - IDX Trading Terminal",
    "short_name": "Alpha IDX",
    "description": "High-Performance Swing Trading Screener & Journal for Indonesia Stock Exchange",
    "start_url": "/",
    "id": "/",
    "scope": "/",
    "display": "standalone",
    "display_override": ["window-controls-overlay", "standalone", "minimal-ui"],
    "orientation": "portrait-primary",
    "background_color": "#06080F",
    "theme_color": "#06080F",
    "categories": ["finance", "productivity", "utilities"],
    "icons": [
        {
            "src": "/favicon.svg?v=3",
            "sizes": "48x48 72x72 96x96 128x128 256x256",
            "type": "image/svg+xml",
            "purpose": "any"
        },
        {
            "src": "/icon-192.svg?v=3",
            "sizes": "192x192",
            "type": "image/svg+xml",
            "purpose": "any"
        },
        {
            "src": "/icon-512.svg?v=3",
            "sizes": "512x512",
            "type": "image/svg+xml",
            "purpose": "any maskable"
        }
    ]
}

@app.get("/manifest.json")
@app.get("/manifest.webmanifest")
async def get_manifest():
    return JSONResponse(content=PWA_MANIFEST, media_type="application/manifest+json", headers={"Cache-Control": "no-cache"})

SW_JS = """const CACHE_NAME = 'alpha-pwa-v1';
const PRECACHE_URLS = [
  '/',
  '/manifest.json',
  '/favicon.svg?v=3'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Network-First for API requests (real-time data)
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request).catch(() => caches.match(event.request))
    );
    return;
  }

  // Navigation requests: Network-First with Cache Fallback
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response && response.status === 200) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          }
          return response;
        })
        .catch(() => caches.match(event.request).then((cached) => cached || caches.match('/')))
    );
    return;
  }

  // Stale-While-Revalidate for other static assets
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      const fetchPromise = fetch(event.request).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const clone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return networkResponse;
      }).catch(() => cachedResponse);

      return cachedResponse || fetchPromise;
    })
  );
});
"""

@app.get("/sw.js")
@app.get("/service-worker.js")
async def get_service_worker():
    return Response(content=SW_JS, media_type="application/javascript", headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})


# Scheduler untuk scan otomatis setiap sore pukul 17:00 WIB
scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup_event():
    init_db()
    # 1. Jadwalkan scan otomatis sore hari
    try:
        scheduler.add_job(run_daily_scheduled_scan, "cron", hour=17, minute=0, timezone="Asia/Jakarta")
        scheduler.start()
    except Exception:
        pass
    
    # 2. Jalankan background worker Telegram Polling & Safety Sentinel
    asyncio.create_task(telegram_polling_worker())
    asyncio.create_task(sentinel_scheduler_worker())

cached_scan_results = []
last_scan_duration = 0.0

async def execute_market_scan() -> list:
    """Melakukan scan seluruh universe saham secara asinkron dengan batch downloader."""
    global last_scan_duration
    t0 = time.time()
    universe = get_universe()
    tickers = [item["ticker"] for item in universe]
    loop = asyncio.get_event_loop()
    
    # Ambil seluruh data saham secara batch multi-threaded
    dfs = await loop.run_in_executor(None, batch_fetch_stock_dfs, tickers, 35)
    
    results = []
    for item in universe:
        df = dfs.get(item["ticker"])
        res = scan_stock(item, df)
        if res is not None:
            results.append(res)
            
    results.sort(key=lambda x: x["score"], reverse=True)
    last_scan_duration = round(time.time() - t0, 2)
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
@app.get("/screener", response_class=HTMLResponse)
@app.get("/rules", response_class=HTMLResponse)
@app.get("/journal", response_class=HTMLResponse)
@app.get("/charts", response_class=HTMLResponse)
@app.get("/performance", response_class=HTMLResponse)
@app.get("/calculator", response_class=HTMLResponse)
@app.get("/alerts", response_class=HTMLResponse)
async def home(request: Request):
    climate = get_market_climate()
    # Detect initial view from path
    path = request.url.path.strip("/").lower()
    initial_view = path if path in ["screener", "rules", "journal", "charts", "performance", "calculator", "alerts"] else "screener"
    if initial_view == "rules":
        initial_view = "playbook"

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "domain": settings.APP_DOMAIN,
            "default_capital": settings.DEFAULT_CAPITAL,
            "default_risk_pct": settings.DEFAULT_MAX_RISK_PCT,
            "app_name": settings.APP_NAME,
            "climate": climate,
            "initial_view": initial_view
        }
    )

@app.get("/api/performance")
async def api_performance(capital: Optional[float] = None):
    base_cap = capital or settings.DEFAULT_CAPITAL or 50000000.0
    metrics = get_performance_metrics(base_cap)
    return {"status": "success", "data": metrics}

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
    global cached_scan_results, last_scan_duration
    if not cached_scan_results or force:
        if force:
            clear_cache()
        cached_scan_results = await execute_market_scan()
    climate = get_market_climate()
    universe = get_universe()
    return {
        "status": "success", 
        "total": len(cached_scan_results),
        "total_universe": len(universe),
        "duration_sec": last_scan_duration,
        "climate": climate,
        "data": cached_scan_results
    }

@app.get("/api/scan-stream")
async def api_scan_stream(force: bool = False):
    """Server-Sent Events endpoint untuk streaming persentase scan langsung ke frontend."""
    async def event_generator():
        global cached_scan_results, last_scan_duration
        t0 = time.time()
        if force:
            clear_cache()
        
        universe = get_universe()
        total_universe = len(universe)
        
        # Step 1: Inisialisasi
        yield f"data: {json.dumps({'progress': 10, 'stage': 'Menyiapkan 104 watchlist universe IDX...', 'total': total_universe})}\n\n"
        await asyncio.sleep(0.05)
        
        # Step 2: Batch Download Data Bursa
        yield f"data: {json.dumps({'progress': 30, 'stage': 'Mengunduh data candle & volume bursa paralel...', 'total': total_universe})}\n\n"
        loop = asyncio.get_event_loop()
        tickers = [item["ticker"] for item in universe]
        dfs = await loop.run_in_executor(None, batch_fetch_stock_dfs, tickers, 35)
        
        # Step 3: Analisis Pola Breakout Raider & Validasi Likuiditas MA20
        yield f"data: {json.dumps({'progress': 70, 'stage': 'Menganalisis Stage 2, VCP, EMA Pullback & Likuiditas MA20...', 'total': total_universe})}\n\n"
        results = []
        for idx, item in enumerate(universe):
            df = dfs.get(item["ticker"])
            res = scan_stock(item, df)
            if res is not None:
                results.append(res)
                
        results.sort(key=lambda x: x["score"], reverse=True)
        cached_scan_results = results
        last_scan_duration = round(time.time() - t0, 2)
        climate = get_market_climate()
        
        # Step 4: Selesai
        yield f"data: {json.dumps({'progress': 100, 'stage': 'Pemindaian selesai!', 'total': len(results), 'total_universe': total_universe, 'duration_sec': last_scan_duration, 'climate': climate, 'data': results})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/api/calculate-size")
async def api_calculate_size(
    capital: float = Form(...),
    risk_pct: float = Form(1.0),
    entry_price: float = Form(...),
    stop_loss: float = Form(...)
):
    try:
        result = calculate_lot_size(capital, risk_pct, entry_price, stop_loss)
        return {"status": "success", "data": result}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})

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

@app.post("/api/journal/delete/{trade_id}")
@app.delete("/api/journal/{trade_id}")
async def api_delete_trade(trade_id: int):
    ok = delete_trade(trade_id)
    return {"status": "success" if ok else "error", "deleted": ok}

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
