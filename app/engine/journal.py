import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/alpha.db"))

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
            notes TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_trade(ticker: str, entry_price: float, stop_loss: float, target_price: float, lots: int, setup_name: str = "Manual / Bot") -> int:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    clean_ticker = ticker.upper().replace(".JK", "").strip()
    cursor.execute("""
        INSERT INTO trades (ticker, entry_date, entry_price, stop_loss, target_price, lots, setup_name, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN')
    """, (clean_ticker, datetime.now().strftime("%Y-%m-%d %H:%M"), float(entry_price), float(stop_loss), float(target_price), int(lots), setup_name))
    trade_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return trade_id

def get_all_trades() -> List[Dict[str, Any]]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trades ORDER BY id DESC")
    rows = cursor.fetchall()
    trades = [dict(row) for row in rows]
    conn.close()
    return trades

def get_open_trades() -> List[Dict[str, Any]]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trades WHERE status = 'OPEN' ORDER BY id DESC")
    rows = cursor.fetchall()
    trades = [dict(row) for row in rows]
    conn.close()
    return trades

def close_trade(trade_id: int, exit_price: float, notes: str = "") -> bool:
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
    lots = int(trade["lots"])
    pnl_amount = (exit_price - entry_price) * (lots * 100)
    pnl_pct = ((exit_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0.0

    cursor.execute("""
        UPDATE trades 
        SET status = 'CLOSED', exit_date = ?, exit_price = ?, pnl_amount = ?, pnl_pct = ?, notes = ?
        WHERE id = ?
    """, (datetime.now().strftime("%Y-%m-%d %H:%M"), float(exit_price), round(pnl_amount, 2), round(pnl_pct, 2), notes, trade_id))
    conn.commit()
    conn.close()
    return True

def close_open_trade_by_ticker(ticker: str, exit_price: float, notes: str = "") -> Optional[Dict[str, Any]]:
    """Menutup posisi OPEN terakhir berdasarkan simbol ticker."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    clean_ticker = ticker.upper().replace(".JK", "").strip()
    cursor.execute("SELECT * FROM trades WHERE ticker = ? AND status = 'OPEN' ORDER BY id DESC LIMIT 1", (clean_ticker,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    
    trade = dict(row)
    trade_id = trade["id"]
    entry_price = float(trade["entry_price"])
    lots = int(trade["lots"])
    pnl_amount = (exit_price - entry_price) * (lots * 100)
    pnl_pct = ((exit_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0.0

    cursor.execute("""
        UPDATE trades 
        SET status = 'CLOSED', exit_date = ?, exit_price = ?, pnl_amount = ?, pnl_pct = ?, notes = ?
        WHERE id = ?
    """, (datetime.now().strftime("%Y-%m-%d %H:%M"), float(exit_price), round(pnl_amount, 2), round(pnl_pct, 2), notes, trade_id))
    conn.commit()
    conn.close()
    
    trade["exit_price"] = exit_price
    trade["pnl_amount"] = round(pnl_amount, 2)
    trade["pnl_pct"] = round(pnl_pct, 2)
    trade["exit_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    return trade

def get_journal_stats() -> Dict[str, Any]:
    trades = get_all_trades()
    total_trades = len(trades)
    open_trades = [t for t in trades if t["status"] == "OPEN"]
    closed_trades = [t for t in trades if t["status"] == "CLOSED"]
    
    winning_trades = [t for t in closed_trades if (t.get("pnl_amount") or 0) > 0]
    losing_trades = [t for t in closed_trades if (t.get("pnl_amount") or 0) < 0]
    
    total_pnl = sum((t.get("pnl_amount") or 0) for t in closed_trades)
    win_rate = round((len(winning_trades) / len(closed_trades)) * 100, 1) if closed_trades else 0.0

    return {
        "total_trades": total_trades,
        "open_trades": len(open_trades),
        "closed_trades": len(closed_trades),
        "winning_trades": len(winning_trades),
        "losing_trades": len(losing_trades),
        "win_rate": win_rate,
        "total_pnl": round(total_pnl, 2)
    }

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

def get_performance_metrics(base_capital: float = 50000000.0) -> Dict[str, Any]:
    """Menghitung metrik performa komprehensif (Win rate, Avg R, Max DD, Profit Factor, Equity curve vs IHSG)."""
    import pandas as pd
    from app.services.market_data import fetch_stock_df

    trades = get_all_trades()
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
    
    # Spek #3: Profit Factor edge case
    if gross_losses > 0:
        profit_factor = round(gross_profits / gross_losses, 2)
    elif gross_profits > 0:
        profit_factor = None  # representasi "infinity" — belum ada loss untuk dibagi
    else:
        profit_factor = None  # belum ada data closed trade / profit
    
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
    
    # Spek #2: Fetch IHSG Real Benchmark (^JKSE)
    df_ihsg = fetch_stock_df("^JKSE")
    ihsg_available = df_ihsg is not None and not df_ihsg.empty

    def ihsg_price_asof(date_str: str) -> Optional[float]:
        if not ihsg_available or not date_str:
            return None
        try:
            date_clean = date_str[:10]
            target = pd.Timestamp(date_clean)
            if df_ihsg.index.tz is not None:
                if target.tz is None:
                    target = target.tz_localize(df_ihsg.index.tz)
                else:
                    target = target.tz_convert(df_ihsg.index.tz)
            elif target.tz is not None:
                target = target.tz_localize(None)

            eligible = df_ihsg[df_ihsg.index <= target]
            if eligible.empty:
                return float(df_ihsg["Close"].iloc[0])
            return float(eligible["Close"].iloc[-1])
        except Exception:
            return None

    ihsg_start_price = None
    if closed_trades_chrono:
        start_date = (closed_trades_chrono[0].get("entry_date") or closed_trades_chrono[0].get("exit_date") or "")[:10]
        ihsg_start_price = ihsg_price_asof(start_date)

    # Equity curve calculation
    current_equity = float(base_capital)
    peak_equity = float(base_capital)
    max_dd_pct = 0.0
    
    equity_curve = [{"date": "Start", "equity": base_capital, "ihsg_pct": 0.0 if ihsg_start_price else None, "account_pct": 0.0}]
    
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
        
        ihsg_price_now = ihsg_price_asof(t_date)
        if ihsg_start_price and ihsg_price_now and ihsg_start_price > 0:
            real_ihsg_pct = round(((ihsg_price_now - ihsg_start_price) / ihsg_start_price) * 100, 2)
        else:
            real_ihsg_pct = None
        
        equity_curve.append({
            "date": t_date,
            "equity": round(current_equity, 2),
            "account_pct": acc_return_pct,
            "ihsg_pct": real_ihsg_pct
        })
        
    return {
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
        "equity_curve": equity_curve
    }
