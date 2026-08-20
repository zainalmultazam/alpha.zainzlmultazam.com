import sqlite3
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.services.market_data import fetch_stock_df, get_market_climate
from app.engine.sector import calculate_sector_rotation

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/alpha.db"))

def diagnose_failed_signal(signal: Dict[str, Any]) -> Dict[str, Any]:
    """
    Melakukan otopsi teknikal otomatis saat suatu sinyal menyentuh Stop Loss (HIT_SL).
    Menganalisis 4 faktor: Tekanan IHSG, Lonjakan Volume Distribusi, Arus Sektor, & Pola False Breakout.
    """
    ticker = signal.get("ticker", "").replace(".JK", "").strip()
    entry_price = float(signal.get("entry_price") or 0)
    current_price = float(signal.get("current_price") or 0)
    stop_loss = float(signal.get("stop_loss") or 0)
    setup_name = signal.get("setup_name") or "Breakout Raider"
    sig_date = signal.get("signal_date", "")[:10]

    # 1. Analisis Iklim Pasar IHSG saat ini
    climate = get_market_climate()
    regime = climate.get("regime", "BULLISH")
    ihsg_change = float(climate.get("change_pct", 0.0))

    # 2. Analisis Volume Breakdown Saham
    ticker_sym = f"{ticker}.JK" if not ticker.endswith(".JK") else ticker
    df = fetch_stock_df(ticker_sym)
    
    heavy_volume = False
    volume_ratio = 1.0
    if df is not None and len(df) >= 5:
        last_vol = float(df["Volume"].iloc[-1])
        ma_vol = float(df["Volume"].tail(20).mean())
        if ma_vol > 0:
            volume_ratio = round(last_vol / ma_vol, 2)
            heavy_volume = volume_ratio >= 1.4

    # 3. Analisis Sektor
    sector_data = calculate_sector_rotation()
    outflow_sectors = sector_data.get("top_outflow_sectors", [])

    # 4. Klasifikasi Akar Masalah (Root Cause Classification)
    if regime == "BEARISH" or ihsg_change < -0.8:
        root_cause = "MARKET_SHOCK_PRESSURE"
        cause_title = "Tekanan Anjloknya IHSG (Market Shock)"
        diagnosis_desc = f"Sinyal {ticker} gagal karena terseret penurunan IHSG ({ihsg_change}%). Kondisi umum bursa sedang Risk-Off sehingga aksi beli melemah."
        lesson = "Perketat aturan filter: Jangan entry agresif saat IHSG berada di bawah EMA 20."
        penalty_rule = {"rule_type": "MARKET_FILTER", "penalty": 10, "condition": "IHSG_UNDER_EMA20"}
    elif heavy_volume:
        root_cause = "HEAVY_DISTRIBUTION_DUMP"
        cause_title = "Distribusi Masif Bandar (Volume Spike)"
        diagnosis_desc = f"Penurunan harga disertai lonjakan volume buangan {volume_ratio}x lipat dari rata-rata 20 hari. Terjadi aksi *profit taking* cepat oleh institusi."
        lesson = "Tingkatkan konfirmasi volume: Hindari emiten yang volume bid-ask nya tidak seimbang saat breakout."
        penalty_rule = {"rule_type": "VOLUME_CONFIRMATION", "penalty": 10, "condition": "RVOL_SPIKE_AFTER_BREAKOUT"}
    else:
        root_cause = "FALSE_BREAKOUT_BULL_TRAP"
        cause_title = "False Breakout / Konsolidasi Tertunda"
        diagnosis_desc = f"Harga sempat menembus titik resistance namun gagal melanjutkan momentum naik (*failed follow-through*) dan kembali ke dalam area base."
        lesson = "Wajibkan jarak SL lebih adaptif dan tunggu retest support sebelum entry kedua."
        penalty_rule = {"rule_type": "SETUP_PENALTY", "penalty": 5, "condition": f"SETUP_{setup_name.upper().replace(' ', '_')}"}

    post_mortem = {
        "ticker": ticker,
        "signal_date": sig_date,
        "entry_price": entry_price,
        "exit_price": current_price,
        "loss_pct": round(((current_price - entry_price) / entry_price) * 100, 2) if entry_price > 0 else -4.0,
        "root_cause": root_cause,
        "cause_title": cause_title,
        "diagnosis": diagnosis_desc,
        "lesson": lesson,
        "penalty_rule": penalty_rule,
        "diagnosed_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    return post_mortem

def get_all_post_mortems() -> List[Dict[str, Any]]:
    """Mengambil seluruh riwayat sinyal gagal beserta hasil otopsi AI."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM signal_tracker WHERE status = 'HIT_SL' ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        item = dict(r)
        # Jika sudah ada notes JSON tersimpan
        notes = item.get("notes") or ""
        if notes and notes.startswith("{") and "root_cause" in notes:
            try:
                results.append(json.loads(notes))
                continue
            except Exception:
                pass
        
        # Jika belum ada, diagnosa sekarang
        pm = diagnose_failed_signal(item)
        results.append(pm)

    return results
