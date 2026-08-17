from typing import Dict, Any

def round_to_idx_fraction(price: float) -> float:
    """Membulatkan harga sesuai fraksi resmi BEI (IDX Tick Size)."""
    if price < 200:
        return float(round(price))  # Fraksi 1
    elif price < 500:
        return float(round(price / 2.0) * 2)  # Fraksi 2
    elif price < 2000:
        return float(round(price / 5.0) * 5)  # Fraksi 5
    elif price < 5000:
        return float(round(price / 10.0) * 10)  # Fraksi 10
    else:
        return float(round(price / 25.0) * 25)  # Fraksi 25

def generate_trade_plan(price: float, atr: float, setup_type: str) -> Dict[str, Any]:
    """Menghasilkan Trading Plan presisi: Entry, Stop Loss, Target 1, Target 2, dan R:R."""
    # Stop Loss ketat berbasis ATR (sekitar 3.5% - 5% dari harga saat ini)
    if atr and not (isinstance(atr, float) and atr != atr):  # check NaN
        sl_distance = max(price * 0.035, atr * 1.2)
    else:
        sl_distance = price * 0.035

    stop_loss = round_to_idx_fraction(price - sl_distance)
    if stop_loss >= price:
        stop_loss = round_to_idx_fraction(price * 0.96)
    
    risk_pct = round(((price - stop_loss) / price) * 100, 2)

    # Target Take Profit 1 (R:R 1:2) -> Ambil sebagian profit 50%
    tp1 = round_to_idx_fraction(price + (sl_distance * 2.0))
    tp1_gain_pct = round(((tp1 - price) / price) * 100, 2)

    # Target Take Profit 2 (R:R 1:3.5) -> Runner / Trailing Stop
    tp2 = round_to_idx_fraction(price + (sl_distance * 3.5))
    tp2_gain_pct = round(((tp2 - price) / price) * 100, 2)

    rr_ratio = round(tp1_gain_pct / risk_pct, 1) if risk_pct > 0 else 2.0

    return {
        "entry_price": int(price),
        "stop_loss": int(stop_loss),
        "risk_pct": risk_pct,
        "tp1": int(tp1),
        "tp1_gain_pct": tp1_gain_pct,
        "tp2": int(tp2),
        "tp2_gain_pct": tp2_gain_pct,
        "rr_ratio": f"1:{rr_ratio}",
        "action": "READY TO BUY" if setup_type in ["VCP Breakout", "EMA 20 Pullback", "Volume Surge"] else "WATCHLIST"
    }

def calculate_lot_size(capital: float, risk_pct: float, entry_price: float, stop_loss: float) -> Dict[str, Any]:
    """Menghitung jumlah Lot yang aman berdasarkan batas risiko maksimal modal."""
    max_risk_amount = capital * (risk_pct / 100.0)
    risk_per_share = max(1.0, entry_price - stop_loss)
    
    total_shares = max_risk_amount / risk_per_share
    lots = int(total_shares // 100)  # 1 Lot = 100 Lembar Saham di Indonesia
    final_lots = max(1, lots)
    
    total_cost = final_lots * 100 * entry_price
    max_loss_idr = final_lots * 100 * risk_per_share
    
    return {
        "lots": final_lots,
        "shares": final_lots * 100,
        "total_cost": int(total_cost),
        "max_risk_idr": int(max_loss_idr),
        "capital_allocation_pct": round((total_cost / capital) * 100, 1) if capital > 0 else 0
    }
