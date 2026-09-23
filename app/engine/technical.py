import pandas as pd
import numpy as np

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Menghitung indikator teknikal untuk strategi swing trading (Daily + Weekly Multi-Timeframe)."""
    if df is None or len(df) < 50:
        return df

    df = df.copy()

    # Exponential Moving Averages (EMA Daily)
    df["ema20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["ema50"] = df["Close"].ewm(span=50, adjust=False).mean()
    df["ema150"] = df["Close"].ewm(span=150, adjust=False).mean()
    df["ema200"] = df["Close"].ewm(span=200, adjust=False).mean()

    # Average True Range (ATR 14) untuk batas volatilitas & Stop Loss dinamis
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr14"] = tr.rolling(14).mean()

    # Relative Volume (RVOL) = Volume hari ini / Rata-rata volume 20 hari
    df["vol_ma20"] = df["Volume"].rolling(20).mean()
    df["rvol"] = df["Volume"] / df["vol_ma20"].replace(0, np.nan)

    # 52-Week High & Low
    window_52w = min(len(df), 250)
    df["high_52w"] = df["High"].rolling(window=window_52w).max()
    df["low_52w"] = df["Low"].rolling(window=window_52w).min()

    # RSI (14)
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi14"] = 100 - (100 / (1 + rs))

    # Volatility Contraction (VCP Ratio: Rentang harga 5 hari terakhir vs 20 hari)
    range_5d = df["High"].rolling(5).max() - df["Low"].rolling(5).min()
    range_20d = df["High"].rolling(20).max() - df["Low"].rolling(20).min()
    df["vcp_ratio"] = range_5d / range_20d.replace(0, np.nan)

    # Volume Dry-Up (VDU: Volume terendah 5 hari sebelum breakout vs MA20)
    min_vol_5d = df["Volume"].shift(1).rolling(5).min()
    df["vdu_ratio"] = (min_vol_5d / df["vol_ma20"].replace(0, np.nan)).fillna(1.0)

    # Up/Down Volume Ratio 20-Hari (CANSLIM Institutional Accumulation Indicator)
    up_vol = df["Volume"].where(df["Close"] > df["Close"].shift(1), 0)
    down_vol = df["Volume"].where(df["Close"] < df["Close"].shift(1), 0)
    df["ud_ratio_20"] = (up_vol.rolling(20).sum() / down_vol.rolling(20).sum().replace(0, np.nan)).fillna(1.0)

    # Close Location Value (CLV: -1.0 to +1.0 mengukur dominasi buyer saat penutupan)
    hl_range = (df["High"] - df["Low"]).replace(0, np.nan)
    df["clv"] = (((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / hl_range).fillna(0.0)

    # Multi-Timeframe: Weekly Trend Calculation (Resample to Weekly)
    try:
        weekly_close = df["Close"].resample("W-FRI").last().dropna()
        if len(weekly_close) >= 10:
            weekly_ema20 = weekly_close.ewm(span=10, adjust=False).mean()
            last_w_close = float(weekly_close.iloc[-1])
            last_w_ema = float(weekly_ema20.iloc[-1])
            prev_w_ema = float(weekly_ema20.iloc[-2]) if len(weekly_ema20) > 1 else last_w_ema
            
            df["weekly_uptrend"] = bool(last_w_close >= last_w_ema and last_w_ema >= prev_w_ema * 0.995)
            df["weekly_ema20"] = last_w_ema
        else:
            df["weekly_uptrend"] = True
            df["weekly_ema20"] = float(df["ema50"].iloc[-1])
    except Exception:
        df["weekly_uptrend"] = True
        df["weekly_ema20"] = float(df["ema50"].iloc[-1]) if "ema50" in df else 0.0

    return df

def calculate_volume_profile(df: pd.DataFrame, lookback: int = 120, n_bins: int = 24) -> dict:
    """Menghitung Volume Profile (Horizontal Volume), Point of Control (POC), VAH & VAL."""
    if df is None or len(df) < 20:
        return {"poc_price": 0, "vah_price": 0, "val_price": 0, "bins": []}
    
    recent = df.iloc[-lookback:].copy()
    p_min = float(recent["Low"].min())
    p_max = float(recent["High"].max())
    if p_max <= p_min:
        return {"poc_price": p_min, "vah_price": p_max, "val_price": p_min, "bins": []}

    bins = np.linspace(p_min, p_max, n_bins + 1)
    buy_vols = np.zeros(n_bins)
    sell_vols = np.zeros(n_bins)
    total_vols = np.zeros(n_bins)

    for _, row in recent.iterrows():
        r_low, r_high, r_vol = float(row["Low"]), float(row["High"]), float(row["Volume"]) if pd.notnull(row["Volume"]) else 0
        is_buy = float(row["Close"]) >= float(row["Open"])
        
        # Alokasi volume proporsional ke setiap bin yang dilewati rentang lilin
        span_bins = []
        for i in range(n_bins):
            if not (r_high < bins[i] or r_low > bins[i+1]):
                span_bins.append(i)
        
        if span_bins:
            vol_per_bin = r_vol / len(span_bins)
            for b_idx in span_bins:
                total_vols[b_idx] += vol_per_bin
                if is_buy:
                    buy_vols[b_idx] += vol_per_bin
                else:
                    sell_vols[b_idx] += vol_per_bin

    max_bin_idx = int(np.argmax(total_vols))
    poc_price = round(float((bins[max_bin_idx] + bins[max_bin_idx+1]) / 2.0), 1)

    # Hitung 70% Value Area (VAH & VAL)
    total_market_vol = np.sum(total_vols)
    target_va_vol = total_market_vol * 0.70
    cum_vol = 0.0
    val_idx = 0
    vah_idx = n_bins - 1

    # Urutkan bin dari POC keluar
    included_indices = {max_bin_idx}
    cum_vol = total_vols[max_bin_idx]
    up_idx = max_bin_idx + 1
    down_idx = max_bin_idx - 1

    while cum_vol < target_va_vol and (up_idx < n_bins or down_idx >= 0):
        up_vol = total_vols[up_idx] if up_idx < n_bins else -1
        down_vol = total_vols[down_idx] if down_idx >= 0 else -1

        if up_vol >= down_vol and up_idx < n_bins:
            cum_vol += up_vol
            included_indices.add(up_idx)
            up_idx += 1
        elif down_idx >= 0:
            cum_vol += down_vol
            included_indices.add(down_idx)
            down_idx -= 1
        else:
            break

    if included_indices:
        val_idx = min(included_indices)
        vah_idx = max(included_indices)

    vah_price = round(float((bins[vah_idx] + bins[vah_idx+1]) / 2.0), 1)
    val_price = round(float((bins[val_idx] + bins[val_idx+1]) / 2.0), 1)

    profile_bins = []
    max_vol = float(np.max(total_vols)) if np.max(total_vols) > 0 else 1.0
    for i in range(n_bins):
        mid_p = float((bins[i] + bins[i+1]) / 2.0)
        profile_bins.append({
            "price": round(mid_p, 1),
            "vol_total": int(total_vols[i]),
            "vol_buy": int(buy_vols[i]),
            "vol_sell": int(sell_vols[i]),
            "rel_pct": round((total_vols[i] / max_vol) * 100, 1),
            "is_poc": i == max_bin_idx,
            "in_value_area": i in included_indices
        })

    return {
        "poc_price": poc_price,
        "vah_price": vah_price,
        "val_price": val_price,
        "profile": profile_bins
    }

def calculate_anchored_vwap(df: pd.DataFrame, lookback: int = 120) -> list:
    """Menghitung Anchored VWAP dari titik Swing Low terendah dalam periode lookback."""
    if df is None or len(df) < 15:
        return []

    recent = df.iloc[-lookback:].copy()
    min_idx = recent["Low"].idxmin()
    min_loc = recent.index.get_loc(min_idx)
    sub_df = recent.iloc[min_loc:].copy()

    typical_price = (sub_df["High"] + sub_df["Low"] + sub_df["Close"]) / 3.0
    vol = sub_df["Volume"].replace(0, 1)
    
    cum_pv = (typical_price * vol).cumsum()
    cum_v = vol.cumsum()
    avwap_series = cum_pv / cum_v

    result = []
    for idx, val in avwap_series.items():
        time_str = idx.strftime("%Y-%m-%d")
        result.append({
            "time": time_str,
            "value": round(float(val), 2)
        })
    return result

def calculate_pocket_pivots_and_markers(df: pd.DataFrame, lookback: int = 180) -> list:
    """Mendeteksi sinyal Pocket Pivot & Breakout Momentum (On-Candle Signals)."""
    if df is None or len(df) < 20:
        return []

    recent = df.iloc[-lookback:].copy()
    markers = []

    # Down volume 10 hari sebelumnya
    is_down = recent["Close"] < recent["Open"]
    down_vol = recent["Volume"].where(is_down, 0)
    max_10d_down_vol = down_vol.rolling(10).max().shift(1)
    
    vol_ma20 = recent["Volume"].rolling(20).mean()
    high_20d = recent["High"].rolling(20).max().shift(1)
    ema20 = recent["Close"].ewm(span=20, adjust=False).mean()
    ema50 = recent["Close"].ewm(span=50, adjust=False).mean()

    for idx, row in recent.iterrows():
        time_str = idx.strftime("%Y-%m-%d")
        close_val = float(row["Close"])
        open_val = float(row["Open"])
        vol_val = float(row["Volume"]) if pd.notnull(row["Volume"]) else 0
        
        # 1. Breakout Bar (New 20D High + High RVOL)
        h20 = high_20d.get(idx)
        vma = vol_ma20.get(idx)
        if pd.notnull(h20) and pd.notnull(vma) and vma > 0:
            if close_val > float(h20) and vol_val >= float(vma) * 1.5 and close_val > open_val:
                markers.append({
                    "time": time_str,
                    "position": "aboveBar",
                    "color": "#10B981",
                    "shape": "arrowUp",
                    "text": "BO"
                })
                continue

        # 2. Pocket Pivot (Vol > max 10D down vol & Close > Open & Close > EMA)
        max_d_vol = max_10d_down_vol.get(idx)
        e20 = ema20.get(idx)
        e50 = ema50.get(idx)
        if pd.notnull(max_d_vol) and close_val > open_val:
            if vol_val > float(max_d_vol) and vol_val >= (float(vma) if pd.notnull(vma) else 0) * 1.1:
                if (pd.notnull(e20) and close_val >= float(e20) * 0.98) or (pd.notnull(e50) and close_val >= float(e50)):
                    markers.append({
                        "time": time_str,
                        "position": "belowBar",
                        "color": "#3B82F6",
                        "shape": "arrowUp",
                        "text": "PIVOT"
                    })

    return markers

def calculate_money_flow(df: pd.DataFrame, period: int = 20) -> dict:
    """
    Menghitung Chaikin Money Flow (CMF) dan On-Balance Volume (OBV)
    untuk mendeteksi akumulasi dana asing & institusi (Big Money Flow).
    """
    if df is None or len(df) < period:
        return {
            "status": "NEUTRAL",
            "score": 50,
            "cmf_val": 0.0,
            "cmf_series": [],
            "obv_trend": "FLAT"
        }

    df = df.copy()
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    volume = df["Volume"]

    # Money Flow Multiplier = [(Close - Low) - (High - Close)] / (High - Low)
    hl_diff = (high - low).replace(0, np.nan)
    mf_mult = (((close - low) - (high - close)) / hl_diff).fillna(0)
    mf_volume = mf_mult * volume

    # Chaikin Money Flow (20) = 20-period Sum(MF Volume) / 20-period Sum(Volume)
    cmf_20 = mf_volume.rolling(period).sum() / volume.rolling(period).sum().replace(0, np.nan)
    cmf_20 = cmf_20.fillna(0)

    # On-Balance Volume (OBV)
    direction = np.where(close > close.shift(1), 1, np.where(close < close.shift(1), -1, 0))
    obv = (direction * volume).cumsum()
    obv_ema20 = obv.ewm(span=20, adjust=False).mean()

    # Hitung series CMF untuk chart
    cmf_series = []
    recent = df.iloc[-180:]
    for idx, row in recent.iterrows():
        time_str = idx.strftime("%Y-%m-%d")
        val = cmf_20.get(idx, 0.0)
        cmf_series.append({
            "time": time_str,
            "value": round(float(val), 3) if pd.notnull(val) else 0.0
        })

    # Nilai terkini
    last_cmf = float(cmf_20.iloc[-1]) if len(cmf_20) > 0 else 0.0
    last_obv = float(obv.iloc[-1]) if len(obv) > 0 else 0.0
    last_obv_ema = float(obv_ema20.iloc[-1]) if len(obv_ema20) > 0 else 0.0

    # Skor Big Money (0 - 100)
    base_score = 50 + int(last_cmf * 150)
    if last_obv > last_obv_ema:
        base_score += 15
        obv_trend = "UP"
    else:
        base_score -= 15
        obv_trend = "DOWN"

    score = max(5, min(99, base_score))

    if score >= 65 and last_cmf > 0.05:
        status = "INFLOW"
    elif score <= 35 and last_cmf < -0.05:
        status = "OUTFLOW"
    else:
        status = "NEUTRAL"

    return {
        "status": status,
        "score": score,
        "cmf_val": round(last_cmf, 3),
        "cmf_series": cmf_series,
        "obv_trend": obv_trend
    }
