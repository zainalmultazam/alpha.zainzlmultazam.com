import sqlite3
import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from app.engine.journal import calculate_trading_days
from app.services.market_data import fetch_stock_df

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/alpha.db"))

def init_tracker_db():
    """Membuat tabel signal_tracker jika belum ada."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signal_tracker (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            signal_date TEXT NOT NULL,
            entry_price REAL NOT NULL,
            stop_loss REAL NOT NULL,
            tp1 REAL NOT NULL,
            tp2 REAL NOT NULL,
            pts_score REAL DEFAULT 0.0,
            setup_name TEXT,
            market_climate TEXT DEFAULT 'BULLISH',
            volume_ratio REAL DEFAULT 1.0,
            current_price REAL,
            max_gain_pct REAL DEFAULT 0.0,
            max_drawdown_pct REAL DEFAULT 0.0,
            current_gain_pct REAL DEFAULT 0.0,
            price_t1 REAL,
            price_t2 REAL,
            price_t3 REAL,
            price_t5 REAL,
            price_t10 REAL,
            status TEXT DEFAULT 'ACTIVE',
            days_tracked INTEGER DEFAULT 1,
            peak_day INTEGER DEFAULT 1,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracker_ticker_date ON signal_tracker(ticker, signal_date)")
    conn.commit()
    conn.close()

def record_signal_snapshot(scan_results: List[Dict[str, Any]], climate: str = "BULLISH") -> int:
    """Menyimpan snapshot saham rekomendasi yang lolos scanner/briefing ke database tanpa duplikasi di hari yang sama."""
    if not scan_results:
        return 0
    
    init_tracker_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    now_time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    inserted_count = 0
    
    for item in scan_results:
        ticker = item.get("ticker", "").upper().replace(".JK", "").strip()
        if not ticker:
            continue
            
        # Cek apakah sudah pernah tercatat pada tanggal hari ini
        cursor.execute("SELECT id FROM signal_tracker WHERE ticker = ? AND signal_date LIKE ?", (ticker, f"{today_str}%"))
        existing = cursor.fetchone()
        if existing:
            continue
            
        entry_price = float(item.get("price") or item.get("close") or item.get("entry_price") or 0.0)
        if entry_price <= 0:
            continue
            
        # Trading plan levels
        plan = item.get("trading_plan") or {}
        sl = float(plan.get("stop_loss") or item.get("stop_loss") or (entry_price * 0.96))
        tp1 = float(plan.get("tp1") or item.get("tp1") or (entry_price + 2 * (entry_price - sl)))
        tp2 = float(plan.get("tp2") or item.get("tp2") or (entry_price + 3.5 * (entry_price - sl)))
        pts = float(item.get("power_trend_score") or item.get("pts") or 70.0)
        setup_name = item.get("setup_type") or item.get("setup_name") or item.get("primary_setup") or "Breakout Raider"
        vol_ratio = float(item.get("volume_ratio") or item.get("vol_surge_ratio") or 1.0)
        
        cursor.execute("""
            INSERT INTO signal_tracker (
                ticker, signal_date, entry_price, stop_loss, tp1, tp2, 
                pts_score, setup_name, market_climate, volume_ratio, 
                current_price, max_gain_pct, max_drawdown_pct, current_gain_pct,
                status, days_tracked, peak_day
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, 0.0, 0.0, 'ACTIVE', 1, 1)
        """, (
            ticker, now_time_str, entry_price, sl, tp1, tp2,
            pts, setup_name, climate, vol_ratio, entry_price
        ))
        inserted_count += 1
        
    conn.commit()
    conn.close()
    return inserted_count

def update_tracked_signals() -> Dict[str, Any]:
    """Mengupdate pergerakan harga historis dan status seluruh sinyal yang sedang aktif dilacak (hingga 10 hari bursa)."""
    init_tracker_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM signal_tracker ORDER BY id DESC")
    rows = cursor.fetchall()
    
    updated_count = 0
    for row in rows:
        item = dict(row)
        sig_id = item["id"]
        ticker = item["ticker"]
        entry_price = float(item["entry_price"])
        sl = float(item["stop_loss"])
        tp1 = float(item["tp1"])
        tp2 = float(item["tp2"])
        sig_date_str = item["signal_date"][:10]
        
        days_held = calculate_trading_days(sig_date_str)
        
        try:
            # Ambil data candle harga saham sejak tanggal sinyal
            ticker_sym = ticker if ticker.endswith(".JK") else f"{ticker}.JK"
            df = fetch_stock_df(ticker_sym)
            if df is None or df.empty:
                continue
                
            # Filter bar sejak tanggal sinyal
            df_dates = df.index.strftime("%Y-%m-%d")
            post_signal_df = df[df_dates >= sig_date_str]
            
            if post_signal_df.empty:
                continue
                
            closes = post_signal_df["Close"].tolist()
            highs = post_signal_df["High"].tolist()
            lows = post_signal_df["Low"].tolist()
            
            curr_price = float(closes[-1])
            curr_gain = round(((curr_price - entry_price) / entry_price) * 100, 2)
            
            # Hitung MFE (Max Favorable Excursion / Kenaikan Tertinggi)
            max_high = max(highs)
            max_gain = round(((max_high - entry_price) / entry_price) * 100, 2)
            
            # Hitung MAE (Max Adverse Excursion / Penurunan Terendah)
            min_low = min(lows)
            max_dd = round(((min_low - entry_price) / entry_price) * 100, 2)
            
            # Cari di hari ke berapa puncak gain tercapai
            peak_idx = highs.index(max_high) + 1  # 1-indexed
            
            # Catat harga T+1, T+2, T+3, T+5, T+10 jika sudah terlewati
            p_t1 = float(closes[1]) if len(closes) > 1 else None
            p_t2 = float(closes[2]) if len(closes) > 2 else None
            p_t3 = float(closes[3]) if len(closes) > 3 else None
            p_t5 = float(closes[5]) if len(closes) > 5 else None
            p_t10 = float(closes[10]) if len(closes) > 10 else None
            
            # Tentukan Status
            if max_high >= tp2:
                status = "HIT_TP2"
            elif max_high >= tp1:
                status = "HIT_TP1"
            elif min_low <= sl:
                status = "HIT_SL"
            elif days_held >= 10:
                status = "EXPIRED_STAGNANT"
            else:
                status = "ACTIVE"
                
            cursor.execute("""
                UPDATE signal_tracker 
                SET current_price = ?, max_gain_pct = ?, max_drawdown_pct = ?, current_gain_pct = ?,
                    price_t1 = ?, price_t2 = ?, price_t3 = ?, price_t5 = ?, price_t10 = ?,
                    status = ?, days_tracked = ?, peak_day = ?
                WHERE id = ?
            """, (
                curr_price, max_gain, max_dd, curr_gain,
                p_t1, p_t2, p_t3, p_t5, p_t10,
                status, min(days_held, 10), peak_idx, sig_id
            ))
            updated_count += 1
        except Exception as e:
            print(f"Error updating tracker for {ticker}: {e}")
            continue
            
    conn.commit()
    conn.close()
    return {"status": "success", "updated_count": updated_count}

def _calc_mean(lst: List[float]) -> float:
    return sum(lst) / len(lst) if lst else 0.0

def get_tracker_dashboard_data() -> Dict[str, Any]:
    """Mengambil seluruh data sinyal yang dilacak beserta kalkulasi agregasi riset kuantitatif dan analisis pola."""
    init_tracker_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM signal_tracker ORDER BY id DESC")
    rows = cursor.fetchall()
    signals = [dict(r) for r in rows]
    conn.close()
    
    total_signals = len(signals)
    if total_signals == 0:
        return {
            "signals": [],
            "summary": {
                "total_signals": 0,
                "active_signals": 0,
                "hit_tp_count": 0,
                "hit_sl_count": 0,
                "win_rate": 0.0,
                "avg_max_gain": 0.0,
                "avg_max_dd": 0.0,
                "avg_days_to_peak": 0.0
            },
            "pts_analysis": [],
            "setup_breakdown": [],
            "ai_insights": ["Belum ada data rekomendasi yang tercatat. Jalankan Screener atau tunggu Morning Briefing untuk memulai pelacakan otomatis."]
        }
        
    active_count = sum(1 for s in signals if s["status"] == "ACTIVE")
    hit_tp_count = sum(1 for s in signals if s["status"] in ["HIT_TP1", "HIT_TP2"])
    hit_sl_count = sum(1 for s in signals if s["status"] == "HIT_SL")
    
    closed_tested = hit_tp_count + hit_sl_count
    win_rate = round((hit_tp_count / closed_tested) * 100, 1) if closed_tested > 0 else round((hit_tp_count / max(1, total_signals)) * 100, 1)
    
    gains = [float(s.get("max_gain_pct") or 0.0) for s in signals]
    dds = [float(s.get("max_drawdown_pct") or 0.0) for s in signals]
    peak_days = [int(s.get("peak_day") or 1) for s in signals if s.get("status") in ["HIT_TP1", "HIT_TP2", "ACTIVE"]]
    
    avg_max_gain = round(_calc_mean(gains), 1)
    avg_max_dd = round(_calc_mean(dds), 1)
    avg_peak_day = round(_calc_mean(peak_days), 1) if peak_days else 1.0
    
    # ── PTS Tier Analysis ────────────────────────────────────────────────────
    tiers = [
        {"name": "PTS 90–100 (Ultra High)", "min_pts": 90.0, "max_pts": 100.0, "color": "emerald"},
        {"name": "PTS 80–89 (Prime Breakout)", "min_pts": 80.0, "max_pts": 89.9, "color": "blue"},
        {"name": "PTS 70–79 (Early Base)", "min_pts": 70.0, "max_pts": 79.9, "color": "amber"},
        {"name": "PTS < 70 (Speculative)", "min_pts": 0.0, "max_pts": 69.9, "color": "slate"}
    ]
    
    pts_analysis = []
    for t in tiers:
        matched = [s for s in signals if t["min_pts"] <= float(s.get("pts_score") or 0) <= t["max_pts"]]
        count = len(matched)
        if count > 0:
            m_gains = [float(s.get("max_gain_pct") or 0.0) for s in matched]
            m_dds = [float(s.get("max_drawdown_pct") or 0.0) for s in matched]
            m_tps = sum(1 for s in matched if s.get("status") in ["HIT_TP1", "HIT_TP2"])
            m_sls = sum(1 for s in matched if s.get("status") == "HIT_SL")
            m_total_closed = m_tps + m_sls
            m_win_rate = round((m_tps / m_total_closed) * 100, 1) if m_total_closed > 0 else round((m_tps / count) * 100, 1)
            
            pts_analysis.append({
                "tier_name": t["name"],
                "color": t["color"],
                "count": count,
                "avg_max_gain": round(_calc_mean(m_gains), 1),
                "avg_max_dd": round(_calc_mean(m_dds), 1),
                "win_rate": m_win_rate,
                "hit_tp_count": m_tps,
                "hit_sl_count": m_sls
            })
        else:
            pts_analysis.append({
                "tier_name": t["name"],
                "color": t["color"],
                "count": 0,
                "avg_max_gain": 0.0,
                "avg_max_dd": 0.0,
                "win_rate": 0.0,
                "hit_tp_count": 0,
                "hit_sl_count": 0
            })
            
    # ── Setup Breakdown Analysis ─────────────────────────────────────────────
    setup_groups = {}
    for s in signals:
        name = s.get("setup_name") or "General Breakout"
        if name not in setup_groups:
            setup_groups[name] = []
        setup_groups[name].append(s)
        
    setup_breakdown = []
    for name, group in setup_groups.items():
        count = len(group)
        g_gains = [float(s.get("max_gain_pct") or 0.0) for s in group]
        g_tps = sum(1 for s in group if s.get("status") in ["HIT_TP1", "HIT_TP2"])
        g_sls = sum(1 for s in group if s.get("status") == "HIT_SL")
        g_win_rate = round((g_tps / (g_tps + g_sls)) * 100, 1) if (g_tps + g_sls) > 0 else round((g_tps / count) * 100, 1)
        
        setup_breakdown.append({
            "setup_name": name,
            "count": count,
            "win_rate": g_win_rate,
            "avg_max_gain": round(_calc_mean(g_gains), 1) if g_gains else 0.0,
            "hit_tp_count": g_tps,
            "hit_sl_count": g_sls
        })
        
    setup_breakdown.sort(key=lambda x: (x["win_rate"], x["avg_max_gain"]), reverse=True)
    
    # ── AI Quantitative Pattern Insights ─────────────────────────────────────
    ai_insights = []
    
    tier_80_89 = next((p for p in pts_analysis if "80–89" in p["tier_name"]), None)
    tier_90_100 = next((p for p in pts_analysis if "90–100" in p["tier_name"]), None)
    
    if tier_80_89 and tier_90_100 and tier_80_89["count"] > 0 and tier_90_100["count"] > 0:
        if tier_80_89["avg_max_gain"] > tier_90_100["avg_max_gain"]:
            diff = round(tier_80_89["avg_max_gain"] - tier_90_100["avg_max_gain"], 1)
            ai_insights.append(
                f"🎯 <b>PTS 80–89 Mengungguli PTS 90–100</b>: Saham di tier 80–89 rata-rata menghasilkan Max Gain <b>+{tier_80_89['avg_max_gain']}%</b> (lebih tinggi +{diff}% dibanding tier 90–100). Ini membuktikan bahwa saham yang baru breakout dari base segar memiliki ruang lari lebih leluasa dibanding saham yang sudah hyper-extended."
            )
        elif tier_90_100["win_rate"] >= tier_80_89["win_rate"]:
            ai_insights.append(
                f"🚀 <b>Momentum Ultra-High PTS 90–100 Paling Konsisten</b>: Memiliki Win Rate tertinggi sebesar <b>{tier_90_100['win_rate']}%</b> dengan rata-rata kenaikan puncak <b>+{tier_90_100['avg_max_gain']}%</b>."
            )
    else:
        ai_insights.append(
            f"📊 <b>Karakteristik Sinyal Aktif</b>: Rata-rata potensi kenaikan puncak (*Max Gain*) seluruh sinyal mencapai <b>+{avg_max_gain}%</b> dengan risiko penurunan terburuk (*Max Drawdown*) rata-rata <b>{avg_max_dd}%</b>."
        )
        
    if avg_peak_day > 0:
        ai_insights.append(
            f"⏱️ <b>Waktu Puncak Keuntungan (*Peak Day*)</b>: Rata-rata puncak gain saham tercapai pada <b>Hari ke-{int(round(avg_peak_day))} Bursa (T+{int(round(avg_peak_day))})</b> sejak sinyal terbit. Disarankan mengamankan TP1 parsial di hari ke-3 s.d ke-4 bursa."
        )
        
    if setup_breakdown and setup_breakdown[0]["count"] >= 1:
        best_setup = setup_breakdown[0]
        ai_insights.append(
            f"⭐ <b>Pola Setup Terbaik</b>: Pola <b>'{best_setup['setup_name']}'</b> mencatatkan Win Rate tertinggi <b>{best_setup['win_rate']}%</b> dengan rata-rata Max Gain <b>+{best_setup['avg_max_gain']}%</b>."
        )

    return {
        "signals": signals,
        "summary": {
            "total_signals": total_signals,
            "active_signals": active_count,
            "hit_tp_count": hit_tp_count,
            "hit_sl_count": hit_sl_count,
            "win_rate": win_rate,
            "avg_max_gain": avg_max_gain,
            "avg_max_dd": avg_max_dd,
            "avg_days_to_peak": avg_peak_day
        },
        "pts_analysis": pts_analysis,
        "setup_breakdown": setup_breakdown,
        "ai_insights": ai_insights
    }
