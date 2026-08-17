import pandas as pd
from typing import Dict, Any, Optional
from app.engine.technical import calculate_indicators
from app.engine.strategy import generate_trade_plan

def scan_stock(ticker_info: Dict[str, str], df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """Memindai satu saham untuk mendeteksi setup swing probabilitas tinggi."""
    if df is None or len(df) < 50:
        return None

    try:
        df = calculate_indicators(df)
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        price = float(last["Close"])
        if price < 100 or pd.isnull(price):  # Abaikan saham di bawah Rp 100 atau invalid
            return None

        volume = float(last["Volume"]) if pd.notnull(last["Volume"]) else 0
        turnover = price * volume
        
        # Filter likuiditas minimum (Rp 1 Miliar turnover per hari)
        if turnover < 1_000_000_000:
            return None

        # Trend Filter (Stage 2 Uptrend Minervini)
        ema50 = float(last["ema50"]) if pd.notnull(last["ema50"]) else price
        ema20 = float(last["ema20"]) if pd.notnull(last["ema20"]) else price
        ema200 = float(last["ema200"]) if pd.notnull(last["ema200"]) else 0

        is_stage2 = (
            price > ema50 and 
            ema20 > ema50 and
            (ema200 == 0 or price > ema200)
        )

        # Deteksi Setup Khusus
        setups = []
        confidence_score = 50

        rvol = float(last["rvol"]) if pd.notnull(last["rvol"]) else 1.0
        vcp_ratio = float(last["vcp_ratio"]) if pd.notnull(last["vcp_ratio"]) else 1.0
        high_52w = float(last["high_52w"]) if pd.notnull(last["high_52w"]) else price
        atr14 = float(last["atr14"]) if pd.notnull(last["atr14"]) else (price * 0.03)

        # 1. VCP Breakout Setup
        if is_stage2 and vcp_ratio < 0.60 and rvol > 1.2:
            setups.append("VCP Breakout")
            confidence_score += 25

        # 2. Pullback EMA 20/50 Retest Setup
        distance_to_ema20 = abs(price - ema20) / price
        if is_stage2 and distance_to_ema20 < 0.025 and price >= float(last["Open"]):
            setups.append("EMA 20 Pullback")
            confidence_score += 20

        # 3. Volume Surge / Smart Money Pocket Pivot
        if rvol >= 1.7 and price > float(prev["Close"]):
            setups.append("Volume Surge")
            confidence_score += 15

        # 4. Stage 2 Strong Momentum
        if is_stage2 and price >= 0.90 * high_52w:
            setups.append("Stage 2 Leader")
            confidence_score += 10

        if not setups and not is_stage2:
            return None

        primary_setup = setups[0] if setups else "Stage 2 Trend"
        trade_plan = generate_trade_plan(price, atr14, primary_setup)
        
        change_pct = round(((price - float(prev["Close"])) / float(prev["Close"])) * 100, 2) if float(prev["Close"]) > 0 else 0.0

        return {
            "ticker": ticker_info["ticker"],
            "symbol": ticker_info["ticker"].replace(".JK", ""),
            "name": ticker_info["name"],
            "sector": ticker_info["sector"],
            "price": price,
            "change_pct": change_pct,
            "volume": int(volume),
            "turnover_bio": round(turnover / 1_000_000_000, 2),
            "rvol": round(rvol, 2),
            "rsi": round(float(last["rsi14"]), 1) if pd.notnull(last["rsi14"]) else 50.0,
            "primary_setup": primary_setup,
            "setups": setups,
            "score": min(98, confidence_score),
            "plan": trade_plan
        }
    except Exception as e:
        print(f"Error scanning {ticker_info.get('ticker')}: {e}")
        return None
