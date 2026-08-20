import sqlite3
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/alpha.db"))

def init_capital_db():
    """Membuat tabel capital_ledger jika belum ada dan mengisi modal awal default jika kosong."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS capital_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TEXT NOT NULL,
            type TEXT NOT NULL, -- 'DEPOSIT', 'WITHDRAWAL', 'INITIAL'
            amount REAL NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    # Cek apakah sudah ada mutasi modal sama sekali
    cursor.execute("SELECT COUNT(*) FROM capital_ledger")
    count = cursor.fetchone()[0]
    if count == 0:
        # Default saldo awal bisnis Rp 100.000.000
        now_date = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("""
            INSERT INTO capital_ledger (entry_date, type, amount, notes)
            VALUES (?, 'INITIAL', 100000000.0, 'Modal Awal Portofolio')
        """, (now_date,))
        conn.commit()
    conn.close()

def log_capital_flow(flow_type: str, amount: float, entry_date: Optional[str] = None, notes: str = "") -> Dict[str, Any]:
    """Mencatat setoran modal (DEPOSIT) atau penarikan dana (WITHDRAWAL)."""
    init_capital_db()
    clean_type = (flow_type or "DEPOSIT").upper().strip()
    if clean_type not in ["DEPOSIT", "WITHDRAWAL", "INITIAL"]:
        clean_type = "DEPOSIT"
    
    clean_amount = abs(float(amount or 0))
    clean_date = (entry_date or datetime.now().strftime("%Y-%m-%d")).strip()
    clean_notes = (notes or "").strip()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO capital_ledger (entry_date, type, amount, notes)
        VALUES (?, ?, ?, ?)
    """, (clean_date, clean_type, clean_amount, clean_notes))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {"status": "success", "id": new_id, "type": clean_type, "amount": clean_amount}

def delete_capital_entry(entry_id: int) -> bool:
    """Menghapus catatan mutasi modal jika ada kesalahan input."""
    init_capital_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM capital_ledger WHERE id = ?", (entry_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def get_capital_statement() -> Dict[str, Any]:
    """
    Menghitung Neraca Finansial Portofolio & HPP Bisnis:
    1. Total Setoran (Deposits) & Penarikan (Withdrawals)
    2. Modal Bersih Disetor (HPP / Net Invested Capital)
    3. Modal Tertanam di Saham Aktif (Invested Open Inventory)
    4. Kas RDN Tersedia (Idle Available Cash)
    5. Total Valuasi Portofolio (Live Equity / NAV)
    6. Laba Bersih Usaha (Net Profit Realized + Unrealized)
    7. Return on Investment (ROI %)
    """
    init_capital_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Ambil seluruh riwayat mutasi modal
    cursor.execute("SELECT * FROM capital_ledger ORDER BY entry_date DESC, id DESC")
    ledger_rows = [dict(r) for r in cursor.fetchall()]

    total_deposits = sum(r["amount"] for r in ledger_rows if r["type"] in ["DEPOSIT", "INITIAL"])
    total_withdrawals = sum(r["amount"] for r in ledger_rows if r["type"] == "WITHDRAWAL")
    net_invested_capital = total_deposits - total_withdrawals

    # 2. Ambil data transaksi trading untuk menghitung realisasi & persediaan saham
    cursor.execute("SELECT * FROM trades")
    trade_rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    open_trades = [t for t in trade_rows if t.get("status") == "OPEN"]
    closed_trades = [t for t in trade_rows if t.get("status") == "CLOSED"]

    # Modal tertanam di saham aktif (HPP Saham = entry_price * lots * 100)
    open_stock_cost = sum(
        float(t.get("entry_price") or 0) * int(t.get("lots") or 0) * 100
        for t in open_trades
    )

    # Realized PnL dari trade yang sudah selesai
    realized_pnl = sum(float(t.get("pnl_amount") or 0) for t in closed_trades)

    # Kas RDN Tersedia = Modal Bersih Disetor + Realized PnL - Modal Saham Terbuka
    available_cash = net_invested_capital + realized_pnl - open_stock_cost

    # Total Valuasi Portofolio (Equity) = Kas Tersedia + Modal Saham Terbuka
    total_equity = available_cash + open_stock_cost

    # Laba Bersih Usaha Trading
    net_profit = total_equity - net_invested_capital

    # ROI Bisnis (%)
    roi_pct = round((net_profit / net_invested_capital) * 100, 2) if net_invested_capital > 0 else 0.0

    # Rasio Utilisasi Modal
    cash_ratio = round((available_cash / total_equity) * 100, 1) if total_equity > 0 else 100.0
    stock_ratio = round((open_stock_cost / total_equity) * 100, 1) if total_equity > 0 else 0.0

    return {
        "summary": {
            "net_invested_capital": round(net_invested_capital, 2), # HPP Pokok
            "total_deposits": round(total_deposits, 2),
            "total_withdrawals": round(total_withdrawals, 2),
            "total_equity": round(total_equity, 2), # NAV / Valuasi Portofolio
            "available_cash": round(available_cash, 2), # Saldo Kas RDN
            "open_stock_cost": round(open_stock_cost, 2), # Modal Terpasang
            "realized_pnl": round(realized_pnl, 2),
            "net_profit": round(net_profit, 2), # Laba Bersih Murni
            "roi_pct": roi_pct, # ROI Bisnis %
            "cash_ratio": cash_ratio,
            "stock_ratio": stock_ratio,
            "open_positions_count": len(open_trades),
            "closed_trades_count": len(closed_trades)
        },
        "ledger": ledger_rows
    }
