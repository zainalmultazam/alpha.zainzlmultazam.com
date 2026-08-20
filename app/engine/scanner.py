import pandas as pd
from typing import Dict, Any, Optional
from app.engine.technical import calculate_indicators, calculate_money_flow
from app.engine.strategy import generate_trade_plan

def scan_stock(ticker_info: Dict[str, str], df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """Memindai satu saham untuk mendeteksi setup swing probabilitas tinggi dengan validasi Multi-Timeframe (Daily + Weekly)."""
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
        
        # Temuan Audit #4: Filter likuiditas rata-rata 20 hari (Turnover MA20 >= Rp 1 Miliar)
        # Menghindari saham gorengan/illiquid yang mendadak dipompa dalam 1 hari
        try:
            turnover_series = df["Close"] * df["Volume"]
            turnover_ma20 = float(turnover_series.rolling(20, min_periods=3).mean().iloc[-1])
            if pd.isna(turnover_ma20) or turnover_ma20 <= 0:
                turnover_ma20 = turnover
        except Exception:
            turnover_ma20 = turnover

        if turnover_ma20 < 1_000_000_000:
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
        rvol = float(last["rvol"]) if pd.notnull(last["rvol"]) else 1.0
        vcp_ratio = float(last["vcp_ratio"]) if pd.notnull(last["vcp_ratio"]) else 1.0
        high_52w = float(last["high_52w"]) if pd.notnull(last["high_52w"]) else price
        atr14 = float(last["atr14"]) if pd.notnull(last["atr14"]) else (price * 0.03)

        # Kalkulasi Big Money Flow & Sponsorship Institusi
        flow_data = calculate_money_flow(df)
        big_money_status = flow_data["status"]  # INFLOW | NEUTRAL | OUTFLOW
        flow_score = flow_data["score"]
        cmf_val = flow_data["cmf_val"]

        # 1. VCP Breakout Setup
        if is_stage2 and vcp_ratio < 0.60 and rvol > 1.2:
            setups.append("VCP Breakout")

        # 2. Pullback EMA 20/50 Retest Setup
        distance_to_ema20 = abs(price - ema20) / price
        if is_stage2 and distance_to_ema20 < 0.025 and price >= float(last["Open"]):
            setups.append("EMA 20 Pullback")

        # 3. Volume Surge / Smart Money Pocket Pivot
        if rvol >= 1.7 and price > float(prev["Close"]):
            setups.append("Volume Surge")

        # 4. Stage 2 Strong Momentum / 52-Week High Breakout
        if is_stage2 and price >= 0.90 * high_52w:
            setups.append("Stage 2 Leader")

        # 1. Hitung Skor Teori Klasik (Buku Baku Minervini)
        classic_score = 50
        if weekly_confirmed:
            classic_score += 15
        if big_money_status == "INFLOW":
            classic_score += 15
        if "VCP Breakout" in setups:
            classic_score += 20
        if "EMA 20 Pullback" in setups:
            classic_score += 15
        if "Volume Surge" in setups:
            classic_score += 15
        if "Stage 2 Leader" in setups:
            classic_score += 10

        # 2. Hitung Skor AI Adaptive (Disesuaikan Data Empiris)
        from app.engine.learner import get_active_learned_weights
        ai_weights = get_active_learned_weights().get("weights", {})
        
        ai_score = ai_weights.get("base_score", 50)
        if weekly_confirmed:
            ai_score += ai_weights.get("weekly_trend", 15)
        if big_money_status == "INFLOW":
            ai_score += ai_weights.get("big_money_inflow", 15)
        if "VCP Breakout" in setups:
            ai_score += ai_weights.get("vcp_breakout", 20)
        if "EMA 20 Pullback" in setups:
            ai_score += ai_weights.get("ema20_pullback", 15)
        if "Volume Surge" in setups:
            ai_score += ai_weights.get("volume_surge", 15)
        if "Stage 2 Leader" in setups:
            ai_score += ai_weights.get("stage2_leader", 10)

        # Wajib memiliki minimal 1 setup teknikal terkonfirmasi dan Skor >= 80
        if not setups or max(classic_score, ai_score) < 80:
            return None

        primary_setup = setups[0]
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
            "turnover_ma20_bio": round(turnover_ma20 / 1_000_000_000, 2),
            "rvol": round(rvol, 2),
            "rsi": round(float(last["rsi14"]), 1) if pd.notnull(last["rsi14"]) else 50.0,
            "weekly_confirmed": weekly_confirmed,
            "primary_setup": primary_setup,
            "setups": setups,
            "score": min(99, ai_score),
            "ai_score": min(99, ai_score),
            "classic_score": min(99, classic_score),
            "big_money_status": big_money_status,
            "flow_score": flow_score,
            "cmf_val": cmf_val,
            "plan": trade_plan
        }
    except Exception as e:
        print(f"Error scanning {ticker_info.get('ticker')}: {e}")
        return None

def run_full_scan() -> list:
    """Melakukan scan cepat seluruh universe saham secara batch."""
    from app.engine.universe import get_universe
    from app.services.market_data import batch_fetch_stock_dfs
    
    universe = get_universe()
    tickers = [item["ticker"] for item in universe]
    dfs = batch_fetch_stock_dfs(tickers, batch_size=35)
    
    results = []
    for item in universe:
        df = dfs.get(item["ticker"])
        res = scan_stock(item, df)
        if res is not None:
            results.append(res)
    results.sort(key=lambda x: x["score"], reverse=True)
    return results

