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
