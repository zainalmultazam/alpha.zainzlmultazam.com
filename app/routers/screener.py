import asyncio
import time
import json
import pandas as pd
from typing import Optional
from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from app.engine.universe import get_universe
from app.engine.universe_us import get_universe_us
from app.services.market_data import fetch_stock_df, batch_fetch_stock_dfs, clear_cache, get_market_climate
from app.engine.scanner import scan_stock
from app.engine.technical import (
    calculate_indicators, 
    calculate_volume_profile, 
    calculate_anchored_vwap, 
    calculate_pocket_pivots_and_markers, 
    calculate_money_flow
)
from app.engine.strategy import generate_trade_plan
from app.engine.relative_strength import calculate_rs_line_series, get_stock_rs_rating
from app.engine.tracker import record_signal_snapshot

router = APIRouter(tags=["Screener"])

cached_scan_results = {"IDX": [], "US": []}
last_scan_duration = {"IDX": 0.0, "US": 0.0}

async def execute_market_scan(market: str = "IDX") -> list:
    """Melakukan scan seluruh universe saham secara asinkron dengan batch downloader (IDX / US)."""
    global last_scan_duration, cached_scan_results
    clean_m = (market or "IDX").upper().strip()
    t0 = time.time()
    if clean_m == "US":
        universe = get_universe_us()
        bench_ticker = "^GSPC"
    else:
        universe = get_universe()
        bench_ticker = "^JKSE"

    tickers = [item["ticker"] for item in universe]
    loop = asyncio.get_event_loop()
    
    # Ambil seluruh data saham secara batch multi-threaded
    dfs = await loop.run_in_executor(None, batch_fetch_stock_dfs, tickers, 35)
    
    try:
        df_bench = await loop.run_in_executor(None, fetch_stock_df, bench_ticker)
        if df_bench is not None and not df_bench.empty:
            from app.engine.relative_strength import compute_universe_rs_ratings
            compute_universe_rs_ratings(dfs, df_bench)
    except Exception:
        pass

    results = []
    for item in universe:
        df = dfs.get(item["ticker"])
        res = scan_stock(item, df, market=clean_m)
        if res is not None:
            results.append(res)
            
    results.sort(key=lambda x: x["score"], reverse=True)
    last_scan_duration[clean_m] = round(time.time() - t0, 2)
    
    # Auto-snapshot top 10 momentum signals to tracker for this market
    if results:
        try:
            climate_data = get_market_climate(market=clean_m)
            regime = climate_data.get("regime", "BULLISH") if isinstance(climate_data, dict) else "BULLISH"
            record_signal_snapshot(results[:10], climate=regime, market=clean_m)
        except Exception as e:
            print(f"Error auto-recording tracker snapshot for {clean_m}: {e}")

    return results

@router.get("/api/scan")
async def api_scan(force: bool = False, market: str = "IDX"):
    global cached_scan_results, last_scan_duration
    clean_m = (market or "IDX").upper().strip()
    if clean_m not in cached_scan_results:
        cached_scan_results[clean_m] = []
        last_scan_duration[clean_m] = 0.0

    if not cached_scan_results[clean_m] or force:
        if force:
            clear_cache()
        cached_scan_results[clean_m] = await execute_market_scan(market=clean_m)

    climate = get_market_climate(market=clean_m)
    universe = get_universe_us() if clean_m == "US" else get_universe()
    return {
        "status": "success",
        "market": clean_m,
        "total": len(cached_scan_results[clean_m]),
        "total_universe": len(universe),
        "duration_sec": last_scan_duration.get(clean_m, 0.0),
        "climate": climate,
        "data": cached_scan_results[clean_m]
    }

@router.get("/api/scan-stream")
async def api_scan_stream(force: bool = False, market: str = "IDX"):
    """Server-Sent Events endpoint untuk streaming persentase scan langsung ke frontend (IDX atau US)."""
    clean_m = (market or "IDX").upper().strip()
    async def event_generator():
        global cached_scan_results, last_scan_duration
        t0 = time.time()
        if force:
            clear_cache()
        
        if clean_m == "US":
            universe = get_universe_us()
            bench_ticker = "^GSPC"
            label = "US Wall Street"
        else:
            universe = get_universe()
            bench_ticker = "^JKSE"
            label = "IDX Kompas100"

        total_universe = len(universe)
        
        # Step 1: Inisialisasi
        yield f"data: {json.dumps({'progress': 10, 'stage': f'Menyiapkan {total_universe} watchlist {label}...', 'total': total_universe})}\n\n"
        await asyncio.sleep(0.05)
        
        # Step 2: Batch Download Data Bursa
        yield f"data: {json.dumps({'progress': 30, 'stage': 'Mengunduh data candle & volume bursa paralel...', 'total': total_universe})}\n\n"
        loop = asyncio.get_event_loop()
        tickers = [item["ticker"] for item in universe]
        dfs = await loop.run_in_executor(None, batch_fetch_stock_dfs, tickers, 35)

        try:
            df_bench = await loop.run_in_executor(None, fetch_stock_df, bench_ticker)
            if df_bench is not None and not df_bench.empty:
                from app.engine.relative_strength import compute_universe_rs_ratings
                compute_universe_rs_ratings(dfs, df_bench)
        except Exception:
            pass
        
        # Step 3: Analisis Pola Breakout Raider & Validasi Likuiditas MA20
        yield f"data: {json.dumps({'progress': 70, 'stage': 'Menganalisis Stage 2, VCP, EMA Pullback & Relative Strength...', 'total': total_universe})}\n\n"
        results = []
        for idx, item in enumerate(universe):
            df = dfs.get(item["ticker"])
            res = scan_stock(item, df, market=clean_m)
            if res is not None:
                results.append(res)
                
        results.sort(key=lambda x: x["score"], reverse=True)
        if clean_m not in cached_scan_results:
            cached_scan_results[clean_m] = []
        cached_scan_results[clean_m] = results
        last_scan_duration[clean_m] = round(time.time() - t0, 2)
        climate = get_market_climate(market=clean_m)
        
        # Step 4: Selesai
        yield f"data: {json.dumps({'progress': 100, 'stage': 'Pemindaian selesai!', 'total': len(results), 'total_universe': total_universe, 'duration_sec': last_scan_duration[clean_m], 'climate': climate, 'data': results})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/api/chart/{ticker}")
async def api_chart(ticker: str, market: str = "IDX"):
    clean_m = (market or "IDX").upper().strip()
    clean_ticker = ticker.upper().strip()
    if clean_m == "IDX":
        clean_ticker = clean_ticker.replace(".JK", "").strip()
        full_ticker = f"{clean_ticker}.JK"
        bench_ticker = "^JKSE"
    else:
        full_ticker = clean_ticker.replace(".JK", "").strip()
        bench_ticker = "^GSPC"

    loop = asyncio.get_event_loop()
    df = await loop.run_in_executor(None, fetch_stock_df, full_ticker)
    
    if df is None or df.empty:
        return JSONResponse(status_code=404, content={"error": "Data not found"})
    
    # Hitung Indikator Teknikal: EMA 20, EMA 50, EMA 200 & Volume MA 20
    df_calc = calculate_indicators(df)
    df_calc["EMA20"] = df_calc["Close"].ewm(span=20, adjust=False).mean()
    df_calc["EMA50"] = df_calc["Close"].ewm(span=50, adjust=False).mean()
    df_calc["EMA200"] = df_calc["Close"].ewm(span=200, adjust=False).mean()
    df_calc["VolMA20"] = df_calc["Volume"].rolling(window=20).mean()

    last_row = df_calc.iloc[-1]
    curr_price = float(last_row["Close"])
    curr_atr = float(last_row.get("ATR", curr_price * 0.04))
    trade_plan = generate_trade_plan(curr_price, curr_atr, "Trade Plan", market=clean_m)

    # Hitung Volume Profile, Anchored VWAP, Pocket Pivot Markers, & Money Flow (CMF/OBV)
    vol_profile = calculate_volume_profile(df_calc, lookback=120)
    avwap_series = calculate_anchored_vwap(df_calc, lookback=120)
    markers = calculate_pocket_pivots_and_markers(df_calc, lookback=180)
    flow_data = calculate_money_flow(df_calc)

    # Format untuk TradingView Lightweight Charts
    candles = []
    volumes = []
    ema20_series = []
    ema50_series = []
    ema200_series = []
    vol_ma20_series = []

    for idx, row in df_calc.iterrows():
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

        if pd.notnull(row.get("EMA20")):
            ema20_series.append({"time": time_str, "value": round(float(row["EMA20"]), 2)})
        if pd.notnull(row.get("EMA50")):
            ema50_series.append({"time": time_str, "value": round(float(row["EMA50"]), 2)})
        if pd.notnull(row.get("EMA200")):
            ema200_series.append({"time": time_str, "value": round(float(row["EMA200"]), 2)})
        if pd.notnull(row.get("VolMA20")):
            vol_ma20_series.append({"time": time_str, "value": round(float(row["VolMA20"]), 2)})

    # Hitung RS Line vs Benchmark & RS Rating (Hedge Fund Metric)
    df_bench = await loop.run_in_executor(None, fetch_stock_df, bench_ticker)
    rs_line_series = calculate_rs_line_series(df_calc, df_bench)
    rs_info = get_stock_rs_rating(full_ticker, df_stock=df_calc, df_ihsg=df_bench)
        
    return {
        "ticker": clean_ticker,
        "market": clean_m,
        "currency": "USD" if clean_m == "US" else "IDR",
        "candles": candles[-180:],
        "volumes": volumes[-180:],
        "ema20": ema20_series[-180:],
        "ema50": ema50_series[-180:],
        "ema200": ema200_series[-180:],
        "vol_ma20": vol_ma20_series[-180:],
        "avwap": avwap_series[-180:],
        "cmf": flow_data["cmf_series"][-180:],
        "rs_line": rs_line_series[-180:],
        "rs_rating": rs_info,
        "big_money": {
            "status": flow_data["status"],
            "score": flow_data["score"],
            "cmf_val": flow_data["cmf_val"],
            "obv_trend": flow_data["obv_trend"]
        },
        "markers": markers,
        "volume_profile": vol_profile,
        "trade_plan": trade_plan
    }

@router.get("/api/ai-analysis/{ticker}")
async def api_ai_analysis(ticker: str, market: str = "IDX"):
    """Mengambil diagnosa AI Deep Reasoning lengkap, skor Bull-Trap, & kemiripan pola historis."""
    clean_m = (market or "IDX").upper().strip()
    clean_ticker = ticker.upper().strip()
    if clean_m == "IDX":
        clean_ticker = clean_ticker.replace(".JK", "").strip()
        full_ticker = f"{clean_ticker}.JK"
        bench_ticker = "^JKSE"
    else:
        full_ticker = clean_ticker.replace(".JK", "").strip()
        bench_ticker = "^GSPC"

    loop = asyncio.get_event_loop()
    df = await loop.run_in_executor(None, fetch_stock_df, full_ticker)
    if df is None or df.empty:
        return JSONResponse(status_code=404, content={"error": "Data saham tidak ditemukan"})

    df_calc = calculate_indicators(df)
    flow_data = calculate_money_flow(df_calc)
    df_bench = await loop.run_in_executor(None, fetch_stock_df, bench_ticker)
    rs_info = get_stock_rs_rating(full_ticker, df_stock=df_calc, df_ihsg=df_bench)

    earnings_info = None
    if clean_m == "US":
        try:
            from app.engine.earnings_us import get_us_earnings_info
            earnings_info = get_us_earnings_info(clean_ticker, df=df_calc)
        except Exception:
            earnings_info = None

    from app.engine.ai_analyst import analyze_stock_ai
    ticker_info = {"ticker": clean_ticker, "name": clean_ticker, "sector": "General"}
    
    # Ambil sektor jika ada di universe
    if clean_m == "US":
        from app.engine.universe_us import get_universe_us
        u = get_universe_us()
    else:
        from app.engine.universe import get_universe
        u = get_universe()
    for item in u:
        if item["ticker"].replace(".JK", "") == clean_ticker:
            ticker_info = item
            break

    ai_eval = analyze_stock_ai(
        ticker_info,
        df_calc,
        market=clean_m,
        rs_info=rs_info,
        flow_data=flow_data,
        earnings_info=earnings_info
    )

    return {
        "status": "success",
        "ticker": clean_ticker,
        "name": ticker_info.get("name", clean_ticker),
        "sector": ticker_info.get("sector", "General"),
        "market": clean_m,
        "ai_analysis": ai_eval
    }
