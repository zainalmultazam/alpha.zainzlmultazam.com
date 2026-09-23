import pandas as pd
from typing import Dict, Any, Optional
from app.engine.technical import calculate_indicators, calculate_money_flow
from app.engine.strategy import generate_trade_plan

def scan_stock(ticker_info: Dict[str, str], df: pd.DataFrame, market: str = "IDX") -> Optional[Dict[str, Any]]:
    """Memindai satu saham untuk mendeteksi setup swing probabilitas tinggi dengan validasi Multi-Timeframe (Daily + Weekly)."""
    clean_m = (market or "IDX").upper().strip()
    if df is None or len(df) < 50:
        return None

    try:
        df = calculate_indicators(df)
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        price = float(last["Close"])
        min_price = 2.0 if clean_m == "US" else 100.0
        if price < min_price or pd.isnull(price):
            return None

        volume = float(last["Volume"]) if pd.notnull(last["Volume"]) else 0
        turnover = price * volume
        
        # Filter likuiditas rata-rata 20 hari
        # US: Turnover MA20 >= $5 Juta USD | IDX: Turnover MA20 >= Rp 1 Miliar IDR
        min_turnover_threshold = 5_000_000 if clean_m == "US" else 1_000_000_000
        try:
            turnover_series = df["Close"] * df["Volume"]
            turnover_ma20 = float(turnover_series.rolling(20, min_periods=3).mean().iloc[-1])
            if pd.isna(turnover_ma20) or turnover_ma20 <= 0:
                turnover_ma20 = turnover
        except Exception:
            turnover_ma20 = turnover

        if turnover_ma20 < min_turnover_threshold:
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

        # Multi-Timeframe Weekly Trend Confirmation
        weekly_confirmed = bool(last.get("weekly_uptrend", True))

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

        # 2. Hitung Skor AI Adaptive (Disesuaikan Rezim Pasar, Rotasi Sektor & Relative Strength)
        from app.services.market_data import get_market_climate
        from app.engine.learner import get_active_learned_weights
        from app.engine.sector import get_top_inflow_sectors
        from app.engine.relative_strength import get_stock_rs_rating

        climate_info = get_market_climate(market=clean_m)
        current_regime = climate_info.get("regime", "BULLISH")
        ai_weights = get_active_learned_weights(current_regime).get("weights", {})
        top_sectors = get_top_inflow_sectors(market=clean_m)
        
        is_sector_leader = ticker_info.get("sector") in top_sectors
        rs_info = get_stock_rs_rating(ticker_info["ticker"], df_stock=df)

        ai_score = ai_weights.get("base_score", 50)
        if weekly_confirmed:
            ai_score += ai_weights.get("weekly_trend", 15)
        if big_money_status == "INFLOW":
            ai_score += ai_weights.get("big_money_inflow", 15)
        if is_sector_leader:
            ai_score += ai_weights.get("sector_inflow_bonus", 5)
        
        # Relative Strength Bonus/Penalty (William O'Neil Institutional Standard)
        if rs_info["rating"] >= 85:
            ai_score += 8  # Elite Leader Bonus
        elif rs_info["rating"] >= 80:
            ai_score += 4  # Strong Outperformer Bonus
        elif rs_info["rating"] < 50:
            ai_score -= 8  # Laggard Penalty

        if "VCP Breakout" in setups:
            ai_score += ai_weights.get("vcp_breakout", 20)
        if "EMA 20 Pullback" in setups:
            ai_score += ai_weights.get("ema20_pullback", 15)
        if "Volume Surge" in setups:
            ai_score += ai_weights.get("volume_surge", 15)
        if "Stage 2 Leader" in setups:
            ai_score += ai_weights.get("stage2_leader", 15)

        # 3. US Earnings Risk Shield (Hedge Fund Blackout & PEAD Catalyst)
        earnings_info = None
        if clean_m == "US":
            try:
                from app.engine.earnings_us import get_us_earnings_info
                earnings_info = get_us_earnings_info(ticker_info["ticker"], df=df)
                if earnings_info:
                    ai_score += earnings_info.get("risk_penalty", 0)
            except Exception:
                earnings_info = None

        # 4. Deep AI Predictive Reasoning & Anti-Trap Detector
        from app.engine.ai_analyst import analyze_stock_ai
        ai_eval = analyze_stock_ai(
            ticker_info,
            df,
            market=clean_m,
            rs_info=rs_info,
            flow_data=flow_data,
            earnings_info=earnings_info
        )

        # =========================================================================
        # PTS HYBRID CONFLUENCE SCORE (Minervini SEPA 45% + AI Deep Reasoning 55%)
        # =========================================================================
        trap_score = ai_eval.get("trap_score", 0) if ai_eval else 0
        sepa_passed = ai_eval.get("sepa_passed_count", 4) if ai_eval else 4

        # Confluence Formula: Menggabungkan presisi teori klasik dengan sentimen & order-flow AI
        raw_confluence = (classic_score * 0.45) + (ai_score * 0.55) - (trap_score * 0.35)
        if trap_score >= 45 or sepa_passed < 3:
            raw_confluence = min(68.0, raw_confluence)
        
        final_pts_score = min(99, max(10, int(round(raw_confluence))))

        # =========================================================================
        # MARKET CLIMATE SENSITIVITY & CASH PRESERVATION FILTER (Hedge-Fund Mode)
        # =========================================================================
        # 1. Tentukan batas minimal skor berdasarkan rezim iklim pasar:
        #    - BULLISH: Min Skor 82, Min RS 60 (Pasar sehat & kondusif)
        #    - CHOPPY / NEUTRAL: Min Skor 88, Min RS 75 (Hanya Market Leader terpilih)
        #    - BEARISH / DEFENSIVE: Min Skor 92, Min RS 85 (Proteksi Modal / Cash Preservation)
        clean_regime = (current_regime or "BULLISH").upper()
        is_hostile_climate = any(x in clean_regime for x in ["CHOPPY", "BEAR", "DEFENSIVE", "RED"])
        
        min_score_required = 92 if "BEAR" in clean_regime else (88 if is_hostile_climate else 82)
        min_rs_required = 82 if "BEAR" in clean_regime else (75 if is_hostile_climate else 60)

        if not setups or final_pts_score < min_score_required:
            return None

        # 2. Wajib memenuhi standar Relative Strength (RS Rating) terhadap benchmark
        if rs_info.get("rating", 50) < min_rs_required:
            return None

        # 3. Filter Anti-Saham Lambat & Anti-Jebakan di Pasar Rawan
        atr_pct = (atr14 / price) * 100 if price > 0 else 2.0
        if is_hostile_climate and (atr_pct < 1.8 and rvol < 1.3):
            return None
        if is_hostile_climate and trap_score >= 45:
            return None

        primary_setup = setups[0]
        trade_plan = generate_trade_plan(price, atr14, primary_setup, sector=ticker_info.get("sector", ""), market=clean_m)
        
        change_pct = round(((price - float(prev["Close"])) / float(prev["Close"])) * 100, 2) if float(prev["Close"]) > 0 else 0.0
        clean_symbol = ticker_info["ticker"].replace(".JK", "").strip() if clean_m == "IDX" else ticker_info["ticker"].strip()

        turnover_scale = 1_000_000_000 if clean_m == "IDX" else 1_000_000

        # Capital Velocity Metric (Saham pergerakan tercepat T+1 s.d T+3)
        vcp_val = float(last.get("vcp_ratio", 1.0))
        is_fast_velocity = bool(rvol >= 1.7 and rs_info.get("rating", 0) >= 85 and vcp_val <= 0.48)

        is_anti_crisis = bool(ticker_info.get("is_anti_crisis", False) or ticker_info.get("sector") in ["Precious Metals", "Inverse ETF"] or clean_symbol in ["BRMS", "PSAB", "ANTM", "MDKA", "ITMG", "MEDC", "GLD", "IAU", "SH", "PSQ", "SQQQ"])
        is_inverse_hedge = bool(ticker_info.get("is_inverse_hedge", False) or clean_symbol in ["SH", "PSQ", "SQQQ"])

        return {
            "market": clean_m,
            "currency": "USD" if clean_m == "US" else "IDR",
            "ticker": ticker_info["ticker"],
            "symbol": clean_symbol,
            "name": ticker_info["name"],
            "sector": ticker_info["sector"],
            "is_anti_crisis": is_anti_crisis,
            "is_inverse_hedge": is_inverse_hedge,
            "price": price,
            "change_pct": change_pct,
            "volume": int(volume),
            "turnover_bio": round(turnover / turnover_scale, 2),
            "turnover_ma20_bio": round(turnover_ma20 / turnover_scale, 2),
            "rvol": round(rvol, 2),
            "rsi": round(float(last["rsi14"]), 1) if pd.notnull(last["rsi14"]) else 50.0,
            "weekly_confirmed": weekly_confirmed,
            "primary_setup": primary_setup,
            "setups": setups,
            "score": final_pts_score,
            "ai_score": min(99, max(10, ai_score)),
            "classic_score": min(99, classic_score),
            "confluence_score": final_pts_score,
            "big_money_status": big_money_status,
            "is_sector_leader": is_sector_leader,
            "rs_rating": rs_info["rating"],
            "rs_tier": rs_info["tier"],
            "rs_label": rs_info["label"],
            "rs_color": rs_info["color"],
            "volatility_profile": trade_plan.get("volatility_profile", "BALANCED_GROWTH"),
            "volatility_badge": trade_plan.get("volatility_badge", "Balanced"),
            "is_fast_velocity": is_fast_velocity,
            "velocity_badge": "⚡ Fast Velocity (T+1 s.d T+3)" if is_fast_velocity else None,
            "earnings_info": earnings_info,
            "earnings_badge": earnings_info.get("badge_text") if earnings_info else None,
            "earnings_status": earnings_info.get("status") if earnings_info else None,
            "earnings_color": earnings_info.get("badge_color") if earnings_info else None,
            "is_earnings_blackout": earnings_info.get("is_blackout", False) if earnings_info else False,
            "earnings_guidance": earnings_info.get("guidance") if earnings_info else None,
            "flow_score": flow_score,
            "cmf_val": cmf_val,
            "vdu_ratio": ai_eval.get("vdu_ratio", 1.0) if ai_eval else 1.0,
            "ud_ratio_20": ai_eval.get("ud_ratio_20", 1.0) if ai_eval else 1.0,
            "sepa_passed_count": ai_eval.get("sepa_passed_count", 0) if ai_eval else 0,
            "ai_analysis": ai_eval,
            "win_probability": ai_eval.get("win_probability", 80.0),
            "conviction_label": ai_eval.get("conviction_label", "Solid Momentum"),
            "conviction_color": ai_eval.get("conviction_color", "emerald"),
            "trap_badge": ai_eval.get("trap_badge", "🛡️ Valid Breakout"),
            "trap_color": ai_eval.get("trap_color", "emerald"),
            "trap_score": ai_eval.get("trap_score", 15),
            "historical_match": ai_eval.get("historical_match"),
            "plan": trade_plan
        }
    except Exception as e:
        print(f"Error scanning {ticker_info.get('ticker')}: {e}")
        return None

def run_full_scan(market: str = "IDX") -> list:
    """Melakukan scan cepat universe saham secara batch (IDX atau US)."""
    clean_m = (market or "IDX").upper().strip()
    from app.services.market_data import batch_fetch_stock_dfs, fetch_stock_df
    from app.engine.relative_strength import compute_universe_rs_ratings

    if clean_m == "US":
        from app.engine.universe_us import get_universe_us
        universe = get_universe_us()
        benchmark_ticker = "^GSPC"
    else:
        from app.engine.universe import get_universe
        universe = get_universe()
        benchmark_ticker = "^JKSE"

    tickers = [item["ticker"] for item in universe]
    dfs = batch_fetch_stock_dfs(tickers, batch_size=35)
    
    # Hitung RS ranking batch vs Benchmark
    try:
        df_bench = fetch_stock_df(benchmark_ticker)
        if df_bench is not None and not df_bench.empty:
            compute_universe_rs_ratings(dfs, df_bench)
    except Exception as e:
        print(f"Error computing universe RS ratings: {e}")

    results = []
    for item in universe:
        df = dfs.get(item["ticker"])
        res = scan_stock(item, df, market=clean_m)
        if res is not None:
            results.append(res)
    results.sort(key=lambda x: x["score"], reverse=True)
    return results

