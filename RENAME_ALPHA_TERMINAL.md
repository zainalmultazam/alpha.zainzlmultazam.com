# Rename konsisten ke "Alpha" (revisi — "Alpha Terminal" dibatalkan)

> Dokumen ini menggantikan versi sebelumnya di file yang sama. Keputusan final: nama produk = **"Alpha"** saja, tanpa tambahan kata apapun.

Kabar baiknya: sebagian besar codebase kamu udah lebih dulu pakai "Alpha" polos (`config.py`, `PROJECT_RULES.md`, semua `index.html`). Yang perlu disamakan cuma 5 titik yang masih nyebut "AlphaSwing IDX" atau "Alpha Terminal".

## Yang perlu diubah

| File | Baris | Dari | Ke |
|---|---|---|---|
| `README.md` | 1 | `# ⚡ AlphaSwing IDX - Personal Swing Trading Platform` | `# Alpha - Personal Swing Trading Platform` |
| `.env.example` | 1 | `APP_NAME=AlphaSwing IDX` | `APP_NAME=Alpha` |
| `app/__init__.py` | 1 | `# AlphaSwing IDX Package` | `# Alpha Package` |
| `app/routers/telegram.py` | 40 | `"🌐 Buka Alpha Terminal"` | `"🌐 Buka Alpha"` |
| `app/services/telegram.py` | 226 | `Buka Alpha Terminal</a>` | `Buka Alpha</a>` |

## Sudah benar, jangan disentuh

`app/config.py:5`, `PROJECT_RULES.md:1`, `.env:1`, `app/templates/index.html` (title, meta tags, logo di baris 526 & 706) — semuanya udah "Alpha" polos.

## Satu hal yang tetap perlu kamu putuskan

`app/templates/index.html:1204` — teks **"AI Alpha Pattern Insights"**. Ini bukan soal branding lagi, ini murni soal makna: "Alpha" di situ kemungkinan besar istilah trading (excess return), bukan nama produk. Begitu brand-nya persis "Alpha" tanpa tambahan apapun, kalimat itu jadi 100% ambigu — pembaca nggak bisa lagi bedain "fitur dari Alpha (produk)" vs "insight yang menghasilkan alpha (istilah)". Ini bukan hal yang bisa dihindari dengan strategi cari-ganti; ini konsekuensi langsung dari keputusan nama. Kalau kamu nggak masalah sama ambiguitas ini, biarkan saja — cuma perlu kamu sadari itu trade-off yang kamu ambil, bukan bug yang kelewat.
