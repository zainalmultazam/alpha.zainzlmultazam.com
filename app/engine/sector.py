import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from app.engine.universe import get_universe
from app.services.market_data import fetch_stock_df, batch_fetch_stock_dfs

# 10 Sektor Resmi Klasifikasi Indeks Kompas100 / BEI
SECTOR_NAMES = [
    "Finance",
    "Industrial",
    "Energy",
    "Materials",
    "Consumer Non-Cyclical",
    "Consumer Cyclical",
    "Healthcare",
    "Infrastructure",
    "Technology",
    "Property"
]

_SECTOR_ROTATION_CACHE = None
_SECTOR_ROTATION_CACHE_TIME = None

def calculate_sector_rotation(force: bool = False) -> Dict[str, Any]:
    """
    Menghitung agregasi momentum, perputaran dana (turnover), dan Chaikin Money Flow
    untuk 10 sektor BEI dari data 101 saham Kompas100.
    """
    global _SECTOR_ROTATION_CACHE, _SECTOR_ROTATION_CACHE_TIME
    now = datetime.now()
    
    # Cache selama 10 menit
    if not force and _SECTOR_ROTATION_CACHE and _SECTOR_ROTATION_CACHE_TIME:
        if (now - _SECTOR_ROTATION_CACHE_TIME).total_seconds() < 600:
            return _SECTOR_ROTATION_CACHE

    universe = get_universe()
    tickers = [s["ticker"] for s in universe]
    dfs = batch_fetch_stock_dfs(tickers, batch_size=35)

    sector_stocks: Dict[str, List[Dict[str, Any]]] = {sec: [] for sec in SECTOR_NAMES}
    for item in universe:
        sec = item.get("sector", "Industrial")
        if sec not in sector_stocks:
            sector_stocks[sec] = []
        
        df = dfs.get(item["ticker"])
        if df is not None and len(df) >= 10:
            last = df.iloc[-1]
            prev = df.iloc[-2]
            p5 = df.iloc[-5] if len(df) >= 5 else prev

            price = float(last["Close"])
            vol = float(last["Volume"]) if pd.notnull(last["Volume"]) else 0
            turnover_bio = round((price * vol) / 1_000_000_000, 2)
            
            # 5-day change
            p5_close = float(p5["Close"])
            chg_5d = round(((price - p5_close) / p5_close) * 100, 2) if p5_close > 0 else 0.0
            
            # 1-day change
            prev_close = float(prev["Close"])
            chg_1d = round(((price - prev_close) / prev_close) * 100, 2) if prev_close > 0 else 0.0

            # CMF approx
            high = float(last["High"])
            low = float(last["Low"])
            close = float(last["Close"])
            mf_multiplier = ((close - low) - (high - close)) / (high - low) if (high - low) > 0 else 0
            
            sector_stocks[sec].append({
                "ticker": item["ticker"].replace(".JK", ""),
                "name": item["name"],
                "price": price,
                "chg_1d": chg_1d,
                "chg_5d": chg_5d,
                "turnover_bio": turnover_bio,
                "mf_val": mf_multiplier * turnover_bio
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
        momentum_score = min(99, max(10, int(50 + (avg_chg_5d * 4) + (avg_chg_1d * 3) + (total_mf * 0.5))))

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

    _SECTOR_ROTATION_CACHE = result
    _SECTOR_ROTATION_CACHE_TIME = now
    return result

def get_top_inflow_sectors() -> List[str]:
    """Mengembalikan daftar nama sektor yang sedang mengalami Net Inflow."""
    data = calculate_sector_rotation()
    return data.get("top_inflow_sectors", [])
