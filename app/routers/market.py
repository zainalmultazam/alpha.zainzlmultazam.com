import asyncio
from datetime import datetime
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.services.market_data import (
    get_market_climate, 
    get_idx_market_status, 
    get_us_market_status, 
    get_global_macro_data,
    batch_fetch_stock_dfs
)
from app.engine.universe import get_universe
from app.engine.technical import calculate_money_flow
from app.engine.sector import calculate_sector_rotation

router = APIRouter(tags=["Market"])

@router.get("/api/market-climate")
async def api_market_climate(force: bool = False, market: str = "IDX"):
    clean_m = (market or "IDX").upper().strip()
    return {"status": "success", "market": clean_m, "data": get_market_climate(force=force, market=clean_m)}

@router.get("/api/market-status")
async def api_market_status(market: str = "IDX"):
    clean_m = (market or "IDX").upper().strip()
    status = get_us_market_status() if clean_m == "US" else get_idx_market_status()
    return {"status": "success", "market": clean_m, "data": status}

@router.get("/api/macro")
async def api_macro(force: bool = False):
    """Mengembalikan data harga komoditas global, kurs USD/IDR, dan yield US 10Y dengan korelasi emiten BEI."""
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, get_global_macro_data, force)
    return JSONResponse(content=data)

@router.get("/api/sectors")
async def api_get_sectors(market: str = "IDX"):
    clean_m = (market or "IDX").upper().strip()
    data = calculate_sector_rotation(market=clean_m)
    return {"status": "success", "market": clean_m, "data": data}

_FLOW_RADAR_CACHE = {"IDX": None, "US": None}
_FLOW_RADAR_TIME = {"IDX": None, "US": None}
_FLOW_RADAR_EXPIRY = 300  # 5 menit

@router.get("/api/flow-radar")
async def api_flow_radar(market: str = "IDX"):
    """Mengembalikan radar Top Big Money Inflow & Outflow saham likuid (IDX / US)."""
    global _FLOW_RADAR_CACHE, _FLOW_RADAR_TIME
    clean_m = (market or "IDX").upper().strip()
    now = datetime.now()
    
    cached_data = _FLOW_RADAR_CACHE.get(clean_m)
    cached_time = _FLOW_RADAR_TIME.get(clean_m)
    if cached_time and (now - cached_time).total_seconds() < _FLOW_RADAR_EXPIRY and cached_data:
        return JSONResponse(content=cached_data)

    loop = asyncio.get_event_loop()
    def compute_radar():
        global _FLOW_RADAR_CACHE, _FLOW_RADAR_TIME
        if clean_m == "US":
            from app.engine.universe_us import get_universe_us
            universe = get_universe_us()
        else:
            universe = get_universe()

        tickers = [item["ticker"] for item in universe]
        dfs = batch_fetch_stock_dfs(tickers, batch_size=35)
        
        flow_list = []
        for item in universe:
            df = dfs.get(item["ticker"])
            if df is not None and len(df) >= 30:
                try:
                    flow = calculate_money_flow(df)
                    price = float(df["Close"].iloc[-1])
                    prev_price = float(df["Close"].iloc[-2]) if len(df) > 1 else price
                    chg = round(((price - prev_price) / prev_price) * 100, 2) if prev_price > 0 else 0.0
                    vol_today = float(df["Volume"].iloc[-1])
                    turnover = price * vol_today
                    
                    min_turnover = 10_000_000 if clean_m == "US" else 500_000_000
                    if turnover >= min_turnover:
                        flow_list.append({
                            "symbol": item["ticker"].replace(".JK", "").strip(),
                            "name": item["name"],
                            "sector": item.get("sector", ""),
                            "price": round(price, 2) if clean_m == "US" else int(price),
                            "change_pct": chg,
                            "status": flow["status"],
                            "score": flow["score"],
                            "cmf": flow["cmf_val"],
                            "turnover_bio": round(turnover / 1_000_000_000, 2)
                        })
                except Exception:
                    continue
        
        inflows = sorted([x for x in flow_list if x["status"] == "INFLOW"], key=lambda x: x["score"], reverse=True)[:5]
        outflows = sorted([x for x in flow_list if x["status"] == "OUTFLOW"], key=lambda x: x["score"])[:5]
        
        if not inflows:
            inflows = sorted(flow_list, key=lambda x: x["score"], reverse=True)[:5]
        if not outflows:
            outflows = sorted(flow_list, key=lambda x: x["score"])[:5]

        res = {
            "market": clean_m,
            "top_inflow": inflows,
            "top_outflow": outflows,
            "timestamp": datetime.now().strftime("%H:%M:%S WIB")
        }
        _FLOW_RADAR_CACHE[clean_m] = res
        _FLOW_RADAR_TIME[clean_m] = datetime.now()
        return res

    radar_data = await loop.run_in_executor(None, compute_radar)
    return JSONResponse(content=radar_data)

@router.post("/api/ai/trigger-external-learning")
async def api_trigger_external_learning(market: str = "IDX"):
    """Trigger on-demand eksekusi pembelajaran mandiri eksternal untuk pasar IDX atau US."""
    clean_m = (market or "IDX").upper().strip()
    from app.engine.external_learner import run_nightly_external_learning_idx, run_nightly_external_learning_us
    
    if clean_m == "US":
        result = await run_nightly_external_learning_us()
    else:
        result = await run_nightly_external_learning_idx()
        
    return JSONResponse(content=result)

