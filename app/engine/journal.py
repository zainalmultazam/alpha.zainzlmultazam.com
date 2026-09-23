import sqlite3
import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/alpha.db"))

def calculate_trading_days(start_date_str: str, end_date_str: Optional[str] = None, market: str = "IDX") -> int:
    """Menghitung jumlah hari bursa aktif (Senin-Jumat dan non-tanggal merah) antara tanggal mulai dan selesai."""
    if not start_date_str:
        return 1
    try:
        s_date = datetime.strptime(start_date_str[:10], "%Y-%m-%d").date()
        if end_date_str:
            e_date = datetime.strptime(end_date_str[:10], "%Y-%m-%d").date()
        else:
            e_date = datetime.now().date()
        
        if s_date > e_date:
            return 1
            
        from app.services.market_data import FIXED_HOLIDAYS
        cur = s_date
        trading_days = 0
        while cur <= e_date:
            # 1. Abaikan Sabtu (5) dan Minggu (6)
            if cur.weekday() < 5:
                # 2. Abaikan Tanggal Merah / Libur Bursa Resmi
                if (cur.month, cur.day) not in FIXED_HOLIDAYS:
                    trading_days += 1
            cur += timedelta(days=1)
        return max(1, trading_days)
    except Exception:
        return 1

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            entry_date TEXT NOT NULL,
            entry_price REAL NOT NULL,
            stop_loss REAL NOT NULL,
            target_price REAL NOT NULL,
            lots INTEGER NOT NULL,
            setup_name TEXT,
            status TEXT DEFAULT 'OPEN',
            exit_date TEXT,
            exit_price REAL,
            pnl_amount REAL,
            pnl_pct REAL,
            notes TEXT,
            exit_reason TEXT DEFAULT 'MANUAL',
            market TEXT DEFAULT 'IDX'
        )
    """)
    # Check if exit_reason, market, gross_pnl_amount, gross_pnl_pct, and fee_amount exist
    cursor.execute("PRAGMA table_info(trades)")
    columns = [row[1] for row in cursor.fetchall()]
    if "exit_reason" not in columns:
        try:
            cursor.execute("ALTER TABLE trades ADD COLUMN exit_reason TEXT DEFAULT 'MANUAL'")
        except Exception:
            pass
    if "market" not in columns:
        try:
            cursor.execute("ALTER TABLE trades ADD COLUMN market TEXT DEFAULT 'IDX'")
        except Exception:
            pass
    if "gross_pnl_amount" not in columns:
        try:
            cursor.execute("ALTER TABLE trades ADD COLUMN gross_pnl_amount REAL")
        except Exception:
            pass
    if "gross_pnl_pct" not in columns:
        try:
            cursor.execute("ALTER TABLE trades ADD COLUMN gross_pnl_pct REAL")
        except Exception:
            pass
    if "fee_amount" not in columns:
        try:
            cursor.execute("ALTER TABLE trades ADD COLUMN fee_amount REAL")
        except Exception:
            pass
    if "ai_coach_verdict" not in columns:
        try:
            cursor.execute("ALTER TABLE trades ADD COLUMN ai_coach_verdict TEXT")
        except Exception:
            pass
    if "ai_coach_notes" not in columns:
        try:
            cursor.execute("ALTER TABLE trades ADD COLUMN ai_coach_notes TEXT")
        except Exception:
            pass
    conn.commit()
    conn.close()

def generate_ai_post_mortem(
    trade: Dict[str, Any],
    exit_price: float,
    net_pnl_pct: float,
    trading_days: int
) -> Dict[str, str]:
    """Menghasilkan diagnosa audit dan catatan evaluasi otomatis AI Coach."""
    entry = float(trade.get("entry_price") or exit_price)
    sl = float(trade.get("stop_loss") or entry * 0.95)
    tp = float(trade.get("target_price") or entry * 1.10)
    setup = trade.get("setup_name") or "Momentum Breakout"
    planned_risk_pct = round(((entry - sl) / entry) * 100, 1) if entry > 0 else 5.0
    
    is_win = net_pnl_pct > 0
    if is_win:
        if net_pnl_pct >= 7.5 or exit_price >= (tp * 0.98):
            verdict = "Target 2R Tercapai"
            notes = f"Setup {setup} berhasil mencapai target (+{net_pnl_pct:.1f}%) dalam {trading_days} hari bursa. Disiplin entry di area kompresi membuahkan hasil optimal."
        else:
            verdict = "Tactical Quick Profit"
            notes = f"Mengamankan profit +{net_pnl_pct:.1f}% dalam {trading_days} hari bursa. Rotasi modal cepat menjaga kestabilan kurva portofolio."
    else:
        if abs(net_pnl_pct) <= (planned_risk_pct + 1.2):
            verdict = "Cut Loss Terkontrol"
            notes = f"Kerugian dipangkas di {net_pnl_pct:.1f}% sesuai batas risiko awal ({planned_risk_pct}%). Disiplin ini melindungi modal Anda dari penurunan lebih dalam."
        elif trading_days > 5:
            verdict = "Evaluasi Waktu Hold (>T+3)"
            notes = f"Posisi ditahan {trading_days} hari bursa dengan hasil {net_pnl_pct:.1f}%. Evaluasi: Hindari menahan posisi melemah terlalu lama melebihi siklus T+3."
        else:
            verdict = "Evaluasi Disiplin Stop Loss"
            notes = f"Kerugian {net_pnl_pct:.1f}% melebihi rencana awal ({planned_risk_pct}%). Perketat disiplin eksekusi Stop Loss di level teknikal."
            
    return {
        "ai_coach_verdict": verdict,
        "ai_coach_notes": notes
    }

def calculate_trade_pnl(
    entry_price: float,
    exit_price: float,
    lots: float,
    market: str = "IDX",
    buy_fee_rate: Optional[float] = None,
    sell_fee_rate: Optional[float] = None
) -> Dict[str, float]:
    """
    Menghitung Gross PnL dan Net Realized PnL setelah dipotong komisi broker dan pajak bursa.
    Default Rate:
    - IDX: Beli 0.15% (0.0015), Jual 0.25% (0.0025) -> Broker fee + Levy + PPh final 0.1% + PPN
    - US: Beli 0.10% (0.0010), Jual 0.10% (0.0010)
    """
    clean_m = (market or "IDX").upper().strip()
    multiplier = 100 if clean_m == "IDX" else 1
    shares = float(lots) * multiplier
    
    if clean_m == "US":
        b_rate = buy_fee_rate if buy_fee_rate is not None else 0.0010
        s_rate = sell_fee_rate if sell_fee_rate is not None else 0.0010
    else:
        b_rate = buy_fee_rate if buy_fee_rate is not None else 0.0015
        s_rate = sell_fee_rate if sell_fee_rate is not None else 0.0025

    gross_buy = float(entry_price) * shares
    gross_sell = float(exit_price) * shares
    gross_pnl = gross_sell - gross_buy
    gross_pnl_pct = ((float(exit_price) - float(entry_price)) / float(entry_price) * 100) if float(entry_price) > 0 else 0.0

    buy_fee = gross_buy * b_rate
    sell_fee = gross_sell * s_rate
    total_fee = buy_fee + sell_fee

    net_buy = gross_buy + buy_fee
    net_sell = gross_sell - sell_fee
    net_pnl = net_sell - net_buy
    net_pnl_pct = (net_pnl / net_buy * 100) if net_buy > 0 else 0.0

    return {
        "gross_pnl_amount": round(gross_pnl, 2),
        "gross_pnl_pct": round(gross_pnl_pct, 2),
        "buy_fee": round(buy_fee, 2),
        "sell_fee": round(sell_fee, 2),
        "total_fee": round(total_fee, 2),
        "fee_amount": round(total_fee, 2),
        "net_pnl_amount": round(net_pnl, 2),
        "net_pnl_pct": round(net_pnl_pct, 2),
        "pnl_amount": round(net_pnl, 2),
        "pnl_pct": round(net_pnl_pct, 2),
    }

def log_trade(ticker: str, entry_price: float, stop_loss: float, target_price: float, lots: float, setup_name: str = "Manual / Bot", market: str = "IDX") -> int:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    clean_market = (market or "IDX").upper().strip()
    clean_ticker = ticker.upper().replace(".JK", "").strip() if clean_market == "IDX" else ticker.upper().strip()
    cursor.execute("""
        INSERT INTO trades (ticker, entry_date, entry_price, stop_loss, target_price, lots, setup_name, status, exit_reason, market)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN', 'MANUAL', ?)
    """, (clean_ticker, datetime.now().strftime("%Y-%m-%d %H:%M"), float(entry_price), float(stop_loss), float(target_price), float(lots), setup_name, clean_market))
    trade_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return trade_id

def _enrich_trade(t: Dict[str, Any]) -> Dict[str, Any]:
    """Menambahkan kalkulasi hari bursa, status holding, fee bursa, dan time-stop flag."""
    entry_date = t.get("entry_date") or ""
    exit_date = t.get("exit_date")
    holding_days = calculate_trading_days(entry_date, exit_date)
    t["holding_days"] = holding_days

    # Hitung & sinkronisasi Net vs Gross PnL untuk transaksi CLOSED
    if t.get("status") == "CLOSED" and t.get("exit_price") is not None:
        pnl_calc = calculate_trade_pnl(
            entry_price=float(t.get("entry_price") or 0.0),
            exit_price=float(t.get("exit_price") or 0.0),
            lots=float(t.get("lots") or 0.0),
            market=t.get("market") or "IDX"
        )
        t["gross_pnl_amount"] = pnl_calc["gross_pnl_amount"]
        t["gross_pnl_pct"] = pnl_calc["gross_pnl_pct"]
        t["fee_amount"] = pnl_calc["total_fee"]
        t["buy_fee"] = pnl_calc["buy_fee"]
        t["sell_fee"] = pnl_calc["sell_fee"]
        t["net_pnl_amount"] = pnl_calc["net_pnl_amount"]
        t["net_pnl_pct"] = pnl_calc["net_pnl_pct"]
        # Standard pnl_amount & pnl_pct reflect realistic net money in bank
        t["pnl_amount"] = pnl_calc["net_pnl_amount"]
        t["pnl_pct"] = pnl_calc["net_pnl_pct"]

    # Floating PnL for open trades if available or rough estimate
    is_open = (t.get("status") == "OPEN")
    if is_open:
        entry_p = float(t.get("entry_price") or 0.0)
        lots_qty = float(t.get("lots") or 0.0)
        market_type = (t.get("market") or "IDX").upper()
        shares_qty = lots_qty if market_type == "US" else lots_qty * 100
        
        t["deployed_capital"] = entry_p * shares_qty
        
        # Live Price Fetching (with fallback to entry_price)
        current_p = entry_p
        try:
            from app.services.market_data import fetch_stock_df
            df = fetch_stock_df(t["ticker"], period="5d", market=market_type)
            if df is not None and not df.empty and "Close" in df.columns:
                current_p = float(df["Close"].iloc[-1])
        except Exception:
            current_p = entry_p

        t["current_price"] = current_p
        float_gain_pct = round(((current_p - entry_p) / entry_p) * 100, 2) if entry_p > 0 else 0.0
        float_gain_amount = round((current_p - entry_p) * shares_qty, 2)
        t["unrealized_pnl_pct"] = float_gain_pct
        t["unrealized_pnl_amount"] = float_gain_amount
        t["pnl_pct"] = float_gain_pct
        t["pnl_amount"] = float_gain_amount

    pnl_pct = float(t.get("pnl_pct") or 0.0)
    
    # Stagnant criteria: > 7 trading days and floating between -2.0% and +3.0%
    is_stagnant = is_open and (holding_days > 7) and (-2.0 <= pnl_pct <= 3.0)
    t["is_stagnant"] = is_stagnant

    if is_stagnant:
        t["holding_status"] = "stagnant"
    elif holding_days >= 5:
        t["holding_status"] = "evaluating"
    else:
        t["holding_status"] = "active"
        
    if not t.get("exit_reason"):
        t["exit_reason"] = "MANUAL"
    if not t.get("market"):
        t["market"] = "IDX"
    
    if t.get("market") == "US":
        try:
            from app.engine.earnings_us import get_us_earnings_info
            e_info = get_us_earnings_info(t["ticker"])
            t["earnings_info"] = e_info
            t["earnings_badge"] = e_info.get("badge_text")
            t["earnings_color"] = e_info.get("badge_color")
            t["is_earnings_blackout"] = e_info.get("is_blackout", False)
            t["earnings_guidance"] = e_info.get("guidance")
            t["days_until_earnings"] = e_info.get("days_until")
            t["earnings_date"] = e_info.get("earnings_date")
        except Exception:
            pass

    return t

def get_all_trades(market: str = "IDX") -> List[Dict[str, Any]]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    clean_m = (market or "IDX").upper().strip()
    cursor.execute("SELECT * FROM trades WHERE market = ? OR (market IS NULL AND ? = 'IDX') ORDER BY id DESC", (clean_m, clean_m))
    rows = cursor.fetchall()
    trades = [_enrich_trade(dict(row)) for row in rows]
    conn.close()
    return trades

def get_open_trades(market: str = "IDX") -> List[Dict[str, Any]]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    clean_m = (market or "IDX").upper().strip()
    cursor.execute("SELECT * FROM trades WHERE status = 'OPEN' AND (market = ? OR (market IS NULL AND ? = 'IDX')) ORDER BY id DESC", (clean_m, clean_m))
    rows = cursor.fetchall()
    trades = [_enrich_trade(dict(row)) for row in rows]
    conn.close()
    return trades

def close_trade(
    trade_id: int, 
    exit_price: float, 
    notes: str = "", 
    exit_reason: str = "MANUAL",
    buy_fee_pct: Optional[float] = None,
    sell_fee_pct: Optional[float] = None
) -> bool:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    
    trade = dict(row)
    entry_price = float(trade["entry_price"])
    lots = float(trade["lots"])
    trade_market = (trade.get("market") or "IDX").upper()
    
    b_rate = (buy_fee_pct / 100.0) if (buy_fee_pct is not None and buy_fee_pct >= 0) else None
    s_rate = (sell_fee_pct / 100.0) if (sell_fee_pct is not None and sell_fee_pct >= 0) else None
    pnl_calc = calculate_trade_pnl(entry_price, float(exit_price), lots, market=trade_market, buy_fee_rate=b_rate, sell_fee_rate=s_rate)

    t_days = calculate_trading_days(trade.get("entry_date", ""))
    coach = generate_ai_post_mortem(trade, float(exit_price), pnl_calc["net_pnl_pct"], t_days)

    cursor.execute("""
        UPDATE trades 
        SET status = 'CLOSED', exit_date = ?, exit_price = ?, 
            pnl_amount = ?, pnl_pct = ?, gross_pnl_amount = ?, gross_pnl_pct = ?, fee_amount = ?,
            notes = ?, exit_reason = ?, ai_coach_verdict = ?, ai_coach_notes = ?
        WHERE id = ?
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M"), 
        float(exit_price), 
        pnl_calc["net_pnl_amount"], 
        pnl_calc["net_pnl_pct"],
        pnl_calc["gross_pnl_amount"],
        pnl_calc["gross_pnl_pct"],
        pnl_calc["total_fee"],
        notes, 
        exit_reason,
        coach["ai_coach_verdict"],
        coach["ai_coach_notes"],
        trade_id
    ))
    conn.commit()
    conn.close()
    return True

def close_open_trade_by_ticker(
    ticker: str, 
    exit_price: float, 
    notes: str = "", 
    exit_reason: str = "MANUAL", 
    market: str = "IDX",
    buy_fee_pct: Optional[float] = None,
    sell_fee_pct: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    """Menutup posisi OPEN terakhir berdasarkan simbol ticker."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    clean_m = (market or "IDX").upper().strip()
    clean_ticker = ticker.upper().replace(".JK", "").strip() if clean_m == "IDX" else ticker.upper().strip()
    cursor.execute("SELECT * FROM trades WHERE ticker = ? AND status = 'OPEN' AND (market = ? OR (market IS NULL AND ? = 'IDX')) ORDER BY id DESC LIMIT 1", (clean_ticker, clean_m, clean_m))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    
    trade = dict(row)
    trade_id = trade["id"]
    entry_price = float(trade["entry_price"])
    lots = float(trade["lots"])
    
    b_rate = (buy_fee_pct / 100.0) if (buy_fee_pct is not None and buy_fee_pct >= 0) else None
    s_rate = (sell_fee_pct / 100.0) if (sell_fee_pct is not None and sell_fee_pct >= 0) else None
    pnl_calc = calculate_trade_pnl(entry_price, float(exit_price), lots, market=clean_m, buy_fee_rate=b_rate, sell_fee_rate=s_rate)

    t_days = calculate_trading_days(trade.get("entry_date", ""))
    coach = generate_ai_post_mortem(trade, float(exit_price), pnl_calc["net_pnl_pct"], t_days)

    cursor.execute("""
        UPDATE trades 
        SET status = 'CLOSED', exit_date = ?, exit_price = ?, 
            pnl_amount = ?, pnl_pct = ?, gross_pnl_amount = ?, gross_pnl_pct = ?, fee_amount = ?,
            notes = ?, exit_reason = ?, ai_coach_verdict = ?, ai_coach_notes = ?
        WHERE id = ?
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M"), 
        float(exit_price), 
        pnl_calc["net_pnl_amount"], 
        pnl_calc["net_pnl_pct"],
        pnl_calc["gross_pnl_amount"],
        pnl_calc["gross_pnl_pct"],
        pnl_calc["total_fee"],
        notes, 
        exit_reason,
        coach["ai_coach_verdict"],
        coach["ai_coach_notes"],
        trade_id
    ))
    conn.commit()
    conn.close()
    
    trade["exit_price"] = exit_price
    trade["pnl_amount"] = pnl_calc["net_pnl_amount"]
    trade["pnl_pct"] = pnl_calc["net_pnl_pct"]
    trade["gross_pnl_amount"] = pnl_calc["gross_pnl_amount"]
    trade["gross_pnl_pct"] = pnl_calc["gross_pnl_pct"]
    trade["fee_amount"] = pnl_calc["total_fee"]
    trade["exit_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    trade["exit_reason"] = exit_reason
    return _enrich_trade(trade)

def get_journal_stats(market: str = "IDX") -> Dict[str, Any]:
    trades = get_all_trades(market=market)
    total_trades = len(trades)
    open_trades = [t for t in trades if t["status"] == "OPEN"]
    closed_trades = [t for t in trades if t["status"] == "CLOSED"]
    
    winning_trades = [t for t in closed_trades if (t.get("pnl_amount") or 0) > 0]
    losing_trades = [t for t in closed_trades if (t.get("pnl_amount") or 0) < 0]
    
    total_pnl = sum((t.get("pnl_amount") or 0) for t in closed_trades)
    total_gross_pnl = sum((t.get("gross_pnl_amount") or t.get("pnl_amount") or 0) for t in closed_trades)
    total_fees = sum((t.get("fee_amount") or 0) for t in closed_trades)
    win_rate = round((len(winning_trades) / len(closed_trades)) * 100, 1) if closed_trades else 0.0
    stagnant_count = sum(1 for t in open_trades if t.get("is_stagnant"))

    open_deployed_capital = sum(float(t.get("deployed_capital") or 0.0) for t in open_trades)
    open_floating_pnl = sum(float(t.get("unrealized_pnl_amount") or 0.0) for t in open_trades)
    open_floating_pct = round((open_floating_pnl / open_deployed_capital * 100), 2) if open_deployed_capital > 0 else 0.0

    r_multiples = []
    for t in closed_trades:
        e_p = float(t.get("entry_price") or 0.0)
        sl_p = float(t.get("stop_loss") or 0.0)
        exit_p = float(t.get("exit_price") or 0.0)
        risk_dist = max(0.01, e_p - sl_p)
        realized_r = (exit_p - e_p) / risk_dist
        r_multiples.append(realized_r)
    
    avg_rr = round(sum(r_multiples) / len(r_multiples), 1) if r_multiples else 2.0

    return {
        "total_trades": total_trades,
        "open_trades": len(open_trades),
        "closed_trades": len(closed_trades),
        "winning_trades": len(winning_trades),
        "losing_trades": len(losing_trades),
        "win_rate": win_rate,
        "avg_rr": avg_rr,
        "total_pnl": round(total_pnl, 2),
        "total_gross_pnl": round(total_gross_pnl, 2),
        "total_fees": round(total_fees, 2),
        "open_deployed_capital": round(open_deployed_capital, 2),
        "open_floating_pnl": round(open_floating_pnl, 2),
        "open_floating_pct": open_floating_pct,
        "stagnant_count": stagnant_count
    }

def update_trade(
    trade_id: int,
    lots: float,
    entry_price: float,
    stop_loss: float,
    target_price: float,
    setup_name: str = "",
    notes: str = "",
    exit_price: Optional[float] = None,
    exit_reason: Optional[str] = None,
    buy_fee_pct: Optional[float] = None,
    sell_fee_pct: Optional[float] = None
) -> bool:
    """Mengupdate data transaksi di database SQLite."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
        
    trade = dict(row)
    trade_market = (trade.get("market") or "IDX").upper()
    
    if trade["status"] == "CLOSED":
        real_exit_price = float(exit_price) if (exit_price is not None and str(exit_price).strip() != "") else float(trade.get("exit_price") or entry_price)
        real_exit_reason = exit_reason if (exit_reason is not None and str(exit_reason).strip() != "") else (trade.get("exit_reason") or "MANUAL")
        
        b_rate = (buy_fee_pct / 100.0) if (buy_fee_pct is not None and buy_fee_pct >= 0) else None
        s_rate = (sell_fee_pct / 100.0) if (sell_fee_pct is not None and sell_fee_pct >= 0) else None
        pnl_calc = calculate_trade_pnl(float(entry_price), real_exit_price, float(lots), market=trade_market, buy_fee_rate=b_rate, sell_fee_rate=s_rate)
        
        cursor.execute("""
            UPDATE trades
            SET lots = ?, entry_price = ?, stop_loss = ?, target_price = ?, setup_name = ?, notes = ?, 
                exit_price = ?, exit_reason = ?, pnl_amount = ?, pnl_pct = ?, gross_pnl_amount = ?, gross_pnl_pct = ?, fee_amount = ?
            WHERE id = ?
        """, (
            float(lots), 
            float(entry_price), 
            float(stop_loss), 
            float(target_price), 
            setup_name, 
            notes, 
            real_exit_price, 
            real_exit_reason, 
            pnl_calc["net_pnl_amount"], 
            pnl_calc["net_pnl_pct"],
            pnl_calc["gross_pnl_amount"],
            pnl_calc["gross_pnl_pct"],
            pnl_calc["total_fee"],
            trade_id
        ))
    else:
        cursor.execute("""
            UPDATE trades
            SET lots = ?, entry_price = ?, stop_loss = ?, target_price = ?, setup_name = ?, notes = ?
            WHERE id = ?
        """, (float(lots), float(entry_price), float(stop_loss), float(target_price), setup_name, notes, trade_id))
        
    conn.commit()
    conn.close()
    return True

def delete_trade(trade_id: int) -> bool:
    """Menghapus transaksi dari database berdasarkan ID."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def get_stock_sector(ticker: str, market: str = "IDX") -> str:
    """Mengambil sektor saham dari universe."""
    clean_sym = ticker.upper().replace(".JK", "").strip()
    try:
        if market == "IDX":
            from app.engine.universe import IDX_STOCKS
            for s in IDX_STOCKS:
                if s["ticker"].replace(".JK", "").upper() == clean_sym:
                    return s.get("sector", "Other")
        else:
            from app.engine.universe_us import UNIVERSE_US
            for s in UNIVERSE_US:
                if s["ticker"].upper() == clean_sym:
                    return s.get("sector", "Other")
    except Exception:
        pass
    return "Other"

def get_performance_metrics(base_capital: float = 50000000.0, market: str = "IDX", timeframe: str = "ALL") -> Dict[str, Any]:
    """Menghitung metrik performa komprehensif (Win rate, Avg R, Max DD, Profit Factor, Equity curve vs Benchmark, Heatmap Kalender, dan Sektor Matrix)."""
    import pandas as pd
    from datetime import datetime, timedelta
    from app.services.market_data import fetch_stock_df

    clean_m = (market or "IDX").upper().strip()
    clean_tf = (timeframe or "ALL").upper().strip()
    all_raw_trades = get_all_trades(market=clean_m)
    now = datetime.now()

    # Timeframe filtering
    def is_within_timeframe(t: Dict[str, Any]) -> bool:
        if clean_tf == "ALL":
            return True
        date_str = (t.get("exit_date") or t.get("entry_date") or "")[:10]
        if not date_str:
            return True
        try:
            t_dt = datetime.strptime(date_str, "%Y-%m-%d")
            if clean_tf == "MTD":
                return t_dt.year == now.year and t_dt.month == now.month
            elif clean_tf == "30D":
                return t_dt >= (now - timedelta(days=30))
            elif clean_tf == "YTD":
                return t_dt.year == now.year
        except Exception:
            return True
        return True

    trades = [t for t in all_raw_trades if is_within_timeframe(t)]
    total_trades = len(trades)
    open_trades = [t for t in trades if t["status"] == "OPEN"]
    closed_trades = [t for t in trades if t["status"] == "CLOSED"]
    
    # Urutkan transaksi closed secara kronologis
    closed_trades_chrono = sorted(closed_trades, key=lambda x: (x.get("exit_date") or x.get("entry_date") or "", x["id"]))
    
    winning_trades = [t for t in closed_trades if (t.get("pnl_amount") or 0) > 0]
    losing_trades = [t for t in closed_trades if (t.get("pnl_amount") or 0) < 0]
    
    total_pnl = sum((t.get("pnl_amount") or 0) for t in closed_trades)
    win_rate = round((len(winning_trades) / len(closed_trades)) * 100, 1) if closed_trades else 0.0
    
    gross_profits = sum((t.get("pnl_amount") or 0) for t in winning_trades)
    gross_losses = abs(sum((t.get("pnl_amount") or 0) for t in losing_trades))
    
    # Profit Factor
    if gross_losses > 0:
        profit_factor = round(gross_profits / gross_losses, 2)
    elif gross_profits > 0:
        profit_factor = None
    else:
        profit_factor = None
    
    # Perhitungan Average R
    r_multiples = []
    for t in closed_trades:
        entry = float(t.get("entry_price") or 0)
        sl = float(t.get("stop_loss") or 0)
        exit_p = float(t.get("exit_price") or 0)
        risk_per_share = entry - sl
        if risk_per_share > 0 and exit_p > 0:
            r = (exit_p - entry) / risk_per_share
            r_multiples.append(r)
        elif t.get("pnl_pct"):
            r = float(t["pnl_pct"]) / 4.0
            r_multiples.append(r)
            
    avg_r = round(sum(r_multiples) / len(r_multiples), 2) if r_multiples else 0.0
    
    # Fetch Benchmark (^JKSE for IDX, ^GSPC for US)
    benchmark_ticker = "^JKSE" if clean_m == "IDX" else "^GSPC"
    df_bench = fetch_stock_df(benchmark_ticker)
    bench_available = df_bench is not None and not df_bench.empty

    def bench_price_asof(date_str: str) -> Optional[float]:
        if not bench_available or not date_str:
            return None
        try:
            date_clean = date_str[:10]
            target = pd.Timestamp(date_clean)
            if df_bench.index.tz is not None:
                if target.tz is None:
                    target = target.tz_localize(df_bench.index.tz)
                else:
                    target = target.tz_convert(df_bench.index.tz)
            elif target.tz is not None:
                target = target.tz_localize(None)

            eligible = df_bench[df_bench.index <= target]
            if eligible.empty:
                return float(df_bench["Close"].iloc[0])
            return float(eligible["Close"].iloc[-1])
        except Exception:
            return None

    bench_start_price = None
    if closed_trades_chrono:
        start_date = (closed_trades_chrono[0].get("entry_date") or closed_trades_chrono[0].get("exit_date") or "")[:10]
        bench_start_price = bench_price_asof(start_date)

    # Equity curve calculation
    current_equity = float(base_capital)
    peak_equity = float(base_capital)
    max_dd_pct = 0.0
    
    equity_curve = [{"date": "Start", "equity": base_capital, "ihsg_pct": 0.0 if bench_start_price else None, "account_pct": 0.0}]
    
    for idx, t in enumerate(closed_trades_chrono):
        pnl = float(t.get("pnl_amount") or 0)
        current_equity += pnl
        if current_equity > peak_equity:
            peak_equity = current_equity
        dd = ((peak_equity - current_equity) / peak_equity) * 100 if peak_equity > 0 else 0.0
        if dd > max_dd_pct:
            max_dd_pct = dd
            
        acc_return_pct = round(((current_equity - base_capital) / base_capital) * 100, 2)
        t_date = (t.get("exit_date") or t.get("entry_date") or f"Trade {idx+1}")[:10]
        
        bench_price_now = bench_price_asof(t_date)
        if bench_start_price and bench_price_now and bench_start_price > 0:
            real_bench_pct = round(((bench_price_now - bench_start_price) / bench_start_price) * 100, 2)
        else:
            real_bench_pct = None
        
        equity_curve.append({
            "date": t_date,
            "equity": round(current_equity, 2),
            "account_pct": acc_return_pct,
            "ihsg_pct": real_bench_pct
        })
        
    # ── Per-setup breakdown ─────────────────────────────────────────────────
    setup_breakdown = {}
    for t in closed_trades:
        setup = t.get("setup_name") or "Manual"
        if setup not in setup_breakdown:
            setup_breakdown[setup] = {"wins": 0, "losses": 0, "pnl": 0.0}
        pnl = float(t.get("pnl_amount") or 0)
        setup_breakdown[setup]["pnl"] += pnl
        if pnl > 0:
            setup_breakdown[setup]["wins"] += 1
        else:
            setup_breakdown[setup]["losses"] += 1

    setup_stats = []
    for setup, data in setup_breakdown.items():
        total_s = data["wins"] + data["losses"]
        wr_s = round(data["wins"] / total_s * 100, 1) if total_s > 0 else 0.0
        setup_stats.append({
            "setup": setup,
            "total": total_s,
            "wins": data["wins"],
            "losses": data["losses"],
            "win_rate": wr_s,
            "pnl": round(data["pnl"], 2)
        })
    setup_stats.sort(key=lambda x: x["total"], reverse=True)

    # ── Sector Profitability Matrix ─────────────────────────────────────────
    sector_dict = {}
    for t in closed_trades:
        sec = get_stock_sector(t.get("ticker", ""), clean_m)
        if sec not in sector_dict:
            sector_dict[sec] = {"wins": 0, "losses": 0, "pnl": 0.0}
        pnl = float(t.get("pnl_amount") or 0)
        sector_dict[sec]["pnl"] += pnl
        if pnl > 0:
            sector_dict[sec]["wins"] += 1
        else:
            sector_dict[sec]["losses"] += 1

    sector_stats = []
    for sec, data in sector_dict.items():
        tot_sec = data["wins"] + data["losses"]
        wr_sec = round(data["wins"] / tot_sec * 100, 1) if tot_sec > 0 else 0.0
        sector_stats.append({
            "sector": sec,
            "trades": tot_sec,
            "wins": data["wins"],
            "losses": data["losses"],
            "win_rate": wr_sec,
            "pnl": round(data["pnl"], 2)
        })
    sector_stats.sort(key=lambda x: x["pnl"], reverse=True)

    # ── Daily PnL Heatmap & Monthly Summary ─────────────────────────────────
    daily_pnl = {}
    monthly_summary = {}
    for t in closed_trades:
        d_key = (t.get("exit_date") or t.get("entry_date") or "")[:10]
        if not d_key or len(d_key) < 10:
            continue
        m_key = d_key[:7]
        pnl = float(t.get("pnl_amount") or 0)

        # Daily aggregation
        if d_key not in daily_pnl:
            daily_pnl[d_key] = {"pnl": 0.0, "trades": 0, "wins": 0, "losses": 0, "symbols": []}
        daily_pnl[d_key]["pnl"] += pnl
        daily_pnl[d_key]["trades"] += 1
        daily_pnl[d_key]["symbols"].append(t.get("ticker", ""))
        if pnl > 0:
            daily_pnl[d_key]["wins"] += 1
        else:
            daily_pnl[d_key]["losses"] += 1

        # Monthly aggregation
        if m_key not in monthly_summary:
            monthly_summary[m_key] = {"pnl": 0.0, "trades": 0, "wins": 0, "losses": 0}
        monthly_summary[m_key]["pnl"] += pnl
        monthly_summary[m_key]["trades"] += 1
        if pnl > 0:
            monthly_summary[m_key]["wins"] += 1
        else:
            monthly_summary[m_key]["losses"] += 1

    # Format daily PnL map with rounded amounts
    daily_pnl_formatted = {}
    for k, v in daily_pnl.items():
        daily_pnl_formatted[k] = {
            "pnl": round(v["pnl"], 2),
            "trades": v["trades"],
            "wins": v["wins"],
            "losses": v["losses"],
            "symbols": list(set(v["symbols"]))
        }

    monthly_summary_formatted = {}
    for k, v in monthly_summary.items():
        wr_m = round((v["wins"] / v["trades"]) * 100, 1) if v["trades"] > 0 else 0.0
        monthly_summary_formatted[k] = {
            "pnl": round(v["pnl"], 2),
            "trades": v["trades"],
            "wins": v["wins"],
            "losses": v["losses"],
            "win_rate": wr_m
        }

    # ── Holding Duration & Exit Reason Breakdown ────────────────────────────
    winner_holding_days = [t.get("holding_days", 1) for t in winning_trades]
    loser_holding_days = [t.get("holding_days", 1) for t in losing_trades]
    all_holding_days = [t.get("holding_days", 1) for t in closed_trades]

    avg_holding_winners = round(sum(winner_holding_days) / len(winner_holding_days), 1) if winner_holding_days else 0.0
    avg_holding_losers = round(sum(loser_holding_days) / len(loser_holding_days), 1) if loser_holding_days else 0.0
    avg_holding_overall = round(sum(all_holding_days) / len(all_holding_days), 1) if all_holding_days else 0.0

    exit_counts = {"TP": 0, "SL": 0, "TIME_STOP": 0, "MANUAL": 0}
    for t in closed_trades:
        reason = (t.get("exit_reason") or "MANUAL").upper()
        if "TIME" in reason:
            exit_counts["TIME_STOP"] += 1
        elif "TP" in reason or "PROFIT" in reason:
            exit_counts["TP"] += 1
        elif "SL" in reason or "LOSS" in reason:
            exit_counts["SL"] += 1
        else:
            exit_counts["MANUAL"] += 1

    return {
        "timeframe": clean_tf,
        "total_trades": total_trades,
        "open_trades": len(open_trades),
        "closed_trades": len(closed_trades),
        "winning_trades": len(winning_trades),
        "losing_trades": len(losing_trades),
        "win_rate": win_rate,
        "total_pnl": round(total_pnl, 2),
        "avg_r": avg_r,
        "profit_factor": profit_factor,
        "max_drawdown": round(max_dd_pct, 2),
        "avg_holding_winners": avg_holding_winners,
        "avg_holding_losers": avg_holding_losers,
        "avg_holding_overall": avg_holding_overall,
        "exit_counts": exit_counts,
        "equity_curve": equity_curve,
        "setup_breakdown": setup_stats,
        "sector_breakdown": sector_stats,
        "daily_pnl": daily_pnl_formatted,
        "monthly_summary": monthly_summary_formatted
    }
