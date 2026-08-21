import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
import time

_RS_CACHE = {
    'timestamp': 0,
    'ratings': {},
    'ttl_seconds': 3600 # 1 jam cache
}

def calculate_rs_score(df_stock: pd.DataFrame, df_ihsg: pd.DataFrame) -> float:
    """
    Menghitung Relative Strength berbobot 4 kuartal (William O'Neil / IBD Standard):
    RS Score = 40% (3-Bulan) + 20% (6-Bulan) + 20% (9-Bulan) + 20% (12-Bulan)
    """
    try:
        if df_stock is None or df_ihsg is None or len(df_stock) < 30 or len(df_ihsg) < 30:
            return 50.0

        close_stock = df_stock['Close']
        close_ihsg = df_ihsg['Close']

        # Hitung return periode saham
        r_stock_3m = (close_stock.iloc[-1] - close_stock.iloc[max(-63, -len(close_stock))]) / close_stock.iloc[max(-63, -len(close_stock))]
        r_stock_6m = (close_stock.iloc[-1] - close_stock.iloc[max(-126, -len(close_stock))]) / close_stock.iloc[max(-126, -len(close_stock))]
        r_stock_9m = (close_stock.iloc[-1] - close_stock.iloc[max(-189, -len(close_stock))]) / close_stock.iloc[max(-189, -len(close_stock))]
        r_stock_12m = (close_stock.iloc[-1] - close_stock.iloc[max(-252, -len(close_stock))]) / close_stock.iloc[max(-252, -len(close_stock))]

        # Hitung return periode IHSG
        r_ihsg_3m = (close_ihsg.iloc[-1] - close_ihsg.iloc[max(-63, -len(close_ihsg))]) / close_ihsg.iloc[max(-63, -len(close_ihsg))]
        r_ihsg_6m = (close_ihsg.iloc[-1] - close_ihsg.iloc[max(-126, -len(close_ihsg))]) / close_ihsg.iloc[max(-126, -len(close_ihsg))]
        r_ihsg_9m = (close_ihsg.iloc[-1] - close_ihsg.iloc[max(-189, -len(close_ihsg))]) / close_ihsg.iloc[max(-189, -len(close_ihsg))]
        r_ihsg_12m = (close_ihsg.iloc[-1] - close_ihsg.iloc[max(-252, -len(close_ihsg))]) / close_ihsg.iloc[max(-252, -len(close_ihsg))]

        # Excess Return vs IHSG
        diff_3m = r_stock_3m - r_ihsg_3m
        diff_6m = r_stock_6m - r_ihsg_6m
        diff_9m = r_stock_9m - r_ihsg_9m
        diff_12m = r_stock_12m - r_ihsg_12m

        weighted_score = (0.4 * diff_3m) + (0.2 * diff_6m) + (0.2 * diff_9m) + (0.2 * diff_12m)
        return float(weighted_score)
    except Exception:
        return 50.0

def compute_universe_rs_ratings(universe_dfs: Dict[str, pd.DataFrame], df_ihsg: pd.DataFrame) -> Dict[str, int]:
    """
    Menghitung dan memetakan skor RS ke dalam persentil 1 s.d 99 di seluruh saham universe.
    """
    raw_scores = {}
    for ticker, df in universe_dfs.items():
        if df is not None and not df.empty:
            raw_scores[ticker] = calculate_rs_score(df, df_ihsg)

    if not raw_scores:
        return {}

    # Urutkan berdasarkan skor terendah ke tertinggi
    sorted_items = sorted(raw_scores.items(), key=lambda x: x[1])
    n = len(sorted_items)

    ratings = {}
    for rank, (ticker, _) in enumerate(sorted_items):
        # Persentil 1 sampai 99
        percentile = int(round((rank / max(1, n - 1)) * 98)) + 1
        ratings[ticker] = min(99, max(1, percentile))

    # Simpan ke cache
    _RS_CACHE['timestamp'] = time.time()
    _RS_CACHE['ratings'] = ratings
    return ratings

def get_stock_rs_rating(ticker: str, df_stock: Optional[pd.DataFrame] = None, df_ihsg: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """
    Mengambil atau mengkalkulasi RS Rating untuk satu saham.
    """
    cached = _RS_CACHE['ratings'].get(ticker)
    if cached is not None and (time.time() - _RS_CACHE['timestamp'] < _RS_CACHE['ttl_seconds']):
        rating = cached
    else:
        if df_stock is not None and df_ihsg is not None:
            raw = calculate_rs_score(df_stock, df_ihsg)
            # Map raw excess return to approx percentile
            approx_percentile = int(np.clip(50 + (raw * 100), 1, 99))
            rating = approx_percentile
        else:
            rating = 75 # Default solid rating

    if rating >= 90:
        tier = "ELITE_LEADER"
        label = "Super Leader (Top 10%)"
        color = "purple"
    elif rating >= 80:
        tier = "STRONG_OUTPERFORMER"
        label = "Strong Outperformer"
        color = "blue"
    elif rating >= 50:
        tier = "MARKET_PERFORMER"
        label = "Market Performer"
        color = "slate"
    else:
        tier = "LAGGARD"
        label = "Underperformer"
        color = "rose"

    return {
        "rating": rating,
        "tier": tier,
        "label": label,
        "color": color
    }

def calculate_rs_line_series(df_stock: pd.DataFrame, df_ihsg: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Menghasilkan data time series garis RS Line (Rasio Harga Saham / IHSG dinormalisasi ke 100).
    """
    try:
        if df_stock is None or df_ihsg is None or df_stock.empty or df_ihsg.empty:
            return []

        # Samakan timezone jika ada
        s_close = df_stock['Close'].copy()
        i_close = df_ihsg['Close'].copy()
        
        if s_close.index.tz is not None and i_close.index.tz is None:
            i_close.index = i_close.index.tz_localize(s_close.index.tz)
        elif i_close.index.tz is not None and s_close.index.tz is None:
            s_close.index = s_close.index.tz_localize(i_close.index.tz)

        aligned = pd.DataFrame({'stock': s_close, 'ihsg': i_close}).dropna()
        if aligned.empty or len(aligned) < 5:
            return []

        rs_ratio = aligned['stock'] / aligned['ihsg']
        # Normalisasi rasio awal menjadi basis 100
        base_val = rs_ratio.iloc[0]
        if base_val <= 0:
            return []

        rs_normalized = (rs_ratio / base_val) * 100.0

        series = []
        for dt, val in rs_normalized.items():
            dt_str = dt.strftime('%Y-%m-%d')
            series.append({'time': dt_str, 'value': round(float(val), 2)})

        return series
    except Exception:
        return []
