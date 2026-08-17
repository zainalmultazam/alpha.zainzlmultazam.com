import yfinance as yf
import pandas as pd
from typing import Dict, Optional
from datetime import datetime

_CACHE: Dict[str, Dict] = {}
_CACHE_EXPIRY_MINUTES = 30

def fetch_stock_df(ticker: str) -> Optional[pd.DataFrame]:
    """Mengambil data historis saham IDX dari Yahoo Finance dengan sistem cache cerdas."""
    now = datetime.now()
    if ticker in _CACHE:
        cached = _CACHE[ticker]
        if (now - cached["timestamp"]).total_seconds() < (_CACHE_EXPIRY_MINUTES * 60):
            return cached["data"]

    try:
        t = yf.Ticker(ticker)
        df = t.history(period="1y", interval="1d")
        if df is not None and not df.empty:
            _CACHE[ticker] = {"data": df, "timestamp": now}
            return df
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
    
    return None

def clear_cache():
    """Mengosongkan cache memory."""
    global _CACHE
    _CACHE = {}
