import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from app.engine.universe import get_universe
from app.engine.universe_us import get_universe_us
from app.services.market_data import fetch_stock_df, batch_fetch_stock_dfs

# 10 Sektor Resmi Klasifikasi Indeks Kompas100 / BEI & US
SECTOR_NAMES = [
    "Finance",
    "Industrial",
    "Energy",
    "Materials",
    "Basic Materials",
    "Consumer Non-Cyclicals",
    "Consumer Non-Cyclical",
    "Consumer Cyclicals",
    "Consumer Cyclical",
    "Healthcare",
    "Infrastructure",
    "Technology",
    "Property",
    "Semiconductors",
    "Software - Infrastructure",
    "Software - Application",
    "Internet Retail",
    "Cybersecurity",
    "Financial Services",
    "Aerospace & Defense"
]

_SECTOR_ROTATION_CACHE = {"IDX": None, "US": None}
_SECTOR_ROTATION_CACHE_TIME = {"IDX": None, "US": None}

def calculate_sector_rotation(force: bool = False, market: str = "IDX") -> Dict[str, Any]:
    """
    Menghitung agregasi momentum, perputaran dana (turnover), dan Chaikin Money Flow
    untuk sektor saham (BEI / Wall Street).
    """
    global _SECTOR_ROTATION_CACHE, _SECTOR_ROTATION_CACHE_TIME
    clean_m = (market or "IDX").upper().strip()
    now = datetime.now()
    
    # Cache selama 10 menit
    cached = _SECTOR_ROTATION_CACHE.get(clean_m)
    cached_time = _SECTOR_ROTATION_CACHE_TIME.get(clean_m)
    if not force and cached and cached_time:
        if (now - cached_time).total_seconds() < 600:
            return cached

    universe = get_universe_us() if clean_m == "US" else get_universe()
    tickers = [s["ticker"] for s in universe]
    dfs = batch_fetch_stock_dfs(tickers, batch_size=35)

    sector_stocks: Dict[str, List[Dict[str, Any]]] = {}
    for item in universe:
        sec = item.get("sector", "Technology" if clean_m == "US" else "Industrial")
        if sec not in sector_stocks:
            sector_stocks[sec] = []
        
        turnover_scale = 1_000_000_000 if clean_m == "IDX" else 1_000_000
        df = dfs.get(item["ticker"])
        if df is not None and len(df) >= 10:
            last = df.iloc[-1]
            prev = df.iloc[-2]
            p5 = df.iloc[-5] if len(df) >= 5 else prev

            price = float(last["Close"]) if pd.notnull(last["Close"]) else 0.0
            vol = float(last["Volume"]) if pd.notnull(last["Volume"]) else 0.0
            turnover_bio = round((price * vol) / turnover_scale, 2) if price > 0 else 0.0
            
            # 5-day change
            p5_close = float(p5["Close"]) if pd.notnull(p5["Close"]) else 0.0
            chg_5d = round(((price - p5_close) / p5_close) * 100, 2) if p5_close > 0 else 0.0
            
            # 1-day change
            prev_close = float(prev["Close"]) if pd.notnull(prev["Close"]) else 0.0
            chg_1d = round(((price - prev_close) / prev_close) * 100, 2) if prev_close > 0 else 0.0

            # CMF approx
            high = float(last["High"]) if pd.notnull(last["High"]) else price
            low = float(last["Low"]) if pd.notnull(last["Low"]) else price
            close = float(last["Close"]) if pd.notnull(last["Close"]) else price
            mf_multiplier = ((close - low) - (high - close)) / (high - low) if (high - low) > 0 else 0
            
            clean_sym = item["ticker"].replace(".JK", "") if clean_m == "IDX" else item["ticker"].strip()
            sector_stocks[sec].append({
                "ticker": clean_sym,
                "name": item["name"],
                "price": price,
                "chg_1d": chg_1d if not (pd.isna(chg_1d) or np.isnan(chg_1d)) else 0.0,
                "chg_5d": chg_5d if not (pd.isna(chg_5d) or np.isnan(chg_5d)) else 0.0,
                "turnover_bio": turnover_bio if not (pd.isna(turnover_bio) or np.isnan(turnover_bio)) else 0.0,
                "mf_val": (mf_multiplier * turnover_bio) if not pd.isna(mf_multiplier * turnover_bio) else 0.0
            })

    # Agregasi per sektor
    sectors_data = []
    for sec_name, stocks in sector_stocks.items():
        if not stocks:
            continue
        
        total_turnover = sum(s["turnover_bio"] for s in stocks)
        avg_chg_1d = round(sum(s["chg_1d"] for s in stocks) / len(stocks), 2)
        avg_chg_5d = round(sum(s["chg_5d"] for s in stocks) / len(stocks), 2)
        total_mf = sum(s["mf_val"] for s in stocks)

        # Status Arus Dana Sektor
        if total_mf > 5.0 and avg_chg_1d > 0.3:
            flow_status = "INFLOW"
            flow_color = "emerald"
        elif total_mf < -5.0 or avg_chg_1d < -0.8:
            flow_status = "OUTFLOW"
            flow_color = "rose"
        else:
            flow_status = "NEUTRAL"
            flow_color = "slate"

        # Momentum Score (0 - 100)
        calc_mom = 50.0 + (float(avg_chg_5d or 0) * 4) + (float(avg_chg_1d or 0) * 3) + (float(total_mf or 0) * 0.5)
        if pd.isna(calc_mom) or np.isnan(calc_mom):
            calc_mom = 50.0
        momentum_score = min(99, max(10, int(calc_mom)))

        top_stocks = sorted(stocks, key=lambda x: x["chg_1d"], reverse=True)[:3]
        top_leaders = [s["ticker"] for s in top_stocks]

        sectors_data.append({
            "sector": sec_name,
            "stock_count": len(stocks),
            "total_turnover_bio": round(total_turnover, 1),
            "avg_chg_1d": avg_chg_1d,
            "avg_chg_5d": avg_chg_5d,
            "flow_status": flow_status,
            "flow_color": flow_color,
            "momentum_score": momentum_score,
            "top_leaders": top_leaders
        })

    # Urutkan berdasarkan Momentum Score tertinggi
    sectors_data.sort(key=lambda x: (x["flow_status"] == "INFLOW", x["momentum_score"]), reverse=True)

    top_inflow_sectors = [s["sector"] for s in sectors_data if s["flow_status"] == "INFLOW"][:3]
    top_outflow_sectors = [s["sector"] for s in sectors_data if s["flow_status"] == "OUTFLOW"][:3]

    result = {
        "updated_at": now.strftime("%Y-%m-%d %H:%M WIB"),
        "top_inflow_sectors": top_inflow_sectors,
        "top_outflow_sectors": top_outflow_sectors,
        "sectors": sectors_data
    }

    _SECTOR_ROTATION_CACHE[clean_m] = result
    _SECTOR_ROTATION_CACHE_TIME[clean_m] = now
    return result

def get_top_inflow_sectors(market: str = "IDX") -> List[str]:
    """Mengembalikan daftar nama sektor yang sedang mengalami Net Inflow."""
    data = calculate_sector_rotation(market=market)
    return data.get("top_inflow_sectors", [])
