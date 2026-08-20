from typing import Dict, Any, Optional

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

def generate_trade_plan(price: float, atr: float, setup_type: str, sector: str = "") -> Dict[str, Any]:
    """
    Menghasilkan Trading Plan presisi berbasis Karakter Volatilitas Aset & Sektor:
    - ⚡ Explosive Beta (Energy, Materials, Tech): Target TP2 lebih lebar (+12% s.d +16%), SL ~4.2%
    - 🛡️ Defensive Stalwart (Finance, Consumer Non-Cyclical, Healthcare): Target TP1 cepat (+5% s.d +7%), SL rapat ~2.8%
    - ⚖️ Balanced Growth (Industrial, Infrastructure, Consumer Cyclical, Property): Target baku R:R 1:2 & 1:3.5
    """
    sec = (sector or "").strip().title()
    
    if sec in ["Energy", "Materials", "Technology"]:
        vol_profile = "EXPLOSIVE_BETA"
        vol_badge = "High Beta"
        base_sl_pct = 0.042
        atr_mult = 1.3
        tp1_mult = 2.0
        tp2_mult = 4.2
    elif sec in ["Finance", "Consumer Non-Cyclical", "Healthcare"]:
        vol_profile = "DEFENSIVE_STALWART"
        vol_badge = "Defensive"
        base_sl_pct = 0.028
        atr_mult = 1.0
        tp1_mult = 1.8
        tp2_mult = 3.0
    else:
        vol_profile = "BALANCED_GROWTH"
        vol_badge = "Balanced"
        base_sl_pct = 0.035
        atr_mult = 1.1
        tp1_mult = 2.0
        tp2_mult = 3.5

    # Hitung SL dinamis sesuai profil
    if atr and not (isinstance(atr, float) and atr != atr):  # check NaN
        sl_distance = max(price * base_sl_pct, atr * atr_mult)
    else:
        sl_distance = price * base_sl_pct

    stop_loss = round_to_idx_fraction(price - sl_distance)
    if stop_loss >= price:
        stop_loss = round_to_idx_fraction(price * (1.0 - base_sl_pct))
    
    risk_pct = round(((price - stop_loss) / price) * 100, 2)

    # Target Take Profit 1
    tp1 = round_to_idx_fraction(price + (sl_distance * tp1_mult))
    tp1_gain_pct = round(((tp1 - price) / price) * 100, 2)

    # Target Take Profit 2
    tp2 = round_to_idx_fraction(price + (sl_distance * tp2_mult))
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
        "volatility_profile": vol_profile,
        "volatility_badge": vol_badge,
        "action": "READY TO BUY" if setup_type in ["VCP Breakout", "EMA 20 Pullback", "Volume Surge"] else "WATCHLIST"
    }

def calculate_lot_size(
    capital: float, 
    risk_pct: float, 
    entry_price: float, 
    stop_loss: float, 
    target_price: Optional[float] = None
) -> Dict[str, Any]:
    """Menghitung jumlah Lot yang aman, potensi profit, dan rasio R:R berdasarkan batas risiko portofolio."""
    if capital <= 0:
        raise ValueError("Modal harus lebih besar dari 0.")
    if entry_price <= 0:
        raise ValueError("Entry price harus lebih besar dari 0.")
    if stop_loss >= entry_price:
        raise ValueError("Stop Loss harus lebih rendah dari Entry Price.")
    if risk_pct <= 0:
        raise ValueError("Risk % harus lebih besar dari 0.")

    max_risk_amount = capital * (risk_pct / 100.0)
    risk_per_share = entry_price - stop_loss  # sudah pasti > 0 karena validasi di atas

    lots_by_risk = max(1, int((max_risk_amount / risk_per_share) // 100))

    max_affordable_lots = int(capital // (100 * entry_price))
    if max_affordable_lots < 1:
        raise ValueError(
            f"Modal Rp{int(capital):,} tidak cukup untuk membeli 1 lot (Rp{int(100*entry_price):,}) di harga entry ini."
        )

    final_lots = min(lots_by_risk, max_affordable_lots)
    capped_by_capital = final_lots < lots_by_risk

    total_cost = final_lots * 100 * entry_price
    max_loss_idr = final_lots * 100 * risk_per_share
    risk_pct_price = round((risk_per_share / entry_price) * 100, 2)
    actual_risk_pct = round((max_loss_idr / capital) * 100, 2)

    # Target Price & Reward Metrics
    tp = target_price if (target_price and target_price > entry_price) else (entry_price + (2 * risk_per_share))
    reward_per_share = tp - entry_price
    tp_gain_idr = int(final_lots * 100 * reward_per_share)
    tp_gain_pct = round((reward_per_share / entry_price) * 100, 2)
    rr_ratio = round(reward_per_share / risk_per_share, 2) if risk_per_share > 0 else 0.0

    return {
        "lots": final_lots,
        "shares": final_lots * 100,
        "total_cost": int(total_cost),
        "max_risk_idr": int(max_loss_idr),
        "risk_pct_price": risk_pct_price,
        "target_risk_pct": risk_pct,
        "actual_risk_pct": actual_risk_pct,
        "capital_allocation_pct": round((total_cost / capital) * 100, 1),
        "capped_by_capital": capped_by_capital,
        "target_price": int(tp),
        "tp_gain_idr": tp_gain_idr,
        "tp_gain_pct": tp_gain_pct,
        "rr_ratio": rr_ratio,
        "is_default_tp": target_price is None or target_price <= entry_price
    }

