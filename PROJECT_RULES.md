# AlphaSwing IDX - Project & UI Design Rules

## 1. Zero Emoji Policy (Strict)
- **DILARANG MENGGUNAKAN EMOJI**: Hindari penggunaan unicode emoji (seperti ⚡, 🌦️, 📈, 🏛️, 📋, 🟢, 🔴, 🟡, ⚪, 🎯, 🚀, 🧮, 📌) di seluruh antarmuka web, modal, toast, skrip GTC, maupun pesan bot Telegram.
- **SEMUA HARUS PAKAI ICON (SVG / Lucide)**: Seluruh indikator visual di UI wajib menggunakan ikon Lucide atau inline SVG yang presisi.
- **Pesan Teks / Telegram**: Gunakan tipografi institusional bersih dengan format bracket seperti `[BUY]`, `[STOP LOSS]`, `[TARGET TP1]`, `[Weekly Confirmed]`, `[STATUS BURSA]`.

## 2. Card Surface & Bezel Rules
- **No Double Borders / Double Outlines**: Dilarang membuat border bertingkat / double outline.
- Gunakan kartu `.clean-card` dengan 1 lapis border halus (`border border-slate-200 dark:border-white/[0.08]`).

## 3. Sidebar Rules
- Default sidebar berukuran mini (`w-16`) dengan floating hover tooltips yang tidak terpotong (`overflow: visible`, `z-index: 99999`).
- Header sidebar dan topbar harus sejajar presisi (`h-16` / 64px).

## 4. Institutional Light & Dark Mode
- Mode default Dark Mode OLED (`#06080F`).
- Mode Light menggunakan Clean Institutional Slate (`#F8FAFC`, kartu `#FFFFFF`, teks `#0F172A`).
