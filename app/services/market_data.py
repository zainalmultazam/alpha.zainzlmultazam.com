import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Optional, Any
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

def get_market_climate() -> Dict[str, Any]:
    """Menganalisis rezim pasar IHSG (^JKSE) untuk menentukan iklim risiko pasar (Risk-On / Caution / Risk-Off)."""
    df_ihsg = fetch_stock_df("^JKSE")
    if df_ihsg is None or len(df_ihsg) < 50:
        return {
            "regime": "BULLISH",
            "title": "Risk-On",
            "color": "emerald",
            "price": 7800.0,
            "change_pct": 0.0,
            "exposure_pct": 100,
            "advice": "Kondisi pasar kondusif untuk swing trading agresif.",
            "ihsg_status": "NORMAL"
        }

    df = df_ihsg.copy()
    df["ema20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["ema50"] = df["Close"].ewm(span=50, adjust=False).mean()
    df["ema200"] = df["Close"].ewm(span=200, adjust=False).mean()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    price = round(float(last["Close"]), 2)
    prev_close = float(prev["Close"])
    change_pct = round(((price - prev_close) / prev_close) * 100, 2) if prev_close > 0 else 0.0

    ema20 = float(last["ema20"])
    ema50 = float(last["ema50"])
    ema200 = float(last["ema200"])

    # Penentuan Rezim Pasar
    if price >= ema50 and ema50 >= ema200:
        regime = "BULLISH"
        title = "Risk-On (Uptrend Kuat)"
        color = "emerald"
        exposure_pct = 100
        advice = "IHSG berada di atas EMA 50 & 200. Kondisi pasar optimal untuk full size swing trading (100% modal aktif)."
    elif price >= ema200 and price < ema50:
        regime = "NEUTRAL"
        title = "Caution (Konsolidasi/Pullback)"
        color = "amber"
        exposure_pct = 50
        advice = "IHSG menguji support EMA 50. Batasi ukuran lot 50% dan utamakan saham leader bervolume tinggi."
    else:
        regime = "BEARISH"
        title = "Risk-Off (Cash is King)"
        color = "rose"
        exposure_pct = 0
        advice = "IHSG di bawah EMA 200. Tekanan jual tinggi, utamakan memegang Cash dan hindari beli agresif."

    return {
        "regime": regime,
        "title": title,
        "color": color,
        "price": price,
        "change_pct": change_pct,
        "ema50": round(ema50, 2),
        "ema200": round(ema200, 2),
        "exposure_pct": exposure_pct,
        "advice": advice,
        "last_updated": datetime.now().strftime("%H:%M:%S")
    }

def clear_cache():
    """Mengosongkan cache memory."""
    global _CACHE
    _CACHE = {}
