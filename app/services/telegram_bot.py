import asyncio
import html
import re
from typing import Dict, Any, Optional
import httpx
from datetime import datetime

from app.config import settings
from app.services.telegram import send_telegram_message, notify_super_digest, format_rupiah_short
from app.services.market_data import fetch_stock_df, get_market_climate
from app.engine.technical import calculate_indicators
from app.engine.strategy import generate_trade_plan
from app.engine.journal import log_trade, get_open_trades, close_open_trade_by_ticker, get_journal_stats
from app.engine.scanner import scan_stock, run_full_scan

_last_update_id = 0
_alerted_trades = set()  # prevent spamming same alert repeatedly

async def process_telegram_command(text: str, chat_id: str) -> None:
    """Memproses command teks yang dikirimkan user di grup/chat Telegram."""
    raw_text = text.strip()
    if not raw_text.startswith("/"):
        return

    parts = raw_text.split()
    cmd = parts[0].lower().replace("@" + (settings.TELEGRAM_BOT_TOKEN.split(":")[0] if settings.TELEGRAM_BOT_TOKEN else ""), "")

    # 1. Command /beli atau /buy
    if cmd in ["/beli", "/buy"]:
        # Format: /beli AUTO 35 [optional_entry] [optional_sl]
        if len(parts) < 3:
            msg = "<b>PANDUAN /beli:</b>\n"
            msg += "Format: <code>/beli [TICKER] [JUMLAH_LOT]</code>\n"
            msg += "Contoh: <code>/beli AUTO 35</code>"
            await send_telegram_message(msg)
            return

        ticker = parts[1].upper().replace(".JK", "").strip()
        try:
            lots = int(parts[2].replace("lot", "").replace("LOT", "").strip())
        except ValueError:
            await send_telegram_message("❌ Jumlah lot harus berupa angka bulat. Contoh: <code>/beli AUTO 35</code>")
            return

        # Ambil data teknikal saham live untuk mendapatkan harga Entry, SL, dan TP otomatis
        df = fetch_stock_df(ticker)
        if df is None or df.empty:
            await send_telegram_message(f"❌ Gagal mengambil data bursa untuk ticker <b>{ticker}</b>. Pastikan simbol benar.")
            return

        df_calc = calculate_indicators(df)
        last_row = df_calc.iloc[-1]
        current_price = float(last_row["close"])
        atr = float(last_row.get("atr", current_price * 0.035))

        # Jika user memasukkan harga entry manual
        if len(parts) >= 4:
            try:
                entry_price = float(parts[3])
            except ValueError:
                entry_price = current_price
        else:
            entry_price = current_price

        # Generate Trading Plan
        plan = generate_trade_plan(entry_price, atr, "Manual / Telegram")
        sl_price = float(parts[4]) if len(parts) >= 5 else float(plan["stop_loss"])
        tp1_price = float(plan["tp1"])

        # Catat ke Database Terpusat (alpha.db)
        trade_id = log_trade(
            ticker=ticker,
            entry_price=entry_price,
            stop_loss=sl_price,
            target_price=tp1_price,
            lots=lots,
            setup_name="Telegram Entry"
        )

        total_cost = lots * 100 * entry_price
        max_risk = lots * 100 * (entry_price - sl_price)
        cost_str = format_rupiah_short(total_cost)
        risk_str = format_rupiah_short(max_risk)

        msg = f"<b>POSISI TERCATAT & DALAM PENGAWASAN</b>\n"
        msg += f"<i>ID Trade: #{trade_id} • {datetime.now().strftime('%d %b %Y %H:%M WIB')}</i>\n"
        msg += "────────────\n"
        msg += f"Saham      : <b>{ticker}</b> ({lots} Lot)\n"
        msg += f"Harga Beli : Rp {entry_price:,.0f}\n"
        msg += f"Stop Loss  : Rp {sl_price:,.0f} (-{((entry_price - sl_price)/entry_price)*100:.1f}%)\n"
        msg += f"Target TP1 : Rp {tp1_price:,.0f} (+{((tp1_price - entry_price)/entry_price)*100:.1f}%)\n"
        msg += f"Total Beli : <b>{cost_str}</b> (Max Risiko: {risk_str})\n"
        msg += "────────────\n"
        msg += "🛡️ <i>Robot Sentinel aktif memantau posisi ini. Peringatan darurat akan otomatis dikirim jika harga mendekati Stop Loss!</i>\n"
        msg += f"• <a href=\"https://stockbit.com/#/symbol/{ticker}\">Buka {ticker} di Stockbit</a>"
        await send_telegram_message(msg)

    # 2. Command /jual atau /sell atau /close
    elif cmd in ["/jual", "/sell", "/close"]:
        # Format: /jual AUTO [optional_harga_jual]
        if len(parts) < 2:
            msg = "<b>PANDUAN /jual:</b>\n"
            msg += "Format: <code>/jual [TICKER] [HARGA_JUAL]</code>\n"
            msg += "Contoh: <code>/jual AUTO 3100</code>"
            await send_telegram_message(msg)
            return

        ticker = parts[1].upper().replace(".JK", "").strip()
        
        # Cari harga exit
        if len(parts) >= 3:
            try:
                exit_price = float(parts[2])
            except ValueError:
                exit_price = None
        else:
            exit_price = None

        if exit_price is None:
            df = fetch_stock_df(ticker)
            if df is not None and not df.empty:
                exit_price = float(df.iloc[-1]["close"])
            else:
                exit_price = 0.0

        if exit_price <= 0:
            await send_telegram_message(f"❌ Masukkan harga jual. Contoh: <code>/jual {ticker} 3100</code>")
            return

        closed_trade = close_open_trade_by_ticker(ticker, exit_price)
        if not closed_trade:
            await send_telegram_message(f"❌ Tidak ditemukan posisi OPEN untuk saham <b>{ticker}</b> di database.")
            return

        pnl_amt = closed_trade["pnl_amount"]
        pnl_pct = closed_trade["pnl_pct"]
        sign = "+" if pnl_amt >= 0 else ""
        badge = "PROFIT" if pnl_amt >= 0 else "CUT LOSS"
        pnl_str = format_rupiah_short(abs(pnl_amt))

        msg = f"<b>TRADE CLOSED: [{badge}]</b>\n"
        msg += f"<i>{ticker} • {datetime.now().strftime('%d %b %Y %H:%M WIB')}</i>\n"
        msg += "────────────\n"
        msg += f"Beli @ Rp {closed_trade['entry_price']:,.0f} ({closed_trade['lots']} Lot)\n"
        msg += f"Jual @ Rp {exit_price:,.0f}\n"
        msg += f"Hasil PnL  : <b>{sign}{pnl_pct:.2f}% ({sign}Rp {abs(pnl_amt):,.0f})</b>\n"
        msg += "────────────\n"
        msg += "✅ <i>Data tersimpan ke Jurnal Riwayat Performance Portofolio.</i>"
        await send_telegram_message(msg)

    # 3. Command /posisi atau /portfolio atau /status
    elif cmd in ["/posisi", "/portfolio", "/status"]:
        open_trades = get_open_trades()
        if not open_trades:
            msg = "<b>STATUS PORTOFOLIO AKTIF:</b>\n"
            msg += "────────────\n"
            msg += "Tidak ada posisi terbuka saat ini.\n"
            msg += "Gunakan <code>/beli [TICKER] [LOT]</code> untuk mencatat posisi baru."
            await send_telegram_message(msg)
            return

        msg = f"<b>STATUS PORTOFOLIO AKTIF ({len(open_trades)} Saham)</b>\n"
        msg += f"<i>{datetime.now().strftime('%d %b %Y %H:%M WIB')}</i>\n"
        msg += "────────────\n\n"

        for i, t in enumerate(open_trades, 1):
            ticker = t["ticker"]
            entry = float(t["entry_price"])
            sl = float(t["stop_loss"])
            tp = float(t["target_price"])
            lots = int(t["lots"])

            # Cek harga live
            df = fetch_stock_df(ticker)
            current_price = float(df.iloc[-1]["close"]) if df is not None and not df.empty else entry
            pnl_pct = ((current_price - entry) / entry) * 100
            sign = "+" if pnl_pct >= 0 else ""

            # Hitung jarak ke SL
            dist_to_sl = ((current_price - sl) / current_price) * 100
            status_text = "🟢 AMAN" if current_price > entry else ("🟡 WASPADA" if dist_to_sl > 1.5 else "🔴 BAHAYA DEKAT SL")

            msg += f"<b>#{i} {ticker}</b> ({lots} Lot)\n"
            msg += f"• Beli @ Rp {entry:,.0f} | Live: <b>Rp {current_price:,.0f} ({sign}{pnl_pct:.1f}%)</b>\n"
            msg += f"• Stop Loss: Rp {sl:,.0f} | Target: Rp {tp:,.0f}\n"
            msg += f"• Status: <i>{status_text}</i> (Jarak ke SL: {dist_to_sl:.1f}%)\n"
            msg += f"• <a href=\"https://stockbit.com/#/symbol/{ticker}\">Buka {ticker} di Stockbit</a>\n"
            if i < len(open_trades):
                msg += "────────────\n\n"

        await send_telegram_message(msg)

    # 4. Command /scan atau /top3
    elif cmd in ["/scan", "/top3"]:
        await send_telegram_message("🔍 <i>Sedang menjalankan scan bursa real-time... Mohon tunggu sebentar.</i>")
        picks = run_full_scan()
        climate = get_market_climate()
        await notify_super_digest(picks[:3], climate)

    # 5. Command /help atau /start atau /menu
    elif cmd in ["/help", "/start", "/menu"]:
        msg = "<b>PANDUAN PERINTAH BOT TELEGRAM:</b>\n"
        msg += "────────────\n"
        msg += "• <code>/beli AUTO 35</code> : Catat beli saham & aktifkan pengawas bahaya\n"
        msg += "• <code>/jual AUTO 3100</code> : Catat jual saham & hitung profit/loss\n"
        msg += "• <code>/posisi</code> : Cek status semua saham yang sedang dipegang\n"
        msg += "• <code>/top3</code> : Jalankan scanner & kirim 3 rekomendasi terbaik\n"
        msg += "• <code>/help</code> : Menampilkan menu panduan ini\n"
        msg += "────────────\n"
        msg += "<i>Semua transaksi otomatis tersinkronisasi ke web terminal.</i>"
        await send_telegram_message(msg)

async def run_safety_sentinel_check() -> None:
    """Memeriksa seluruh posisi OPEN untuk mengirimkan alert bahaya jika menembus SL atau alert TP1."""
    open_trades = get_open_trades()
    if not open_trades:
        return

    for t in open_trades:
        trade_id = t["id"]
        ticker = t["ticker"]
        entry = float(t["entry_price"])
        sl = float(t["stop_loss"])
        tp = float(t["target_price"])
        lots = int(t["lots"])

        df = fetch_stock_df(ticker)
        if df is None or df.empty:
            continue

        current_price = float(df.iloc[-1]["close"])

        # 1. ALERT DARURAT: Harga menyentuh atau menembus Stop Loss
        if current_price <= sl and (trade_id, "SL") not in _alerted_trades:
            _alerted_trades.add((trade_id, "SL"))
            pnl_amt = (current_price - entry) * (lots * 100)
            pnl_pct = ((current_price - entry) / entry) * 100

            msg = f"🚨 <b>PERINGATAN DARURAT: {ticker}</b>\n"
            msg += f"<i>Harga saat ini menembus batas Stop Loss!</i>\n"
            msg += "────────────\n"
            msg += f"Saham             : <b>{ticker}</b> ({lots} Lot)\n"
            msg += f"Harga Beli        : Rp {entry:,.0f}\n"
            msg += f"Harga Live        : <b>Rp {current_price:,.0f}</b>\n"
            msg += f"Batas Stop Loss   : Rp {sl:,.0f}\n"
            msg += f"Floating Loss     : <b>{pnl_pct:.2f}% (-Rp {abs(pnl_amt):,.0f})</b>\n"
            msg += "────────────\n"
            msg += "<b>TINDAKAN SEGERA:</b>\n"
            msg += "Buka aplikasi Stockbit sekarang dan lakukan Cut Loss manual untuk melindungi sisa modal Anda!\n\n"
            msg += f"• <a href=\"https://stockbit.com/#/symbol/{ticker}\">Buka {ticker} di Stockbit</a>"
            await send_telegram_message(msg)

        # 2. ALERT PROFIT: Harga menyentuh Target TP1
        elif current_price >= tp and (trade_id, "TP") not in _alerted_trades:
            _alerted_trades.add((trade_id, "TP"))
            half_lots = max(1, lots // 2)
            pnl_pct = ((current_price - entry) / entry) * 100

            msg = f"🎯 <b>TARGET TP1 TERCAPAI: {ticker}</b>\n"
            msg += f"<i>Harga saat ini telah mencapai target Take Profit 1!</i>\n"
            msg += "────────────\n"
            msg += f"Saham        : <b>{ticker}</b> ({lots} Lot)\n"
            msg += f"Harga Beli   : Rp {entry:,.0f}\n"
            msg += f"Harga Live   : <b>Rp {current_price:,.0f} (+{pnl_pct:.2f}%)</b>\n"
            msg += "────────────\n"
            msg += "<b>PANDUAN EKSEKUSI:</b>\n"
            msg += f"1. Jual 50% posisi ({half_lots} Lot) di Stockbit untuk amankan profit.\n"
            msg += f"2. Geser Stop Loss sisa lot ke Rp {entry:,.0f} (Breakeven/Modal) agar bebas risiko!\n\n"
            msg += f"• <a href=\"https://stockbit.com/#/symbol/{ticker}\">Buka {ticker} di Stockbit</a>"
            await send_telegram_message(msg)

async def telegram_polling_worker():
    """Background worker untuk mendengarkan pesan masuk dari Telegram (Long Polling)."""
    global _last_update_id
    if not settings.TELEGRAM_BOT_TOKEN:
        return

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getUpdates"
    
    while True:
        try:
            params = {"offset": _last_update_id + 1, "timeout": 20}
            async with httpx.AsyncClient() as client:
                res = await client.get(url, params=params, timeout=25.0)
                if res.status_code == 200:
                    data = res.json()
                    for update in data.get("result", []):
                        _last_update_id = update["update_id"]
                        
                        # Cek pesan
                        msg_obj = update.get("message") or update.get("channel_post")
                        if msg_obj and "text" in msg_obj:
                            chat_id = str(msg_obj["chat"]["id"])
                            text = msg_obj["text"]
                            # Proses perintah asinkron
                            asyncio.create_task(process_telegram_command(text, chat_id))
        except Exception as e:
            await asyncio.sleep(5)
        await asyncio.sleep(1)

async def sentinel_scheduler_worker():
    """Background worker untuk memantau keselamatan posisi setiap 15 menit."""
    while True:
        try:
            await run_safety_sentinel_check()
        except Exception as e:
            pass
        await asyncio.sleep(900)  # Cek setiap 15 menit
