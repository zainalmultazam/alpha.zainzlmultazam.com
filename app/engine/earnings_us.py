"""
Modul Pelindung Risiko Laba Kuartalan (US Earnings Risk Shield & PEAD Detector)
Khusus untuk Pasar Saham Amerika Serikat (Wall Street: NYSE & NASDAQ).

Aturan Hedge Fund:
1. Blackout Period (<= 3 hari menuju Earnings): Dilarang entry posisi swing baru karena gap down risk.
2. Caution Period (4-7 hari menuju Earnings): Peringatan volatilitas tinggi.
3. PEAD Catalyst (1-5 hari setelah Earnings): Sinyal momentum pasca-laporan keuangan.
4. Safe Period (> 7 hari atau sudah lewat): Optimal untuk standard swing trading.
"""

from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional
import yfinance as yf
import pandas as pd

_EARNINGS_CACHE: Dict[str, Dict[str, Any]] = {}
_EARNINGS_CACHE_EXPIRY = 43200  # 12 Jam

def get_us_earnings_info(ticker: str, df: Optional[Any] = None) -> Dict[str, Any]:
    """
    Mengambil dan menganalisis status rilis laporan keuangan kuartalan untuk emiten US Stock.
    """
    clean_ticker = ticker.upper().replace(".JK", "").strip()
    now = datetime.now()
    today_date = now.date()

    cached = _EARNINGS_CACHE.get(clean_ticker)
    if cached and (now - cached["cached_at"]).total_seconds() < _EARNINGS_CACHE_EXPIRY:
        return cached["data"]

    earnings_date: Optional[date] = None
    try:
        t = yf.Ticker(clean_ticker)
        # 1. Check t.calendar (dict or DataFrame)
        cal = t.calendar
        if cal is not None:
            if isinstance(cal, dict):
                # Format: {'Earnings Date': [datetime.date(...), ...]}
                for key in ["Earnings Date", "Earnings High", "Earnings Low", "Earnings Average"]:
                    if key in cal and cal[key]:
                        ed_val = cal[key]
                        if isinstance(ed_val, (list, tuple)) and len(ed_val) > 0:
                            first_ed = ed_val[0]
                            if isinstance(first_ed, datetime):
                                earnings_date = first_ed.date()
                                break
                            elif isinstance(first_ed, date):
                                earnings_date = first_ed
                                break
            elif hasattr(cal, 'to_dict'):
                # Format: DataFrame with index or columns
                cdict = cal.to_dict()
                if "Earnings Date" in cdict:
                    val = cdict["Earnings Date"]
                    if isinstance(val, dict):
                        for item in val.values():
                            if isinstance(item, datetime):
                                earnings_date = item.date()
                                break
                            elif isinstance(item, date):
                                earnings_date = item
                                break

        # 2. Check t.earnings_dates if not found
        if not earnings_date:
            try:
                ed = t.earnings_dates
                if ed is not None and not ed.empty:
                    # Filter future dates
                    idx_dates = [ts.date() if isinstance(ts, (datetime, pd.Timestamp)) else ts for ts in ed.index]
                    future_dates = [d for d in idx_dates if d >= today_date]
                    if future_dates:
                        earnings_date = min(future_dates)
                    elif idx_dates:
                        earnings_date = idx_dates[0]
            except Exception:
                pass
    except Exception:
        pass

    # Analisis Days Until Earnings
    if earnings_date:
        delta_days = (earnings_date - today_date).days
        formatted_date = earnings_date.strftime("%d %b %Y")
        
        if 0 <= delta_days <= 3:
            status = "BLACKOUT"
            badge_text = f"⚠️ Earnings {delta_days}D (Blackout)" if delta_days > 0 else "⚠️ Earnings Hari Ini!"
            badge_color = "rose"
            is_blackout = True
            is_safe_to_enter = False
            risk_penalty = -35
            guidance = f"Blackout Risk: Emiten rilis Earnings {formatted_date}. Hindari entry baru untuk cegah gap down!"
        elif 4 <= delta_days <= 7:
            status = "WARNING"
            badge_text = f"⚡ Earnings: {delta_days} Hari"
            badge_color = "amber"
            is_blackout = False
            is_safe_to_enter = True
            risk_penalty = -5
            guidance = f"Perhatian: Earnings dalam {delta_days} hari ({formatted_date}). Siapkan SL ketat jika ambil swing pendek."
        elif delta_days < 0 and delta_days >= -5:
            status = "POST_EARNINGS"
            badge_text = "🚀 Post-Earnings Leader"
            badge_color = "purple"
            is_blackout = False
            is_safe_to_enter = True
            risk_penalty = 10  # PEAD Bonus
            guidance = f"Katalis Laba: Rilis laporan keuangan telah lewat ({formatted_date}). Momentum pasca-earnings aktif!"
        else:
            status = "SAFE"
            badge_text = f"📅 Earnings: {delta_days}D"
            badge_color = "slate"
            is_blackout = False
            is_safe_to_enter = True
            risk_penalty = 0
            guidance = f"Jadwal Earnings aman ({formatted_date}). Optimal untuk eksekusi swing trading."
    else:
        status = "SAFE"
        delta_days = 99
        badge_text = "📅 Earnings Aman"
        badge_color = "slate"
        is_blackout = False
        is_safe_to_enter = True
        risk_penalty = 0
        guidance = "Tidak ada jadwal earnings rilis dalam waktu dekat. Aman untuk swing trading."

    res_data = {
        "status": status,
        "earnings_date": earnings_date.isoformat() if earnings_date else None,
        "days_until": delta_days,
        "badge_text": badge_text,
        "badge_color": badge_color,
        "is_blackout": is_blackout,
        "is_safe_to_enter": is_safe_to_enter,
        "risk_penalty": risk_penalty,
        "guidance": guidance
    }

    _EARNINGS_CACHE[clean_ticker] = {
        "cached_at": now,
        "data": res_data
    }

    return res_data
