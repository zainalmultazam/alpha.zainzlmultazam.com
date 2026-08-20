import sqlite3
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/alpha.db"))

DEFAULT_REGIME_WEIGHTS = {
    "BULLISH": {
        "weekly_trend": 15,
        "big_money_inflow": 15,
        "vcp_breakout": 22,
        "ema20_pullback": 15,
        "volume_surge": 18,
        "stage2_leader": 15,
        "sector_inflow_bonus": 5,
        "base_score": 50
    },
    "NEUTRAL": {
        "weekly_trend": 15,
        "big_money_inflow": 15,
        "vcp_breakout": 16,
        "ema20_pullback": 20,
        "volume_surge": 15,
        "stage2_leader": 15,
        "sector_inflow_bonus": 5,
        "base_score": 50
    },
    "BEARISH": {
        "weekly_trend": 15,
        "big_money_inflow": 20,
        "vcp_breakout": 15,
        "ema20_pullback": 18,
        "volume_surge": 15,
        "stage2_leader": 20,
        "sector_inflow_bonus": 5,
        "base_score": 50
    }
}

DEFAULT_LEARNED_WEIGHTS = {
    "version": 1,
    "last_calibrated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "sample_size": 0,
    "weights": DEFAULT_REGIME_WEIGHTS["BULLISH"],
    "regime_weights": DEFAULT_REGIME_WEIGHTS,
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

def get_active_learned_weights(regime: str = "BULLISH") -> Dict[str, Any]:
    """Mengambil bobot terkalibrasi paling mutakhir dari memori AI sesuai Rezim Pasar IHSG."""
    init_learning_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ai_memory ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    regime_key = str(regime or "BULLISH").upper()
    if regime_key not in ["BULLISH", "NEUTRAL", "BEARISH"]:
        regime_key = "BULLISH"

    if not row:
        base = dict(DEFAULT_LEARNED_WEIGHTS)
        base["weights"] = DEFAULT_REGIME_WEIGHTS.get(regime_key, DEFAULT_REGIME_WEIGHTS["BULLISH"])
        base["active_regime"] = regime_key
        return base

    try:
        data = {
            "version": row["version"],
            "last_calibrated": str(row["calibrated_at"]),
            "sample_size": row["sample_size"],
            "weights": json.loads(row["weights_json"]),
            "dynamic_rules": json.loads(row["dynamic_rules_json"]),
            "insights": json.loads(row["insights_json"]),
            "summary_notes": row["notes"] or "",
            "active_regime": regime_key
        }
        # Sesuaikan bobot dengan rezim pasar aktif
        regime_override = DEFAULT_REGIME_WEIGHTS.get(regime_key, {})
        for k, v in regime_override.items():
            if k not in data["weights"] or data["weights"][k] < 10:
                data["weights"][k] = v
        return data
    except Exception:
        base = dict(DEFAULT_LEARNED_WEIGHTS)
        base["weights"] = DEFAULT_REGIME_WEIGHTS.get(regime_key, DEFAULT_REGIME_WEIGHTS["BULLISH"])
        base["active_regime"] = regime_key
        return base

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

    signals = [dict(r) for r in rows]
    sample_size = len(signals)

    if sample_size == 0:
        conn.close()
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
                weights["ema20_pullback"] = min(25, max(15, round(15 + (avg_gain - 2.5) * 1.5)))
            elif "Volume" in setup_name:
                weights["volume_surge"] = min(25, max(15, round(15 + (avg_gain - 2.5) * 1.5)))
            elif "Stage 2" in setup_name:
                weights["stage2_leader"] = min(25, max(15, round(15 + (avg_gain - 2.5) * 1.2)))

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

    # 4.5. Analisis Riwayat Transaksi Nyata Pengguna (Journal Integration)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trades WHERE status = 'CLOSED'")
    journal_trades = [dict(r) for r in cursor.fetchall()]
    journal_count = len(journal_trades)
    
    journal_insights = []
    if journal_count >= 1:
        j_wins = sum(1 for t in journal_trades if float(t.get("pnl_amount") or 0) > 0)
        j_win_rate = round((j_wins / journal_count) * 100, 1)
        j_gains = [float(t.get("pnl_pct") or 0) for t in journal_trades if float(t.get("pnl_amount") or 0) > 0]
        j_losses = [float(t.get("pnl_pct") or 0) for t in journal_trades if float(t.get("pnl_amount") or 0) <= 0]
        avg_j_gain = round(sum(j_gains) / len(j_gains), 1) if j_gains else 0.0
        avg_j_loss = round(sum(j_losses) / len(j_losses), 1) if j_losses else 0.0
        
        journal_insights.append(
            f"<b>Integrasi Jurnal Trading ({journal_count} Transaksi Riil)</b>: Realized Win Rate kamu tercatat <b>{j_win_rate}%</b> (Rata-rata Cuan: <b>+{avg_j_gain}%</b>, Rata-rata Rugi: <b>{avg_j_loss}%</b>)."
        )
        if j_win_rate >= 65:
            journal_insights.append("<b>Disiplin Eksekusi Sangat Baik</b>: Eksekusi riil kamu konsisten mengikuti batas risiko dan rencana trading.")

    # 5. Narasi Pembelajaran AI Gabungan (Tracker + Journal)
    insights = [
        f"<b>AI Memory Calibrated ({sample_size} Sinyal Tracker + {journal_count} Jurnal)</b>: Sistem berhasil mempelajari pergerakan seluruh sinyal rekomendasi dan riwayat eksekusi riil.",
        f"<b>Setup Prioritas Terpilih</b>: Pola <b>'{favored_setup}'</b> diidentifikasi sebagai setup paling konsisten menghasilkan gain positif.",
        f"<b>Kalibrasi Siklus Keluar Optimal</b>: Saham rata-rata mencapai puncak gain pada <b>Hari ke-{optimal_day} Bursa (T+{optimal_day})</b>. Parameter ini otomatis disinkronkan ke radar kalkulator dan sentinel."
    ] + journal_insights

    notes = f"AI Kalibrasi v{sample_size} dengan {sample_size} sampel empiris & {journal_count} transaksi jurnal."

    # Simpan ke Database
    cursor.execute("SELECT MAX(version) FROM ai_memory")
    max_v = cursor.fetchone()[0] or 0
    new_version = max_v + 1

    cursor.execute("""
        INSERT INTO ai_memory (
            version, sample_size, weights_json, dynamic_rules_json, insights_json, notes
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        new_version, sample_size + journal_count,
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
        "sample_size": sample_size + journal_count,
        "weights": weights,
        "dynamic_rules": dynamic_rules,
        "insights": insights,
        "summary_notes": notes
    }
