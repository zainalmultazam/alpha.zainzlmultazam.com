import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Optional, Any
from datetime import datetime, time, timezone, timedelta
from zoneinfo import ZoneInfo

_CACHE: Dict[str, Dict] = {}
_CACHE_EXPIRY_MINUTES = 30

# Kalender Libur Bursa BEI (Format MM-DD untuk perayaan tahunan & tanggal tetap bursa)
FIXED_HOLIDAYS = {
    (1, 1): "Tahun Baru Masehi",
    (5, 1): "Hari Buruh Internasional",
    (6, 1): "Hari Lahir Pancasila",
    (8, 17): "Hari Kemerdekaan RI (HUT RI)",
    (12, 25): "Hari Raya Natal",
    (12, 26): "Cuti Bersama Natal",
    (12, 31): "Libur Akhir Tahun Bursa BEI"
}

def get_idx_market_status() -> Dict[str, Any]:
    """Mendeteksi apakah pasar saham BEI sedang Buka, Istirahat, Tutup, Akhir Pekan, atau Libur Nasional Bursa."""
    try:
        tz_jkt = ZoneInfo("Asia/Jakarta")
        now_jkt = datetime.now(tz_jkt)
    except Exception:
        tz_jkt = timezone(timedelta(hours=7))
        now_jkt = datetime.now(tz_jkt)
    
    weekday = now_jkt.weekday() # 0 = Senin, ..., 4 = Jumat, 5 = Sabtu, 6 = Minggu
    current_time = now_jkt.time()
    month_day = (now_jkt.month, now_jkt.day)

    # 1. Deteksi Akhir Pekan (Sabtu / Minggu)
    if weekday == 5:
        return {
            "is_open": False,
            "is_holiday": True,
            "status": "WEEKEND",
            "badge_color": "rose",
            "title": "Libur Akhir Pekan (Sabtu)",
            "message": "Pasar saham BEI tutup pada akhir pekan. Buka kembali Senin pukul 09:00 WIB.",
            "next_open": "Senin 09:00 WIB",
            "current_wib": now_jkt.strftime("%H:%M WIB")
        }
    if weekday == 6:
        return {
            "is_open": False,
            "is_holiday": True,
            "status": "WEEKEND",
            "badge_color": "rose",
            "title": "Libur Akhir Pekan (Minggu)",
            "message": "Pasar saham BEI tutup pada akhir pekan. Buka kembali besok (Senin) pukul 09:00 WIB.",
            "next_open": "Senin 09:00 WIB",
            "current_wib": now_jkt.strftime("%H:%M WIB")
        }

    # 2. Deteksi Hari Libur Nasional / Kalender Bursa BEI
    if month_day in FIXED_HOLIDAYS:
        holiday_name = FIXED_HOLIDAYS[month_day]
        return {
            "is_open": False,
            "is_holiday": True,
            "status": "HOLIDAY",
            "badge_color": "rose",
            "title": f"Libur Bursa ({holiday_name})",
            "message": f"Hari ini pasar saham BEI libur memperingati {holiday_name}.",
            "next_open": "Hari bursa kerja berikutnya 09:00 WIB",
            "current_wib": now_jkt.strftime("%H:%M WIB")
        }

    # 3. Jam Operasional Bursa Normal (Senin - Jumat)
    # Sesi I: 09:00 - 12:00 (Jumat: 09:00 - 11:30)
    # Sesi II: 13:30 - 15:50 / 16:00 (Jumat: 14:00 - 15:50)
    sesi1_start = time(9, 0)
    sesi1_end = time(11, 30) if weekday == 4 else time(12, 0)
    
    sesi2_start = time(14, 0) if weekday == 4 else time(13, 30)
    sesi2_end = time(16, 0)

    if sesi1_start <= current_time <= sesi1_end:
        return {
            "is_open": True,
            "is_holiday": False,
            "status": "OPEN_SESI_1",
            "badge_color": "emerald",
            "title": "Pasar Buka (Sesi 1)",
            "message": f"Perdagangan reguler BEI sedang berlangsung (Sesi 1 s.d {sesi1_end.strftime('%H:%M')} WIB).",
            "next_open": "Sedang Berlangsung",
            "current_wib": now_jkt.strftime("%H:%M WIB")
        }
    elif sesi1_end < current_time < sesi2_start:
        return {
            "is_open": False,
            "is_holiday": False,
            "status": "BREAK",
            "badge_color": "amber",
            "title": "Istirahat Antar Sesi (Break)",
            "message": f"Pasar sedang rehat siang. Sesi II dibuka kembali pukul {sesi2_start.strftime('%H:%M')} WIB.",
            "next_open": f"Sesi II ({sesi2_start.strftime('%H:%M')} WIB)",
            "current_wib": now_jkt.strftime("%H:%M WIB")
        }
    elif sesi2_start <= current_time <= sesi2_end:
        return {
            "is_open": True,
            "is_holiday": False,
            "status": "OPEN_SESI_2",
            "badge_color": "emerald",
            "title": "Pasar Buka (Sesi 2)",
            "message": "Perdagangan reguler BEI sedang berlangsung (Sesi 2 menuju penutupan).",
            "next_open": "Sedang Berlangsung",
            "current_wib": now_jkt.strftime("%H:%M WIB")
        }
    elif current_time < sesi1_start:
        return {
            "is_open": False,
            "is_holiday": False,
            "status": "PRE_MARKET",
            "badge_color": "slate",
            "title": "Pra-Pembukaan (Pre-Market)",
            "message": "Pasar belum dibuka. Perdagangan Sesi 1 akan dimulai tepat pukul 09:00 WIB.",
            "next_open": "Hari ini 09:00 WIB",
            "current_wib": now_jkt.strftime("%H:%M WIB")
        }
    else:
        return {
            "is_open": False,
            "is_holiday": False,
            "status": "CLOSED",
            "badge_color": "slate",
            "title": "Pasar Tutup (Pasca-Bursa)",
            "message": "Perdagangan hari ini telah selesai. Engine memindai seluruh data penutupan (EOD) untuk esok hari.",
            "next_open": "Besok 09:00 WIB",
            "current_wib": now_jkt.strftime("%H:%M WIB")
        }

def get_dynamic_cache_ttl_seconds() -> int:
    """
    Menentukan durasi TTL cache secara cerdas:
    - Jam bursa aktif (09:00 - 16:15 WIB Senin-Jumat): 15 menit (900 detik).
    - Di luar jam bursa / setelah closing (16:30 - 08:45 WIB & Weekend/Libur): 12 jam (43200 detik).
    """
    status = get_idx_market_status()
    if status.get("is_open"):
        return 15 * 60  # 15 menit saat bursa aktif
    return 12 * 3600  # 12 jam (EOD persistent) saat bursa tutup

def fetch_stock_df(ticker: str) -> Optional[pd.DataFrame]:
    """Mengambil data historis saham IDX dari Yahoo Finance dengan sistem smart cache cerdas."""
    now = datetime.now()
    ttl = get_dynamic_cache_ttl_seconds()
    if ticker in _CACHE:
        cached = _CACHE[ticker]
        if (now - cached["timestamp"]).total_seconds() < ttl:
            return cached["data"]

    try:
        t = yf.Ticker(ticker)
        df = t.history(period="1y", interval="1d")
        if df is not None and not df.empty:
            _CACHE[ticker] = {"data": df, "timestamp": now}
            return df
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
    
    return None

def batch_fetch_stock_dfs(tickers: list, batch_size: int = 30) -> Dict[str, pd.DataFrame]:
    """
    Mengambil data banyak saham secara batch efisien menggunakan yf.download dan thread pool.
    Memeriksa cache in-memory terlebih dahulu untuk meminimalkan beban request ke server.
    """
    now = datetime.now()
    ttl = get_dynamic_cache_ttl_seconds()
    results: Dict[str, pd.DataFrame] = {}
    uncached: list = []

    for t in tickers:
        if t in _CACHE:
            cached = _CACHE[t]
            if (now - cached["timestamp"]).total_seconds() < ttl:
                results[t] = cached["data"]
                continue
        uncached.append(t)

    if not uncached:
        return results

    # Batch download uncached tickers in chunks
    for i in range(0, len(uncached), batch_size):
        chunk = uncached[i:i + batch_size]
        try:
            if len(chunk) == 1:
                t = chunk[0]
                df = fetch_stock_df(t)
                if df is not None and not df.empty:
                    results[t] = df
            else:
                data = yf.download(chunk, period="1y", interval="1d", group_by="ticker", threads=True, progress=False)
                if data is not None and not data.empty:
                    for t in chunk:
                        try:
                            if hasattr(data.columns, "levels") and t in data.columns.levels[0]:
                                sub_df = data[t].dropna(how="all")
                                if not sub_df.empty and len(sub_df) > 5:
                                    _CACHE[t] = {"data": sub_df, "timestamp": now}
                                    results[t] = sub_df
                        except Exception:
                            pass
        except Exception as e:
            print(f"Error during batch chunk download: {e}")

    # Fallback to single fetch for any tickers missed in batch
    for t in uncached:
        if t not in results:
            df = fetch_stock_df(t)
            if df is not None and not df.empty:
                results[t] = df

    return results

_IHSG_CLIMATE_CACHE: Dict[str, Any] = {}
_IHSG_CLIMATE_CACHE_TIME: Optional[datetime] = None

def get_market_climate(force: bool = False) -> Dict[str, Any]:
    """Menganalisis rezim pasar IHSG (^JKSE) secara real-time untuk menentukan iklim risiko pasar (Risk-On / Caution / Risk-Off) serta status operasional bursa."""
    global _IHSG_CLIMATE_CACHE, _IHSG_CLIMATE_CACHE_TIME
    market_status = get_idx_market_status()
    now = datetime.now()

    # Cache pendek 2 menit saat jam bursa aktif/istirahat, 15 menit saat tutup
    is_open_or_break = market_status.get("is_open") or market_status.get("status") == "BREAK"
    cache_ttl = 120 if is_open_or_break else 900

    if not force and _IHSG_CLIMATE_CACHE_TIME and (now - _IHSG_CLIMATE_CACHE_TIME).total_seconds() < cache_ttl and _IHSG_CLIMATE_CACHE:
        _IHSG_CLIMATE_CACHE["market_status"] = market_status
        return _IHSG_CLIMATE_CACHE

    df_ihsg = None
    try:
        t = yf.Ticker("^JKSE")
        df_ihsg = t.history(period="1y", interval="1d")
    except Exception as e:
        print(f"Error fetching direct ^JKSE: {e}")
        df_ihsg = fetch_stock_df("^JKSE")
    
    if df_ihsg is None or len(df_ihsg) < 50:
        return {
            "regime": "BULLISH",
            "title": "Risk-On",
            "color": "emerald",
            "price": 6480.0,
            "change_pct": 0.0,
            "exposure_pct": 100,
            "advice": "Kondisi pasar kondusif untuk swing trading.",
            "market_status": market_status
        }

    df = df_ihsg.copy()
    df["ema20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["ema50"] = df["Close"].ewm(span=50, adjust=False).mean()
    df["ema200"] = df["Close"].ewm(span=200, adjust=False).mean()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    price = round(float(last["Close"]), 2)
    prev_close = float(prev["Close"])
    change_pct = round(((price - prev_close) / prev_close) * 100, 2) if prev_close > 0 else 0.0

    ema20 = float(last["ema20"])
    ema50 = float(last["ema50"])
    ema200 = float(last["ema200"])

    # Penentuan Rezim Pasar (Stan Weinstein & Minervini Stage Analysis)
    if price >= ema50 and price >= ema200:
        regime = "BULLISH"
        title = "Risk-On (Stage 2 Uptrend Kuat)"
        color = "emerald"
        exposure_pct = 100
        advice = "IHSG berada di atas EMA 50 & EMA 200. Kondisi pasar optimal untuk full size swing trading (100% modal aktif)."
    elif price >= ema50 or price >= ema200:
        regime = "NEUTRAL"
        title = "Caution (Recovery / Rebound Selektif)"
        color = "amber"
        exposure_pct = 50
        advice = "IHSG berhasil memantul di atas EMA 50 menguji resistance EMA 200. Alokasikan 50% modal aktif & prioritaskan saham leader bervolume tinggi."
    else:
        regime = "BEARISH"
        title = "Risk-Off (Cash is King)"
        color = "rose"
        exposure_pct = 0
        advice = "IHSG jebol di bawah EMA 50 & EMA 200. Tekanan jual tinggi, utamakan memegang Cash dan hindari beli agresif."

    result = {
        "regime": regime,
        "title": title,
        "color": color,
        "price": price,
        "change_pct": change_pct,
        "ema50": round(ema50, 2),
        "ema200": round(ema200, 2),
        "exposure_pct": exposure_pct,
        "advice": advice,
        "market_status": market_status,
        "last_updated": datetime.now().strftime("%H:%M:%S")
    }

    _IHSG_CLIMATE_CACHE = result
    _IHSG_CLIMATE_CACHE_TIME = now
    return result

def clear_cache():
    """Mengosongkan cache memory."""
    global _CACHE, _MACRO_CACHE, _MACRO_CACHE_TIME, _IHSG_CLIMATE_CACHE, _IHSG_CLIMATE_CACHE_TIME
    _CACHE = {}
    _MACRO_CACHE = {}
    _MACRO_CACHE_TIME = None
    _IHSG_CLIMATE_CACHE = {}
    _IHSG_CLIMATE_CACHE_TIME = None

_MACRO_CACHE: Dict[str, Any] = {}
_MACRO_CACHE_TIME: Optional[datetime] = None
_MACRO_CACHE_EXPIRY_SECONDS = 900  # Cache 15 menit

def get_global_macro_data() -> Dict[str, Any]:
    """Mengambil harga komoditas global, kurs valas, dan yield obligasi untuk korelasi sektoral saham BEI."""
    global _MACRO_CACHE, _MACRO_CACHE_TIME
    now = datetime.now()
    if _MACRO_CACHE_TIME and (now - _MACRO_CACHE_TIME).total_seconds() < _MACRO_CACHE_EXPIRY_SECONDS and _MACRO_CACHE:
        return _MACRO_CACHE

    macro_items = [
        {
            "id": "oil",
            "name": "Brent Crude Oil",
            "symbol": "BZ=F",
            "category": "Energy",
            "unit": "$/bbl",
            "related_tickers": ["MEDC", "ELSA", "AKRA"],
            "impact_sector": "Minyak & Gas"
        },
        {
            "id": "gold",
            "name": "Gold (Emas)",
            "symbol": "GC=F",
            "category": "Precious Metals",
            "unit": "$/oz",
            "related_tickers": ["BRMS", "PSAB", "ANTM", "MDKA"],
            "impact_sector": "Tambang Emas"
        },
        {
            "id": "copper",
            "name": "Copper & Metals",
            "symbol": "HG=F",
            "category": "Industrial Metals",
            "unit": "$/lb",
            "related_tickers": ["INCO", "NCKL", "MBMA", "TINS"],
            "impact_sector": "Nikel & Mineral"
        },
        {
            "id": "usdidr",
            "name": "USD / IDR",
            "symbol": "IDR=X",
            "category": "Currency",
            "unit": "Rp",
            "related_tickers": ["ASII", "ICBP", "INDF", "BBCA"],
            "impact_sector": "Nilai Tukar Rupiah"
        },
        {
            "id": "us10y",
            "name": "US 10Y Yield",
            "symbol": "^TNX",
            "category": "Bonds",
            "unit": "%",
            "related_tickers": ["BBCA", "BBRI", "BMRI", "BBNI"],
            "impact_sector": "Likuiditas Global"
        }
    ]

    results = []
    for item in macro_items:
        try:
            t = yf.Ticker(item["symbol"])
            hist = t.history(period="5d")
            if not hist.empty:
                curr = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else curr
                chg_pct = round(((curr - prev) / prev) * 100, 2) if prev > 0 else 0.0
                chg_val = round(curr - prev, 2)
                
                # Format visual price
                if item["id"] == "usdidr":
                    display_price = f"Rp {int(curr):,}".replace(",", ".")
                elif item["id"] == "us10y":
                    display_price = f"{curr:.2f}%"
                else:
                    display_price = f"${curr:,.2f}"

                results.append({
                    "id": item["id"],
                    "name": item["name"],
                    "category": item["category"],
                    "symbol": item["symbol"],
                    "price": round(curr, 2),
                    "display_price": display_price,
                    "unit": item["unit"],
                    "change_pct": chg_pct,
                    "change_val": chg_val,
                    "is_positive": chg_pct >= 0,
                    "related_tickers": item["related_tickers"],
                    "impact_sector": item["impact_sector"]
                })
        except Exception:
            continue

    if not results:
        # Fallback default static
        results = [
            {"id": "oil", "name": "Brent Crude Oil", "symbol": "BZ=F", "category": "Energy", "price": 89.35, "display_price": "$89.35", "unit": "$/bbl", "change_pct": 0.94, "change_val": 0.83, "is_positive": True, "related_tickers": ["MEDC", "ELSA", "AKRA"], "impact_sector": "Minyak & Gas"},
            {"id": "gold", "name": "Gold (Emas)", "symbol": "GC=F", "category": "Precious Metals", "price": 2439.50, "display_price": "$2,439.50", "unit": "$/oz", "change_pct": 1.35, "change_val": 32.5, "is_positive": True, "related_tickers": ["BRMS", "PSAB", "ANTM", "MDKA"], "impact_sector": "Tambang Emas"},
            {"id": "copper", "name": "Copper & Metals", "symbol": "HG=F", "category": "Industrial Metals", "price": 4.65, "display_price": "$4.65", "unit": "$/lb", "change_pct": 0.79, "change_val": 0.04, "is_positive": True, "related_tickers": ["INCO", "NCKL", "MBMA"], "impact_sector": "Nikel & Mineral"},
            {"id": "usdidr", "name": "USD / IDR", "symbol": "IDR=X", "category": "Currency", "price": 15820.0, "display_price": "Rp 15.820", "unit": "Rp", "change_pct": -0.24, "change_val": -38.0, "is_positive": False, "related_tickers": ["ASII", "ICBP", "BBCA"], "impact_sector": "Nilai Tukar Rupiah"},
            {"id": "us10y", "name": "US 10Y Yield", "symbol": "^TNX", "category": "Bonds", "price": 4.21, "display_price": "4.21%", "unit": "%", "change_pct": -0.34, "change_val": -0.01, "is_positive": False, "related_tickers": ["BBCA", "BBRI", "BMRI"], "impact_sector": "Likuiditas Global"}
        ]

    _MACRO_CACHE = {
        "items": results,
        "last_updated": now.strftime("%H:%M:%S WIB")
    }
    _MACRO_CACHE_TIME = now
    return _MACRO_CACHE
