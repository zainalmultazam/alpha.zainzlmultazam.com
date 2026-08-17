import asyncio
import html
import re
from typing import Dict, Any, Optional
import httpx
from datetime import datetime

from app.config import settings
from app.services.telegram import send_telegram_message, answer_callback_query, notify_super_digest, format_rupiah_short
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

        df = fetch_stock_df(ticker)
        if df is None or df.empty:
            await send_telegram_message(f"❌ Gagal mengambil data bursa untuk ticker <b>{ticker}</b>. Pastikan simbol benar.")
            return

        df_calc = calculate_indicators(df)
        last_row = df_calc.iloc[-1]
        current_price = float(last_row["close"])
        atr = float(last_row.get("atr", current_price * 0.035))

        if len(parts) >= 4:
            try:
                entry_price = float(parts[3])
            except ValueError:
                entry_price = current_price
        else:
            entry_price = current_price

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
        msg += f"• <a href=\"https://stockbit.com/#/symbol/{ticker}\">Buka {ticker} di Stockbit</a>\n"
        msg += "────────────\n"
        msg += "🛡️ <i>Robot Sentinel aktif memantau posisi ini. Peringatan darurat akan otomatis dikirim jika harga mendekati Stop Loss!</i>"

        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": f"🔴 Tutup Posisi {ticker}", "callback_data": f"close:{ticker}"}
                ]
            ]
        }
        await send_telegram_message(msg, reply_markup=reply_markup)

    # 2. Command /jual atau /sell atau /close
    elif cmd in ["/jual", "/sell", "/close"]:
        if len(parts) < 2:
            msg = "<b>PANDUAN /jual:</b>\n"
            msg += "Format: <code>/jual [TICKER] [HARGA_JUAL]</code>\n"
            msg += "Contoh: <code>/jual AUTO 3100</code>"
            await send_telegram_message(msg)
            return

        ticker = parts[1].upper().replace(".JK", "").strip()
        
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
            msg += "Tekan tombol <b>[Beli & Catat]</b> pada rekomendasi atau ketik <code>/beli [TICKER] [LOT]</code> untuk mencatat."
            await send_telegram_message(msg)
            return

        msg = f"<b>STATUS PORTOFOLIO AKTIF ({len(open_trades)} Saham)</b>\n"
        msg += f"<i>{datetime.now().strftime('%d %b %Y %H:%M WIB')}</i>\n"
        msg += "────────────\n\n"

        inline_buttons = []
        for i, t in enumerate(open_trades, 1):
            ticker = t["ticker"]
            entry = float(t["entry_price"])
            sl = float(t["stop_loss"])
            tp = float(t["target_price"])
            lots = int(t["lots"])

            df = fetch_stock_df(ticker)
            current_price = float(df.iloc[-1]["close"]) if df is not None and not df.empty else entry
            pnl_pct = ((current_price - entry) / entry) * 100
            sign = "+" if pnl_pct >= 0 else ""

            dist_to_sl = ((current_price - sl) / current_price) * 100
            status_text = "🟢 AMAN" if current_price > entry else ("🟡 WASPADA" if dist_to_sl > 1.5 else "🔴 BAHAYA DEKAT SL")

            msg += f"<b>#{i} {ticker}</b> ({lots} Lot)\n"
            msg += f"• Beli @ Rp {entry:,.0f} | Live: <b>Rp {current_price:,.0f} ({sign}{pnl_pct:.1f}%)</b>\n"
            msg += f"• Stop Loss: Rp {sl:,.0f} | Target: Rp {tp:,.0f}\n"
            msg += f"• Status: <i>{status_text}</i> (Jarak ke SL: {dist_to_sl:.1f}%)\n"
            if i < len(open_trades):
                msg += "────────────\n\n"

            inline_buttons.append([
                {"text": f"🔴 Tutup Posisi {ticker}", "callback_data": f"close:{ticker}"}
            ])

        reply_markup = {"inline_keyboard": inline_buttons} if inline_buttons else None
        await send_telegram_message(msg, reply_markup=reply_markup)

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
        msg += "<i>Anda juga bisa langsung menekan tombol interaktif di bawah setiap rekomendasi!</i>"
        await send_telegram_message(msg)

async def process_telegram_callback(callback: Dict[str, Any]) -> None:
    """Memproses klik tombol interaktif (Inline Button Callback Query) dari Telegram."""
    callback_id = str(callback.get("id", ""))
    data = str(callback.get("data", ""))
    from_user = callback.get("from", {}).get("first_name", "Trader")

    if not data:
        return

    # 0. Callback Buka Lot Picker Grid: picklot:TICKER:RECLOTS:ENTRY:SL:TP1
    if data.startswith("picklot:"):
        parts = data.split(":")
        if len(parts) >= 6:
            ticker = parts[1]
            rec_lots = int(parts[2])
            entry = float(parts[3])
            sl = float(parts[4])
            tp1 = float(parts[5])

            await answer_callback_query(callback_id, text=f"Pilih jumlah lot {ticker}...", show_alert=False)

            half_lots = max(1, rec_lots // 2)
            
            # Buat opsi tombol lot yang dinamis dan bervariasi
            lot_options = [half_lots, rec_lots, 10, 25, 50, 100]
            # Hapus duplikat dan urutkan
            unique_lots = sorted(list(set([l for l in lot_options if l > 0])))

            msg = f"<b>PILIH JUMLAH LOT: {ticker}</b>\n"
            msg += f"<i>Harga Entry: Rp {entry:,.0f} | Stop Loss: Rp {sl:,.0f}</i>\n"
            msg += "────────────\n"
            msg += "Pilih jumlah lot yang Anda beli di Stockbit:\n"

            inline_keyboard = []
            
            # Baris 1: Preset Rekomendasi
            row_rec = [
                {"text": f"🛒 {rec_lots} Lot (Rekomendasi)", "callback_data": f"buy:{ticker}:{rec_lots}:{entry}:{sl}:{tp1}"}
            ]
            if half_lots != rec_lots:
                row_rec.insert(0, {"text": f"🛒 {half_lots} Lot (50%)", "callback_data": f"buy:{ticker}:{half_lots}:{entry}:{sl}:{tp1}"})
            inline_keyboard.append(row_rec)

            # Baris 2: Pilihan Angka Bulat Populer
            row_numbers = []
            for l in [10, 25, 50, 100]:
                if l != rec_lots and l != half_lots:
                    row_numbers.append({"text": f"{l} Lot", "callback_data": f"buy:{ticker}:{l}:{entry}:{sl}:{tp1}"})
            if row_numbers:
                inline_keyboard.append(row_numbers[:4])

            # Baris 3: Custom Input
            inline_keyboard.append([
                {"text": "✏️ Ketik Jumlah Lot Lain", "callback_data": f"customlot:{ticker}:{entry}:{sl}:{tp1}"}
            ])

            reply_markup = {"inline_keyboard": inline_keyboard}
            await send_telegram_message(msg, reply_markup=reply_markup)
            return

    # 0.1 Callback Petunjuk Custom Lot: customlot:TICKER:ENTRY:SL:TP1
    elif data.startswith("customlot:"):
        parts = data.split(":")
        ticker = parts[1]
        await answer_callback_query(callback_id, text=f"Ketik /beli {ticker} [LOT]", show_alert=False)
        msg = f"<b>INPUT JUMLAH LOT CUSTOM: {ticker}</b>\n"
        msg += "────────────\n"
        msg += "Ketik perintah berikut di chat dengan jumlah lot yang Anda beli:\n"
        msg += f"<code>/beli {ticker} [JUMLAH_LOT]</code>\n\n"
        msg += f"Contoh: <code>/beli {ticker} 15</code>"
        await send_telegram_message(msg)
        return

    # 1. Callback 1-Click Beli: buy:TICKER:LOTS:ENTRY:SL:TP1
    elif data.startswith("buy:"):
        parts = data.split(":")
        if len(parts) >= 6:
            ticker = parts[1]
            lots = int(parts[2])
            entry = float(parts[3])
            sl = float(parts[4])
            tp1 = float(parts[5])

            # Jawab callback pop-up
            await answer_callback_query(callback_id, text=f"✅ {ticker} ({lots} Lot) berhasil dicatat & dipantau!", show_alert=False)

            # Catat ke Database
            trade_id = log_trade(
                ticker=ticker,
                entry_price=entry,
                stop_loss=sl,
                target_price=tp1,
                lots=lots,
                setup_name="1-Click Button"
            )

            total_cost = lots * 100 * entry
            max_risk = lots * 100 * (entry - sl)
            cost_str = format_rupiah_short(total_cost)
            risk_str = format_rupiah_short(max_risk)

            msg = f"<b>1-CLICK BUY TERCATAT & DIAWASI</b>\n"
            msg += f"<i>Eksekusi oleh: {from_user} • ID: #{trade_id}</i>\n"
            msg += "────────────\n"
            msg += f"Saham      : <b>{ticker}</b> ({lots} Lot)\n"
            msg += f"Harga Beli : Rp {entry:,.0f}\n"
            msg += f"Stop Loss  : Rp {sl:,.0f} (-{((entry - sl)/entry)*100:.1f}%)\n"
            msg += f"Target TP1 : Rp {tp1:,.0f} (+{((tp1 - entry)/entry)*100:.1f}%)\n"
            msg += f"Total Beli : <b>{cost_str}</b> (Max Risiko: {risk_str})\n"
            msg += f"• <a href=\"https://stockbit.com/#/symbol/{ticker}\">Buka {ticker} di Stockbit</a>\n"
            msg += "────────────\n"
            msg += "🛡️ <i>Radar Safety Sentinel aktif memantau saham ini dari risiko!</i>"

            reply_markup = {
                "inline_keyboard": [
                    [
                        {"text": f"🔴 Tutup Posisi {ticker}", "callback_data": f"close:{ticker}"}
                    ]
                ]
            }
            await send_telegram_message(msg, reply_markup=reply_markup)

    # 2. Callback 1-Click Tutup / Cut Loss / Jual: close:TICKER
    elif data.startswith("close:") or data.startswith("sl:"):
        ticker = data.split(":")[1]
        await answer_callback_query(callback_id, text=f"Menutup posisi {ticker}...", show_alert=False)

        df = fetch_stock_df(ticker)
        exit_price = float(df.iloc[-1]["close"]) if df is not None and not df.empty else 0.0

        if exit_price > 0:
            closed_trade = close_open_trade_by_ticker(ticker, exit_price, notes="1-Click Telegram Close")
            if closed_trade:
                pnl_amt = closed_trade["pnl_amount"]
                pnl_pct = closed_trade["pnl_pct"]
                sign = "+" if pnl_amt >= 0 else ""
                badge = "PROFIT" if pnl_amt >= 0 else "CUT LOSS"

                msg = f"<b>TRADE CLOSED VIA 1-CLICK: [{badge}]</b>\n"
                msg += f"<i>{ticker} • Ditutup oleh: {from_user}</i>\n"
                msg += "────────────\n"
                msg += f"Beli @ Rp {closed_trade['entry_price']:,.0f} ({closed_trade['lots']} Lot)\n"
                msg += f"Jual @ Rp {exit_price:,.0f}\n"
                msg += f"Hasil PnL : <b>{sign}{pnl_pct:.2f}% ({sign}Rp {abs(pnl_amt):,.0f})</b>\n"
                msg += "────────────\n"
                msg += "✅ <i>Riwayat jurnal dan win rate portofolio berhasil diperbarui.</i>"
                await send_telegram_message(msg)
            else:
                await send_telegram_message(f"ℹ️ Posisi {ticker} sudah tidak berstatus OPEN di database.")

    # 3. Callback 1-Click Amankan TP1: tp:TICKER
    elif data.startswith("tp:"):
        ticker = data.split(":")[1]
        await answer_callback_query(callback_id, text=f"✅ Target TP1 {ticker} dikonfirmasi!", show_alert=False)
        msg = f"🎯 <b>KONFIRMASI TAKE PROFIT 1: {ticker}</b>\n"
        msg += "────────────\n"
        msg += "1. Amankan 50% lot di aplikasi sekuritas.\n"
        msg += "2. Geser Stop Loss sisa lot ke harga modal (Breakeven) agar menjadi trade bebas risiko!"
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
            msg += "Buka aplikasi sekuritas Anda dan lakukan Cut Loss manual untuk melindungi sisa modal!\n"
            msg += f"• <a href=\"https://stockbit.com/#/symbol/{ticker}\">Buka {ticker} di Stockbit</a>"

            reply_markup = {
                "inline_keyboard": [
                    [
                        {"text": f"🔴 Konfirmasi Cut Loss Selesai", "callback_data": f"close:{ticker}"}
                    ]
                ]
            }
            await send_telegram_message(msg, reply_markup=reply_markup)

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
            msg += f"1. Jual 50% posisi ({half_lots} Lot) untuk amankan profit.\n"
            msg += f"2. Geser Stop Loss sisa lot ke Rp {entry:,.0f} (Breakeven/Modal) agar bebas risiko!\n"
            msg += f"• <a href=\"https://stockbit.com/#/symbol/{ticker}\">Buka {ticker} di Stockbit</a>"

            reply_markup = {
                "inline_keyboard": [
                    [
                        {"text": f"🎯 Konfirmasi Amankan Profit", "callback_data": f"tp:{ticker}"}
                    ]
                ]
            }
            await send_telegram_message(msg, reply_markup=reply_markup)

async def telegram_polling_worker():
    """Background worker untuk mendengarkan pesan masuk dan klik tombol dari Telegram (Long Polling)."""
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
                        
                        # 1. Cek Pesan Teks
                        msg_obj = update.get("message") or update.get("channel_post")
                        if msg_obj and "text" in msg_obj:
                            chat_id = str(msg_obj["chat"]["id"])
                            text = msg_obj["text"]
                            asyncio.create_task(process_telegram_command(text, chat_id))

                        # 2. Cek Klik Tombol Interaktif (Callback Query)
                        callback_obj = update.get("callback_query")
                        if callback_obj:
                            asyncio.create_task(process_telegram_callback(callback_obj))
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
