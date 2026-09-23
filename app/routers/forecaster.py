from fastapi import APIRouter, Query
from typing import Optional
from app.engine.forecaster import generate_price_forecast, validate_prediction_against_actual
from app.services.market_data import fetch_stock_df
from app.engine.universe import get_universe
from app.engine.universe_us import get_universe_us
import numpy as np

router = APIRouter(prefix="/api/forecast", tags=["Forecaster"])

@router.get("")
@router.get("/")
async def api_get_forecast(
    ticker: str = Query(..., description="Kode saham / ticker symbol"),
    market: str = Query("IDX", description="IDX atau US"),
    entry_price: Optional[float] = Query(None),
    stop_loss: Optional[float] = Query(None),
    tp1: Optional[float] = Query(None),
    tp2: Optional[float] = Query(None),
    pts_score: Optional[float] = Query(None),
    setup_name: Optional[str] = Query(None),
    volume_ratio: Optional[float] = Query(None),
    market_climate: Optional[str] = Query(None)
):
    clean_ticker = (ticker or "").upper().strip()
    clean_market = (market or "IDX").upper().strip()
    
    # 1. Cari Sektor & Peringkat Sektor Emiten
    universe = get_universe_us() if clean_market == "US" else get_universe()
    sec_name = "Technology" if clean_market == "US" else "Finance"
    for item in universe:
        raw_t = item.get("ticker", "").replace(".JK", "").upper()
        if raw_t == clean_ticker:
            sec_name = item.get("sector", sec_name)
            break

    # Estimasi Sector Rank berdasarkan sektor populer (atau default 3 jika leading)
    leading_sectors = ["Finance", "Energy", "Basic Materials", "Industrial", "Technology", "Semiconductors"]
    sec_rank = 2 if sec_name in leading_sectors[:3] else (4 if sec_name in leading_sectors else 6)

    # 2. Ambil data teknikal & historis
    daily_atr = None
    entry_target = float(entry_price) if entry_price and entry_price > 0 else None
    live_price = entry_target or (1000.0 if clean_market == "IDX" else 100.0)
    today_change_pct = 0.0
    df = None
    
    try:
        sym = f"{clean_ticker}.JK" if clean_market == "IDX" and not clean_ticker.endswith(".JK") else clean_ticker
        df = fetch_stock_df(sym)
        if df is not None and not df.empty and len(df) >= 14:
            live_price = float(df['Close'].iloc[-1])
            prev_close = float(df['Close'].iloc[-2]) if len(df) > 1 else live_price
            today_change_pct = round(((live_price - prev_close) / prev_close) * 100, 2) if prev_close > 0 else 0.0
            
            # Hitung ATR 14
            high = df['High']
            low = df['Low']
            close = df['Close'].shift(1)
            tr = np.maximum(high - low, np.maximum(abs(high - close), abs(low - close)))
            daily_atr = float(tr.rolling(14).mean().iloc[-1])
    except Exception as e:
        print(f"Error getting historical data for {clean_ticker}: {e}")

    if not entry_target or entry_target <= 0:
        entry_target = live_price

    sl = stop_loss if stop_loss and stop_loss > 0 else round(entry_target * 0.95, 2)
    t1 = tp1 if tp1 and tp1 > 0 else round(entry_target * 1.08, 2)
    t2 = tp2 if tp2 and tp2 > 0 else round(entry_target * 1.15, 2)
    pts = pts_score if pts_score and pts_score > 0 else 88.5
    s_name = setup_name or "VCP Breakout"
    rvol = volume_ratio or 1.5
    climate = market_climate or "BULLISH"

    # 3. Jalankan Enriched Forecaster Engine
    forecast_data = generate_price_forecast(
        ticker=clean_ticker,
        market=clean_market,
        entry_price=entry_target,
        stop_loss=sl,
        tp1=t1,
        tp2=t2,
        pts_score=pts,
        setup_name=s_name,
        volume_ratio=rvol,
        market_climate=climate,
        atr=daily_atr,
        historical_df=df,
        sector_name=sec_name,
        sector_rank=sec_rank
    )

    forecast_data["live_price"] = live_price
    forecast_data["current_price"] = live_price
    forecast_data["entry_price"] = entry_target
    forecast_data["today_change_pct"] = today_change_pct
    forecast_data["gain_vs_entry_pct"] = round(((live_price - entry_target) / entry_target) * 100, 2) if entry_target > 0 else 0.0

    return {
        "status": "success",
        "market": clean_market,
        "ticker": clean_ticker,
        "forecast": forecast_data
    }
