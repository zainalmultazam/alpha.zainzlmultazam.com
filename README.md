# Alpha - Personal Swing Trading Platform

Platform Quant & Swing Trading Otomatis untuk Saham Likuid Bursa Efek Indonesia (IDX).  
Domain: **[alpha.zainalmultazam.com](https://alpha.zainalmultazam.com)**

---

## 🌟 Fitur Utama
1. **Automated Screener**: Memindai 150+ saham likuid IDX (LQ45 / Kompas100) menggunakan strategi **Stage 2 Super Trend, VCP (Volatility Contraction Pattern), EMA 20/50 Pullback, dan Smart Money Volume Surge**.
2. **Dynamic Position Sizing**: Kalkulator lot otomatis dengan manajemen risiko ketat (maksimal 1% modal portofolio per transaksi).
3. **Interactive TradingView Chart**: Grafik Candlestick harian interaktif + volume histogram langsung di dashboard.
4. **Trading Journal & Tracker**: Pencatatan riwayat transaksi open/closed dan kalkulasi PnL otomatis via SQLite.
5. **Scheduled Daily Scan & Telegram Bot**: Notifikasi otomatis Top 5 Alpha Picks setiap pukul 17:00 WIB setelah pasar tutup.

---

## 🛠️ Menjalankan di Komputer Lokal

### 1. Buat Virtual Environment & Install Dependencies
```bash
python3 -m venv venv
source venv/bin/activate  # Untuk Mac / Linux
# venv\Scripts\activate   # Untuk Windows

pip install -r requirements.txt
```

### 2. Konfigurasi Environment
Salin `.env.example` ke `.env`:
```bash
cp .env.example .env
```

### 3. Jalankan Server FastAPI
```bash
uvicorn app.main:app --reload --port 8000
```
Buka browser di: `http://localhost:8000`

---

## 🐳 Menjalankan Menggunakan Docker

```bash
docker compose up -d --build
```
Akses platform di: `http://localhost:8000`

---

## 🌐 Setup DNS Subdomain (alpha.zainalmultazam.com)

Di dashboard DNS (Cloudflare / cPanel / Provider Domain):
1. Tambahkan **A Record**:
   - **Type**: `A`
   - **Name**: `alpha`
   - **Target / IPv4**: `<IP_VPS_ANDA>`
   - **Proxy**: `Proxied (Cloudflare CDN / SSL Otomatis)`
