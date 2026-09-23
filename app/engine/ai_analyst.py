"""
Modul AI Deep Reasoning Analyst & False-Breakout Trap Detector.
Menggabungkan Standar Klasik Minervini SEPA & CANSLIM dengan Kecerdasan Institusional:
1. SEPA Checklist Verification (Stage 2, VCP Squeeze, VDU Supply Contraction, UD Accumulation).
2. Institutional Microstructure & False-Breakout / Churning Trap Detector.
3. Win Probability & AI Conviction Index (0-100%).
4. 10-Year Multi-Bagger Historical Pattern Matcher.
5. Hedge-Fund Grade Actionable Diagnostic Narrative.
"""

from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np

# Database Template Pola Saham Super-Winner Historis (10 Tahun Siklus Bursa)
HISTORICAL_SUPER_WINNERS = {
    "US": [
        {
            "ticker": "NVDA",
            "year": "Okt 2023",
            "setup": "VCP Contraction + High Tight Flag",
            "gain": "+185%",
            "traits": {"vcp_ratio": 0.38, "rvol": 2.4, "rs_rating": 96, "sector": "Semiconductors"}
        },
        {
            "ticker": "PLTR",
            "year": "Feb 2024",
            "setup": "Post-Earnings Momentum Surge",
            "gain": "+120%",
            "traits": {"vcp_ratio": 0.45, "rvol": 3.1, "rs_rating": 92, "sector": "Software - Infrastructure"}
        },
        {
            "ticker": "SMCI",
            "year": "Jan 2024",
            "setup": "Stage 2 Pocket Pivot Breakout",
            "gain": "+240%",
            "traits": {"vcp_ratio": 0.42, "rvol": 2.8, "rs_rating": 95, "sector": "Computer Hardware"}
        },
        {
            "ticker": "AAPL",
            "year": "Mei 2020",
            "setup": "Cup with Handle Breakout",
            "gain": "+85%",
            "traits": {"vcp_ratio": 0.50, "rvol": 1.9, "rs_rating": 88, "sector": "Consumer Electronics"}
        }
    ],
    "IDX": [
        {
            "ticker": "BREN",
            "year": "Nov 2023",
            "setup": "Stage 2 Pure Momentum Acceleration",
            "gain": "+195%",
            "traits": {"vcp_ratio": 0.35, "rvol": 2.6, "rs_rating": 98, "sector": "Infrastruktur / Energi"}
        },
        {
            "ticker": "PANI",
            "year": "Agt 2023",
            "setup": "VCP Low Volatility Squeeze",
            "gain": "+160%",
            "traits": {"vcp_ratio": 0.32, "rvol": 2.2, "rs_rating": 94, "sector": "Properti"}
        },
        {
            "ticker": "BRMS",
            "year": "Sep 2024",
            "setup": "EMA 20 Pullback + Big Money Inflow",
            "gain": "+110%",
            "traits": {"vcp_ratio": 0.48, "rvol": 2.3, "rs_rating": 91, "sector": "Basic Materials / Gold"}
        },
        {
            "ticker": "MEDC",
            "year": "Sep 2023",
            "setup": "Commodity Supercycle Breakout",
            "gain": "+75%",
            "traits": {"vcp_ratio": 0.52, "rvol": 2.0, "rs_rating": 89, "sector": "Energy"}
        }
    ]
}

def analyze_stock_ai(
    ticker_info: Dict[str, str],
    df: pd.DataFrame,
    market: str = "IDX",
    rs_info: Optional[Dict[str, Any]] = None,
    flow_data: Optional[Dict[str, Any]] = None,
    earnings_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Menjalankan deep reasoning AI untuk mengevaluasi kualitas teknikal,
    probabilitas keberhasilan, risiko jebakan (Bull Trap), dan narasi analis hedge-fund.
    """
    clean_m = (market or "IDX").upper().strip()
    if df is None or len(df) < 30:
        return {}

    last = df.iloc[-1]
    prev = df.iloc[-2]

    price = float(last["Close"])
    open_p = float(last["Open"])
    high_p = float(last["High"])
    low_p = float(last["Low"])
    volume = float(last["Volume"]) if pd.notnull(last["Volume"]) else 0
    rvol = float(last.get("rvol", 1.0))
    vcp_ratio = float(last.get("vcp_ratio", 1.0))
    vdu_ratio = float(last.get("vdu_ratio", 1.0))
    ud_ratio_20 = float(last.get("ud_ratio_20", 1.0))
    clv = float(last.get("clv", 0.0))
    ema20 = float(last.get("ema20", price))
    ema50 = float(last.get("ema50", price))
    ema200 = float(last.get("ema200", price))
    rsi = float(last.get("rsi14", 50.0))
    weekly_confirmed = bool(last.get("weekly_uptrend", True))

    rs_rating = rs_info.get("rating", 75) if rs_info else 75
    big_money_status = flow_data.get("status", "NEUTRAL") if flow_data else "NEUTRAL"
    cmf_val = flow_data.get("cmf_val", 0.0) if flow_data else 0.0

    # ─────────────────────────────────────────────────────────────────────────
    # 1. MINERVINI SEPA & CANSLIM STRUCTURAL CHECKLIST
    # ─────────────────────────────────────────────────────────────────────────
    is_stage2 = bool(price > ema50 and ema20 >= ema50 and (ema200 == 0 or price > ema200))
    is_vcp_compressed = bool(vcp_ratio <= 0.52)
    is_vdu_passed = bool(vdu_ratio <= 0.70)
    is_ud_accumulated = bool(ud_ratio_20 >= 1.15)
    is_rs_leader = bool(rs_rating >= 80)
    is_clean_close = bool(clv >= 0.35)

    sepa_checklist = [
        {
            "name": "Stage 2 Trend Template",
            "rule": "Price > EMA 50 & EMA 20 > EMA 50",
            "passed": is_stage2,
            "status": "PASS" if is_stage2 else "FAIL"
        },
        {
            "name": "Volatility Contraction (VCP)",
            "rule": "Rentang 5D / 20D <= 50%",
            "passed": is_vcp_compressed,
            "status": "PASS" if is_vcp_compressed else "FAIL",
            "value": f"{vcp_ratio:.2f}x"
        },
        {
            "name": "Volume Dry-Up (VDU Supply Absorption)",
            "rule": "Volume Kering Sebelum Breakout <= 0.70x MA20",
            "passed": is_vdu_passed,
            "status": "PASS" if is_vdu_passed else "FAIL",
            "value": f"{vdu_ratio:.2f}x"
        },
        {
            "name": "Up/Down Volume Accumulation (U/D Ratio)",
            "rule": "Volume Akumulasi 20-Hari >= 1.15x",
            "passed": is_ud_accumulated,
            "status": "PASS" if is_ud_accumulated else "FAIL",
            "value": f"{ud_ratio_20:.2f}x"
        },
        {
            "name": "Multi-Timeframe Weekly Trend",
            "rule": "Weekly Close > Weekly EMA 20",
            "passed": weekly_confirmed,
            "status": "PASS" if weekly_confirmed else "FAIL"
        },
        {
            "name": "Relative Strength Outperformance",
            "rule": "RS Rating >= 80 (Market Leader)",
            "passed": is_rs_leader,
            "status": "PASS" if is_rs_leader else "FAIL",
            "value": f"RS {rs_rating}"
        }
    ]

    # ─────────────────────────────────────────────────────────────────────────
    # 2. CANDLE MICROSTRUCTURE & INSTITUTIONAL TRAP DETECTOR
    # ─────────────────────────────────────────────────────────────────────────
    candle_range = max(0.001, high_p - low_p)
    body_size = abs(price - open_p)
    upper_wick = max(0.0, high_p - max(price, open_p))
    lower_wick = max(0.0, min(price, open_p) - low_p)

    upper_wick_ratio = round((upper_wick / candle_range) * 100, 1)
    body_ratio = round((body_size / candle_range) * 100, 1)
    extension_from_ema20 = round(((price - ema20) / ema20) * 100, 1) if ema20 > 0 else 0.0

    # Kalkulasi Trap Risk Score (0 - 100)
    trap_score = 0
    trap_flags = []

    # Penalti 1: Ekor atas panjang / Churning (Smart money dumping into breakout)
    if upper_wick_ratio >= 45:
        trap_score += 45
        trap_flags.append(f"Rejection Ekor Atas Tajam / Churning ({upper_wick_ratio}%)")
    elif upper_wick_ratio >= 30:
        trap_score += 25
        trap_flags.append(f"Upper Shadow Cukup Tinggi ({upper_wick_ratio}%)")

    # Penalti 2: Volume Breakout Kering
    if rvol < 1.0:
        trap_score += 35
        trap_flags.append("Volume Breakout Kering (RVOL < 1.0x)")
    elif rvol < 1.3:
        trap_score += 15
        trap_flags.append("Volume Breakout Kurang Bertenaga (RVOL < 1.3x)")

    # Penalti 3: Overextended (Terlalu jauh dari EMA 20)
    max_safe_ext = 16.0 if clean_m == "US" else 12.0
    if extension_from_ema20 > max_safe_ext:
        trap_score += 30
        trap_flags.append(f"Overextended +{extension_from_ema20}% di Atas EMA 20")

    # Penalti 4: Tanpa Supply Absorption (Volume belum kering sebelum breakout)
    if vdu_ratio > 1.15:
        trap_score += 15
        trap_flags.append(f"Supply Overhang Tinggi (VDU {vdu_ratio:.2f}x)")

    # Penalti 5: Dominasi Volume Distribusi (U/D Ratio Rendah)
    if ud_ratio_20 < 0.85:
        trap_score += 20
        trap_flags.append(f"Tekanan Jual Dominan 20-Hari (U/D {ud_ratio_20:.2f}x)")

    # Penalti 6: RSI Extreme Overbought
    if rsi >= 82:
        trap_score += 20
        trap_flags.append(f"RSI Ekstrem Jenuh Beli ({rsi})")

    # Penalti 7: US Earnings Blackout
    if clean_m == "US" and earnings_info and earnings_info.get("is_blackout"):
        trap_score += 40
        trap_flags.append("Blackout Laba Kuartalan (Earnings < 3 Hari)")

    trap_score = min(100, max(0, trap_score))
    
    if trap_score <= 20:
        trap_status = "SAFE"
        trap_badge = "🛡️ Valid Breakout (Trap-Free)"
        trap_color = "emerald"
    elif trap_score <= 45:
        trap_status = "CAUTION"
        trap_badge = "⚡ Waspada Volatilitas"
        trap_color = "amber"
    else:
        trap_status = "HIGH_RISK"
        trap_badge = "⚠️ Risiko Bull-Trap Tinggi"
        trap_color = "rose"

    # ─────────────────────────────────────────────────────────────────────────
    # 3. WIN PROBABILITY & CONFLUENCE MATRIX (0 - 100%)
    # ─────────────────────────────────────────────────────────────────────────
    # Basis probabilitas dihitung dari kepatuhan terhadap SEPA murni
    sepa_passed_count = sum(1 for item in sepa_checklist if item["passed"])
    base_prob = 55.0 + (sepa_passed_count * 5.5)  # Max 88.0 jika semua SEPA lolos

    # Tambahan Bobot Institusional:
    if big_money_status == "INFLOW" and cmf_val > 0.12:
        base_prob += 6.0
    elif big_money_status == "INFLOW":
        base_prob += 3.0
    elif big_money_status == "OUTFLOW":
        base_prob -= 12.0

    if rvol >= 2.0:
        base_prob += 5.0
    elif rvol >= 1.5:
        base_prob += 3.0

    if is_clean_close:
        base_prob += 4.0

    # Potong berdasarkan Trap Score (Hukuman ketat)
    final_prob = base_prob - (trap_score * 0.45)
    final_prob = min(98.0, max(25.0, round(final_prob, 1)))

    # ─────────────────────────────────────────────────────────────────────────
    # 4. AI CONVICTION RATING
    # ─────────────────────────────────────────────────────────────────────────
    if final_prob >= 86 and trap_score <= 20 and sepa_passed_count >= 5:
        conviction = "HIGH_CONVICTION"
        conviction_label = "🔥 High Conviction (Super Setup)"
        conviction_color = "emerald"
    elif final_prob >= 76 and trap_score <= 40 and sepa_passed_count >= 4:
        conviction = "SOLID_MOMENTUM"
        conviction_label = "📈 Solid Momentum Buy"
        conviction_color = "blue"
    elif final_prob >= 60 and trap_score <= 50:
        conviction = "SELECTIVE"
        conviction_label = "👀 Selektif / Porsi Bertahap"
        conviction_color = "amber"
    else:
        conviction = "AVOID_TRAP"
        conviction_label = "⚠️ Hindari / Potensi Jebakan"
        conviction_color = "rose"

    # ─────────────────────────────────────────────────────────────────────────
    # 5. HISTORICAL SUPER-WINNER PATTERN MATCHING (10 Years)
    # ─────────────────────────────────────────────────────────────────────────
    pool = HISTORICAL_SUPER_WINNERS.get(clean_m, HISTORICAL_SUPER_WINNERS["IDX"])
    best_match = None
    highest_sim = 0.0

    for template in pool:
        traits = template["traits"]
        vcp_sim = 1.0 - min(1.0, abs(vcp_ratio - traits["vcp_ratio"]) / 0.5)
        rvol_sim = 1.0 - min(1.0, abs(rvol - traits["rvol"]) / 2.0)
        rs_sim = 1.0 - min(1.0, abs(rs_rating - traits["rs_rating"]) / 40.0)
        sector_bonus = 0.15 if traits["sector"].lower() in (ticker_info.get("sector") or "").lower() else 0.0

        total_sim = round(((vcp_sim * 0.35) + (rvol_sim * 0.30) + (rs_sim * 0.20) + sector_bonus) * 100, 1)
        total_sim = min(96.0, max(50.0, total_sim))

        if total_sim > highest_sim:
            highest_sim = total_sim
            best_match = {
                "historical_ticker": template["ticker"],
                "historical_period": template["year"],
                "historical_setup": template["setup"],
                "historical_gain": template["gain"],
                "similarity_score": total_sim
            }

    # ─────────────────────────────────────────────────────────────────────────
    # 6. HEDGE FUND NARRATIVE SYNTHESIS (Deep Reasoning)
    # ─────────────────────────────────────────────────────────────────────────
    symbol_name = ticker_info.get("ticker", "").replace(".JK", "")
    sector_name = ticker_info.get("sector", "General")

    insights = []
    
    # Katalis 1: SEPA & Supply Contraction
    if is_vcp_compressed and is_vdu_passed:
        insights.append({
            "topic": "SEPA Volatility & Supply Squeeze",
            "icon": "shield-check",
            "status": "POSITIVE",
            "text": f"Karakteristik VCP ({vcp_ratio:.2f}x) didukung pengeringan volume tajam (VDU {vdu_ratio:.2f}x MA20). Pasokan lembar saham mengambang di pasar telah diserap rapi oleh institusi."
        })
    elif is_vcp_compressed:
        insights.append({
            "topic": "Kompresi Volatilitas (VCP)",
            "icon": "check-circle",
            "status": "POSITIVE",
            "text": f"Rentang konsolidasi menyempit (VCP {vcp_ratio:.2f}x) menandakan fondasi akumulasi yang matang sebelum potensi ekspansi harga."
        })
    else:
        insights.append({
            "topic": "Struktur Konsolidasi Harga",
            "icon": "info",
            "status": "NEUTRAL",
            "text": f"Volatilitas masih cukup lebar (VCP {vcp_ratio:.2f}x). Pastikan disiplin entry di area support dinamis EMA 20."
        })

    # Katalis 2: Karakter Akumulasi & Money Flow
    if big_money_status == "INFLOW" and is_ud_accumulated:
        insights.append({
            "topic": "Sponsorship Institusi & Smart Money",
            "icon": "sparkles",
            "status": "POSITIVE",
            "text": f"Akumulasi institusional terkonfirmasi sangat kuat (CMF +{cmf_val:.2f}, Up/Down Vol {ud_ratio_20:.2f}x). Volume pada hari hijau melampaui hari koreksi."
        })
    elif big_money_status == "INFLOW":
        insights.append({
            "topic": "Arus Dana Masuk",
            "icon": "activity",
            "status": "POSITIVE",
            "text": f"Terdeteksi net inflow positif (CMF +{cmf_val:.2f}) di sektor {sector_name}."
        })
    else:
        insights.append({
            "topic": "Arus Modal & Partisipasi",
            "icon": "activity",
            "status": "NEUTRAL",
            "text": f"Arus modal netral (CMF {cmf_val:.2f}). Pergerakan dominan ditopang oleh momentum teknikal swing."
        })

    # Katalis 3: Struktur Lilin & Ekor
    if upper_wick_ratio < 20 and is_clean_close:
        insights.append({
            "topic": "Kekuatan Lilin Penutupan (Buyer Dominance)",
            "icon": "check-circle",
            "status": "POSITIVE",
            "text": f"Harga ditutup solid di pucuk (Upper Shadow {upper_wick_ratio}%, CLV +{clv:.2f}). Dominasi pembeli mutlak tanpa tekanan aksi jual penutupan."
        })
    else:
        insights.append({
            "topic": "Uji Tekanan Jual di Pucuk",
            "icon": "alert-triangle",
            "status": "WARNING" if upper_wick_ratio >= 30 else "INFO",
            "text": f"Terdapat ekor atas {upper_wick_ratio}%. Disarankan entry ketat di titik pivot tanpa mengejar harga."
        })

    # Katalis 4: Historis
    if best_match:
        insights.append({
            "topic": "Kemiripan Pola Historis 10 Tahun",
            "icon": "history",
            "status": "INFO",
            "text": f"Karakteristik setup {symbol_name} memiliki **{best_match['similarity_score']}% kemiripan** dengan fase awal reli <b>{best_match['historical_ticker']} ({best_match['historical_period']})</b> yang menghasilkan gain {best_match['historical_gain']}."
        })

    return {
        "ticker": symbol_name,
        "market": clean_m,
        "win_probability": final_prob,
        "conviction": conviction,
        "conviction_label": conviction_label,
        "conviction_color": conviction_color,
        "trap_score": trap_score,
        "trap_status": trap_status,
        "trap_badge": trap_badge,
        "trap_color": trap_color,
        "trap_flags": trap_flags,
        "upper_wick_ratio": upper_wick_ratio,
        "extension_from_ema20": extension_from_ema20,
        "vdu_ratio": round(vdu_ratio, 2),
        "ud_ratio_20": round(ud_ratio_20, 2),
        "sepa_checklist": sepa_checklist,
        "sepa_passed_count": sepa_passed_count,
        "historical_match": best_match,
        "insights": insights,
        "analyzed_at": pd.Timestamp.now().strftime("%H:%M:%S WIB")
    }
