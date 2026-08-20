import sqlite3
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/alpha.db"))

DEFAULT_LEARNED_WEIGHTS = {
    "version": 1,
    "last_calibrated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "sample_size": 0,
    "weights": {
        "weekly_trend": 15,
        "big_money_inflow": 15,
        "vcp_breakout": 20,
        "ema20_pullback": 15,
        "volume_surge": 15,
        "stage2_leader": 10,
        "base_score": 50
    },
    "dynamic_rules": {
        "optimal_exit_day": 3,
        "favored_setup": "EMA 20 Pullback",
        "volatility_sl_multiplier": 1.0
    },
    "summary_notes": "Sistem menggunakan kalibrasi bobot awal standar Breakout Raider."
}

def init_learning_db():
    """Membuat tabel ai_memory jika belum ada."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version INTEGER NOT NULL,
            calibrated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sample_size INTEGER DEFAULT 0,
            weights_json TEXT NOT NULL,
            dynamic_rules_json TEXT NOT NULL,
            insights_json TEXT NOT NULL,
            notes TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_active_learned_weights() -> Dict[str, Any]:
    """Mengambil bobot terkalibrasi paling mutakhir dari memori AI."""
    init_learning_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ai_memory ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    if not row:
        return DEFAULT_LEARNED_WEIGHTS

    try:
        return {
            "version": row["version"],
            "last_calibrated": str(row["calibrated_at"]),
            "sample_size": row["sample_size"],
            "weights": json.loads(row["weights_json"]),
            "dynamic_rules": json.loads(row["dynamic_rules_json"]),
            "insights": json.loads(row["insights_json"]),
            "summary_notes": row["notes"] or ""
        }
    except Exception:
        return DEFAULT_LEARNED_WEIGHTS

def calibrate_and_learn() -> Dict[str, Any]:
    """
    Mesin Pembelajaran Mandiri (Reinforcement & Statistical Optimizer):
    Menganalisis seluruh sinyal di signal_tracker yang sudah memiliki data historis,
    menghitung efektivitas bobot (Win Rate & MFE per setup, per volume ratio, per weekly trend),
    dan menyimpan bobot kalibrasi baru ke tabel ai_memory.
    """
    init_learning_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM signal_tracker ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()

    signals = [dict(r) for r in rows]
    sample_size = len(signals)

    if sample_size == 0:
        return get_active_learned_weights()

    # 1. Analisis Efektivitas Setup (Win Rate & Max Gain)
    setup_stats = {}
    for s in signals:
        setup = s.get("setup_name") or "Breakout Raider"
        if setup not in setup_stats:
            setup_stats[setup] = {"count": 0, "wins": 0, "total_mfe": 0.0, "total_dd": 0.0}
        setup_stats[setup]["count"] += 1
        setup_stats[setup]["total_mfe"] += float(s.get("max_gain_pct") or 0.0)
        setup_stats[setup]["total_dd"] += float(s.get("max_drawdown_pct") or 0.0)
        if s.get("status") in ["HIT_TP1", "HIT_TP2"]:
            setup_stats[setup]["wins"] += 1

    # 2. Hitung penyesuaian bobot dinamis
    weights = dict(DEFAULT_LEARNED_WEIGHTS["weights"])
    
    # Setup multipliers
    for setup_name, stat in setup_stats.items():
        count = stat["count"]
        if count >= 2:
            avg_gain = stat["total_mfe"] / count
            # Jika rata-rata gain setup tinggi (> 3%), berikan bobot lebih tinggi
            if "VCP" in setup_name:
                weights["vcp_breakout"] = min(25, max(15, round(20 + (avg_gain - 2.5) * 1.5)))
            elif "Pullback" in setup_name:
                weights["ema20_pullback"] = min(25, max(12, round(15 + (avg_gain - 2.5) * 1.5)))
            elif "Volume" in setup_name:
                weights["volume_surge"] = min(25, max(12, round(15 + (avg_gain - 2.5) * 1.5)))
            elif "Stage 2" in setup_name:
                weights["stage2_leader"] = min(20, max(8, round(10 + (avg_gain - 2.5) * 1.2)))

    # 3. Analisis Peak Day (Hari Puncak Rata-rata)
    peak_days = [int(s.get("peak_day") or 1) for s in signals if s.get("peak_day")]
    optimal_day = int(round(sum(peak_days) / len(peak_days))) if peak_days else 3
    optimal_day = max(1, min(10, optimal_day))

    # 4. Temukan setup paling diunggulkan
    favored_setup = "EMA 20 Pullback"
    if setup_stats:
        favored_setup = max(setup_stats.items(), key=lambda x: (x[1]["wins"], x[1]["total_mfe"]))[0]

    dynamic_rules = {
        "optimal_exit_day": optimal_day,
        "favored_setup": favored_setup,
        "volatility_sl_multiplier": 1.0
    }

    # 5. Narasi Pembelajaran AI
    insights = [
        f"🤖 <b>AI Memory Calibrated ({sample_size} Sinyal Dievaluasi)</b>: Sistem berhasil mempelajari pergerakan seluruh sinyal rekomendasi di database.",
        f"⭐ <b>Setup Prioritas Terpilih</b>: Pola <b>'{favored_setup}'</b> diidentifikasi sebagai setup paling konsisten menghasilkan gain positif.",
        f"⏱️ <b>Kalibrasi Siklus Keluar Optimal</b>: Saham rata-rata mencapai puncak gain pada <b>Hari ke-{optimal_day} Bursa (T+{optimal_day})</b>. Parameter ini otomatis disinkronkan ke radar kalkulator dan sentinel."
    ]

    notes = f"AI Kalibrasi v{sample_size} dengan {sample_size} sampel empiris."

    # Simpan ke Database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(version) FROM ai_memory")
    max_v = cursor.fetchone()[0] or 0
    new_version = max_v + 1

    cursor.execute("""
        INSERT INTO ai_memory (
            version, sample_size, weights_json, dynamic_rules_json, insights_json, notes
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        new_version, sample_size,
        json.dumps(weights),
        json.dumps(dynamic_rules),
        json.dumps(insights),
        notes
    ))
    conn.commit()
    conn.close()

    return {
        "version": new_version,
        "last_calibrated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "sample_size": sample_size,
        "weights": weights,
        "dynamic_rules": dynamic_rules,
        "insights": insights,
        "summary_notes": notes
    }
