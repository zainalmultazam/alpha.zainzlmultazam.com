import os
import json
import logging
from typing import Optional
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.config import settings
from app.services.market_data import get_market_climate, get_global_macro_data

logger = logging.getLogger("alpha.diagnostics")

router = APIRouter(tags=["Pages"])

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "../templates"))

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

PWA_MANIFEST = {
    "name": "Alpha",
    "short_name": "Alpha",
    "description": "High-Performance Swing Trading Screener & Journal for IDX & US Stock Markets",
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
            "src": "/favicon.svg?v=4",
            "sizes": "48x48 72x72 96x96 128x128 256x256",
            "type": "image/svg+xml",
            "purpose": "any"
        },
        {
            "src": "/icon-192.png?v=4",
            "sizes": "192x192",
            "type": "image/png",
            "purpose": "any"
        },
        {
            "src": "/icon-192-maskable.png?v=4",
            "sizes": "192x192",
            "type": "image/png",
            "purpose": "maskable"
        },
        {
            "src": "/icon-512.png?v=4",
            "sizes": "512x512",
            "type": "image/png",
            "purpose": "any"
        },
        {
            "src": "/icon-512-maskable.png?v=4",
            "sizes": "512x512",
            "type": "image/png",
            "purpose": "maskable"
        }
    ]
}

SW_JS = """// Alpha Self-Unregister Service Worker
self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.map((k) => caches.delete(k))))
      .then(() => self.registration.unregister())
      .then(() => self.clients.claim())
  );
});
"""

STATIC_ICONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../static/icons"))

@router.api_route("/favicon.svg", methods=["GET", "HEAD"])
@router.api_route("/icon-192.svg", methods=["GET", "HEAD"])
@router.api_route("/icon-512.svg", methods=["GET", "HEAD"])
async def get_favicon_svg():
    return Response(content=FAVICON_SVG, media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})

@router.api_route("/favicon.ico", methods=["GET", "HEAD"])
async def get_favicon_ico():
    path = os.path.join(STATIC_ICONS_DIR, "favicon.ico")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return Response(content=f.read(), media_type="image/x-icon", headers={"Cache-Control": "public, max-age=86400"})
    return Response(content=FAVICON_SVG, media_type="image/svg+xml")

@router.api_route("/icon-192.png", methods=["GET", "HEAD"])
@router.api_route("/icon-192-maskable.png", methods=["GET", "HEAD"])
async def get_icon_192():
    path = os.path.join(STATIC_ICONS_DIR, "icon-192.png")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return Response(content=f.read(), media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})
    return Response(content=FAVICON_SVG, media_type="image/svg+xml")

@router.api_route("/icon-512.png", methods=["GET", "HEAD"])
@router.api_route("/icon-512-maskable.png", methods=["GET", "HEAD"])
async def get_icon_512():
    path = os.path.join(STATIC_ICONS_DIR, "icon-512.png")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return Response(content=f.read(), media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})
    return Response(content=FAVICON_SVG, media_type="image/svg+xml")

@router.api_route("/apple-touch-icon.png", methods=["GET", "HEAD"])
@router.api_route("/apple-touch-icon-precomposed.png", methods=["GET", "HEAD"])
async def get_apple_touch_icon():
    path = os.path.join(STATIC_ICONS_DIR, "apple-touch-icon.png")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return Response(content=f.read(), media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})
    return Response(content=FAVICON_SVG, media_type="image/svg+xml")

@router.api_route("/favicon-32x32.png", methods=["GET", "HEAD"])
async def get_favicon_32():
    path = os.path.join(STATIC_ICONS_DIR, "favicon-32x32.png")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return Response(content=f.read(), media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})
    return Response(content=FAVICON_SVG, media_type="image/svg+xml")

@router.api_route("/favicon-16x16.png", methods=["GET", "HEAD"])
async def get_favicon_16():
    path = os.path.join(STATIC_ICONS_DIR, "favicon-16x16.png")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return Response(content=f.read(), media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})
    return Response(content=FAVICON_SVG, media_type="image/svg+xml")

@router.api_route("/manifest.json", methods=["GET", "HEAD"])
@router.api_route("/manifest.webmanifest", methods=["GET", "HEAD"])
async def get_manifest():
    return JSONResponse(content=PWA_MANIFEST, media_type="application/manifest+json", headers={"Cache-Control": "no-cache"})

@router.api_route("/sw.js", methods=["GET", "HEAD"])
@router.api_route("/service-worker.js", methods=["GET", "HEAD"])
async def get_service_worker():
    return Response(content=SW_JS, media_type="application/javascript", headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})

@router.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "domain": settings.APP_DOMAIN}

@router.post("/api/diagnostics/log")
async def receive_client_log(request: Request):
    try:
        body = await request.json()
        err_msg = body.get("error", "Unknown error")
        stack = body.get("stack", "")
        url = body.get("url", "")
        ua = body.get("userAgent", "")
        logger.error(f"🚨 [CLIENT ERROR] {err_msg} | URL: {url} | Stack: {stack[:300]}")
        
        # Also append to tmp/client_errors.log for immediate tail inspection
        log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../tmp"))
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "client_errors.log")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(body) + "\n")
            
        return {"status": "recorded"}
    except Exception as e:
        return {"status": "ignored", "error": str(e)}

VALID_VIEWS = {"screener", "tracker", "rules", "playbook", "journal", "charts", "performance", "calculator", "alerts", "settings", "stock-detail", "stock"}
VALID_MARKETS = {"idx", "us"}

def _render_terminal_page(request: Request, initial_market: str = "IDX", initial_view: str = "screener", initial_ticker: Optional[str] = None):
    theme = request.cookies.get("theme", "dark")
    climate_idx = get_market_climate(market="IDX")
    climate_us = get_market_climate(market="US")
    macro = get_global_macro_data()
    clean_view = "playbook" if initial_view == "rules" else initial_view
    if clean_view == "stock":
        clean_view = "stock-detail"
    
    return templates.TemplateResponse(
        request=request,
        name="index.html", 
        context={
            "request": request,
            "initial_market": initial_market.upper(),
            "initial_view": clean_view,
            "initial_ticker": initial_ticker.upper() if initial_ticker else None,
            "theme": theme,
            "climate_idx": climate_idx,
            "climate_us": climate_us,
            "macro": macro,
            "default_risk_pct": settings.DEFAULT_MAX_RISK_PCT,
            "default_capital": settings.DEFAULT_CAPITAL
        },
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

# ── Market-Prefixed Page Routes (e.g. /idx/stock-detail/TAPG, /us/screener) ─
@router.api_route("/us/stock-detail/{ticker}", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/idx/stock-detail/{ticker}", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/us/stock/{ticker}", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/idx/stock/{ticker}", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/us/screener/{ticker}", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/idx/screener/{ticker}", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def market_ticker_detail_page(ticker: str, request: Request):
    path_parts = request.url.path.strip("/").split("/")
    market = path_parts[0].upper()
    clean_ticker = ticker.upper().strip().replace(".JK", "")
    return _render_terminal_page(request, initial_market=market, initial_view="stock-detail", initial_ticker=clean_ticker)

@router.api_route("/us/{view}", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/idx/{view}", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def market_view_page(view: str, request: Request, ticker: Optional[str] = None):
    path_parts = request.url.path.strip("/").split("/")
    market = path_parts[0].upper()
    v = view.lower()
    if v not in VALID_VIEWS:
        v = "screener"
    clean_ticker = ticker.upper().strip().replace(".JK", "") if ticker else None
    if clean_ticker and v in ["screener", "stock-detail", "stock"]:
        v = "stock-detail"
    return _render_terminal_page(request, initial_market=market, initial_view=v, initial_ticker=clean_ticker)

@router.api_route("/us", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/idx", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def market_root_page(request: Request):
    path_parts = request.url.path.strip("/").split("/")
    market = path_parts[0].upper()
    return _render_terminal_page(request, initial_market=market, initial_view="screener")

# ── Unprefixed Page Routes (Smart Fallback & Dual Compatibility) ───────────
@router.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/screener", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/tracker", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/rules", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/journal", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/charts", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/performance", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/calculator", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/alerts", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/stock-detail", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/stock-detail/{ticker}", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/stock/{ticker}", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/settings", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def unprefixed_page(request: Request, ticker: Optional[str] = None):
    path_parts = request.url.path.strip("/").lower().split("/")
    initial_view = path_parts[0] if path_parts and path_parts[0] in VALID_VIEWS else "screener"
    clean_ticker = ticker.upper().strip().replace(".JK", "") if ticker else None
    if clean_ticker and initial_view in ["screener", "stock-detail", "stock"]:
        initial_view = "stock-detail"
    active_market = request.cookies.get("alpha_active_market", "IDX").upper()
    if active_market not in ["IDX", "US"]:
        active_market = "IDX"
    return _render_terminal_page(request, initial_market=active_market, initial_view=initial_view, initial_ticker=clean_ticker)

