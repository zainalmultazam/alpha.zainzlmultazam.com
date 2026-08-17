import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/trades.db"))

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

def log_trade(ticker: str, entry_price: float, stop_loss: float, target_price: float, lots: int, setup_name: str) -> int:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO trades (ticker, entry_date, entry_price, stop_loss, target_price, lots, setup_name, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN')
    """, (ticker, datetime.now().strftime("%Y-%m-%d %H:%M"), entry_price, stop_loss, target_price, lots, setup_name))
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
    """, (datetime.now().strftime("%Y-%m-%d %H:%M"), exit_price, round(pnl_amount, 2), round(pnl_pct, 2), notes, trade_id))
    conn.commit()
    conn.close()
    return True
