import math
import random
from typing import Dict, Any, List, Optional
from datetime import datetime

# Impor learner & sector engine secara aman (fallback graceful)
try:
    from app.engine.learner import get_learned_weights
except Exception:
    def get_learned_weights():
        return {}

def calculate_empirical_ticker_factor(df) -> Dict[str, Any]:
    """
    Menganalisis 60-120 bar historis saham untuk menghitung rekam jejak riil:
    - Follow-Through Win Rate (% keberhasilan mencapai minimal +2.5% dalam 5 hari setelah uji EMA 20 / Breakout)
    - Trend Stability (Konsistensi harga bertahan di atas EMA 20)
    - Average Gain on Bullish Follow-Through
    """
    if df is None or len(df) < 20:
        return {
            "empirical_win_rate": 78.0,
            "trend_stability": 75.0,
            "clean_breakout_ratio": 72.0,
            "sample_events": 0,
            "ema20": None,
            "status": "STANDARD_BASE"
        }

    try:
        closes = df['Close'].tolist()
        highs = df['High'].tolist()
        lows = df['Low'].tolist()
        volumes = df['Volume'].tolist()
        n = len(closes)

        # Hitung EMA 20
        ema20 = []
        multiplier = 2 / (20 + 1)
        ema = closes[0]
        for c in closes:
            ema = (c - ema) * multiplier + ema
            ema20.append(ema)

        # Cari setup breakout / bounce events dalam 90 bar terakhir
        events_total = 0
        events_successful = 0
        stability_count = 0

        eval_start = max(20, n - 90)
        for i in range(eval_start, n - 5):
            c_now = closes[i]
            e_now = ema20[i]
            v_now = volumes[i] if i < len(volumes) else 1
            v_ma = sum(volumes[max(0, i-20):i]) / max(1, min(20, i)) if volumes else 1

            if c_now >= e_now:
                stability_count += 1

            # Trigger event: Breakout candle atau bounce di atas EMA 20 dengan volume sehat
            is_trigger = (c_now > e_now and closes[i-1] <= ema20[i-1]) or (c_now > e_now and v_now >= v_ma * 1.2 and c_now > closes[i-1])
            if is_trigger:
                events_total += 1
                # Cek pergerakan 5 hari ke depan
                max_future_high = max(highs[i+1:i+6]) if i+6 <= n else max(highs[i+1:])
                future_gain = (max_future_high - c_now) / c_now
                if future_gain >= 0.025:  # Gain minimal +2.5%
                    events_successful += 1

        total_evaluated_bars = max(1, n - 5 - eval_start)
        trend_stability = round((stability_count / total_evaluated_bars) * 100, 1)

        if events_total >= 3:
            emp_win_rate = round((events_successful / events_total) * 100, 1)
        else:
            emp_win_rate = 75.0 + (trend_stability - 50.0) * 0.2

        emp_win_rate = max(55.0, min(95.0, emp_win_rate))
        trend_stability = max(40.0, min(95.0, trend_stability))

        return {
            "empirical_win_rate": emp_win_rate,
            "trend_stability": trend_stability,
            "clean_breakout_ratio": round(emp_win_rate * 0.95, 1),
            "sample_events": events_total,
            "ema20": round(ema20[-1], 2) if ema20 else None,
            "status": "CALIBRATED_HISTORICAL"
        }
    except Exception as e:
        return {
            "empirical_win_rate": 78.0,
            "trend_stability": 75.0,
            "clean_breakout_ratio": 72.0,
            "sample_events": 0,
            "ema20": None,
            "status": "FALLBACK"
        }

def calculate_smart_money_concentration(df, volume_ratio: float = 1.5) -> Dict[str, Any]:
    """Mengukur konsentrasi akumulasi institusi (Smart Money) berdasarkan volume spread & up/down ratio."""
    rvol = max(0.5, float(volume_ratio or 1.2))
    if df is None or len(df) < 15:
        score = min(95.0, max(50.0, 60.0 + (rvol - 1.0) * 18.0))
        return {
            "smart_money_score": round(score, 1),
            "volume_z_score": round((rvol - 1.0) * 1.5, 2),
            "accumulation_status": "Institutional Inflow" if rvol >= 1.5 else "Moderate Inflow",
            "is_accumulated": rvol >= 1.3
        }

    try:
        closes = df['Close'].tolist()[-15:]
        volumes = df['Volume'].tolist()[-15:]
        up_vol = sum(v for i, v in enumerate(volumes[1:], start=1) if closes[i] >= closes[i-1])
        down_vol = sum(v for i, v in enumerate(volumes[1:], start=1) if closes[i] < closes[i-1])
        total_vol = up_vol + down_vol

        up_ratio = (up_vol / total_vol) if total_vol > 0 else 0.5
        vol_z = round((rvol - 1.0) * 1.8 + (up_ratio - 0.5) * 2.0, 2)
        score = 50.0 + (up_ratio * 30.0) + min(20.0, (rvol - 1.0) * 12.0)
        score = max(45.0, min(98.0, round(score, 1)))

        status = "Heavy Institutional Inflow" if score >= 82 else ("Moderate Inflow" if score >= 65 else "Neutral Volume")

        return {
            "smart_money_score": score,
            "volume_z_score": vol_z,
            "accumulation_status": status,
            "is_accumulated": score >= 70.0
        }
    except Exception:
        return {
            "smart_money_score": 75.0,
            "volume_z_score": 1.2,
            "accumulation_status": "Moderate Inflow",
            "is_accumulated": True
        }

def calculate_scenario_probabilities(
    pts_score: float,
    volume_ratio: float,
    market_climate: str,
    setup_name: str,
    sector_rank: int = 4,
    empirical_win_rate: float = 78.0,
    smart_money_score: float = 75.0
) -> Dict[str, float]:
    """
    Menghitung bobot probabilitas dinamis terkalibrasi (Multi-Factor Quantitative Calibration).
    Mengintegrasikan PTS teknikal, Smart Money, Sektor, Rekam Jejak Historis Emiten, dan Iklim Pasar.
    """
    clean_climate = (market_climate or "BULLISH").upper()
    pts = max(50.0, min(100.0, float(pts_score or 85.0)))
    rvol = max(0.5, min(5.0, float(volume_ratio or 1.2)))
    emp_wr = max(50.0, min(95.0, float(empirical_win_rate or 78.0)))
    sm_score = max(40.0, min(98.0, float(smart_money_score or 75.0)))

    # 1. Base Probability Calculation
    prob_a = 52.0 + (pts - 85.0) * 0.45 + (rvol - 1.0) * 3.5
    prob_b = 32.0 - (pts - 85.0) * 0.20
    prob_c = 16.0 - (pts - 85.0) * 0.25 - (rvol - 1.0) * 1.8

    # 2. Empirical Historical Pattern Multiplier
    emp_delta = (emp_wr - 75.0) * 0.35
    prob_a += emp_delta
    prob_c -= emp_delta * 0.7

    # 3. Smart Money / Volume Concentration Boost
    sm_delta = (sm_score - 70.0) * 0.25
    prob_a += sm_delta
    prob_b -= sm_delta * 0.4
    prob_c -= sm_delta * 0.6

    # 4. Sector Synergy Multiplier
    if sector_rank <= 3:
        # Leading Sector Boost
        prob_a += 5.5
        prob_c -= 3.5
    elif sector_rank >= 8:
        # Lagging Sector Penalty
        prob_a -= 4.0
        prob_b += 2.0
        prob_c += 2.0

    # 5. Market Climate Multiplier
    if "BULL" in clean_climate:
        prob_a += 6.0
        prob_c -= 4.0
    elif "BEAR" in clean_climate:
        prob_a -= 12.0
        prob_b += 4.0
        prob_c += 8.0
    else:  # NEUTRAL / CHOPPY
        prob_a -= 2.0
        prob_b += 4.0
        prob_c -= 2.0

    # 6. Setup Specific Fine-Tuning
    s_lower = (setup_name or "").lower()
    if "vcp" in s_lower:
        prob_a += 4.0
        prob_b -= 2.0
    elif "pullback" in s_lower:
        prob_b += 6.0
        prob_a -= 3.0
    elif "volume surge" in s_lower:
        prob_a += 5.0
        prob_c += 2.0

    # Normalisasi & Clamping
    prob_a = max(38.0, min(84.0, prob_a))
    prob_b = max(12.0, min(42.0, prob_b))
    prob_c = max(4.0, min(28.0, prob_c))

    total = prob_a + prob_b + prob_c
    prob_a = round((prob_a / total) * 100, 1)
    prob_b = round((prob_b / total) * 100, 1)
    prob_c = round(100.0 - prob_a - prob_b, 1)

    return {
        "scenario_a_prob": prob_a,
        "scenario_b_prob": prob_b,
        "scenario_c_prob": prob_c
    }

def calculate_model_reliability_index(
    pts_score: float,
    volume_ratio: float,
    sector_rank: int,
    empirical_win_rate: float,
    smart_money_score: float,
    market_climate: str,
    data_quality_score: float = 95.0
) -> Dict[str, Any]:
    """Menghitung Model Reliability Index (MRI) 0-100% dan 4 Pilar Konfluensi Kuantitatif."""
    score_pts = min(100.0, max(50.0, pts_score))
    score_sm = min(100.0, max(50.0, smart_money_score))
    score_sector = 95.0 if sector_rank <= 3 else (80.0 if sector_rank <= 7 else 62.0)
    score_emp = min(100.0, max(50.0, empirical_win_rate))

    mri_composite = (score_pts * 0.25) + (score_sm * 0.25) + (score_sector * 0.25) + (score_emp * 0.25)
    
    # Climate penalty if market is hostile
    if "BEAR" in (market_climate or "").upper():
        mri_composite -= 8.0
    elif "NEUTRAL" in (market_climate or "").upper():
        mri_composite -= 2.0

    mri_score = round(max(55.0, min(98.5, mri_composite)), 1)

    if mri_score >= 90.0:
        badge = "Ultra High Confluence"
        grade = "Hedge-Fund Grade"
        color = "emerald"
    elif mri_score >= 82.0:
        badge = "High Confluence"
        grade = "Institutional Grade"
        color = "purple"
    elif mri_score >= 72.0:
        badge = "Moderate Confluence"
        grade = "Standard Setup"
        color = "blue"
    else:
        badge = "Cautionary Setup"
        grade = "Low Confluence"
        color = "amber"

    # 4 Pilar Konfluensi Detail
    pillars = [
        {
            "id": "sector",
            "name": "Rotasi Sektor",
            "status": "Leading Sector (Rank " + str(sector_rank) + ")" if sector_rank <= 3 else ("Neutral Sector" if sector_rank <= 7 else "Lagging Sector"),
            "is_positive": sector_rank <= 4,
            "icon": "pie-chart",
            "score": round(score_sector, 1)
        },
        {
            "id": "smart_money",
            "name": "Konsentrasi Smart Money",
            "status": "Heavy Accumulation" if smart_money_score >= 80 else ("Active Inflow" if smart_money_score >= 65 else "Neutral Volume"),
            "is_positive": smart_money_score >= 68,
            "icon": "shield-check",
            "score": round(smart_money_score, 1)
        },
        {
            "id": "historical",
            "name": "Rekam Jejak Historis",
            "status": f"{empirical_win_rate}% Win-Rate (120D)",
            "is_positive": empirical_win_rate >= 75,
            "icon": "history",
            "score": round(empirical_win_rate, 1)
        },
        {
            "id": "technical",
            "name": "Konfluensi Trend & Volume",
            "status": f"{pts_score} PTS · RVol {volume_ratio:.1f}x",
            "is_positive": pts_score >= 85 and volume_ratio >= 1.2,
            "icon": "trending-up",
            "score": round(pts_score, 1)
        }
    ]

    return {
        "mri_score": mri_score,
        "badge": badge,
        "grade": grade,
        "color": color,
        "pillars": pillars
    }

def generate_price_forecast(
    ticker: str,
    market: str = "IDX",
    entry_price: float = 0.0,
    stop_loss: float = 0.0,
    tp1: float = 0.0,
    tp2: float = 0.0,
    pts_score: float = 85.0,
    setup_name: str = "Momentum Breakout",
    volume_ratio: float = 1.5,
    market_climate: str = "BULLISH",
    atr: Optional[float] = None,
    historical_df: Any = None,
    sector_name: str = "Industrial",
    sector_rank: int = 3
) -> Dict[str, Any]:
    """
    Menghasilkan proyeksi harga 5 hari bursa, ghost candles realistis multi-scenario,
    corong volatilitas, serta Model Reliability Index (MRI) kuantitatif.
    """
    is_us = market.upper() == "US"
    entry = float(entry_price or (100.0 if is_us else 1000.0))
    sl = float(stop_loss or (entry * 0.95))
    t1 = float(tp1 or (entry * 1.08))
    t2 = float(tp2 or (entry * 1.15))

    # Estimasi ATR harian
    daily_atr = float(atr) if atr and atr > 0 else entry * 0.028

    # 1. Hitung Pilar Empiris & Smart Money dari Data Historis
    empirical_data = calculate_empirical_ticker_factor(historical_df)
    smart_money_data = calculate_smart_money_concentration(historical_df, volume_ratio)

    emp_wr = empirical_data["empirical_win_rate"]
    sm_score = smart_money_data["smart_money_score"]
    ema20_val = empirical_data.get("ema20") or round(entry * 0.985, 2)

    # 2. Hitung Probabilitas Skenario Terkalibrasi
    probs = calculate_scenario_probabilities(
        pts_score=pts_score,
        volume_ratio=volume_ratio,
        market_climate=market_climate,
        setup_name=setup_name,
        sector_rank=sector_rank,
        empirical_win_rate=emp_wr,
        smart_money_score=sm_score
    )

    # 3. Hitung Model Reliability Index (MRI)
    mri = calculate_model_reliability_index(
        pts_score=pts_score,
        volume_ratio=volume_ratio,
        sector_rank=sector_rank,
        empirical_win_rate=emp_wr,
        smart_money_score=sm_score,
        market_climate=market_climate
    )

    # 4. Velocity & Time-to-Target Estimator
    velocity_boost = 0.3 if sector_rank <= 3 else 0.0
    time_to_tp1_days = round(max(1.4, 3.2 - (pts_score - 85.0) * 0.05 - (volume_ratio - 1.0) * 0.3 - velocity_boost), 1)
    time_to_tp2_days = round(time_to_tp1_days + 2.2, 1)

    # 5. Helper format harga untuk narasi
    def fmt(p):
        if is_us:
            return f"${p:,.2f}"
        return f"Rp {round(p):,}".replace(",", ".")

    gain_tp1_pct = round(((t1 - entry) / entry) * 100, 1)
    gain_tp2_pct = round(((t2 - entry) / entry) * 100, 1)
    risk_sl_pct = round(((entry - sl) / entry) * 100, 1)

    # =========================================================================
    # 6. REALISTIC GHOST CANDLESTICK PROJECTIONS (OHLC Simulation)
    # =========================================================================
    
    # ── Skenario A: Bullish Momentum Acceleration (Ekspansi Kuat) ──
    c_a1 = round(entry + min(t1 - entry, daily_atr * 0.90), 2)
    c_a2 = round(entry + (t1 - entry) * 0.88, 2)
    c_a3 = round(t1 + (t2 - t1) * 0.30, 2)
    c_a4 = round(t1 + (t2 - t1) * 0.72, 2)
    c_a5 = round(t2, 2)

    ghost_candles_a = [
        {
            "day": 1, "label": "T+1",
            "open": round(entry, 2),
            "high": round(c_a1 + daily_atr * 0.22, 2),
            "low": round(entry - daily_atr * 0.15, 2),
            "close": c_a1,
            "gain_pct": round(((c_a1 - entry) / entry) * 100, 2)
        },
        {
            "day": 2, "label": "T+2",
            "open": round(c_a1 - daily_atr * 0.05, 2),
            "high": round(max(c_a2, t1 * 0.995) + daily_atr * 0.15, 2),
            "low": round(c_a1 - daily_atr * 0.22, 2),
            "close": c_a2,
            "gain_pct": round(((c_a2 - entry) / entry) * 100, 2)
        },
        {
            "day": 3, "label": "T+3",
            "open": round(c_a2, 2),
            "high": round(c_a3 + daily_atr * 0.25, 2),
            "low": round(c_a2 - daily_atr * 0.12, 2),
            "close": c_a3,
            "gain_pct": round(((c_a3 - entry) / entry) * 100, 2)
        },
        {
            "day": 4, "label": "T+4",
            "open": round(c_a3, 2),
            "high": round(c_a4 + daily_atr * 0.20, 2),
            "low": round(t1 * 0.992, 2),
            "close": c_a4,
            "gain_pct": round(((c_a4 - entry) / entry) * 100, 2)
        },
        {
            "day": 5, "label": "T+5",
            "open": round(c_a4, 2),
            "high": round(t2 + daily_atr * 0.18, 2),
            "low": round(c_a4 - daily_atr * 0.15, 2),
            "close": c_a5,
            "gain_pct": round(((c_a5 - entry) / entry) * 100, 2)
        }
    ]

    # ── Skenario B: Pullback & EMA 20 Retest Rebound ──
    dip_support = max(sl * 1.015, min(ema20_val, entry - daily_atr * 0.45))
    c_b1 = round(entry - daily_atr * 0.32, 2)
    c_b2 = round(dip_support + daily_atr * 0.20, 2)
    c_b3 = round(entry + (t1 - entry) * 0.38, 2)
    c_b4 = round(entry + (t1 - entry) * 0.82, 2)
    c_b5 = round(t1 * 1.008, 2)

    ghost_candles_b = [
        {
            "day": 1, "label": "T+1",
            "open": round(entry, 2),
            "high": round(entry + daily_atr * 0.20, 2),
            "low": round(c_b1 - daily_atr * 0.12, 2),
            "close": c_b1,
            "gain_pct": round(((c_b1 - entry) / entry) * 100, 2)
        },
        {
            "day": 2, "label": "T+2",
            "open": round(c_b1, 2),
            "high": round(c_b1 + daily_atr * 0.10, 2),
            "low": round(dip_support - daily_atr * 0.18, 2),
            "close": c_b2,
            "gain_pct": round(((c_b2 - entry) / entry) * 100, 2)
        },
        {
            "day": 3, "label": "T+3",
            "open": round(c_b2, 2),
            "high": round(c_b3 + daily_atr * 0.18, 2),
            "low": round(c_b2 - daily_atr * 0.10, 2),
            "close": c_b3,
            "gain_pct": round(((c_b3 - entry) / entry) * 100, 2)
        },
        {
            "day": 4, "label": "T+4",
            "open": round(c_b3, 2),
            "high": round(c_b4 + daily_atr * 0.22, 2),
            "low": round(c_b3 - daily_atr * 0.12, 2),
            "close": c_b4,
            "gain_pct": round(((c_b4 - entry) / entry) * 100, 2)
        },
        {
            "day": 5, "label": "T+5",
            "open": round(c_b4, 2),
            "high": round(c_b5 + daily_atr * 0.20, 2),
            "low": round(c_b4 - daily_atr * 0.15, 2),
            "close": c_b5,
            "gain_pct": round(((c_b5 - entry) / entry) * 100, 2)
        }
    ]

    # ── Skenario C: Invalidation Risk & Breakdown ke Stop Loss ──
    c_c1 = round(entry - daily_atr * 0.38, 2)
    c_c2 = round(sl + daily_atr * 0.25, 2)
    c_c3 = round(sl, 2)
    c_c4 = round(sl - daily_atr * 0.20, 2)
    c_c5 = round(sl - daily_atr * 0.30, 2)

    ghost_candles_c = [
        {
            "day": 1, "label": "T+1",
            "open": round(entry, 2),
            "high": round(entry + daily_atr * 0.32, 2),
            "low": round(c_c1 - daily_atr * 0.12, 2),
            "close": c_c1,
            "gain_pct": round(((c_c1 - entry) / entry) * 100, 2)
        },
        {
            "day": 2, "label": "T+2",
            "open": round(c_c1, 2),
            "high": round(c_c1 + daily_atr * 0.08, 2),
            "low": round(c_c2 - daily_atr * 0.15, 2),
            "close": c_c2,
            "gain_pct": round(((c_c2 - entry) / entry) * 100, 2)
        },
        {
            "day": 3, "label": "T+3",
            "open": round(c_c2, 2),
            "high": round(c_c2 + daily_atr * 0.06, 2),
            "low": round(sl - daily_atr * 0.22, 2),
            "close": c_c3,
            "gain_pct": round(((c_c3 - entry) / entry) * 100, 2)
        },
        {
            "day": 4, "label": "T+4",
            "open": round(c_c3, 2),
            "high": round(sl + daily_atr * 0.12, 2),
            "low": round(c_c4 - daily_atr * 0.15, 2),
            "close": c_c4,
            "gain_pct": round(((c_c4 - entry) / entry) * 100, 2)
        },
        {
            "day": 5, "label": "T+5",
            "open": round(c_c4, 2),
            "high": round(c_c4 + daily_atr * 0.10, 2),
            "low": round(c_c5 - daily_atr * 0.15, 2),
            "close": c_c5,
            "gain_pct": round(((c_c5 - entry) / entry) * 100, 2)
        }
    ]

    # 7. Corong Ketidakpastian (Cone of Uncertainty)
    cone_bounds = []
    for day in range(1, 6):
        spread = daily_atr * math.sqrt(day)
        cone_bounds.append({
            "day": day,
            "label": f"T+{day}",
            "upper_price": round(entry + spread * 1.75, 2),
            "lower_price": round(max(sl * 0.96, entry - spread * 1.25), 2),
            "expected_mid": round(entry + (t1 - entry) * (day / 5.0) * 0.8, 2)
        })

    # 8. Dynamic Context-Rich Scenario Descriptions
    scen_a_sub = f"Ghost Candles Tembus TP1 ({fmt(t1)}) ~{time_to_tp1_days} Hari"
    scen_b_sub = f"Uji Support EMA 20 ({fmt(ema20_val)}) Lalu Rebound ke TP1"
    scen_c_sub = f"Gagal Tembus & Kena Stop Loss ({fmt(sl)})"

    scen_a_desc = (
        f"Katalis volume buy terkonfirmasi (RVol {volume_ratio:.1f}x) didukung akumulasi Smart Money ({sm_score}/100) "
        f"dan sinyal {setup_name}. Harga diproyeksikan berekspansi cepat melewati resistance awal menuju Target TP1 {fmt(t1)} (+{gain_tp1_pct}%) "
        f"dalam ~{time_to_tp1_days} hari bursa sebelum menguji target lanjutan TP2 {fmt(t2)} (+{gain_tp2_pct}%)."
    )

    scen_b_desc = (
        f"Terjadi profit taking jangka pendek di T+1/T+2 yang menguji bantalan support dinamis EMA 20 (~{fmt(ema20_val)}) "
        f"dengan toleransi ATR harian ({fmt(daily_atr)}). Reaksi akumulasi buyer di area support ini berpotensi memicu swing rebound "
        f"menuju TP1 {fmt(t1)} (+{gain_tp1_pct}%) pada T+4 hingga T+5."
    )

    scen_c_desc = (
        f"Skenario momentum batal jika timbul selling pressure mendadak atau penurunan indeks pasar yang menekan harga di bawah {fmt(entry)}. "
        f"Batas proteksi modal (Stop Loss) ketat di level {fmt(sl)} (-{risk_sl_pct}%) wajib dieksekusi tanpa kompromi untuk menghindari drawdown besar."
    )

    return {
        "ticker": ticker.upper(),
        "market": market.upper(),
        "entry_price": entry,
        "stop_loss": sl,
        "tp1": t1,
        "tp2": t2,
        "daily_atr": round(daily_atr, 2),
        "ema20": ema20_val,
        "probabilities": probs,
        "model_reliability": mri,
        "empirical_metrics": empirical_data,
        "smart_money_metrics": smart_money_data,
        "sector_synergy": {
            "sector_name": sector_name,
            "sector_rank": sector_rank,
            "is_leading": sector_rank <= 3
        },
        "time_to_target": {
            "tp1_estimated_days": time_to_tp1_days,
            "tp2_estimated_days": time_to_tp2_days,
            "optimal_exit_day": int(round(time_to_tp1_days)),
            "velocity_label": "High Momentum Fast" if time_to_tp1_days <= 2.2 else "Steady Swing Progression"
        },
        "scenarios": {
            "scenario_a": {
                "name": "Skenario A: Bullish Acceleration",
                "tag": "PRIMARY_BULLISH",
                "prob": probs["scenario_a_prob"],
                "color": "emerald",
                "subtitle": scen_a_sub,
                "headline": f"🚀 Akselerasi Momentum Cepat Menuju Target TP1 ({fmt(t1)}) & TP2 ({fmt(t2)})",
                "description": scen_a_desc,
                "path": [
                    {"label": "Day 0", "price": entry, "gain_pct": 0.0},
                    {"label": "T+1", "price": c_a1, "gain_pct": round(((c_a1 - entry) / entry) * 100, 2)},
                    {"label": "T+2", "price": c_a2, "gain_pct": round(((c_a2 - entry) / entry) * 100, 2)},
                    {"label": "T+3", "price": c_a3, "gain_pct": round(((c_a3 - entry) / entry) * 100, 2)},
                    {"label": "T+4", "price": c_a4, "gain_pct": round(((c_a4 - entry) / entry) * 100, 2)},
                    {"label": "T+5", "price": c_a5, "gain_pct": round(((c_a5 - entry) / entry) * 100, 2)},
                ],
                "ghost_candles": ghost_candles_a
            },
            "scenario_b": {
                "name": "Skenario B: Base Pullback & Retest",
                "tag": "PULLBACK_RETEST",
                "prob": probs["scenario_b_prob"],
                "color": "blue",
                "subtitle": scen_b_sub,
                "headline": f"🔄 Konsolidasi Pullback Menguji Support EMA 20 ({fmt(ema20_val)}) Sebelum Rebound",
                "description": scen_b_desc,
                "path": [
                    {"label": "Day 0", "price": entry, "gain_pct": 0.0},
                    {"label": "T+1", "price": c_b1, "gain_pct": round(((c_b1 - entry) / entry) * 100, 2)},
                    {"label": "T+2", "price": c_b2, "gain_pct": round(((c_b2 - entry) / entry) * 100, 2)},
                    {"label": "T+3", "price": c_b3, "gain_pct": round(((c_b3 - entry) / entry) * 100, 2)},
                    {"label": "T+4", "price": c_b4, "gain_pct": round(((c_b4 - entry) / entry) * 100, 2)},
                    {"label": "T+5", "price": c_b5, "gain_pct": round(((c_b5 - entry) / entry) * 100, 2)},
                ],
                "ghost_candles": ghost_candles_b
            },
            "scenario_c": {
                "name": "Skenario C: Invalidation / Breakdown",
                "tag": "INVALIDATION_RISK",
                "prob": probs["scenario_c_prob"],
                "color": "rose",
                "subtitle": scen_c_sub,
                "headline": f"⚠️ Rejeksi Skenario & Invalidation Risk ke Batas Stop Loss ({fmt(sl)})",
                "description": scen_c_desc,
                "path": [
                    {"label": "Day 0", "price": entry, "gain_pct": 0.0},
                    {"label": "T+1", "price": c_c1, "gain_pct": round(((c_c1 - entry) / entry) * 100, 2)},
                    {"label": "T+2", "price": c_c2, "gain_pct": round(((c_c2 - entry) / entry) * 100, 2)},
                    {"label": "T+3", "price": c_c3, "gain_pct": round(((c_c3 - entry) / entry) * 100, 2)},
                    {"label": "T+4", "price": c_c4, "gain_pct": round(((c_c4 - entry) / entry) * 100, 2)},
                    {"label": "T+5", "price": c_c5, "gain_pct": round(((c_c5 - entry) / entry) * 100, 2)},
                ],
                "ghost_candles": ghost_candles_c
            }
        },
        "cone_of_uncertainty": cone_bounds,
        "confidence_rating": {
            "score": pts_score,
            "badge": mri["badge"],
            "mri_score": mri["mri_score"],
            "grade": mri["grade"],
            "risk_reward_ratio": round(abs((t1 - entry) / max(0.01, entry - sl)), 2)
        }
    }

def validate_prediction_against_actual(
    forecast: Dict[str, Any],
    actual_daily_prices: List[float]
) -> Dict[str, Any]:
    """Membandingkan pergerakan harga riil aktual dengan proyeksi awal untuk menghitung skor validasi dan akurasi model."""
    if not actual_daily_prices or len(actual_daily_prices) == 0:
        return {
            "is_validated": False,
            "accuracy_score_pct": 100.0,
            "matched_scenario": "SCENARIO_A",
            "validation_status": "WAITING_FIRST_BAR",
            "status_label": "Menunggu Candle T+1",
            "deviation_pct": 0.0,
            "insights": "Sinyal baru terbit. Evaluasi akurasi prediksi akan aktif setelah penutupan bursa hari pertama (T+1)."
        }

    scen_a = [p["price"] for p in forecast["scenarios"]["scenario_a"]["path"][1:]]
    scen_b = [p["price"] for p in forecast["scenarios"]["scenario_b"]["path"][1:]]
    scen_c = [p["price"] for p in forecast["scenarios"]["scenario_c"]["path"][1:]]

    n_days = min(len(actual_daily_prices), len(scen_a))
    actual_subset = actual_daily_prices[:n_days]

    def calc_mape(actuals, predicted):
        errors = [abs(act - pred) / max(1.0, pred) for act, pred in zip(actuals, predicted[:len(actuals)])]
        return sum(errors) / len(errors) if errors else 0.0

    mape_a = calc_mape(actual_subset, scen_a)
    mape_b = calc_mape(actual_subset, scen_b)
    mape_c = calc_mape(actual_subset, scen_c)

    latest_actual = actual_subset[-1]
    entry = forecast["entry_price"]
    tp1 = forecast["tp1"]
    sl = forecast["stop_loss"]

    best_scenario = "SCENARIO_A"
    lowest_mape = mape_a
    if mape_b < lowest_mape:
        best_scenario = "SCENARIO_B"
        lowest_mape = mape_b
    if mape_c < lowest_mape and latest_actual <= sl:
        best_scenario = "SCENARIO_C"
        lowest_mape = mape_c

    accuracy_score = max(0.0, min(100.0, round((1.0 - lowest_mape) * 100, 1)))

    return {
        "is_validated": True,
        "accuracy_score_pct": accuracy_score,
        "matched_scenario": best_scenario,
        "validation_status": "HIGH_ACCURACY" if accuracy_score >= 85 else ("MODERATE_ALIGNMENT" if accuracy_score >= 70 else "DIVERGENCE"),
        "status_label": f"Valid {accuracy_score}% Presisi Skenario",
        "deviation_pct": round(lowest_mape * 100, 2),
        "evaluated_bars": n_days,
        "insights": f"Pergerakan aktual {n_days} hari terdekat paling selaras dengan {best_scenario.replace('_', ' ')} (Deviasi {lowest_mape*100:.1f}%)."
    }
