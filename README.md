# Sistem Cerdas Dashboard Performa, Kuota Target Harian, Perhitungan Komisi & Bot Telegram Telesales ISP

Sistem terintegrasi berbasis **Python 3.12**, **Streamlit**, **Pandas**, **Pillow (PIL)**, **pyTelegramBotAPI (`telebot`)**, dan **CustomTkinter** untuk mengotomatisasi pelacakan performa *Month-to-Date (MTD)* Sales Active (SA), evaluasi kuota wajib harian (`Harus Paid / Hari` & `Harus SA / Hari`) bagi agen yang secara persentase masih di bawah target berjalan, perhitungan komisi bulanan (potong PPN 11%, tier 35% vs 20%), serta pengiriman laporan visual (Gambar Presentasi `.png` + Teks HTML) ke Bot Telegram.

---

## Struktur File Proyek (`D:\Skripsi_Komisi_Telesales`)

```text
D:\Skripsi_Komisi_Telesales\
├── .venv\                        # Virtual environment Python 3.12
├── app.py                        # [MODUL UTAMA] Web Dashboard Streamlit (MTD SA, Detail Agent, Kuota Harian, Tab Harian, AI Chatbot & Push Telegram)
├── gambar_laporan.py             # [MODUL VISUAL] Generator Gambar Presentasi Laporan (Pillow PNG): Tabel MTD SA & Detail Agent per Leader
├── bot_interaktif.py             # [MODUL BOT] Layanan Bot Telegram Interaktif 2-Arah (/target, /cektarget, /id) dengan Data Access Control
├── main.py                       # [MODUL DESKTOP] Aplikasi Desktop GUI (CustomTkinter Dark Mode)
├── logic_komisi.py               # [MODUL LOGIKA] Mesin pembacaan file Excel/HTML fleksibel & fungsi hitung_komisi()
├── TARGET PER MONTH.xlsx         # Dataset Master Target Bulanan Agen & Struktur Tim (Multi-Sheet: NOVEMBER'26, dll.)
├── data_target.xlsx              # Dataset Target Total Eksklusif Tim ALPHA WOLF SQUAD (Sinkronisasi Bot Interaktif)
├── list_prospect September.xls   # Dataset Prospek CRM Bulan September (Format HTML .xls)
├── list_prospect Oktober.xls     # Dataset Prospek CRM Bulan Oktober (Format HTML .xls)
├── list_prospect November.xls    # Dataset Prospek CRM Bulan November (Format HTML .xls)
├── jalankan_semua.bat            # Pintasan 1-Klik: Menyalakan Bot Telegram + Web Dashboard Streamlit secara bersamaan
├── jalankan_streamlit.bat        # Pintasan 1-Klik: Menyalakan Web Dashboard Streamlit (http://localhost:8501)
├── jalankan_bot.bat              # Pintasan 1-Klik: Menyalakan Bot Telegram Interaktif
├── jalankan_aplikasi.bat         # Pintasan 1-Klik: Menyalakan Aplikasi Desktop CustomTkinter
├── requirements.txt              # Daftar pustaka Python yang digunakan
├── PRD.md                        # Product Requirements Document (PRD) Versi 3.0 (Edisi Sinkronisasi Skripsi)
└── README.md                     # Panduan penggunaan proyek
```

---

## Cara Menjalankan Sistem

### 1. Menjalankan Web Dashboard + Bot Telegram Sekaligus (Direkomendasikan)
Klik 2x pada file **`jalankan_semua.bat`**, atau jalankan lewat terminal:
```powershell
D:\Skripsi_Komisi_Telesales\.venv\Scripts\streamlit.exe run D:\Skripsi_Komisi_Telesales\app.py
```
Buka di browser: **http://localhost:8501**

### 2. Menjalankan Bot Telegram Interaktif (`/target` & `/cektarget`)
Klik 2x pada file **`jalankan_bot.bat`**, atau jalankan lewat terminal:
```powershell
D:\Skripsi_Komisi_Telesales\.venv\Scripts\python.exe D:\Skripsi_Komisi_Telesales\bot_interaktif.py
```

### 3. Menjalankan Aplikasi Desktop GUI (CustomTkinter)
Klik 2x pada file **`jalankan_aplikasi.bat`**, atau jalankan lewat terminal:
```powershell
D:\Skripsi_Komisi_Telesales\.venv\Scripts\python.exe D:\Skripsi_Komisi_Telesales\main.py
```
