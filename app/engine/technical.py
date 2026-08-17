import pandas as pd
import numpy as np

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Menghitung indikator teknikal untuk strategi swing trading."""
    if df is None or len(df) < 50:
        return df

    df = df.copy()

    # Exponential Moving Averages (EMA)
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

    return df
