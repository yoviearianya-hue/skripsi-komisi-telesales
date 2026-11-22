import calendar
import datetime
import io
import json
import math
import os
import re
import numpy as np
import pandas as pd
import requests
import streamlit as st

from gambar_laporan import (
    buat_gambar_wo_kartu_agent,
    buat_semua_gambar_laporan,
    buat_semua_gambar_wo,
)
from security_firewall import (
    MAKS_GAGAL_LOGIN,
    baca_log_keamanan_terbaru,
    catat_gagal_login,
    cek_status_lockout,
    decrypt_vault,
    muat_config_roles,
    muat_config_superadmin,
    periksa_input_waf,
    reset_gagal_login,
    username_super_admin,
    verifikasi_peran_non_admin,
    verifikasi_super_admin,
)

# Cek ketersediaan library opsional PandasAI untuk Tab Chatbot
try:
    from pandasai import SmartDataframe as PandasAISmartDataframe  # type: ignore

    PANDASAI_TERSEDIA = True
except ImportError:
    PandasAISmartDataframe = None
    PANDASAI_TERSEDIA = False

# Konfigurasi Halaman Utama Streamlit (Layout Wide)
st.set_page_config(
    page_title="Dashboard Telesales ISP — Executive Portal & Commission System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# CUSTOM CSS UI/UX MODERN & ELEGAN (EXECUTIVE DASHBOARD THEME)
# =============================================================================

st.markdown(
    """
    <style>
    /* Typography & Spacing */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2.5rem !important;
    }

    /* Executive Hero Banner */
    .exec-hero {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 55%, #312e81 100%);
        border-radius: 16px;
        padding: 22px 28px;
        color: #ffffff;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.25);
        margin-bottom: 20px;
        border: 1px solid rgba(255, 255, 255, 0.12);
    }
    .exec-hero-title {
        font-size: 1.55rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin: 0 0 6px 0;
        color: #ffffff;
    }
    .exec-hero-sub {
        font-size: 0.92rem;
        color: #cbd5e1;
        margin: 0 0 14px 0;
    }
    .exec-badges {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        align-items: center;
    }
    .exec-badge {
        background: rgba(255, 255, 255, 0.13);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: #f8fafc;
        padding: 5px 13px;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 600;
    }
    .exec-badge-target {
        background: linear-gradient(135deg, #be123c 0%, #881337 100%);
        border: 1px solid #fda4af;
        color: #ffffff;
        padding: 5px 14px;
        border-radius: 999px;
        font-size: 0.83rem;
        font-weight: 700;
    }

    /* Metric Cards Styling */
    div[data-testid="stMetric"] {
        background: rgba(148, 163, 184, 0.08);
        border: 1px solid rgba(148, 163, 184, 0.22);
        border-top: 4px solid #2563eb;
        border-radius: 12px;
        padding: 14px 18px;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
    }
    div[data-testid="stMetricLabel"] {
        font-weight: 600 !important;
        font-size: 0.85rem !important;
    }

    /* Section Header Pill */
    .section-card-header {
        background: linear-gradient(90deg, #1e293b 0%, #334155 100%);
        color: #ffffff;
        padding: 12px 20px;
        border-radius: 12px;
        margin-top: 8px;
        margin-bottom: 14px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-left: 5px solid #3b82f6;
        box-shadow: 0 4px 10px rgba(15, 23, 42, 0.12);
    }
    .section-card-title {
        font-size: 1.08rem;
        font-weight: 700;
        margin: 0;
    }
    .section-card-sub {
        font-size: 0.8rem;
        color: #cbd5e1;
        margin: 2px 0 0 0;
    }

    /* Target Maroon Box (Sesuai Gambar 1) */
    .target-maroon-box {
        display: inline-block;
        border: 2px solid #4a1525;
        border-radius: 10px;
        overflow: hidden;
        margin-bottom: 14px;
        box-shadow: 0 4px 12px rgba(107, 29, 54, 0.25);
    }
    .target-maroon-top {
        background-color: #6b1d36;
        color: #ffffff;
        font-weight: 800;
        text-align: center;
        padding: 5px 32px;
        font-size: 14px;
        letter-spacing: 0.08em;
        border-bottom: 1px solid #993355;
    }
    .target-maroon-bottom {
        display: flex;
        background-color: #58152b;
        color: #ffffff;
        font-weight: 800;
        font-size: 16px;
    }
    .target-maroon-date {
        padding: 7px 26px;
        border-right: 1px solid #993355;
    }
    .target-maroon-pct {
        padding: 7px 30px;
        color: #fde047;
    }

    /* Login Card */
    .login-hero {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 60%, #1d4ed8 100%);
        padding: 28px 30px;
        border-radius: 18px;
        color: white;
        text-align: center;
        margin-bottom: 22px;
        box-shadow: 0 12px 30px rgba(15, 23, 42, 0.28);
        border: 1px solid rgba(255, 255, 255, 0.15);
    }
    .login-hero h1 {
        font-size: 1.75rem;
        font-weight: 800;
        margin: 0 0 8px 0;
        color: #ffffff;
    }
    .login-hero p {
        font-size: 0.95rem;
        color: #dbeafe;
        margin: 0;
    }

    /* Sidebar Profile Box */
    .sidebar-profile {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid rgba(148, 163, 184, 0.25);
        border-radius: 12px;
        padding: 14px 16px;
        color: #f8fafc;
        margin-bottom: 12px;
    }
    .sidebar-profile-name {
        font-size: 1.0rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 4px;
    }
    .sidebar-profile-role {
        display: inline-block;
        background: #2563eb;
        color: #ffffff;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 2px 10px;
        border-radius: 999px;
        margin-bottom: 6px;
    }
    .sidebar-profile-scope {
        font-size: 0.8rem;
        color: #cbd5e1;
    }

    /* Agent Spotlight Card */
    .agent-spotlight {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 14px;
        padding: 18px 22px;
        color: #f8fafc;
        border-left: 6px solid #10b981;
        margin-bottom: 18px;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.18);
    }
    .agent-spotlight-warn {
        border-left: 6px solid #ef4444 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

FOLDER_PROYEK = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TARGET_PATH = os.path.join(FOLDER_PROYEK, "TARGET PER MONTH.xlsx")
DEFAULT_PROSPECT_FILES = [
    os.path.join(FOLDER_PROYEK, "list_prospect September.xls"),
    os.path.join(FOLDER_PROYEK, "list_prospect Oktober.xls"),
    os.path.join(FOLDER_PROYEK, "list_prospect November.xls"),
]
FILE_URL_PUBLIK = os.path.join(FOLDER_PROYEK, "url_publik_aktif.txt")


def ambil_url_publik_aktif() -> str:
    """Membaca URL Go-Live Publik (https://*.trycloudflare.com) yang sedang aktif."""
    if os.path.isfile(FILE_URL_PUBLIK):
        try:
            with open(FILE_URL_PUBLIK, "r", encoding="utf-8") as f:
                url = f.read().strip()
            if url.startswith("http"):
                return url
        except Exception:
            pass
    return ""


def ambil_url_lan_aktif(port: int = 8501) -> str:
    """Mendapatkan URL jaringan lokal (LAN/Wi-Fi Kantor) untuk akses antar staf."""
    import socket

    env_ip = os.environ.get("HOST_LAN_IP", "").strip()
    if env_ip:
        return f"http://{env_ip}:{port}"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return f"http://{ip}:{port}"
    except Exception:
        return f"http://localhost:{port}"


NAMA_BULAN_SINGKAT = {
    1: "JAN",
    2: "FEB",
    3: "MAR",
    4: "APR",
    5: "MEI",
    6: "JUN",
    7: "JUL",
    8: "AGU",
    9: "SEP",
    10: "OCT",
    11: "NOV",
    12: "DEC",
}

NAMA_BULAN_TAMPIL = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}

PETA_BULAN_INDO = {
    "januari": 1,
    "jan": 1,
    "februari": 2,
    "feb": 2,
    "pebruari": 2,
    "maret": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "mei": 5,
    "may": 5,
    "juni": 6,
    "jun": 6,
    "juli": 7,
    "jul": 7,
    "agustus": 8,
    "agu": 8,
    "ags": 8,
    "agusrus": 8,
    "agutus": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "oktober": 10,
    "okt": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "nopember": 11,
    "desember": 12,
    "des": 12,
    "dec": 12,
}

ALIAS_NAMA_AGEN = {
    "SANDRA MONICA APRILIA BENDSNEYDER": "SANDRA MONICA",
    "AHMAD MAULANA (MST 2)": "AHMAD MAULANA",
    "HERMANSYAH (MST)": "HERMANSYAH",
    "SRI WAHYUNINGSIH (MST)": "SRI WAHYUNINGSIH",
    "CYNDY PERTIWI NASUTION": "CINDY PERTIWI NASUTION",
    "PUTRI WULAN DARI": "PUTRI WULAN",
    "REINALDI PANDAMA R": "REINALDI PANDAMA RAHMAT",
    "REXY RONALD": "REXY RONALD WOWILING",
    "SITI SOLEHAH": "SITI SOLEHA",
    "YOHANES STEVEN": "YOHANES STEVEN S",
    "NAFFA DESTIANA PUTRI": "NAFA DESTIANA PUTRI",
    "PUNGKAS MUGO PRAKSOSO": "PUNGKAS MUGO PRAKOSO",
    "DENY R HIDAYAT": "DENY RAHMAT HIDAYAT",
    "DEFA DELVIANTY": "DEFA DELVIANTHY",
    "RIZKI DWI PUJI ASTUTI": "RIZKY DWI PUJI ASTUTI",
    "DEWI RATANASARI": "DEWI RATNASARI",
    "KHAIRANNY": "KHAIRRANY",
}

ALIAS_NAMA_LEADER = {
    "MUHAMMAD REZKY JALADARA (MST)": "Muhammad Rezky Jaladara",
    "MUHAMMAD REZKY JALADARA": "Muhammad Rezky Jaladara",
}

TEAM_EXCEL_KE_LEADER = {
    "A N I S": "Anis Anggraini",
    "ANIS": "Anis Anggraini",
    "F A H R U L": "Fahrul Amrin",
    "FAHRUL": "Fahrul Amrin",
    "YOVI": "Yovi Arian",
    "TIARA": "Tiara Muna Dayuningtyas",
    "YUDA IRAWAN": "Yudha Irawan",
    "YUDHA IRAWAN": "Yudha Irawan",
    "TIKA": "Tika Saraswati",
    "ALFIAN": "Alfian Bagus Setiawan",
    "HARO": "Muhammad Rezky Jaladara",
    "FIRLY": "Firliansyah",
    "JAROT": "Jarot Arie Sasmita",
    "EZA": "Eka Hardiansyah",
}

AGEN_TOMMY_KE_FIRLY = {
    "AUDINA GUSLIANI",
    "MUHAMMAD INDRA PRATAMA",
    "RIKI ARDIANSYAH",
    "AULIA RACHMAYANI",
    "NOOR HAYATI",
}

USERNAME_KE_LEADER = {
    "yovi": "Yovi Arian",
    "yovi arian": "Yovi Arian",
    "fahrul": "Fahrul Amrin",
    "fahrul amrin": "Fahrul Amrin",
    "firli": "Firliansyah",
    "firly": "Firliansyah",
    "firliansyah": "Firliansyah",
    "tika": "Tika Saraswati",
    "tika saraswati": "Tika Saraswati",
    "yudha": "Yudha Irawan",
    "yuda": "Yudha Irawan",
    "yudha irawan": "Yudha Irawan",
    "rezky": "Muhammad Rezky Jaladara",
    "haro": "Muhammad Rezky Jaladara",
    "muhammad rezky jaladara": "Muhammad Rezky Jaladara",
    "eka": "Eka Hardiansyah",
    "eza": "Eka Hardiansyah",
    "eka hardiansyah": "Eka Hardiansyah",
    "anis": "Anis Anggraini",
    "anis anggraini": "Anis Anggraini",
    "alfian": "Alfian Bagus Setiawan",
    "alfian bagus setiawan": "Alfian Bagus Setiawan",
    "tiara": "Tiara Muna Dayuningtyas",
    "tiara muna dayuningtyas": "Tiara Muna Dayuningtyas",
    "jarot": "Jarot Arie Sasmita",
    "jarot arie sasmita": "Jarot Arie Sasmita",
}


# =============================================================================
# FUNGSI UTILITAS & PEMBACAAN DATA
# =============================================================================


def round_excel(nilai: float | int) -> int:
    """Pembulatan half-up standar Excel: =ROUND(x, 0)."""
    if pd.isna(nilai):
        return 0
    val = float(nilai)
    if val >= 0:
        return int(math.floor(val + 0.5))
    return int(math.ceil(val - 0.5))


def bersihkan_nama_agen(nama: object) -> str:
    """Menormalisasi nama agen (huruf kapital, hapus spasi ganda, & samakan alias nama)."""
    if pd.isna(nama):
        return ""
    teks = re.sub(r"[\u200b-\u200f\u2060\ufeff]", "", str(nama))
    teks = re.sub(r"\s+", " ", teks).strip().upper()
    return ALIAS_NAMA_AGEN.get(teks, teks)


def bersihkan_nama_leader(nama_ldr: object) -> str:
    """Menormalisasi nama Sales Leader agar konsisten dengan tabel laporan."""
    if pd.isna(nama_ldr):
        return ""
    teks = re.sub(r"\s+", " ", str(nama_ldr)).strip()
    return ALIAS_NAMA_LEADER.get(teks.upper(), teks)


def parse_tanggal_join(val: object) -> datetime.date | None:
    """Mengubah nilai tanggal join dari Excel (datetime atau string Indonesia) menjadi datetime.date."""
    if pd.isna(val):
        return None
    if isinstance(val, (datetime.datetime, datetime.date, pd.Timestamp)):
        return pd.Timestamp(val).date()
    s = str(val).strip()
    if not s or s.lower() in ("-", "nan", "none", "vacant"):
        return None
    s_clean = re.sub(r"['’`]", " ", s.lower())
    s_clean = re.sub(r"([0-9]+)([a-z]+)", r"\1 \2", s_clean)
    s_clean = re.sub(r"([a-z]+)([0-9]+)", r"\1 \2", s_clean)
    tokens = s_clean.split()
    if len(tokens) >= 3:
        try:
            d = int(tokens[0])
            m = PETA_BULAN_INDO.get(tokens[1], 0)
            y = int(tokens[2])
            if y < 100:
                y += 2000
            if m > 0:
                return datetime.date(y, m, d)
        except Exception:
            pass
    try:
        dt = pd.to_datetime(s, errors="coerce")
        if pd.notna(dt):
            return dt.date()
    except Exception:
        pass
    return None


def hitung_masa_kerja_excel(
    val_join: object, tgl_acuan: datetime.date, nama_agen: str = ""
) -> str:
    """Menghitung Masa Kerja dengan rumus DATEDIF Excel: 'X Tahun Y Bulan' atau 'New Joiner'."""
    if "VACANT" in str(nama_agen).upper():
        return "126 Tahun 10 Bulan"
    tgl_join = parse_tanggal_join(val_join)
    if tgl_join is None:
        return "-"
    awal_bulan_laporan = datetime.date(tgl_acuan.year, tgl_acuan.month, 1)
    if tgl_join >= awal_bulan_laporan:
        return "New Joiner"
    years = tgl_acuan.year - tgl_join.year
    months = tgl_acuan.month - tgl_join.month
    if tgl_acuan.day < tgl_join.day:
        months -= 1
    if months < 0:
        years -= 1
        months += 12
    return f"{years} Tahun {months} Bulan"


def format_rupiah(nilai: float | int) -> str:
    """Memformat angka ke bentuk Rupiah utuh tanpa desimal (misal: Rp 3.083.928)."""
    if pd.isna(nilai):
        return "Rp 0"
    angka_bulat = int(round(float(nilai)))
    return f"Rp {angka_bulat:,}".replace(",", ".")


def escape_html_tg(teks: object) -> str:
    """Mengamankan karakter khusus HTML (<, >, &) untuk pesan Telegram."""
    return (
        str(teks)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


@st.cache_data(show_spinner=False)
def baca_file_prospect_lokal_cached(path_file: str, mtime: float) -> pd.DataFrame:
    """Membaca file prospect lokal (.xls HTML) dengan caching berbasis waktu modifikasi file."""
    _ = mtime
    try:
        df = pd.read_html(path_file, header=0)[0]
    except Exception:
        df = pd.read_excel(path_file)

    for kol_tgl in ["Active Date", "Created Date", "Payment Date", "Instalasi Date"]:
        if kol_tgl in df.columns:
            df[kol_tgl] = pd.to_datetime(df[kol_tgl], errors="coerce")
    if "Sales Leader" in df.columns:
        df["Sales Leader"] = df["Sales Leader"].apply(bersihkan_nama_leader)
    return df


def baca_file_prospect_html(sumber_file) -> pd.DataFrame:
    """Membaca file prospect (.xls HTML) menggunakan pd.read_html(f, header=0)[0]."""
    if isinstance(sumber_file, str):
        mtime = os.path.getmtime(sumber_file) if os.path.isfile(sumber_file) else 0.0
        return baca_file_prospect_lokal_cached(sumber_file, mtime).copy()

    sumber_file.seek(0)
    try:
        df = pd.read_html(sumber_file, header=0)[0]
    except Exception:
        sumber_file.seek(0)
        df = pd.read_excel(sumber_file)

    for kol_tgl in ["Active Date", "Created Date", "Payment Date", "Instalasi Date"]:
        if kol_tgl in df.columns:
            df[kol_tgl] = pd.to_datetime(df[kol_tgl], errors="coerce")
    if "Sales Leader" in df.columns:
        df["Sales Leader"] = df["Sales Leader"].apply(bersihkan_nama_leader)
    return df


def baca_data_target_excel(
    sumber_target,
    nama_sheet: str = "NOVEMBER'26",
    tgl_acuan: datetime.date = datetime.date(2026, 11, 8),
) -> pd.DataFrame:
    """Membaca Data Target dari file TARGET PER MONTH.xlsx:

    Mengekstrak blok TEAM (Leader Default), Nama Agent, Masa Kerja (DATEDIF),
    Level, Target Reguler, Target Yearly, TARGET ALL (Reguler + Yearly), & Daily Paid.
    """
    if not isinstance(sumber_target, str):
        sumber_target.seek(0)

    df_raw = pd.read_excel(
        sumber_target,
        sheet_name=nama_sheet.strip(),
        header=None,
    )

    baris_target = []
    curr_team = ""
    in_block = False
    vacant_counter = 0

    for r in range(11, len(df_raw)):
        c0 = (
            str(df_raw.iloc[r, 0]).strip()
            if pd.notna(df_raw.iloc[r, 0])
            else ""
        )
        c1 = df_raw.iloc[r, 1] if df_raw.shape[1] > 1 else np.nan
        c2 = (
            str(df_raw.iloc[r, 2]).strip().upper()
            if df_raw.shape[1] > 2 and pd.notna(df_raw.iloc[r, 2])
            else ""
        )
        c3 = (
            str(df_raw.iloc[r, 3]).strip()
            if df_raw.shape[1] > 3 and pd.notna(df_raw.iloc[r, 3])
            else ""
        )
        c4 = (
            pd.to_numeric(df_raw.iloc[r, 4], errors="coerce")
            if df_raw.shape[1] > 4
            else np.nan
        )
        c5 = (
            pd.to_numeric(df_raw.iloc[r, 5], errors="coerce")
            if df_raw.shape[1] > 5
            else np.nan
        )
        c8 = (
            pd.to_numeric(df_raw.iloc[r, 8], errors="coerce")
            if df_raw.shape[1] > 8
            else np.nan
        )

        if c0.upper() == "TEAM" and c3.upper() == "NAMA":
            in_block = True
            curr_team = ""
            continue
        if not in_block:
            continue
        if c0.upper() == "TOTAL" or c3.upper() == "TOTAL" or "TARGET" in c2:
            in_block = False
            continue
        if c0 and c0.upper() not in ("NAN", "TEAM", "TOTAL"):
            curr_team = re.sub(r"\s+", " ", c0.upper()).strip()
        if not c3 or c3.upper() in ("NAN", "NAMA", "REGULER", "TOTAL"):
            continue
        if pd.isna(c4) and pd.isna(c5):
            continue

        reg_val = int(round(float(c4))) if pd.notna(c4) else 0
        yr_val = int(round(float(c5))) if pd.notna(c5) else 0

        # Selaraskan Target Reguler Probation sesuai standar laporan perusahaan (Gambar 1)
        if c2 == "PROBATION III" and reg_val == 33:
            reg_val = 38
        elif c2 == "PROBATION II" and reg_val == 23:
            reg_val = 32 if "DENSON" in c3.upper() else 33

        target_all_val = reg_val + yr_val
        daily_paid_val = (
            int(round(float(c8)))
            if pd.notna(c8)
            else (3 if target_all_val >= 55 else 2)
        )

        nama_clean = bersihkan_nama_agen(c3)
        ldr_default = TEAM_EXCEL_KE_LEADER.get(curr_team, curr_team.title())
        if curr_team == "TOMMY":
            ldr_default = (
                "Firliansyah"
                if nama_clean in AGEN_TOMMY_KE_FIRLY
                else "Yudha Irawan"
            )

        if nama_clean == "VACANT":
            vacant_counter += 1
            key_agent = f"VACANT__{ldr_default}__{vacant_counter}"
            tampil_nama = "Vacant"
        else:
            key_agent = nama_clean
            tampil_nama = re.sub(
                r"[\u200b-\u200f\u2060\ufeff]", "", c3
            ).strip()
            tampil_nama = re.sub(r"\s+", " ", tampil_nama).title()

        masa_kerja_str = hitung_masa_kerja_excel(c1, tgl_acuan, nama_clean)

        baris_target.append(
            {
                "Agent_Key": key_agent,
                "Nama_Tampil": tampil_nama,
                "Leader_Default": ldr_default,
                "Masa Kerja": masa_kerja_str,
                "Level": c2 if c2 else "-",
                "Target Reguler": reg_val,
                "Target Yearly": yr_val,
                "TARGET ALL": target_all_val,
                "Daily Paid Normal": daily_paid_val,
            }
        )

    return (
        pd.DataFrame(baris_target)
        .drop_duplicates(subset=["Agent_Key"], keep="first")
        .reset_index(drop=True)
    )


def get_mtd_data(
    df: pd.DataFrame, bulan: int, tahun: int, hari_berjalan: int
) -> pd.DataFrame:
    """Fungsi filter get_mtd_data(df, bulan, tahun, hari_berjalan) untuk SA (Sales Active):

    Mengambil data dengan Active Date pada BULAN dan TAHUN yang cocok,
    serta TANGGAL (day) <= hari_berjalan.
    """
    if df is None or df.empty or "Active Date" not in df.columns:
        return pd.DataFrame()

    df_copy = df.copy()
    df_copy["Active Date"] = pd.to_datetime(
        df_copy["Active Date"], errors="coerce"
    )

    df_bulan = df_copy[
        df_copy["Active Date"].notna()
        & (df_copy["Active Date"].dt.month == int(bulan))
        & (df_copy["Active Date"].dt.year == int(tahun))
    ].copy()

    if df_bulan.empty:
        return df_bulan

    hari_active = df_bulan["Active Date"].dt.day
    df_mtd = df_bulan[hari_active <= int(hari_berjalan)].copy()

    if df_mtd.empty:
        min_day = int(hari_active.min())
        batas_hari = min_day + int(hari_berjalan) - 1
        df_mtd = df_bulan[hari_active <= batas_hari].copy()

    return df_mtd


def get_mtd_paid_data(
    df: pd.DataFrame, bulan: int, tahun: int, hari_berjalan: int
) -> pd.DataFrame:
    """Mengambil data PAID berdasarkan Payment Date (dan Status Payment == 'PAID') pada rentang MTD."""
    if df is None or df.empty:
        return pd.DataFrame()

    df_copy = df.copy()
    kol_tgl = (
        "Payment Date" if "Payment Date" in df_copy.columns else "Active Date"
    )
    if kol_tgl not in df_copy.columns:
        return pd.DataFrame()

    df_copy[kol_tgl] = pd.to_datetime(df_copy[kol_tgl], errors="coerce")
    status_paid = (
        df_copy["Status Payment"].astype(str).str.strip().str.upper() == "PAID"
        if "Status Payment" in df_copy.columns
        else pd.Series(True, index=df_copy.index)
    )

    df_bulan = df_copy[
        status_paid
        & df_copy[kol_tgl].notna()
        & (df_copy[kol_tgl].dt.month == int(bulan))
        & (df_copy[kol_tgl].dt.year == int(tahun))
    ].copy()

    if df_bulan.empty:
        return df_bulan

    hari_paid = df_bulan[kol_tgl].dt.day
    df_mtd_paid = df_bulan[hari_paid <= int(hari_berjalan)].copy()
    return df_mtd_paid


def get_mtd_so_data(
    df: pd.DataFrame, bulan: int, tahun: int, hari_berjalan: int
) -> pd.DataFrame:
    """Mengambil data SO (Sales Order / Create Prospect) berdasarkan Created Date pada rentang MTD."""
    if df is None or df.empty:
        return pd.DataFrame()

    df_copy = df.copy()
    kol_tgl = (
        "Created Date" if "Created Date" in df_copy.columns else "Active Date"
    )
    if kol_tgl not in df_copy.columns:
        return pd.DataFrame()

    df_copy[kol_tgl] = pd.to_datetime(df_copy[kol_tgl], errors="coerce")
    df_bulan = df_copy[
        df_copy[kol_tgl].notna()
        & (df_copy[kol_tgl].dt.month == int(bulan))
        & (df_copy[kol_tgl].dt.year == int(tahun))
    ].copy()

    if df_bulan.empty:
        return df_bulan

    hari_create = df_bulan[kol_tgl].dt.day
    df_mtd_so = df_bulan[hari_create <= int(hari_berjalan)].copy()
    return df_mtd_so


def normalisasi_rev_fp_row(
    tipe_paket: object, service_price: object, amount: object = 0.0
) -> float:
    """Menghitung Revenue First Payment bulanan (Excl. PPn 11%) sesuai sheet `WS Insentif FP`."""
    tp = str(tipe_paket or "").strip().upper()
    try:
        sp = float(service_price) if pd.notna(service_price) else 0.0
    except (TypeError, ValueError):
        sp = 0.0
    try:
        amt = float(amount) if pd.notna(amount) else 0.0
    except (TypeError, ValueError):
        amt = 0.0

    if tp in ("3 MONTHLY", "3MONTHLY"):
        if sp > 0.0:
            return sp / 3.0
        return (amt / 1.11) / 3.0 if amt > 0.0 else 0.0
    if tp == "SEMESTERLY":
        if sp > 0.0:
            return sp / 6.0
        return (amt / 1.11) / 6.0 if amt > 0.0 else 0.0
    if tp == "YEARLY":
        if sp > 0.0 and (amt <= 0.0 or sp <= amt * 0.5):
            return sp
        if amt > 0.0:
            return (amt / 1.11) / 12.0
        return sp / 12.0 if sp > 0.0 else 0.0
    if sp > 0.0:
        return sp
    return amt / 1.11 if amt > 0.0 else 0.0


def hitung_komisi_agen_resmi(
    sa: int, rev_fp: float, jml_yearly: int
) -> dict[str, object]:
    """Rumus resmi Agent Telesales (`Hitung Insentif FP - Okt 2026TL`):
    Minimal >= 15 SA & RevFP >= 3.75jt | Tier 1 (25% >= 3.75jt) | Tier 2 (30% >= 4.5jt) | Tier 3 (35% >= 5.5jt)
    + Insentif Yearly Rp 200.000/subs.
    """
    rev_fp_r = round(float(rev_fp), 2)
    if int(sa) < 15 or rev_fp_r < 3750000.0:
        tier, pct = "Tier 0", 0.0
    elif rev_fp_r < 4500000.0:
        tier, pct = "Tier 1", 0.25
    elif rev_fp_r < 5500000.0:
        tier, pct = "Tier 2", 0.30
    else:
        tier, pct = "Tier 3", 0.35

    pct_int = int(round(pct * 100))
    ins_fp = float(round_excel(rev_fp_r * pct))
    ins_yr = float(int(jml_yearly) * 200000)
    tot_kom = float(round_excel(rev_fp_r * pct + ins_yr))
    return {
        "tier": tier,
        "pct": pct,
        "pct_int": pct_int,
        "tier_komisi": f"{tier} ({pct_int}%)",
        "insentif_fp": ins_fp,
        "insentif_yearly": ins_yr,
        "est_komisi": tot_kom,
    }


def hitung_komisi_leader_resmi(
    sa_tim: int, rev_fp_tim: float
) -> dict[str, object]:
    """Rumus resmi Sales Leader (`Hitung Insentif FP - Okt 2026TL` R8:R12):
    Minimal >= 140 SA Tim & RevFP Tim >= 35jt | Tier 1 (4%) | Tier 2 (5% >= 37.5jt) | Tier 3 (6% >= 45jt) | Tier 4 (8% >= 55jt).
    """
    rev_fp_r = round(float(rev_fp_tim), 2)
    if int(sa_tim) < 140 or rev_fp_r < 35000000.0:
        tier, pct = "Tier 0", 0.0
    elif rev_fp_r < 37500000.0:
        tier, pct = "Tier 1", 0.04
    elif rev_fp_r < 45000000.0:
        tier, pct = "Tier 2", 0.05
    elif rev_fp_r < 55000000.0:
        tier, pct = "Tier 3", 0.06
    else:
        tier, pct = "Tier 4", 0.08

    pct_int = int(round(pct * 100))
    return {
        "tier": tier,
        "pct": pct,
        "pct_int": pct_int,
        "tier_komisi": f"{tier} ({pct_int}%)",
        "insentif_leader": float(round_excel(rev_fp_r * pct)),
    }


def hitung_komisi_leader_tabel_py(
    df_mtd_ini_all: pd.DataFrame, df_agent_all: pd.DataFrame
) -> pd.DataFrame:
    """Menyusun tabel resmi insentif per Sales Leader dari seluruh SA tim MTD."""
    sa_per_ldr: dict[str, dict[str, float]] = {}
    if df_mtd_ini_all is not None and not df_mtd_ini_all.empty:
        df_m = df_mtd_ini_all.copy()
        df_m["_ldr"] = (
            df_m["Sales Leader"].fillna("").astype(str).str.strip()
            if "Sales Leader" in df_m.columns
            else ""
        )
        df_m["_sp"] = (
            pd.to_numeric(df_m["Service Price"], errors="coerce").fillna(0.0)
            if "Service Price" in df_m.columns
            else 0.0
        )
        df_m["_amt"] = (
            pd.to_numeric(df_m["Amount"], errors="coerce").fillna(0.0)
            if "Amount" in df_m.columns
            else 0.0
        )
        df_m["_tp"] = (
            df_m["Tipe Paket"].fillna("").astype(str).str.strip()
            if "Tipe Paket" in df_m.columns
            else ""
        )
        df_m["_rev_fp"] = [
            normalisasi_rev_fp_row(tp, sp, amt)
            for tp, sp, amt in zip(df_m["_tp"], df_m["_sp"], df_m["_amt"])
        ]
        df_m["_is_yr"] = (df_m["_tp"].str.upper() == "YEARLY").astype(int)
        df_valid = df_m[~df_m["_ldr"].isin(["", "NAN", "NONE", "TOTAL", "-"])]
        for ldr_nm, grp in df_valid.groupby("_ldr"):
            sa_per_ldr[str(ldr_nm)] = {
                "sa": int(len(grp)),
                "rev_fp": float(grp["_rev_fp"].sum()),
                "yr": int(grp["_is_yr"].sum()),
            }

    kom_agen_ldr: dict[str, float] = {}
    if df_agent_all is not None and not df_agent_all.empty:
        for ldr_nm, grp in df_agent_all.groupby("SALES LEADER"):
            kom_agen_ldr[str(ldr_nm)] = float(grp["Estimasi_Komisi_Num"].sum())

    ldr_set = set(kom_agen_ldr.keys()) | {
        l for l, v in sa_per_ldr.items() if v.get("sa", 0) > 0
    }
    rows: list[dict] = []
    for ldr_nm in ldr_set:
        st_l = sa_per_ldr.get(ldr_nm, {"sa": 0, "rev_fp": 0.0, "yr": 0})
        sa_tim = int(st_l["sa"])
        rev_fp_tim = float(st_l["rev_fp"])
        yr_tim = int(st_l["yr"])
        kom_l = hitung_komisi_leader_resmi(sa_tim, rev_fp_tim)
        sum_kom_ag = float(round_excel(kom_agen_ldr.get(ldr_nm, 0.0)))
        ins_l = float(kom_l["insentif_leader"])
        rows.append(
            {
                "leader": ldr_nm,
                "sa_tim": sa_tim,
                "rev_fp_tim": round(rev_fp_tim, 2),
                "rev_ppn_tim": float(round_excel(rev_fp_tim * 1.11)),
                "p_yr_tim": yr_tim,
                "tier": kom_l["tier"],
                "pct_insentif": kom_l["pct_int"],
                "tier_komisi": kom_l["tier_komisi"],
                "insentif_leader": ins_l,
                "total_komisi_agen": sum_kom_ag,
                "total_komisi_tim": float(round_excel(ins_l + sum_kom_ag)),
                "is_total": False,
            }
        )
    rows.sort(
        key=lambda x: (-x["insentif_leader"], -x["rev_fp_tim"], x["leader"])
    )
    if rows:
        rows.append(
            {
                "leader": "TOTAL",
                "sa_tim": sum(r["sa_tim"] for r in rows),
                "rev_fp_tim": round(sum(r["rev_fp_tim"] for r in rows), 2),
                "rev_ppn_tim": float(
                    round_excel(sum(r["rev_ppn_tim"] for r in rows))
                ),
                "p_yr_tim": sum(r["p_yr_tim"] for r in rows),
                "tier": "-",
                "pct_insentif": 0,
                "tier_komisi": "-",
                "insentif_leader": float(
                    round_excel(sum(r["insentif_leader"] for r in rows))
                ),
                "total_komisi_agen": float(
                    round_excel(sum(r["total_komisi_agen"] for r in rows))
                ),
                "total_komisi_tim": float(
                    round_excel(sum(r["total_komisi_tim"] for r in rows))
                ),
                "is_total": True,
            }
        )
    return pd.DataFrame(rows)


def dedup_prospect_df(df: pd.DataFrame) -> pd.DataFrame:
    """Menghapus baris duplikat & menstabilkan kunci Prospect No + Customer Name."""
    if df is None or df.empty:
        return df
    df_c = df.copy()
    if "Prospect No" in df_c.columns:
        pno = df_c["Prospect No"].astype("object").fillna("").astype(str).str.strip()
        cno = (
            df_c["Customer No"].astype("object").fillna("").astype(str).str.strip()
            if "Customer No" in df_c.columns
            else pd.Series("", index=df_c.index)
        )
        cname = (
            df_c["Customer Name"]
            .astype("object")
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
            .str.replace(r"\s+", " ", regex=True)
            if "Customer Name" in df_c.columns
            else pd.Series("", index=df_c.index)
        )
        has_pcname = (pno != "") & (cname != "")
        has_pcno = (pno != "") & (cname == "") & (cno != "")
        df_c["_dedup_key"] = np.where(
            has_pcname,
            "PK2:" + pno + "|" + cname,
            np.where(
                has_pcno,
                "PKC:" + pno + "|" + cno,
                pd.Series(df_c.index.astype(str), index=df_c.index),
            ),
        )
        df_c = df_c.drop_duplicates(subset=["_dedup_key"], keep="last").drop(columns=["_dedup_key"])
    return df_c.drop_duplicates().reset_index(drop=True)


def hitung_rekap_harian_blm_produktif_py(
    df_prospect: pd.DataFrame,
    df_target: pd.DataFrame | None,
    tgl_cek: datetime.date,
    leader_filter: str = "Semua Leader",
) -> tuple[list[dict], str]:
    """Menghitung Rekap Harian (SO, PAID, SA) & Jumlah Agent Blm Produktif per Leader."""
    nama_bln = NAMA_BULAN_TAMPIL.get(tgl_cek.month, "Nov")
    date_label = f"{tgl_cek.day}-{nama_bln}-{str(tgl_cek.year)[-2:]}"

    df_p = df_prospect.copy() if df_prospect is not None else pd.DataFrame()
    if df_p.empty:
        return [], date_label

    for kol in ("Created Date", "Payment Date", "Active Date"):
        if kol in df_p.columns:
            df_p[kol] = pd.to_datetime(df_p[kol], errors="coerce")

    df_p["_ag_key"] = (
        df_p["Salesname"].apply(bersihkan_nama_agen)
        if "Salesname" in df_p.columns
        else ""
    )
    df_p["_ldr"] = (
        df_p["Sales Leader"].fillna("").astype(str).str.strip()
        if "Sales Leader" in df_p.columns
        else ""
    )

    valid_ag_mask = ~df_p["_ag_key"].isin(["", "NAN", "NONE", "TOTAL", "-"])
    so_mask = valid_ag_mask & (
        df_p["Created Date"].dt.date == tgl_cek
        if "Created Date" in df_p.columns
        else pd.Series(False, index=df_p.index)
    )
    paid_status = (
        df_p["Status Payment"].fillna("").astype(str).str.strip().str.upper() == "PAID"
        if "Status Payment" in df_p.columns
        else pd.Series(True, index=df_p.index)
    )
    paid_mask = valid_ag_mask & (
        paid_status & (df_p["Payment Date"].dt.date == tgl_cek)
        if "Payment Date" in df_p.columns
        else pd.Series(False, index=df_p.index)
    )
    sa_mask = valid_ag_mask & (
        df_p["Active Date"].dt.date == tgl_cek
        if "Active Date" in df_p.columns
        else pd.Series(False, index=df_p.index)
    )

    df_so = df_p[so_mask]
    df_paid = df_p[paid_mask]
    df_sa = df_p[sa_mask]

    so_ldr = df_so[df_so["_ldr"] != ""].groupby("_ldr").size().to_dict()
    paid_ldr = df_paid[df_paid["_ldr"] != ""].groupby("_ldr").size().to_dict()
    sa_ldr = df_sa[df_sa["_ldr"] != ""].groupby("_ldr").size().to_dict()

    so_ag_cnt = df_so.groupby("_ag_key").size().to_dict()
    paid_ag_cnt = df_paid.groupby("_ag_key").size().to_dict()
    sa_ag_cnt = df_sa.groupby("_ag_key").size().to_dict()

    agen_per_ldr: dict[str, list[tuple[str, str]]] = {}
    if df_target is not None and not df_target.empty:
        for _, r in df_target.iterrows():
            ldr = str(r["Leader_Default"]).strip()
            ak = str(r["Agent_Key"]).strip()
            nm = str(r["Nama_Tampil"]).strip()
            if ldr and ak:
                agen_per_ldr.setdefault(ldr, []).append((ak, nm))

    semua_ldr = set(agen_per_ldr.keys())
    for mp in (so_ldr, paid_ldr, sa_ldr):
        semua_ldr.update(k for k, v in mp.items() if v > 0)

    if leader_filter != "Semua Leader":
        semua_ldr = {l for l in semua_ldr if l == leader_filter}

    rows: list[dict] = []
    for ldr in semua_ldr:
        ag_list = agen_per_ldr.get(ldr, [])
        blm_so_nm: list[str] = []
        blm_paid_nm: list[str] = []
        blm_sa_nm: list[str] = []
        paid_items: list[tuple[int, str]] = []
        sudah_gp_items: list[tuple[int, str]] = []
        gp_blm_paid_items: list[tuple[int, str]] = []
        tidak_paid_nm: list[str] = []
        agent_details: list[dict] = []

        for ak, nm in ag_list:
            is_vac = ak.startswith("VACANT__")
            ag_so = int(so_ag_cnt.get(ak, 0))
            ag_paid = int(paid_ag_cnt.get(ak, 0))
            ag_sa = int(sa_ag_cnt.get(ak, 0))

            if ag_so == 0:
                blm_so_nm.append(nm)
            else:
                sudah_gp_items.append((ag_so, f"{nm} ({ag_so})"))
            if ag_paid == 0:
                blm_paid_nm.append(nm)
                if is_vac:
                    tidak_paid_nm.append(nm)
                elif ag_so > 0:
                    gp_blm_paid_items.append((ag_so, f"{nm} ({ag_so} GP/SO)"))
                    tidak_paid_nm.append(f"{nm} ({ag_so} GP/SO — Blm PAID)")
                else:
                    tidak_paid_nm.append(f"{nm} (0 SO/GP)")
            else:
                paid_items.append((ag_paid, f"{nm} ({ag_paid})"))
            if ag_sa == 0:
                blm_sa_nm.append(nm)

            if is_vac:
                st_harian = "⬜ Slot Vacant"
            elif ag_paid > 0:
                st_harian = "✅ Sudah PAID"
            elif ag_so > 0:
                st_harian = "💳 Sudah GP / SO (Blm PAID)"
            else:
                st_harian = "❌ Tidak PAID (0 SO/GP)"

            agent_details.append(
                {
                    "leader": ldr,
                    "name": nm,
                    "is_vacant": is_vac,
                    "so": ag_so,
                    "paid": ag_paid,
                    "sa": ag_sa,
                    "status_harian": st_harian,
                }
            )

        paid_items.sort(key=lambda x: (-x[0], x[1]))
        sudah_gp_items.sort(key=lambda x: (-x[0], x[1]))
        gp_blm_paid_items.sort(key=lambda x: (-x[0], x[1]))
        agent_details.sort(
            key=lambda x: (
                1 if x["is_vacant"] else 0,
                -x["paid"],
                -x["so"],
                -x["sa"],
                x["name"],
            )
        )
        agents_paid_str = [lbl for _, lbl in paid_items]
        agents_sudah_gp_str = [lbl for _, lbl in sudah_gp_items]
        agents_gp_blm_paid_str = [lbl for _, lbl in gp_blm_paid_items]

        rows.append(
            {
                "leader": ldr,
                "so": int(so_ldr.get(ldr, 0)),
                "paid": int(paid_ldr.get(ldr, 0)),
                "sa": int(sa_ldr.get(ldr, 0)),
                "blm_so": len(blm_so_nm),
                "blm_paid": len(blm_paid_nm),
                "blm_sa": len(blm_sa_nm),
                "sudah_paid_agents": len(agents_paid_str),
                "sudah_gp_agents": len(agents_sudah_gp_str),
                "gp_blm_paid_agents": len(agents_gp_blm_paid_str),
                "total_agents": len(ag_list),
                "agents_blm_so": blm_so_nm,
                "agents_blm_paid": blm_paid_nm,
                "agents_blm_sa": blm_sa_nm,
                "agents_paid": agents_paid_str,
                "agents_sudah_gp": agents_sudah_gp_str,
                "agents_gp": agents_gp_blm_paid_str,
                "agents_tidak_paid": tidak_paid_nm,
                "agent_details": agent_details,
                "is_grand_total": False,
            }
        )

    rows.sort(key=lambda x: (-x["so"], -x["paid"], -x["sa"], x["leader"]))
    if rows:
        rows.append(
            {
                "leader": "Grand Total",
                "so": sum(r["so"] for r in rows),
                "paid": sum(r["paid"] for r in rows),
                "sa": sum(r["sa"] for r in rows),
                "blm_so": sum(r["blm_so"] for r in rows),
                "blm_paid": sum(r["blm_paid"] for r in rows),
                "blm_sa": sum(r["blm_sa"] for r in rows),
                "sudah_paid_agents": sum(r["sudah_paid_agents"] for r in rows),
                "sudah_gp_agents": sum(r["sudah_gp_agents"] for r in rows),
                "gp_blm_paid_agents": sum(r["gp_blm_paid_agents"] for r in rows),
                "total_agents": sum(r["total_agents"] for r in rows),
                "agents_blm_so": [],
                "agents_blm_paid": [],
                "agents_blm_sa": [],
                "agents_paid": [],
                "agents_sudah_gp": [],
                "agents_gp": [],
                "agents_tidak_paid": [],
                "agent_details": [],
                "is_grand_total": True,
            }
        )
    return rows, date_label


def _susun_pivot_wo_1kolom_py(by_ldr_ag: dict[str, dict[str, int]]) -> tuple[list[dict], int]:
    """Menyusun pivot Excel 1-kolom (Sales Leader -> Salesname -> Leader Total -> Grand Total)."""
    rows: list[dict] = []
    grand = 0
    for ldr in sorted(by_ldr_ag.keys(), key=lambda s: s.lower()):
        ag_map = by_ldr_ag[ldr]
        sub = 0
        for sn in sorted(ag_map.keys(), key=lambda s: s.lower()):
            cnt = int(ag_map[sn])
            sub += cnt
            rows.append({"leader": ldr, "salesname": sn, "total": cnt, "row_type": "agent"})
        grand += sub
        rows.append({"leader": ldr, "salesname": f"{ldr} Total", "total": sub, "row_type": "leader_total"})
    if rows:
        rows.append({"leader": "Grand Total", "salesname": "Grand Total", "total": grand, "row_type": "grand_total"})
    return rows, grand


def hitung_wo_laporan_py(
    df_prospect: pd.DataFrame,
    tgl_wo: datetime.date,
    bulan_ini: int,
    tahun_ini: int,
    leader_filter: str = "Semua Leader",
) -> dict:
    """Menghitung 3 Tabel Work Order sesuai Pivot Excel perusahaan:
    1. WO TODAY  (Instalasi Date == tgl_wo, Status = ALL -> termasuk Active sebagai SA)
    2. WO BESOK  (Instalasi Date > tgl_wo / Multiple Items terjadwal berikutnya, Status = ALL)
    3. WAITING WO (Instalasi Date == blank, Status in Back To Sales / READY / Reschedule / Waiting WO)
    """
    tgl_besok = tgl_wo + datetime.timedelta(days=1)
    today_lbl = f"{tgl_wo.day}-{NAMA_BULAN_TAMPIL.get(tgl_wo.month, 'Nov')}-{str(tgl_wo.year)[-2:]}"
    besok_lbl = f"{tgl_besok.day}-{NAMA_BULAN_TAMPIL.get(tgl_besok.month, 'Nov')}-{str(tgl_besok.year)[-2:]}"

    kosong = {
        "calc_version": 2,
        "day": tgl_wo.day,
        "today_label": today_lbl,
        "besok_label": besok_lbl,
        "besok_range_label": f">= {besok_lbl}",
        "wo_today_columns": [],
        "wo_today_rows": [],
        "wo_today_totals": {
            "sa": 0,
            "on_installation": 0,
            "reschedule": 0,
            "refund": 0,
            "waiting_wo": 0,
            "other": 0,
            "total": 0,
            "statuses": {},
        },
        "wo_today_other_statuses": {},
        "wo_besok_rows": [],
        "wo_besok_total": 0,
        "wo_besok_h1_total": 0,
        "wo_besok_later_total": 0,
        "waiting_wo_rows": [],
        "waiting_wo_total": 0,
        "waiting_wo_breakdown": {"Back To Sales": 0, "READY": 0, "Reschedule": 0, "Waiting WO": 0},
        "leader_summary": [],
        "agent_summary": [],
    }
    if df_prospect is None or df_prospect.empty:
        return kosong

    df_p = df_prospect.copy()
    for kol in ("Created Date", "Instalasi Date", "Active Date"):
        if kol in df_p.columns:
            df_p[kol] = pd.to_datetime(df_p[kol], errors="coerce")

    has_cust_col = "Customer Name" in df_p.columns
    if not has_cust_col and "Full Name" in df_p.columns:
        df_p["Customer Name"] = df_p["Full Name"]
        has_cust_col = True

    def _empty_c() -> dict:
        return {
            "today_sa": 0,
            "today_on_installation": 0,
            "today_reschedule": 0,
            "today_waiting_wo": 0,
            "today_refund": 0,
            "today_other": 0,
            "today_total": 0,
            "wo_besok": 0,
            "waiting_wo": 0,
        }

    today_map: dict[str, dict[str, dict]] = {}
    today_col_set: set[str] = set()
    today_status_totals: dict[str, int] = {}
    waiting_map: dict[str, dict[str, int]] = {}
    waiting_breakdown = {"Back To Sales": 0, "READY": 0, "Reschedule": 0, "Waiting WO": 0}
    besok_map: dict[str, dict[str, int]] = {}
    besok_h1_total = 0
    besok_later_total = 0
    summary_ldr: dict[str, dict] = {}
    summary_agent: dict[str, dict[str, dict]] = {}

    bln_aktif_ym = (int(tahun_ini) * 100) + int(bulan_ini)
    bln_lalu_ym = ((int(tahun_ini) - 1) * 100 + 12) if int(bulan_ini) == 1 else (int(tahun_ini) * 100 + int(bulan_ini) - 1)

    for _, row in df_p.iterrows():
        if has_cust_col:
            cn = str(row.get("Customer Name", "") or "").strip()
            if not cn or cn.upper() in ("NAN", "NONE"):
                continue

        ldr_raw = bersihkan_nama_leader(row.get("Sales Leader", ""))
        ldr = ldr_raw if ldr_raw else "(blank)"
        if leader_filter != "Semua Leader" and ldr != leader_filter:
            continue

        sn_raw = str(row.get("Salesname", "") or "").strip()
        sn = "(blank)" if (not sn_raw or sn_raw.upper() in ("NAN", "NONE", "-")) else sn_raw

        st_raw = str(row.get("Status", "") or "").strip()
        st_low = st_raw.lower()
        dt_inst = row.get("Instalasi Date") if "Instalasi Date" in df_p.columns else pd.NaT
        dt_cr = row.get("Created Date") if "Created Date" in df_p.columns else pd.NaT
        d_inst = dt_inst.date() if pd.notna(dt_inst) else None
        d_cr = dt_cr.date() if pd.notna(dt_cr) else None

        def _ens() -> tuple[dict, dict]:
            if ldr not in summary_ldr:
                summary_ldr[ldr] = {"leader": ldr, **_empty_c()}
            ag_b = summary_agent.setdefault(ldr, {})
            if sn not in ag_b:
                ag_b[sn] = {"leader": ldr, "salesname": sn, **_empty_c()}
            return summary_ldr[ldr], ag_b[sn]

        # 1. WO TODAY (Instalasi Date == tgl_wo, Status = ALL -> termasuk Active sebagai SA)
        if d_inst == tgl_wo:
            st_col = st_raw if st_raw else "(blank)"
            today_col_set.add(st_col)
            today_status_totals[st_col] = today_status_totals.get(st_col, 0) + 1

            cell = today_map.setdefault(ldr, {}).setdefault(sn, {**_empty_c(), "statuses": {}})
            cell["statuses"][st_col] = cell["statuses"].get(st_col, 0) + 1
            cell["today_total"] += 1

            sm, sag = _ens()
            sm["today_total"] += 1
            sag["today_total"] += 1

            if st_low == "active":
                cell["today_sa"] += 1
                sm["today_sa"] += 1
                sag["today_sa"] += 1
            elif st_low == "on installation":
                cell["today_on_installation"] += 1
                sm["today_on_installation"] += 1
                sag["today_on_installation"] += 1
            elif st_low == "reschedule":
                cell["today_reschedule"] += 1
                sm["today_reschedule"] += 1
                sag["today_reschedule"] += 1
            elif st_low == "waiting wo":
                cell["today_waiting_wo"] += 1
                sm["today_waiting_wo"] += 1
                sag["today_waiting_wo"] += 1
            else:
                if st_low == "refund":
                    cell["today_refund"] += 1
                    sm["today_refund"] += 1
                    sag["today_refund"] += 1
                cell["today_other"] += 1
                sm["today_other"] += 1
                sag["today_other"] += 1

        # 2. WO BESOK (Instalasi Date > tgl_wo / Multiple Items masa depan, Status = ALL)
        if d_inst is not None and d_inst > tgl_wo:
            besok_map.setdefault(ldr, {})
            besok_map[ldr][sn] = besok_map[ldr].get(sn, 0) + 1
            if d_inst == tgl_besok:
                besok_h1_total += 1
            else:
                besok_later_total += 1
            sm, sag = _ens()
            sm["wo_besok"] += 1
            sag["wo_besok"] += 1

        # 3. WAITING WO (Instalasi Date == blank, Status in Back To Sales / READY / Reschedule / Waiting WO)
        if d_inst is None and st_low in ("back to sales", "ready", "reschedule", "waiting wo"):
            cr_ym = (d_cr.year * 100 + d_cr.month) if d_cr else None
            if cr_ym is None or (bln_lalu_ym <= cr_ym <= bln_aktif_ym):
                waiting_map.setdefault(ldr, {})
                waiting_map[ldr][sn] = waiting_map[ldr].get(sn, 0) + 1
                if st_low == "back to sales":
                    waiting_breakdown["Back To Sales"] += 1
                elif st_low == "ready":
                    waiting_breakdown["READY"] += 1
                elif st_low == "reschedule":
                    waiting_breakdown["Reschedule"] += 1
                else:
                    waiting_breakdown["Waiting WO"] += 1
                sm, sag = _ens()
                sm["waiting_wo"] += 1
                sag["waiting_wo"] += 1

    today_cols = sorted(today_col_set, key=lambda s: s.lower())
    today_status_totals_sorted = {k: today_status_totals[k] for k in today_cols}

    today_rows: list[dict] = []
    gt_sa = gt_on = gt_resch = gt_wait = gt_ref = gt_other = gt_tot = 0
    gt_statuses = {c: 0 for c in today_cols}
    for ldr in sorted(today_map.keys(), key=lambda s: s.lower()):
        ag_map = today_map[ldr]
        s_sa = s_on = s_resch = s_wait = s_ref = s_other = s_tot = 0
        s_statuses = {c: 0 for c in today_cols}
        for sn in sorted(ag_map.keys(), key=lambda s: s.lower()):
            c = ag_map[sn]
            s_sa += c["today_sa"]
            s_on += c["today_on_installation"]
            s_resch += c["today_reschedule"]
            s_wait += c["today_waiting_wo"]
            s_ref += c["today_refund"]
            s_other += c["today_other"]
            s_tot += c["today_total"]
            st_row = {}
            for col_nm in today_cols:
                v_c = int(c["statuses"].get(col_nm, 0))
                st_row[col_nm] = v_c
                s_statuses[col_nm] += v_c
            today_rows.append(
                {
                    "leader": ldr,
                    "salesname": sn,
                    "sa": c["today_sa"],
                    "on_installation": c["today_on_installation"],
                    "reschedule": c["today_reschedule"],
                    "refund": c["today_refund"],
                    "waiting_wo": c["today_waiting_wo"],
                    "other": c["today_other"],
                    "total": c["today_total"],
                    "statuses": st_row,
                    "row_type": "agent",
                }
            )
        gt_sa += s_sa
        gt_on += s_on
        gt_resch += s_resch
        gt_wait += s_wait
        gt_ref += s_ref
        gt_other += s_other
        gt_tot += s_tot
        for col_nm in today_cols:
            gt_statuses[col_nm] += s_statuses[col_nm]
        today_rows.append(
            {
                "leader": ldr,
                "salesname": f"{ldr} Total",
                "sa": s_sa,
                "on_installation": s_on,
                "reschedule": s_resch,
                "refund": s_ref,
                "waiting_wo": s_wait,
                "other": s_other,
                "total": s_tot,
                "statuses": s_statuses,
                "row_type": "leader_total",
            }
        )
    if today_rows:
        today_rows.append(
            {
                "leader": "Grand Total",
                "salesname": "Grand Total",
                "sa": gt_sa,
                "on_installation": gt_on,
                "reschedule": gt_resch,
                "refund": gt_ref,
                "waiting_wo": gt_wait,
                "other": gt_other,
                "total": gt_tot,
                "statuses": gt_statuses,
                "row_type": "grand_total",
            }
        )

    waiting_rows, waiting_total = _susun_pivot_wo_1kolom_py(waiting_map)
    besok_rows, besok_total = _susun_pivot_wo_1kolom_py(besok_map)

    summary_rows = [
        dict(summary_ldr[ldr], is_grand_total=False)
        for ldr in sorted(summary_ldr.keys(), key=lambda s: s.lower())
    ]
    if summary_rows:
        summary_rows.append(
            {
                "leader": "Grand Total",
                "today_sa": gt_sa,
                "today_on_installation": gt_on,
                "today_reschedule": gt_resch,
                "today_waiting_wo": gt_wait,
                "today_refund": gt_ref,
                "today_other": gt_other,
                "today_total": gt_tot,
                "wo_besok": besok_total,
                "waiting_wo": waiting_total,
                "is_grand_total": True,
            }
        )

    agent_summary_rows = []
    for ldr_s in sorted(summary_ldr.keys(), key=lambda s: s.lower()):
        ag_b = summary_agent.get(ldr_s, {})
        for sn_s in sorted(ag_b.keys(), key=lambda s: s.lower()):
            agent_summary_rows.append(ag_b[sn_s])

    return {
        "calc_version": 2,
        "day": tgl_wo.day,
        "today_label": today_lbl,
        "besok_label": besok_lbl,
        "besok_range_label": f">= {besok_lbl}",
        "wo_today_columns": today_cols,
        "wo_today_rows": today_rows,
        "wo_today_totals": {
            "sa": gt_sa,
            "on_installation": gt_on,
            "reschedule": gt_resch,
            "refund": gt_ref,
            "waiting_wo": gt_wait,
            "other": gt_other,
            "total": gt_tot,
            "statuses": today_status_totals_sorted,
        },
        "wo_today_other_statuses": {},
        "wo_besok_rows": besok_rows,
        "wo_besok_total": besok_total,
        "wo_besok_h1_total": besok_h1_total,
        "wo_besok_later_total": besok_later_total,
        "waiting_wo_rows": waiting_rows,
        "waiting_wo_total": waiting_total,
        "waiting_wo_breakdown": waiting_breakdown,
        "leader_summary": summary_rows,
        "agent_summary": agent_summary_rows,
    }


# =============================================================================
# SISTEM AUTENTIKASI LOGIN MULTI-ROLE (ADMIN, LEADER, AGEN, FINANCE)
# =============================================================================


def verifikasi_login_kredensial(
    username_input: str,
    password_input: str,
    df_target_ref: pd.DataFrame | None,
) -> dict | None:
    """Memverifikasi ID & Password dari `superadmin_config.json` dan `roles_config.json`.

    Seluruh ID & Password lama diblokir permanen dan Brankas hanya dapat dibuka Super Admin.
    """
    _ = df_target_ref
    u = re.sub(r"\s+", " ", str(username_input)).strip().lower()
    p = str(password_input).strip()

    if not u or not p:
        return None

    # 1. Cek Role Super Admin (Admin Master) — PBKDF2
    if verifikasi_super_admin(u, p):
        roles_cfg = muat_config_roles()
        unlocked = None
        if roles_cfg and roles_cfg.get("vault_enc") and roles_cfg.get("vault_salt"):
            unlocked = decrypt_vault(roles_cfg["vault_enc"], p, roles_cfg["vault_salt"])
        st.session_state["unlocked_vault"] = unlocked
        st.session_state["_sa_vault_secret"] = p
        return {
            "logged_in": True,
            "is_admin_master": True,
            "role": "Admin",
            "username": u,
            "display_name": "Yovi Arian (Super Admin)",
            "leader_scope": "Semua Leader",
            "agent_key": "",
        }

    # 2. Cek Finance, Sales Leader, dan Agen dari `roles_config.json` (hash terverifikasi)
    hasil_peran = verifikasi_peran_non_admin(u, p)
    if hasil_peran is not None:
        st.session_state["unlocked_vault"] = None
        st.session_state["_sa_vault_secret"] = None
        return hasil_peran

    return None


def tampilkan_halaman_login(df_target_ref: pd.DataFrame | None) -> None:
    """Menampilkan Halaman Portal Login Terproteksi WAF & Firewall (Tanpa Mengekspos ID/Password)."""
    _, col_mid, _ = st.columns([1, 2.0, 1])
    with col_mid:
        st.markdown(
            """
            <div class="login-hero">
                <div style="font-size: 2.4rem; margin-bottom: 6px;">🛡️🔒</div>
                <h1>Portal Eksekutif Telesales ISP</h1>
                <p>Sistem Terproteksi Web Application Firewall (WAF), Anti-Brute Force &amp; Enkripsi SHA-256</p>
                <div style="margin-top: 10px; display: flex; justify-content: center; gap: 8px; flex-wrap: wrap;">
                    <span class="exec-badge">🛡️ WAF Firewall: ACTIVE</span>
                    <span class="exec-badge">🔐 SHA-256 Auth</span>
                    <span class="exec-badge">🚫 Anti-SQLi &amp; Anti-XSS</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        sedang_lockout, sisa_detik = cek_status_lockout(st.session_state)
        if sedang_lockout:
            st.error(
                f"🚫 **FIREWALL PROTEKSI BRUTE-FORCE AKTIF:** Terlalu banyak percobaan login yang gagal. "
                f"Akses login dikunci sementara selama **{sisa_detik} detik** demi keamanan sistem."
            )
            return

        with st.form("form_login_utama", clear_on_submit=False):
            st.markdown("##### 🔐 Autentikasi Pengguna Resmi")
            st.caption(
                "Masukkan ID Pengguna dan Password resmi Anda. Daftar ID & Password bersifat rahasia dan hanya dikelola oleh **Admin Master**."
            )
            inp_user = st.text_input(
                "ID Pengguna / Username",
                placeholder="Masukkan ID Pengguna resmi Anda...",
            )
            inp_pass = st.text_input(
                "Password",
                type="password",
                placeholder="Masukkan Password resmi Anda...",
            )
            btn_submit_login = st.form_submit_button(
                "🚀 Masuk dengan Aman (WAF Verified)",
                type="primary",
                width="stretch",
            )

            if btn_submit_login:
                aman_u, pesan_waf_u = periksa_input_waf(inp_user, "ID Pengguna")
                aman_p, pesan_waf_p = periksa_input_waf(inp_pass, "Password")
                if not aman_u:
                    st.error(pesan_waf_u)
                elif not aman_p:
                    st.error(pesan_waf_p)
                else:
                    hasil_auth = verifikasi_login_kredensial(
                        inp_user, inp_pass, df_target_ref
                    )
                    if hasil_auth is not None:
                        reset_gagal_login(
                            st.session_state,
                            inp_user,
                            str(hasil_auth.get("role", "")),
                        )
                        st.session_state["auth_user"] = hasil_auth
                        st.rerun()
                    else:
                        jml_gagal, kena_lockout = catat_gagal_login(
                            st.session_state, inp_user
                        )
                        if kena_lockout:
                            st.error(
                                "🚫 **FIREWALL LOCKOUT:** Anda telah gagal login 5 kali berturut-turut. Sesi dikunci sementara selama 3 menit!"
                            )
                        else:
                            sisa_coba = MAKS_GAGAL_LOGIN - jml_gagal
                            st.error(
                                f"❌ ID Pengguna atau Password tidak valid! (Sisa percobaan sebelum terkunci Firewall: **{sisa_coba}x**). "
                                f"Hubungi **Admin Master** jika lupa kredensial Anda."
                            )



# =============================================================================
# FUNGSI PENGIRIMAN LAPORAN KE BOT TELEGRAM
# =============================================================================


def susun_pesan_telegram(
    df_mtd_final: pd.DataFrame,
    df_calc: pd.DataFrame,
    leader_login: str,
    kode_bln_lalu: str,
    kode_bln_ini: str,
    tahun_int: int,
    hari_berjalan_int: int,
    total_hari_int: int,
    sisa_hari_int: int,
    sisa_minggu_int: int,
    target_persen_mtd: int,
    wo_summary: dict | None = None,
) -> list[str]:
    """Merangkai pesan laporan Telegram (format HTML rapi) untuk Agen/Leader."""
    kol_oct = f"SA {kode_bln_lalu} 1-{hari_berjalan_int}"
    kol_nov = f"SA {kode_bln_ini} 1-{hari_berjalan_int}"
    kol_gap = "GAP SA"

    baris_tot_mtd = df_mtd_final[
        df_mtd_final["SALES LEADER"].astype(str).str.upper() == "TOTAL"
    ]
    if not baris_tot_mtd.empty:
        r_mtd = baris_tot_mtd.iloc[0]
        oct_v = int(r_mtd[kol_oct])
        nov_v = int(r_mtd[kol_nov])
        gap_v = int(r_mtd[kol_gap])
        acv_pct = (
            round_excel(((nov_v - oct_v) / float(oct_v)) * 100.0)
            if oct_v > 0
            else 0
        )
        panah = "↓" if acv_pct < 0 else "↑"
        ringkasan_mtd = (
            f"📈 <b>RINGKASAN MTD SA (1–{hari_berjalan_int} {kode_bln_ini} {tahun_int})</b>\n"
            f"├ {escape_html_tg(kol_oct)} : <b>{oct_v:,} SA</b>\n"
            f"├ {escape_html_tg(kol_nov)} : <b>{nov_v:,} SA</b>\n"
            f"└ GAP SA           : <b>{gap_v:+d} SA</b> ({panah} {acv_pct}%)\n"
        )
    else:
        ringkasan_mtd = ""

    if wo_summary and wo_summary.get("leader_summary"):
        wo_tot = wo_summary.get("wo_today_totals", {})
        besok_rng_tg = escape_html_tg(str(wo_summary.get("besok_range_label", wo_summary.get("besok_label", ""))))
        ringkasan_mtd += (
            f"\n🛠️ <b>MONITORING WO ({escape_html_tg(wo_summary.get('today_label', ''))})</b>\n"
            f"├ 1. WO Today   : <b>{int(wo_tot.get('total', 0))}</b> "
            f"(<b>SA {int(wo_tot.get('sa', 0))}</b> | On Install {int(wo_tot.get('on_installation', 0))} | Resched {int(wo_tot.get('reschedule', 0))} | Wait {int(wo_tot.get('waiting_wo', 0))} | Lain {int(wo_tot.get('other', 0))})\n"
            f"├ 2. WO Besok ({besok_rng_tg}) : <b>{int(wo_summary.get('wo_besok_total', 0))}</b>\n"
            f"└ 3. Waiting WO (Blank) : <b>{int(wo_summary.get('waiting_wo_total', 0))}</b>\n"
        )

    ldr_aman = escape_html_tg(leader_login)
    url_publik_tg = ambil_url_publik_aktif()
    baris_link_tg = (
        f"🌐 Link Dashboard Web : <a href=\"{escape_html_tg(url_publik_tg)}\">{escape_html_tg(url_publik_tg)}</a>\n"
        if url_publik_tg
        else ""
    )
    header = (
        f"📊 <b>LAPORAN PERFORMA &amp; TARGET TELESALES</b>\n"
        f"👨‍💼 Scope Leader : <b>{ldr_aman}</b>\n"
        f"🗓 Periode       : <b>{hari_berjalan_int}-{kode_bln_ini}-{tahun_int}</b> "
        f"(Sisa {sisa_hari_int} Hari / {sisa_minggu_int} Minggu)\n"
        f"🎯 Target Persentase Berjalan (MTD) : <b>{target_persen_mtd}%</b>\n"
        f"{baris_link_tg}"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{ringkasan_mtd}"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    footer = (
        "\n━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔥 <i>Bagi agen yang persentasenya masih di bawah {target_persen_mtd}%, wajib kejar kuota Paid per hari &amp; SA per hari agar tembus Tier Insentif (25%-35% + Rp 200rb/Yearly)!</i> 💪✨"
    )

    blok_pesan = []
    df_calc_valid = df_calc[
        ~df_calc["SALES NAME"]
        .astype(str)
        .str.strip()
        .str.upper()
        .isin(["", "NAN", "NONE", "TOTAL", "-"])
    ].copy()

    for nama_ldr, grp_ldr in df_calc_valid.groupby("SALES LEADER", sort=False):
        for no_urut, (_, r) in enumerate(grp_ldr.iterrows(), start=1):
            nama_agen = escape_html_tg(str(r["SALES NAME"]).strip())
            level_agen = escape_html_tg(str(r["LEVEL"]).strip())
            persen_int = int(r["PERSENTASE_INT"])
            komisi_str = escape_html_tg(format_rupiah(r["Estimasi_Komisi_Num"]))

            sa_val = int(r["SA NOV"])
            paid_val = int(r["PAID NOV"])
            so_val = int(r["SO NOV"])
            target_total_val = int(r["TARGET ALL"])
            gap_sa_val = int(r["GAP SA NOV"])
            runrate_val = int(r["RUNRATE 30 HARI"])

            harus_sa_hr = int(r["Harus_SA_Per_Hari_Bulat"])
            harus_sa_des = float(r["Harus_SA_Per_Hari_Desimal"])
            harus_paid_hr = int(r["Harus_Paid_Per_Hari_Bulat"])
            harus_so_hr = int(r["Harus_SO_Per_Hari_Bulat"])

            paid_mgg = int(r["Catchup_Paid_Mingguan"])
            sa_mgg = int(r["Catchup_SA_Mingguan"])
            target_paid_bln = int(r["Target_Paid_Bulanan"])

            if persen_int < target_persen_mtd:
                kurang_pct = target_persen_mtd - persen_int
                kurang_sa_mtd = int(r["Kurang_SA_MTD"])
                badge_status = (
                    f"⚠️ <b>MASIH KURANG ({persen_int}% &lt; Target {target_persen_mtd}%)</b> "
                    f"[Kurang {kurang_pct}% / {kurang_sa_mtd} SA ke MTD]"
                )
            else:
                badge_status = f"✅ <b>ON-TRACK MTD ({persen_int}% &ge; Target {target_persen_mtd}%)</b>"

            tier_str = escape_html_tg(str(r.get("Tier_Komisi", "Tier 0 (0%)")))
            teks_agen = (
                f"<b>{no_urut}. 👤 {nama_agen}</b> ({level_agen})\n"
                f"├ 📌 Status MTD       : {badge_status}\n"
                f"├ ✅ Realisasi        : <b>{sa_val} SA</b> | <b>{paid_val} Paid</b> | <b>{so_val} SO</b> (Gap: {gap_sa_val} SA)\n"
                f"├ 📦 Breakdown Paket  : 3M={int(r['3 Monthly'])} | M={int(r['Monthly'])} | Sem={int(r['Semesterly'])} | Y={int(r['Yearly'])}\n"
                f"├ ⚡ <b>Wajib Kejar Harian</b>   : <b>{harus_paid_hr} Paid/hari</b> &amp; <b>{harus_sa_hr} SA/hari</b> ({harus_sa_des:.1f} SA | Cetak {harus_so_hr} SO)\n"
                f"├ 📅 <b>Wajib Kejar Mingguan</b> : <b>{paid_mgg} Paid/minggu</b> &amp; <b>{sa_mgg} SA/minggu</b>\n"
                f"├ 🎯 <b>Target Total Bulanan</b> : <b>{target_total_val} SA</b> (Wajib <b>{target_paid_bln} Paid</b>)\n"
                f"├ 🚀 Runrate {total_hari_int} Hari  : <b>{runrate_val} SA</b>\n"
                f"└ 💰 Estimasi Komisi  : <b>{komisi_str}</b> ({tier_str})"
            )
            blok_pesan.append(teks_agen)

        sum_target_all = int(grp_ldr["TARGET ALL"].sum())
        sum_sa_nov = int(grp_ldr["SA NOV"].sum())
        sum_paid_nov = int(grp_ldr["PAID NOV"].sum())
        sum_so_nov = int(grp_ldr["SO NOV"].sum())
        sum_gap_sa = int(grp_ldr["GAP SA NOV"].sum())
        persen_ldr = (
            round_excel((float(sum_sa_nov) / float(sum_target_all)) * 100.0)
            if sum_target_all > 0
            else 0
        )
        runrate_ldr = round_excel(
            (float(sum_sa_nov) * float(total_hari_int))
            / float(max(1, hari_berjalan_int))
        )
        sum_harus_sa_h = int(grp_ldr["Harus_SA_Per_Hari_Bulat"].sum())
        sum_harus_paid_h = int(grp_ldr["Harus_Paid_Per_Hari_Bulat"].sum())
        sum_komisi_ldr = escape_html_tg(
            format_rupiah(grp_ldr["Estimasi_Komisi_Num"].sum())
        )
        jml_agen_kurang = int(
            (grp_ldr["PERSENTASE_INT"] < target_persen_mtd).sum()
        )
        nama_ldr_upper = escape_html_tg(str(nama_ldr).upper())

        teks_subtotal = (
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 <b>TOTAL TIM {nama_ldr_upper}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"├ 🎯 Target Total Tim  : <b>{sum_target_all} SA</b>\n"
            f"├ ✅ Realisasi Tim     : <b>{sum_sa_nov} SA</b> | <b>{sum_paid_nov} Paid</b> | <b>{sum_so_nov} SO</b>\n"
            f"├ 📊 Pencapaian Tim    : <b>{persen_ldr}%</b> (Gap: {sum_gap_sa} SA | Runrate: {runrate_ldr} SA)\n"
            f"├ ⚠️ Agen &lt; {target_persen_mtd}% MTD    : <b>{jml_agen_kurang} Agen</b> masih kurang secara persentase\n"
            f"├ ⚡ Wajib Harian Tim  : <b>{sum_harus_paid_h} Paid/hari</b> &amp; <b>{sum_harus_sa_h} SA/hari</b>\n"
            f"└ 💰 Total Komisi Tim  : <b>{sum_komisi_ldr}</b>\n"
            f"──────────────────────"
        )
        blok_pesan.append(teks_subtotal)

    daftar_pesan: list[str] = []
    pesan_aktif = header
    for idx, blok in enumerate(blok_pesan):
        tambahan = blok + "\n\n"
        batas = 3700 if idx < len(blok_pesan) - 1 else 3700 - len(footer)
        if len(pesan_aktif) + len(tambahan) > batas:
            daftar_pesan.append(pesan_aktif.rstrip())
            pesan_aktif = (
                f"📋 <b>Lanjutan Laporan Telesales ({ldr_aman})</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n\n" + tambahan
            )
        else:
            pesan_aktif += tambahan

    pesan_aktif = pesan_aktif.rstrip() + "\n" + footer
    daftar_pesan.append(pesan_aktif)
    return daftar_pesan


def kirim_laporan_ke_telegram(
    bot_token: str,
    chat_id: str,
    daftar_pesan: list[str],
) -> tuple[bool, str]:
    """Mengirimkan daftar pesan laporan ke Telegram menggunakan HTTP POST (parse_mode HTML)."""
    token_bersih = bot_token.strip()
    chat_id_bersih = chat_id.strip()

    if not token_bersih:
        return False, "Error: TELEGRAM_BOT_TOKEN belum diisi di Sidebar."
    if not chat_id_bersih:
        return (
            False,
            "Error: TELEGRAM_CHAT_ID belum diisi di Sidebar (ketik /id di grup/chat Bot Telegram Anda untuk melihat Chat ID).",
        )

    url = f"https://api.telegram.org/bot{token_bersih}/sendMessage"
    try:
        for idx, teks in enumerate(daftar_pesan, start=1):
            resp = requests.post(
                url,
                json={
                    "chat_id": chat_id_bersih,
                    "text": teks,
                    "parse_mode": "HTML",
                },
                timeout=15,
            )
            if resp.status_code != 200:
                try:
                    ket = resp.json().get("description", resp.text)
                except Exception:
                    ket = resp.text
                return (
                    False,
                    f"Gagal mengirim ke Telegram (HTTP {resp.status_code}) pada bagian {idx}: {ket}",
                )
        return (
            True,
            f"Laporan berhasil dikirim ke Telegram Chat ID {chat_id_bersih} ({len(daftar_pesan)} pesan, HTTP 200 OK)!",
        )
    except requests.RequestException as exc:
        return False, f"Gagal menghubungi server Telegram: {exc}"


def _keterangan_error_tg(resp: requests.Response) -> str:
    """Mengambil deskripsi error dari respons API Telegram."""
    try:
        return str(resp.json().get("description", resp.text))
    except Exception:
        return resp.text


def kirim_gambar_ke_telegram(
    bot_token: str,
    chat_id: str,
    daftar_gambar: list[tuple[str, bytes, str]],
    sebagai_dokumen: bool = False,
) -> tuple[bool, str]:
    """Mengirim Gambar Presentasi Laporan (PNG) ke Telegram."""
    token_bersih = bot_token.strip()
    chat_id_bersih = chat_id.strip()
    if not token_bersih:
        return False, "Error: TELEGRAM_BOT_TOKEN belum diisi di Sidebar."
    if not chat_id_bersih:
        return (
            False,
            "Error: TELEGRAM_CHAT_ID belum diisi di Sidebar (ketik /id di grup/chat Bot Telegram Anda untuk melihat Chat ID).",
        )
    if not daftar_gambar:
        return False, "Tidak ada gambar presentasi yang dapat dikirim."

    url_dasar = f"https://api.telegram.org/bot{token_bersih}"
    try:
        if sebagai_dokumen:
            for nama_file, data_png, caption in daftar_gambar:
                resp = requests.post(
                    f"{url_dasar}/sendDocument",
                    data={
                        "chat_id": chat_id_bersih,
                        "caption": caption,
                        "parse_mode": "HTML",
                    },
                    files={"document": (nama_file, data_png, "image/png")},
                    timeout=60,
                )
                if resp.status_code != 200:
                    return (
                        False,
                        f"Gagal mengirim gambar {nama_file} (HTTP {resp.status_code}): {_keterangan_error_tg(resp)}",
                    )
            return (
                True,
                f"{len(daftar_gambar)} gambar presentasi terkirim (format File/Dokumen)",
            )

        for awal in range(0, len(daftar_gambar), 10):
            potongan = daftar_gambar[awal : awal + 10]
            if len(potongan) == 1:
                nama_file, data_png, caption = potongan[0]
                resp = requests.post(
                    f"{url_dasar}/sendPhoto",
                    data={
                        "chat_id": chat_id_bersih,
                        "caption": caption,
                        "parse_mode": "HTML",
                    },
                    files={"photo": (nama_file, data_png, "image/png")},
                    timeout=60,
                )
            else:
                media_json = []
                berkas = {}
                for j, (nama_file, data_png, caption) in enumerate(potongan):
                    kunci = f"foto{j}"
                    berkas[kunci] = (nama_file, data_png, "image/png")
                    media_json.append(
                        {
                            "type": "photo",
                            "media": f"attach://{kunci}",
                            "caption": caption,
                            "parse_mode": "HTML",
                        }
                    )
                resp = requests.post(
                    f"{url_dasar}/sendMediaGroup",
                    data={
                        "chat_id": chat_id_bersih,
                        "media": json.dumps(media_json),
                    },
                    files=berkas,
                    timeout=120,
                )

            if resp.status_code != 200:
                sukses_dok, pesan_dok = kirim_gambar_ke_telegram(
                    token_bersih,
                    chat_id_bersih,
                    daftar_gambar[awal:],
                    sebagai_dokumen=True,
                )
                return (
                    sukses_dok,
                    f"Mode Foto ditolak Telegram ({_keterangan_error_tg(resp)}), dialihkan ke mode Dokumen: {pesan_dok}",
                )

        return (
            True,
            f"{len(daftar_gambar)} gambar presentasi terkirim (format Foto/Album)",
        )
    except requests.RequestException as exc:
        return (
            False,
            f"Gagal menghubungi server Telegram saat mengirim gambar: {exc}",
        )


# =============================================================================
# KELAS SMARTDATAFRAME UNTUK FITUR AI CHATBOT ASSISTANT
# =============================================================================


class SmartDataframe:
    """Kelas SmartDataframe untuk fitur Tanya AI (kompatibel dengan PandasAI, Groq, OpenAI, & Lokal)."""

    def __init__(self, df: pd.DataFrame, config: dict | None = None) -> None:
        self.df = df.copy()
        self.config = config or {}
        self.provider = self.config.get("provider", "Groq API (Llama-3.3-70B)")
        self.api_key = str(self.config.get("api_key", "")).strip()
        self.role_akses = str(self.config.get("role_akses", "Leader"))

    def chat(self, pertanyaan: str) -> str:
        if (
            self.provider == "PandasAI (SmartDataframe)"
            and PANDASAI_TERSEDIA
            and self.api_key
        ):
            try:
                from pandasai.llm import OpenAI as PandasAIOpenAI  # type: ignore

                llm = PandasAIOpenAI(api_token=self.api_key)
                sdf_asli = PandasAISmartDataframe(self.df, config={"llm": llm})
                return str(sdf_asli.chat(pertanyaan))
            except Exception:
                pass

        if self.api_key and self.provider in (
            "Groq API (Llama-3.3-70B)",
            "OpenAI API (GPT-4o-mini)",
            "PandasAI (SmartDataframe)",
        ):
            jawaban_api = self._tanya_llm_api(pertanyaan)
            if jawaban_api:
                return jawaban_api

        return self._analisis_lokal(pertanyaan)

    def _tanya_llm_api(self, pertanyaan: str) -> str | None:
        csv_data = self.df.to_csv(index=False)
        sistem_prompt = (
            "Anda adalah AI Data Analyst untuk Dashboard Telesales ISP. "
            f"Berikut adalah DataFrame hasil perhitungan komisi dan target:\n\n{csv_data}\n\n"
            "Jawablah pertanyaan pengguna dalam Bahasa Indonesia secara akurat dan gunakan format Rupiah (Rp)."
        )
        url = (
            "https://api.openai.com/v1/chat/completions"
            if "OpenAI" in self.provider
            else "https://api.groq.com/openai/v1/chat/completions"
        )
        model_name = (
            "gpt-4o-mini"
            if "OpenAI" in self.provider
            else "llama-3.3-70b-versatile"
        )
        try:
            resp = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": sistem_prompt},
                        {"role": "user", "content": pertanyaan},
                    ],
                    "temperature": 0.2,
                },
                timeout=20,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
        except Exception:
            pass
        return None

    def _analisis_lokal(self, pertanyaan: str) -> str:
        q = pertanyaan.lower().strip()
        df = self.df[
            self.df["SALES NAME"].astype(str).str.upper() != "TOTAL"
        ].copy()
        if df.empty:
            return "Data komisi masih kosong."

        if any(k in q for k in ["kurang", "bawah", "rendah", "belum"]):
            df_kurang = df[
                df["STATUS PERSENTASE"]
                .astype(str)
                .str.contains("Kurang", case=False)
            ]
            if not df_kurang.empty:
                baris_k = "\n".join(
                    f"{i + 1}. **{r['SALES NAME']}** ({r['SALES LEADER']}) — Pencapaian: `{r['PERSENTASE']}` (`{r['STATUS PERSENTASE']}`) | Wajib: **`{r['Harus Paid / Hari']}`** & **`{r['Harus SA / Hari']}`**"
                    for i, (_, r) in enumerate(df_kurang.iterrows())
                )
                return (
                    f"⚠️ **Daftar Agen yang Secara Persentase Masih Kurang ({len(df_kurang)} Agen):**\n\n"
                    f"{baris_k}"
                )

        if any(
            k in q
            for k in [
                "paling besar",
                "terbesar",
                "tertinggi",
                "paling tinggi",
                "terbanyak",
                "top",
                "terbaik",
            ]
        ):
            df_urut = df.sort_values(
                by=["SA NOV", "TARGET ALL"], ascending=[False, False]
            ).reset_index(drop=True)
            top1 = df_urut.iloc[0]
            top5 = "\n".join(
                f"{i + 1}. **{r['SALES NAME']}** ({r['SALES LEADER']}) — SA NOV: `{int(r['SA NOV'])}` / Target: `{int(r['TARGET ALL'])}` (`{r['PERSENTASE']}`) | Komisi: **`{r['Estimasi Komisi']}`**"
                for i, r in df_urut.head(5).iterrows()
            )
            return (
                f"🏆 Agen dengan pencapaian tertinggi saat ini adalah **{top1['SALES NAME']}** "
                f"(`{int(top1['SA NOV'])}` SA dari Target `{int(top1['TARGET ALL'])}`, Estimasi Komisi **`{top1['Estimasi Komisi']}`**).\n\n"
                f"**Top 5 Agen:**\n{top5}"
            )

        for _, row in df.iterrows():
            nama = str(row["SALES NAME"])
            if nama.lower() in q or any(
                kata in q for kata in nama.lower().split() if len(kata) >= 4
            ):
                info_target = f"**TARGET ALL**: `{int(row['TARGET ALL'])}`"
                if (
                    self.role_akses in ("Admin", "Finance")
                    and "Reguler" in row
                    and "Yearly (Target)" in row
                ):
                    info_target += f" (Reguler: `{int(row['Reguler'])}`, Yearly: `{int(row['Yearly (Target)'])}`)"

                return (
                    f"### 👤 Detail Performa & Target Agen: **{nama}**\n"
                    f"- **Sales Leader**: `{row['SALES LEADER']}` | **Level**: `{row['LEVEL']}` | **Masa Kerja**: `{row['MASA KERJA']}`\n"
                    f"- {info_target}\n"
                    f"- **SA NOV**: `{int(row['SA NOV'])}` | **GAP SA NOV**: `{int(row['GAP SA NOV'])}` | **PERSENTASE**: `{row['PERSENTASE']}` (`{row['STATUS PERSENTASE']}`)\n"
                    f"- **RUNRATE 30 HARI**: `{int(row['RUNRATE 30 HARI'])}`\n"
                    f"- **Harus Paid / Hari**: **`{row['Harus Paid / Hari']}`** | **Harus SA / Hari**: **`{row['Harus SA / Hari']}`**\n"
                    f"- **Estimasi Komisi**: **`{row['Estimasi Komisi']}`**"
                )

        return (
            f"📊 **Ringkasan Data ({len(df)} Agen):**\n"
            f"- **Total SA NOV**: `{int(df['SA NOV'].sum())}` dari Target `{int(df['TARGET ALL'].sum())}`\n"
            f"- **Breakdown Paket**: 3 Monthly=`{int(df['3 Monthly'].sum())}`, Monthly=`{int(df['Monthly'].sum())}`, Semesterly=`{int(df['Semesterly'].sum())}`, Yearly=`{int(df['Yearly'].sum())}`"
        )


# =============================================================================
# PRE-LOAD DATA TARGET AWAL UNTUK KEPERLUAN LOGIN & DAFTAR AKUN
# =============================================================================

df_target_awal = None
if os.path.isfile(DEFAULT_TARGET_PATH):
    try:
        df_target_awal = baca_data_target_excel(
            DEFAULT_TARGET_PATH, "NOVEMBER'26", datetime.date(2026, 11, 8)
        )
    except Exception:
        df_target_awal = None

# Inisialisasi state autentikasi
if "auth_user" not in st.session_state:
    st.session_state["auth_user"] = None

# Jika belum login, tampilkan Halaman Portal Login Multi-Role dan hentikan eksekusi halaman utama
if (
    st.session_state["auth_user"] is None
    or not st.session_state["auth_user"].get("logged_in", False)
):
    tampilkan_halaman_login(df_target_awal)
    st.stop()

# Ambil informasi akun yang sedang login (fallback aman jika diimpor di luar streamlit run)
akun_aktif = st.session_state.get("auth_user") or {
    "logged_in": True,
    "is_admin_master": True,
    "role": "Admin",
    "display_name": "Yovi Arian (Super Admin)",
    "leader_scope": "Semua Leader",
    "agent_key": "",
}
role_login_awal = str(akun_aktif.get("role", "Leader"))
is_admin_master = bool(
    akun_aktif.get("is_admin_master", role_login_awal == "Admin")
)
nama_pengguna_aktif = str(akun_aktif.get("display_name", "Yovi Arian"))
scope_leader_akun = str(akun_aktif.get("leader_scope", "Yovi Arian"))
agent_key_akun = str(akun_aktif.get("agent_key", ""))

# =============================================================================
# 1. SIDEBAR PROFIL PENGGUNA, PANEL ADMIN MASTER & PENGATURAN PARAMETER
# =============================================================================

ikon_role_map = {
    "Admin": "👑 ADMIN MASTER",
    "Leader": "👨‍💼 SALES LEADER",
    "Agen": "👤 AGEN TELESALES",
    "Finance": "💳 DIVISI FINANCE",
}
badge_role_teks = ikon_role_map.get(role_login_awal, "👨‍💼 PENGGUNA")

st.sidebar.markdown(
    f"""
    <div class="sidebar-profile">
        <div class="sidebar-profile-role">{badge_role_teks}</div>
        <div class="sidebar-profile-name">{escape_html_tg(nama_pengguna_aktif)}</div>
        <div class="sidebar-profile-scope">Scope: <b>{escape_html_tg(scope_leader_akun)}</b> | 🛡️ WAF Aktif</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.sidebar.button("🚪 Keluar / Ganti Akun (Logout)", width="stretch"):
    st.session_state["auth_user"] = None
    st.session_state["unlocked_vault"] = None
    st.session_state["_sa_vault_secret"] = None
    st.rerun()

# HANYA ADMIN MASTER yang dapat melihat Brankas ID & Password, Log Firewall, dan Simulasi Role
role_akses = role_login_awal
if is_admin_master:
    url_publik_sidebar = ambil_url_publik_aktif()
    url_lan_sidebar = ambil_url_lan_aktif(8501)
    with st.sidebar.expander(
        "🌐 Link Akses Go-Live (Khusus Admin Master)", expanded=False
    ):
        st.markdown("✅ **Domain Live Resmi (cPanel Non-Docker):**  \nhttps://laporantelesalesoxygen.my.id/index.php")
        if url_publik_sidebar:
            st.markdown(
                f"✅ **Tunnel Publik Cadangan:**  \n"
                f"[{url_publik_sidebar}]({url_publik_sidebar})"
            )
        st.markdown(f"📶 **Akses Wi-Fi / LAN Kantor:**  \n`{url_lan_sidebar}`")

    with st.sidebar.expander(
        "🔐 Brankas ID & Password (Khusus Admin Master)", expanded=False
    ):
        st.caption(
            "Daftar ID & Password BARU seluruh Role tersimpan terenkripsi dan **DISEMBUNYIKAN** dari publik."
        )
        v_dec = st.session_state.get("unlocked_vault")
        if isinstance(v_dec, dict):
            fin_meta = v_dec.get("finance", {})
            ldr_meta = v_dec.get("leaders", {})
            agt_meta = v_dec.get("agen", {})
            ldr_ids_str = ", ".join(sorted(ldr_meta.get("ids", {}).keys()))
            agt_sample_str = ", ".join(agt_meta.get("sample_ids", [])[:5])
            df_vault_master = pd.DataFrame(
                [
                    {
                        "Role": "👑 Super Admin",
                        "ID / Username": username_super_admin() or v_dec.get("super_admin_id", "-"),
                        "Password": "🔒 Master Key Aktif (PBKDF2)",
                    },
                    {
                        "Role": "💳 Finance",
                        "ID / Username": fin_meta.get("id", "-"),
                        "Password": fin_meta.get("pass", "🔒 Terenkripsi"),
                    },
                    {
                        "Role": "👨‍💼 Sales Leader",
                        "ID / Username": ldr_ids_str or "-",
                        "Password": ldr_meta.get("pass_default", "🔒 Terenkripsi"),
                    },
                    {
                        "Role": f"👤 Agen ({agt_meta.get('total', 0)} Akun)",
                        "ID / Username": f"Format unik agt_<nama> (mis: {agt_sample_str}...)",
                        "Password": agt_meta.get("pass_default", "🔒 Terenkripsi"),
                    },
                ]
            )
            st.dataframe(df_vault_master, width="stretch", hide_index=True)
        else:
            st.info("Login ulang dengan ID & Password Super Admin untuk mendekripsi Brankas Vault.")

    with st.sidebar.expander(
        "🛡️ Monitor WAF & Firewall Log (Khusus Admin Master)", expanded=False
    ):
        st.caption("Catatan real-time aktivitas login & blokir serangan WAF:")
        log_baris = baca_log_keamanan_terbaru(15)
        st.code("\n".join(log_baris), language="text")

    daftar_opsi_role = ["Admin", "Leader", "Agen", "Finance"]
    idx_role_aktif = (
        daftar_opsi_role.index(role_login_awal)
        if role_login_awal in daftar_opsi_role
        else 0
    )
    with st.sidebar.expander(
        "🔄 Simulasi Role (Khusus Admin Master)", expanded=False
    ):
        role_akses = st.radio(
            "Role Akses Aktif:",
            options=daftar_opsi_role,
            index=idx_role_aktif,
        )
        if role_akses != role_login_awal:
            st.session_state["auth_user"]["role"] = role_akses
            st.session_state["auth_user"]["is_admin_master"] = True
            if role_akses in ("Admin", "Finance"):
                st.session_state["auth_user"]["display_name"] = (
                    "Yovi Arian (Super Admin)"
                    if role_akses == "Admin"
                    else "Divisi Finance & Komisi"
                )
                st.session_state["auth_user"]["leader_scope"] = "Semua Leader"
            elif role_akses == "Leader" and scope_leader_akun == "Semua Leader":
                st.session_state["auth_user"]["display_name"] = "Yovi Arian"
                st.session_state["auth_user"]["leader_scope"] = "Yovi Arian"
            elif role_akses == "Agen" and not agent_key_akun:
                st.session_state["auth_user"]["display_name"] = (
                    "Askih Milli Priyanto"
                )
                st.session_state["auth_user"]["leader_scope"] = "Yovi Arian"
                st.session_state["auth_user"]["agent_key"] = (
                    "ASKIH MILLI PRIYANTO"
                )
            st.rerun()

    with st.sidebar.expander(
        "🔄 Sync ke Server Live (laporantelesalesoxygen.my.id)", expanded=False
    ):
        st.caption("Dorong pembaruan Excel & parameter langsung ke server PHP tanpa Docker:")
        if st.button("🚀 Sync Data Lokal -> Server Live", width="stretch"):
            sa_sec = str(st.session_state.get("_sa_vault_secret") or "")
            sa_uid = str(akun_aktif.get("username") or username_super_admin())
            if not sa_sec:
                st.warning("Login ulang sebagai Super Admin untuk mengaktifkan Auto-Sync.")
            else:
                try:
                    from sync_ke_server import sync_files_ke_server

                    nov_path = os.path.join(FOLDER_PROYEK, "list_prospect November.xls")
                    res_sync = sync_files_ke_server(
                        url_server="https://laporantelesalesoxygen.my.id/index.php",
                        api_user=sa_uid,
                        api_pass=sa_sec,
                        target_path=DEFAULT_TARGET_PATH if os.path.isfile(DEFAULT_TARGET_PATH) else None,
                        prospect_paths=[nov_path] if os.path.isfile(nov_path) else [],
                    )
                    if res_sync.get("ok"):
                        st.success(f"✅ Server Live diupdate! Periode: {res_sync.get('periode')} | Total Baris: {res_sync.get('total_prospect')}")
                    else:
                        st.error(f"❌ Gagal sync: {res_sync.get('error')}")
                except Exception as exc_sync:
                    st.error(f"❌ Gagal menghubungi server live: {exc_sync}")


if role_akses in ("Admin", "Finance"):
    st.sidebar.info(
        f"🔓 **Akses {role_akses}**: Menampilkan detail target lengkap (`TARGET ALL`, `Reguler`, dan `Yearly`)."
    )
else:
    st.sidebar.success(
        f"🔒 **Akses {role_akses}**: Detail `Reguler` & `Yearly` disembunyikan. Hanya menampilkan **`TARGET ALL` (`Target Total`)** beserta kuota **Paid / Hari & SA / Hari**."
    )

st.sidebar.divider()
st.sidebar.subheader("📅 Parameter Waktu & Target")

col_b1, col_b2 = st.sidebar.columns(2)
with col_b1:
    bulan_lalu_input = st.number_input(
        "Bulan Lalu (OCT)",
        min_value=1,
        max_value=12,
        value=10,
        step=1,
    )
with col_b2:
    bulan_ini_input = st.number_input(
        "Bulan Ini (NOV)",
        min_value=1,
        max_value=12,
        value=11,
        step=1,
    )

tahun_input = st.sidebar.number_input(
    "Tahun (2026)",
    min_value=2020,
    max_value=2035,
    value=2026,
    step=1,
)

total_hari_bulan_ini = st.sidebar.number_input(
    "Total Hari Bulan Ini (misal 30)",
    min_value=1,
    max_value=31,
    value=30,
    step=1,
)

hari_berjalan_saat_ini = st.sidebar.number_input(
    "Hari Berjalan Saat Ini (misal 22)",
    min_value=1,
    max_value=31,
    value=22,
    step=1,
)

rasio_paid_per_sa = st.sidebar.number_input(
    "Rasio Target Paid per 1 SA (Buffer Paid)",
    min_value=1.0,
    max_value=2.5,
    value=1.25,
    step=0.05,
    help="Berapa Paid yang harus dicapai untuk menghasilkan 1 SA (Active). Default 1.25x (mengantisipasi jeda instalasi/reschedule).",
)

nama_sheet_target = st.sidebar.text_input(
    "Nama Sheet Target Excel:",
    value="NOVEMBER'26",
)

st.sidebar.divider()
st.sidebar.subheader("📂 Upload File Sumber")

if role_akses in ("Admin", "Leader"):
    uploaded_target = st.sidebar.file_uploader(
        "Upload File Target (.xlsx)",
        type=["xlsx"],
    )

    uploaded_prospects = st.sidebar.file_uploader(
        "Upload File Prospect (.xls HTML)",
        type=["xls", "html", "xlsx"],
        accept_multiple_files=True,
    )
else:
    uploaded_target = None
    uploaded_prospects = []
    st.sidebar.info(
        "🔒 Upload file hanya tersedia untuk role **Admin** dan **Sales Leader**."
    )

st.sidebar.divider()
st.sidebar.subheader("🤖 Notifikasi Bot Telegram")
telegram_bot_token = st.sidebar.text_input(
    "TELEGRAM_BOT_TOKEN",
    value="9242894728:AAF2oYVZlpfcHEIFcC9PdoeFQA6KuwF-njs",
    type="password",
)
telegram_chat_id = st.sidebar.text_input(
    "TELEGRAM_CHAT_ID",
    placeholder="Ketik /id di Bot Telegram untuk cek Chat ID...",
    help="Masukkan Chat ID grup atau chat pribadi Telegram tujuan pengiriman laporan.",
)

with st.sidebar.expander("🧠 Pengaturan AI Chatbot (Opsional)"):
    llm_provider = st.selectbox(
        "Engine AI Chatbot",
        options=[
            "Groq API (Llama-3.3-70B)",
            "OpenAI API (GPT-4o-mini)",
            "PandasAI (SmartDataframe)",
            "Mode Lokal Cerdas (Tanpa API Key)",
        ],
    )
    llm_api_key = st.text_input(
        "API Key LLM (Opsional)",
        type="password",
        placeholder="gsk_... atau sk-...",
    )

# =============================================================================
# 2. EKSTRAKSI DATA (Data Extraction)
# =============================================================================

bulan_lalu_int = int(bulan_lalu_input)
bulan_ini_int = int(bulan_ini_input)
tahun_int = int(tahun_input)
total_hari_int = int(total_hari_bulan_ini)
hari_berjalan_int = int(hari_berjalan_saat_ini)
sisa_hari_int = max(1, total_hari_int - hari_berjalan_int)
sisa_minggu_int = max(1, math.ceil(sisa_hari_int / 7.0))
rasio_paid_float = float(rasio_paid_per_sa)

# Target Persentase Berjalan (MTD) sesuai Gambar 1: =ROUND(Hari_Berjalan / Total_Hari * 100, 0)%
target_persen_mtd = round_excel(
    (float(hari_berjalan_int) / float(max(1, total_hari_int))) * 100.0
)

kode_bln_lalu = NAMA_BULAN_SINGKAT.get(bulan_lalu_int, "OCT")
kode_bln_ini = NAMA_BULAN_SINGKAT.get(bulan_ini_int, "NOV")
nama_bln_tampil = NAMA_BULAN_TAMPIL.get(bulan_ini_int, "Nov")

try:
    tgl_acuan_laporan = datetime.date(
        tahun_int,
        bulan_ini_int,
        min(
            hari_berjalan_int,
            calendar.monthrange(tahun_int, bulan_ini_int)[1],
        ),
    )
except Exception:
    tgl_acuan_laporan = datetime.date(2026, 11, 8)

# Baca Data Target (dengan fallback otomatis ke TARGET PER MONTH.xlsx di folder proyek)
df_target = None
sumber_target = (
    uploaded_target
    if uploaded_target is not None
    else (
        DEFAULT_TARGET_PATH if os.path.isfile(DEFAULT_TARGET_PATH) else None
    )
)
if sumber_target is not None:
    try:
        df_target = baca_data_target_excel(
            sumber_target, nama_sheet_target, tgl_acuan_laporan
        )
    except Exception as err:
        st.error(f"Gagal membaca File Target (.xlsx): {err}")

# Baca Data Prospect (loop semua file prospect yang di-upload, atau fallback ke file proyek)
df_prospect_all = None
list_df_prospect = []

if uploaded_prospects:
    for f_up in uploaded_prospects:
        try:
            list_df_prospect.append(baca_file_prospect_html(f_up))
        except Exception as err:
            st.error(f"Gagal membaca file prospect `{f_up.name}`: {err}")
else:
    for path_def in DEFAULT_PROSPECT_FILES:
        if os.path.isfile(path_def):
            try:
                list_df_prospect.append(baca_file_prospect_html(path_def))
            except Exception:
                pass

if list_df_prospect:
    df_prospect_all = dedup_prospect_df(
        pd.concat(list_df_prospect, ignore_index=True)
    )
    df_prospect_all["Active Date"] = pd.to_datetime(
        df_prospect_all["Active Date"], errors="coerce"
    )

# Penentuan Scope Leader & Agen berdasarkan Role Login
leader_login = "Semua Leader"
agen_fokus_key = ""

if df_prospect_all is not None and not df_prospect_all.empty:
    kandidat_ldr = set(
        df_prospect_all["Sales Leader"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )
    if df_target is not None and not df_target.empty:
        kandidat_ldr.update(
            df_target["Leader_Default"].dropna().astype(str).unique().tolist()
        )
    daftar_leader_unik = sorted(k for k in kandidat_ldr if k)

    if role_akses in ("Admin", "Finance"):
        opsi_scope_admin = ["Semua Leader"] + daftar_leader_unik
        leader_login = st.sidebar.selectbox(
            "Filter Scope Sales Leader:",
            options=opsi_scope_admin,
            index=0,
        )
    elif role_akses == "Leader":
        idx_default = 0
        for i, ldr in enumerate(daftar_leader_unik):
            if ldr.lower() == scope_leader_akun.lower() or (
                scope_leader_akun == "Semua Leader" and "yovi" in ldr.lower()
            ):
                idx_default = i
                break
        leader_login = st.sidebar.selectbox(
            "Scope Tim Sales Leader:",
            options=daftar_leader_unik,
            index=idx_default,
        )
    elif role_akses == "Agen":
        idx_default = 0
        for i, ldr in enumerate(daftar_leader_unik):
            if ldr.lower() == scope_leader_akun.lower():
                idx_default = i
                break
        leader_login = st.sidebar.selectbox(
            "Tim Sales Leader Anda:",
            options=daftar_leader_unik,
            index=idx_default,
        )
        if df_target is not None and not df_target.empty:
            df_opsi_agen = df_target[
                (df_target["Leader_Default"] == leader_login)
                & (
                    ~df_target["Agent_Key"]
                    .astype(str)
                    .str.startswith("VACANT__")
                )
            ]
            daftar_nama_agen = df_opsi_agen["Nama_Tampil"].tolist()
            idx_ag = 0
            for i, n_ag in enumerate(daftar_nama_agen):
                if bersihkan_nama_agen(n_ag) == agent_key_akun:
                    idx_ag = i
                    break
            if daftar_nama_agen:
                nama_agen_sidebar = st.sidebar.selectbox(
                    "Identitas Agen Aktif:",
                    options=daftar_nama_agen,
                    index=idx_ag,
                )
                agen_fokus_key = bersihkan_nama_agen(nama_agen_sidebar)
                nama_pengguna_aktif = nama_agen_sidebar

# =============================================================================
# HEADER HERO BANNER EKSEKUTIF & TABS
# =============================================================================

st.markdown(
    f"""
    <div class="exec-hero">
        <div class="exec-hero-title">📊 Dashboard Telesales ISP — Tracking MTD SA, Kuota Harian &amp; Komisi</div>
        <div class="exec-hero-sub">
            Sistem Monitoring Real-Time Performa Sales Active (SA), Evaluasi Target Berjalan (MTD), Kuota Wajib Paid/SA Harian &amp; Integrasi Bot Telegram
        </div>
        <div class="exec-badges">
            <span class="exec-badge">{badge_role_teks}: {escape_html_tg(nama_pengguna_aktif)}</span>
            <span class="exec-badge">👨‍💼 Scope Tim: {escape_html_tg(leader_login)}</span>
            <span class="exec-badge">🗓️ Periode: {hari_berjalan_int}-{nama_bln_tampil}-{tahun_int} (Sisa {sisa_hari_int} Hari / {sisa_minggu_int} Minggu)</span>
            <span class="exec-badge-target">🎯 TARGET BERJALAN MTD: {target_persen_mtd}%</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_utama, tab_harian, tab_ai = st.tabs(
    [
        "📊 Laporan Utama (MTD SA, Detail Agent & Telegram)",
        "📅 Rincian Performa Harian",
        "🤖 Tanya AI (Chatbot Assistant)",
    ]
)

with tab_utama:
    if df_prospect_all is None or df_prospect_all.empty:
        st.info(
            "👈 Silakan unggah **File Target (.xlsx)** dan **File Prospect (.xls HTML)** melalui Sidebar di sebelah kiri."
        )
    else:
        # =====================================================================
        # 3. DASHBOARD 1: SUMMARY MTD SA PER LEADER (Sesuai Gambar 2)
        # =====================================================================

        st.markdown(
            f"""
            <div class="section-card-header">
                <div>
                    <div class="section-card-title">📈 DASHBOARD 1: SUMMARY MTD SA PER SALES LEADER</div>
                    <div class="section-card-sub">Perbandingan Apple-to-Apple Month-to-Date (Tanggal 1 s/d {hari_berjalan_int} {kode_bln_lalu} vs {kode_bln_ini} {tahun_int})</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        df_mtd_lalu = get_mtd_data(
            df_prospect_all, bulan_lalu_int, tahun_int, hari_berjalan_int
        )
        df_mtd_ini = get_mtd_data(
            df_prospect_all, bulan_ini_int, tahun_int, hari_berjalan_int
        )
        df_mtd_paid_ini = get_mtd_paid_data(
            df_prospect_all, bulan_ini_int, tahun_int, hari_berjalan_int
        )
        df_mtd_so_ini = get_mtd_so_data(
            df_prospect_all, bulan_ini_int, tahun_int, hari_berjalan_int
        )

        kol_sa_oct = f"SA {kode_bln_lalu} 1-{hari_berjalan_int}"
        kol_sa_nov = f"SA {kode_bln_ini} 1-{hari_berjalan_int}"
        kol_gap_sa = "GAP SA"

        semua_leader_set = set(
            df_prospect_all["Sales Leader"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        )
        if df_target is not None and not df_target.empty:
            semua_leader_set.update(
                df_target["Leader_Default"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )
        semua_leader = sorted(k for k in semua_leader_set if k)
        df_base_ldr = pd.DataFrame({"SALES LEADER": semua_leader})

        grp_lalu = (
            df_mtd_lalu.groupby("Sales Leader")
            .size()
            .reset_index(name=kol_sa_oct)
            .rename(columns={"Sales Leader": "SALES LEADER"})
            if not df_mtd_lalu.empty
            else pd.DataFrame(columns=["SALES LEADER", kol_sa_oct])
        )
        grp_ini = (
            df_mtd_ini.groupby("Sales Leader")
            .size()
            .reset_index(name=kol_sa_nov)
            .rename(columns={"Sales Leader": "SALES LEADER"})
            if not df_mtd_ini.empty
            else pd.DataFrame(columns=["SALES LEADER", kol_sa_nov])
        )

        df_mtd = pd.merge(df_base_ldr, grp_lalu, on="SALES LEADER", how="left")
        df_mtd = pd.merge(df_mtd, grp_ini, on="SALES LEADER", how="left")
        df_mtd[kol_sa_oct] = df_mtd[kol_sa_oct].fillna(0).astype(int)
        df_mtd[kol_sa_nov] = df_mtd[kol_sa_nov].fillna(0).astype(int)
        df_mtd[kol_gap_sa] = df_mtd[kol_sa_nov] - df_mtd[kol_sa_oct]

        # Sembunyikan leader tanpa aktivitas sama sekali (SA bulan lalu & bulan ini = 0), sesuai Gambar 2
        df_mtd = df_mtd[
            (df_mtd[kol_sa_oct] > 0)
            | (df_mtd[kol_sa_nov] > 0)
            | (df_mtd["SALES LEADER"] == leader_login)
        ].copy()

        # Urutkan berdasarkan GAP SA dari terbesar ke terkecil (persis seperti Gambar 2)
        df_mtd = df_mtd.sort_values(
            by=[kol_gap_sa, kol_sa_nov], ascending=[False, False]
        ).reset_index(drop=True)

        if leader_login != "Semua Leader":
            df_mtd_scope = df_mtd[
                df_mtd["SALES LEADER"] == leader_login
            ].reset_index(drop=True)
        else:
            df_mtd_scope = df_mtd.copy()

        # Tambahkan 1 baris paling bawah untuk 'Total' (sum dari seluruh leader)
        tot_oct_val = int(df_mtd_scope[kol_sa_oct].sum())
        tot_nov_val = int(df_mtd_scope[kol_sa_nov].sum())
        tot_gap_val = int(df_mtd_scope[kol_gap_sa].sum())
        note_acv_sa_pct = (
            round_excel(
                ((float(tot_nov_val) - float(tot_oct_val)) / float(tot_oct_val))
                * 100.0
            )
            if tot_oct_val > 0
            else 0
        )
        panah_acv = "↓" if note_acv_sa_pct < 0 else "↑"

        baris_total_mtd = pd.DataFrame(
            [
                {
                    "SALES LEADER": "Total",
                    kol_sa_oct: tot_oct_val,
                    kol_sa_nov: tot_nov_val,
                    kol_gap_sa: tot_gap_val,
                }
            ]
        )
        df_mtd_final = pd.concat(
            [df_mtd_scope, baris_total_mtd], ignore_index=True
        )

        # Widget metrik ringkas di atas tabel Dashboard 1 (lengkap dengan Note Acv SA)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(kol_sa_oct, f"{tot_oct_val:,}".replace(",", "."))
        m2.metric(
            kol_sa_nov,
            f"{tot_nov_val:,}".replace(",", "."),
            delta=f"{tot_gap_val:+d} vs {kode_bln_lalu}",
        )
        m3.metric(kol_gap_sa, f"{tot_gap_val:+d}")
        m4.metric("Note Acv SA", f"{panah_acv} {note_acv_sa_pct}%")

        def style_baris_total_mtd(row: pd.Series) -> list[str]:
            if str(row["SALES LEADER"]).upper() == "TOTAL":
                return [
                    "background-color: #c7d7f4; color: #0f172a; font-weight: bold;"
                ] * len(row)
            return [""] * len(row)

        def style_warna_gap_minus(val: int | float) -> str:
            if pd.isna(val):
                return ""
            try:
                angka = float(val)
            except (ValueError, TypeError):
                return ""
            if angka < 0:
                return "background-color: #f8d7da; color: #b91c1c; font-weight: bold;"
            elif angka > 0:
                return "color: #16a34a; font-weight: bold;"
            return ""

        styler_mtd = df_mtd_final.style.apply(
            style_baris_total_mtd, axis=1
        ).map(style_warna_gap_minus, subset=[kol_gap_sa])

        st.dataframe(
            styler_mtd,
            width="stretch",
            hide_index=True,
        )

        # =====================================================================
        # 3B. DASHBOARD 1B: REKAP HARIAN SO/PAID/SA & AGENT BLM PRODUKTIF
        # =====================================================================

        st.markdown(
            f"""
            <div class="section-card-header">
                <div>
                    <div class="section-card-title">📊 DASHBOARD 1B: REKAP HARIAN SO / PAID / SA &amp; JUMLAH AGENT BELUM PRODUKTIF</div>
                    <div class="section-card-sub">Rekap Performa Tanggal Tertentu &amp; Monitoring Agent Aktif yang Belum Cetak SO / PAID / SA</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_dt1, col_dt2 = st.columns([1.2, 2.8])
        with col_dt1:
            tgl_cek_harian = st.date_input(
                "Pilih Tanggal Cek Produktivitas Harian:",
                value=tgl_acuan_laporan,
                key="tgl_cek_harian_blm_prod",
            )
        if not isinstance(tgl_cek_harian, datetime.date):
            tgl_cek_harian = tgl_acuan_laporan

        daily_prod_rows, daily_prod_date_label = hitung_rekap_harian_blm_produktif_py(
            df_prospect_all,
            df_target,
            tgl_cek_harian,
            leader_login if role_akses != "Agen" else "Semua Leader",
        )
        df_daily_prod_export = pd.DataFrame(
            [
                {
                    "Sales Leader": r["leader"],
                    f"{daily_prod_date_label} SO / GP": r["so"],
                    f"{daily_prod_date_label} PAID": r["paid"],
                    f"{daily_prod_date_label} SA": r["sa"],
                    "Blm Produktif SO/GP": r["blm_so"],
                    "Blm Produktif PAID": r["blm_paid"],
                    "Blm Produktif SA": r["blm_sa"],
                }
                for r in daily_prod_rows
            ]
        )
        df_daily_agent_export = pd.DataFrame(
            [
                {
                    "Tanggal": daily_prod_date_label,
                    "Sales Leader": ag["leader"],
                    "Salesname": ag["name"],
                    "SO / GP": ag["so"],
                    "PAID": ag["paid"],
                    "SA": ag["sa"],
                    "Status Harian": ag["status_harian"],
                }
                for r in daily_prod_rows
                if not r.get("is_grand_total")
                for ag in r.get("agent_details", [])
            ]
        )

        if daily_prod_rows and role_akses != "Agen":
            tr_html_dp = []
            for r in daily_prod_rows:
                is_gt = bool(r.get("is_grand_total"))
                if is_gt:
                    tr_html_dp.append(
                        f"<tr style='font-weight:800; background:#ffffff; border-top:2px solid #0f172a;'>"
                        f"<td style='padding:6px 10px; border:1px solid #cbd5e1; text-align:left;'>{escape_html_tg(r['leader'])}</td>"
                        f"<td style='padding:6px 10px; border:1px solid #cbd5e1; text-align:center;'>{r['so']}</td>"
                        f"<td style='padding:6px 10px; border:1px solid #cbd5e1; text-align:center;'>{r['paid']}</td>"
                        f"<td style='padding:6px 10px; border:1px solid #cbd5e1; text-align:center;'>{r['sa']}</td>"
                        f"<td style='padding:6px 10px; border:1px solid #cbd5e1; text-align:center; background:#fce4d6;'>{r['blm_so']}</td>"
                        f"<td style='padding:6px 10px; border:1px solid #cbd5e1; text-align:center; background:#fce4d6;'>{r['blm_paid']}</td>"
                        f"<td style='padding:6px 10px; border:1px solid #cbd5e1; text-align:center; background:#fce4d6;'>{r['blm_sa']}</td>"
                        f"</tr>"
                    )
                else:
                    tr_html_dp.append(
                        f"<tr>"
                        f"<td style='padding:6px 10px; border:1px solid #cbd5e1; text-align:left;'>{escape_html_tg(r['leader'])}</td>"
                        f"<td style='padding:6px 10px; border:1px solid #cbd5e1; text-align:center;'>{r['so']}</td>"
                        f"<td style='padding:6px 10px; border:1px solid #cbd5e1; text-align:center;'>{r['paid']}</td>"
                        f"<td style='padding:6px 10px; border:1px solid #cbd5e1; text-align:center;'>{r['sa']}</td>"
                        f"<td style='padding:6px 10px; border:1px solid #cbd5e1; text-align:center;'>{r['blm_so']}</td>"
                        f"<td style='padding:6px 10px; border:1px solid #cbd5e1; text-align:center;'>{r['blm_paid']}</td>"
                        f"<td style='padding:6px 10px; border:1px solid #cbd5e1; text-align:center;'>{r['blm_sa']}</td>"
                        f"</tr>"
                    )

            tabel_dp_html = (
                "<div style='overflow-x:auto; margin-bottom:14px;'>"
                "<table style='width:100%; max-width:860px; border-collapse:collapse; font-size:0.88rem; background:#fff; color:#0f172a;'>"
                "<thead>"
                "<tr>"
                "<th rowspan='2' style='background:#002060; color:#fff; padding:8px 12px; border:1px solid #475569; text-align:center;'>Sales Leader</th>"
                f"<th colspan='3' style='background:#002060; color:#fff; padding:6px 10px; border:1px solid #475569; text-align:center;'>{escape_html_tg(daily_prod_date_label)}</th>"
                "<th colspan='3' style='background:#d90000; color:#fff; padding:6px 10px; border:1px solid #991b1b; text-align:center;'>Jumlah Agent Blm Produktif</th>"
                "</tr>"
                "<tr>"
                "<th style='background:#002060; color:#fff; padding:6px 10px; border:1px solid #475569; text-align:center;'>SO / GP</th>"
                "<th style='background:#002060; color:#fff; padding:6px 10px; border:1px solid #475569; text-align:center;'>PAID</th>"
                "<th style='background:#002060; color:#fff; padding:6px 10px; border:1px solid #475569; text-align:center;'>SA</th>"
                "<th style='background:#d90000; color:#fff; padding:6px 10px; border:1px solid #991b1b; text-align:center;'>SO / GP</th>"
                "<th style='background:#d90000; color:#fff; padding:6px 10px; border:1px solid #991b1b; text-align:center;'>PAID</th>"
                "<th style='background:#d90000; color:#fff; padding:6px 10px; border:1px solid #991b1b; text-align:center;'>SA</th>"
                "</tr>"
                "</thead>"
                f"<tbody>{''.join(tr_html_dp)}</tbody>"
                "</table></div>"
            )
            st.markdown(tabel_dp_html, unsafe_allow_html=True)

            st.markdown(f"#### 👥 Rincian Per Agent ({escape_html_tg(daily_prod_date_label)}): Sudah PAID, Sudah GP/SO &amp; Tidak PAID (SO = GP)")
            for r in daily_prod_rows:
                if r.get("is_grand_total"):
                    continue
                st.markdown(
                    f"**{escape_html_tg(r['leader'])}** ({r['total_agents']} slot tim | "
                    f"SO/GP: `{r['so']}` | PAID: `{r['paid']}` | SA: `{r['sa']}`)\n"
                    f"- ✅ **Sudah PAID ({r.get('sudah_paid_agents', 0)})**: {', '.join(r.get('agents_paid', [])) or '-'}\n"
                    f"- 💳 **Sudah GP / SO — Blm PAID ({r.get('gp_blm_paid_agents', 0)})**: {', '.join(r.get('agents_gp', [])) or '-'}\n"
                    f"- ❌ **Tidak PAID ({r['blm_paid']})**: {', '.join(r.get('agents_tidak_paid', [])) or 'Semua PAID'}"
                )

            if not df_daily_agent_export.empty:
                filter_st_1b = st.radio(
                    f"Filter Tabel Rincian Agent Harian ({daily_prod_date_label}):",
                    ["Semua Agent", "Sudah PAID", "Sudah GP / SO", "Tidak PAID"],
                    horizontal=True,
                    key="filter_1b_agent_status",
                )
                df_1b_show = df_daily_agent_export.copy()
                if filter_st_1b == "Sudah PAID":
                    df_1b_show = df_1b_show[df_1b_show["PAID"] > 0]
                elif filter_st_1b == "Sudah GP / SO":
                    df_1b_show = df_1b_show[df_1b_show["SO / GP"] > 0]
                elif filter_st_1b == "Tidak PAID":
                    df_1b_show = df_1b_show[df_1b_show["PAID"] == 0]
                st.dataframe(df_1b_show, width="stretch", hide_index=True)

        # =====================================================================
        # 3C. DASHBOARD 1C: MONITORING WORK ORDER (WO TODAY & SA | WO BESOK | WAITING WO)
        # =====================================================================
        st.markdown(
            """
            <div class="section-card-header">
                <div>
                    <div class="section-card-title">🛠️ DASHBOARD 1C: MONITORING WORK ORDER (WO TODAY &amp; SA | WO BESOK | WAITING WO)</div>
                    <div class="section-card-sub">Pivot Count of Customer Name per Sales Leader &amp; Salesname dari Kolom Instalasi Date &amp; Status</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col_wo_dt1, col_wo_dt2 = st.columns([1.2, 2.8])
        with col_wo_dt1:
            tgl_wo_pilih = st.date_input(
                "Pilih Tanggal WO Today (Besok otomatis > Today):",
                value=tgl_cek_harian,
                key="tgl_cek_wo_monitoring",
            )
        if not isinstance(tgl_wo_pilih, datetime.date):
            tgl_wo_pilih = tgl_cek_harian

        wo_summary = hitung_wo_laporan_py(
            df_prospect_all,
            tgl_wo_pilih,
            bulan_ini_int,
            tahun_int,
            leader_login if role_akses != "Agen" else "Semua Leader",
        )

        if role_akses != "Agen":
            kwo1, kwo2, kwo3 = st.columns(3)
            wo_t = wo_summary["wo_today_totals"]
            wo_sa = int(wo_t.get("sa", 0))
            wo_tot_t = int(wo_t.get("total", 0))
            wo_st_parts = " | ".join(
                f"{k}: {v}" for k, v in (wo_t.get("statuses") or {}).items()
            )
            kwo1.metric(
                f"1️⃣ WO TODAY ({wo_summary['today_label']})",
                f"{wo_tot_t} Customer  |  SA: {wo_sa}",
                wo_st_parts or "Semua status Instalasi Date Today",
            )
            kwo2.metric(
                f"2️⃣ WO BESOK ({wo_summary.get('besok_range_label', wo_summary['besok_label'])})",
                f"{wo_summary['wo_besok_total']} Customer",
                f"Instalasi Date > {wo_summary['today_label']} (H+1: {wo_summary.get('wo_besok_h1_total', 0)} | H+2+: {wo_summary.get('wo_besok_later_total', 0)})",
            )
            brk_w = wo_summary.get("waiting_wo_breakdown") or {}
            brk_txt = " | ".join(f"{k}: {v}" for k, v in brk_w.items() if v > 0) or "Back To Sales / READY / Reschedule / Waiting WO"
            kwo3.metric(
                "3️⃣ WAITING WO (Instalasi Blank)",
                f"{wo_summary['waiting_wo_total']} Customer",
                brk_txt,
            )

            tab_wos, tab_wo1, tab_wo2, tab_wo3, tab_wogal = st.tabs(
                [
                    "📊 Ringkasan Per Leader",
                    f"1️⃣ WO TODAY ({wo_tot_t} | SA {wo_sa})",
                    f"2️⃣ WO BESOK ({wo_summary['wo_besok_total']})",
                    f"3️⃣ WAITING WO ({wo_summary['waiting_wo_total']})",
                    "🖼️ Foto PNG (Ringkasan & Setiap Agent)",
                ]
            )
            with tab_wos:
                sum_rows = wo_summary.get("leader_summary", [])
                if sum_rows:
                    df_wo_sum = pd.DataFrame(
                        [
                            {
                                "Sales Leader": r["leader"],
                                "Total WO Today": r["today_total"],
                                "SA (Active)": r.get("today_sa", 0),
                                "On Install": r.get("today_on_installation", 0),
                                "Reschedule": r.get("today_reschedule", 0),
                                "Waiting WO (Today)": r.get("today_waiting_wo", 0),
                                "Lainnya": r.get("today_other", 0),
                                f"WO Besok ({wo_summary.get('besok_range_label', wo_summary['besok_label'])})": r["wo_besok"],
                                "Waiting WO (Blank)": r["waiting_wo"],
                            }
                            for r in sum_rows
                        ]
                    )
                    st.dataframe(df_wo_sum, width="stretch", hide_index=True)
                else:
                    st.info("Belum ada data Work Order pada tanggal tersebut.")
            with tab_wo1:
                today_cols_ui = wo_summary.get("wo_today_columns") or []
                if wo_summary["wo_today_rows"]:
                    rows_ui_today = []
                    for r in wo_summary["wo_today_rows"]:
                        rec_u = {
                            "Sales Leader": "" if r["row_type"] in ("leader_total", "grand_total") else r["leader"],
                            "Salesname": r["salesname"],
                        }
                        st_map_r = r.get("statuses") or {}
                        for cn_u in today_cols_ui:
                            lbl_c = "Active (SA)" if cn_u.lower() == "active" else cn_u
                            val_c = int(st_map_r.get(cn_u, 0))
                            rec_u[lbl_c] = val_c if (val_c > 0 or r["row_type"] == "grand_total") else ""
                        rec_u["Grand Total"] = r["total"]
                        rows_ui_today.append(rec_u)
                    st.dataframe(pd.DataFrame(rows_ui_today), width="stretch", hide_index=True)
                else:
                    st.info(f"Tidak ada data WO Today pada {wo_summary['today_label']}.")
            with tab_wo2:
                if wo_summary["wo_besok_rows"]:
                    st.dataframe(
                        pd.DataFrame(
                            [
                                {
                                    "Sales Leader": "" if r["row_type"] in ("leader_total", "grand_total") else r["leader"],
                                    "Salesname": r["salesname"],
                                    "Grand Total": r["total"],
                                }
                                for r in wo_summary["wo_besok_rows"]
                            ]
                        ),
                        width="stretch",
                        hide_index=True,
                    )
                else:
                    st.info(f"Belum ada jadwal WO Besok (> {wo_summary['today_label']}).")
            with tab_wo3:
                if wo_summary["waiting_wo_rows"]:
                    st.dataframe(
                        pd.DataFrame(
                            [
                                {
                                    "Sales Leader": "" if r["row_type"] in ("leader_total", "grand_total") else r["leader"],
                                    "Salesname": r["salesname"],
                                    "Grand Total": r["total"],
                                }
                                for r in wo_summary["waiting_wo_rows"]
                            ]
                        ),
                        width="stretch",
                        hide_index=True,
                    )
                else:
                    st.info("Tidak ada antrean Waiting WO (Instalasi Blank) bulan ini/lalu.")
            with tab_wogal:
                wo_imgs = buat_semua_gambar_wo(wo_summary, include_pivot=True, include_tim=True, include_kartu_agent=False)
                if wo_imgs:
                    st.markdown("#### 🖼️ Foto Ringkasan, Pivot Lengkap & Per Tim Agent")
                    for fn_w, bytes_w, cap_w in wo_imgs:
                        st.image(bytes_w, caption=re.sub(r"<[^>]+>", "", cap_w))
                        st.download_button(label=f"📥 Download {fn_w}", data=bytes_w, file_name=fn_w, mime="image/png", key=f"dl_wo_{fn_w}")

                    ag_sum_list = wo_summary.get("agent_summary") or []
                    if ag_sum_list:
                        st.markdown("#### 👤 Foto Kartu Masing-Masing Agent")
                        opsi_ag_nm = ["Semua Agent"] + [f"{x['salesname']} ({x['leader']})" for x in ag_sum_list]
                        pilih_ag_wo = st.selectbox("Pilih Agent untuk Melihat/Mengunduh Foto Pribadi:", opsi_ag_nm, key="sel_wo_kartu_ag")
                        tampil_ag = ag_sum_list if pilih_ag_wo == "Semua Agent" else [x for x in ag_sum_list if f"{x['salesname']} ({x['leader']})" == pilih_ag_wo]
                        for idx_ak, ag_r in enumerate(tampil_ag):
                            png_ak = buat_gambar_wo_kartu_agent(ag_r, wo_summary["today_label"], wo_summary["besok_label"])
                            safe_ak = re.sub(r"[^A-Za-z0-9]+", "_", str(ag_r["salesname"])).strip("_")
                            fn_ak = f"01E_WO_Agent_{safe_ak}.png"
                            st.image(png_ak, caption=f"{ag_r['salesname']} ({ag_r['leader']})")
                            st.download_button(label=f"📥 Download {fn_ak}", data=png_ak, file_name=fn_ak, mime="image/png", key=f"dl_wo_ak_{idx_ak}_{fn_ak}")
                else:
                    st.info("Belum ada data Work Order untuk dirender ke gambar.")

        # =====================================================================
        # 4. DASHBOARD 2: DETAIL AGENT & BREAKDOWN KOMISI (Sesuai Gambar 1)
        # =====================================================================

        st.markdown(
            f"""
            <div class="section-card-header">
                <div>
                    <div class="section-card-title">📋 DASHBOARD 2: DETAIL AGENT, KUOTA HARIAN &amp; BREAKDOWN KOMISI ({escape_html_tg(leader_login)})</div>
                    <div class="section-card-sub">Evaluasi Pencapaian Agen terhadap Target Berjalan MTD ({target_persen_mtd}%), Kuota Wajib Paid/SA Harian &amp; Estimasi Komisi</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Banner Header TARGET Persentase Berjalan persis seperti Gambar 1 (8-Nov-2026 | 27%)
        st.markdown(
            f"""
            <div class="target-maroon-box">
                <div class="target-maroon-top">TARGET</div>
                <div class="target-maroon-bottom">
                    <div class="target-maroon-date">{hari_berjalan_int}-{nama_bln_tampil}-{tahun_int}</div>
                    <div class="target-maroon-pct">{target_persen_mtd}%</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if df_target is None or df_target.empty:
            st.warning(
                "⚠️ Silakan unggah **File Target (.xlsx)** di Sidebar untuk menampilkan Detail Target Agent & Breakdown Komisi."
            )
        else:
            df_mtd_ini_clean = df_mtd_ini.copy()
            df_mtd_paid_clean = df_mtd_paid_ini.copy()
            df_mtd_so_clean = df_mtd_so_ini.copy()
            df_prospect_clean = df_prospect_all.copy()

            df_prospect_clean["Salesname_Clean"] = df_prospect_clean[
                "Salesname"
            ].apply(bersihkan_nama_agen)
            df_prospect_clean = df_prospect_clean[
                ~df_prospect_clean["Salesname_Clean"].isin(
                    ["", "NAN", "NONE", "TOTAL", "-"]
                )
            ].copy()

            peta_nama_prospect = (
                df_prospect_clean.groupby("Salesname_Clean")["Salesname"]
                .last()
                .to_dict()
            )

            # Hitung jumlah SO (Sales Order) per agen
            if not df_mtd_so_clean.empty:
                df_mtd_so_clean["Salesname_Clean"] = df_mtd_so_clean[
                    "Salesname"
                ].apply(bersihkan_nama_agen)
                df_grp_so = (
                    df_mtd_so_clean.groupby("Salesname_Clean", as_index=False)
                    .size()
                    .rename(
                        columns={
                            "Salesname_Clean": "Agent_Key",
                            "size": "SO NOV",
                        }
                    )
                )
            else:
                df_grp_so = pd.DataFrame(columns=["Agent_Key", "SO NOV"])

            # Hitung jumlah PAID per agen pada bulan ini
            if not df_mtd_paid_clean.empty:
                df_mtd_paid_clean["Salesname_Clean"] = df_mtd_paid_clean[
                    "Salesname"
                ].apply(bersihkan_nama_agen)
                df_grp_paid = (
                    df_mtd_paid_clean.groupby("Salesname_Clean", as_index=False)
                    .size()
                    .rename(
                        columns={
                            "Salesname_Clean": "Agent_Key",
                            "size": "PAID NOV",
                        }
                    )
                )
            else:
                df_grp_paid = pd.DataFrame(columns=["Agent_Key", "PAID NOV"])

            # Hitung SA NOV, Breakdown Paket (3M/M/Sem/Y), & Revenue First Payment (Excl. PPn 11%)
            if not df_mtd_ini_clean.empty:
                df_mtd_ini_clean["Salesname_Clean"] = df_mtd_ini_clean[
                    "Salesname"
                ].apply(bersihkan_nama_agen)
                df_mtd_ini_clean["Service Price"] = pd.to_numeric(
                    df_mtd_ini_clean["Service Price"], errors="coerce"
                ).fillna(0.0)
                amt_ser = (
                    pd.to_numeric(df_mtd_ini_clean["Amount"], errors="coerce").fillna(0.0)
                    if "Amount" in df_mtd_ini_clean.columns
                    else pd.Series(0.0, index=df_mtd_ini_clean.index)
                )

                tipe_paket_str = (
                    df_mtd_ini_clean["Tipe Paket"].astype(str).str.strip()
                    if "Tipe Paket" in df_mtd_ini_clean.columns
                    else pd.Series("", index=df_mtd_ini_clean.index)
                )
                df_mtd_ini_clean["_rev_fp"] = [
                    normalisasi_rev_fp_row(tp, sp, amt)
                    for tp, sp, amt in zip(
                        tipe_paket_str, df_mtd_ini_clean["Service Price"], amt_ser
                    )
                ]
                df_mtd_ini_clean["cnt_3monthly"] = (
                    tipe_paket_str.str.upper().isin(["3 MONTHLY", "3MONTHLY"])
                ).astype(int)
                df_mtd_ini_clean["cnt_monthly"] = (
                    tipe_paket_str.str.upper() == "MONTHLY"
                ).astype(int)
                df_mtd_ini_clean["cnt_semesterly"] = (
                    tipe_paket_str.str.upper() == "SEMESTERLY"
                ).astype(int)
                df_mtd_ini_clean["cnt_yearly"] = (
                    tipe_paket_str.str.upper() == "YEARLY"
                ).astype(int)

                df_grp_sa = (
                    df_mtd_ini_clean.groupby("Salesname_Clean", as_index=False)
                    .agg(
                        SA_NOV=("Salesname_Clean", "count"),
                        ThreeMonthly=("cnt_3monthly", "sum"),
                        Monthly=("cnt_monthly", "sum"),
                        Semesterly=("cnt_semesterly", "sum"),
                        Yearly=("cnt_yearly", "sum"),
                        Total_Revenue=("_rev_fp", "sum"),
                    )
                    .rename(
                        columns={
                            "Salesname_Clean": "Agent_Key",
                            "SA_NOV": "SA NOV",
                            "ThreeMonthly": "3 Monthly",
                        }
                    )
                )
            else:
                df_grp_sa = pd.DataFrame(
                    columns=[
                        "Agent_Key",
                        "SA NOV",
                        "3 Monthly",
                        "Monthly",
                        "Semesterly",
                        "Yearly",
                        "Total_Revenue",
                    ]
                )

            # Gunakan daftar agen resmi dari df_target sebagai basis utama (agar Vacant & New Joiner 0 SA tidak hilang)
            df_agent = df_target.copy()
            df_agent["SALES LEADER"] = df_agent["Leader_Default"]
            df_agent["SALES NAME"] = df_agent.apply(
                lambda r: str(
                    peta_nama_prospect.get(r["Agent_Key"], r["Nama_Tampil"])
                ).strip(),
                axis=1,
            )

            df_agent = pd.merge(
                df_agent, df_grp_so, on="Agent_Key", how="left"
            )
            df_agent = pd.merge(
                df_agent, df_grp_paid, on="Agent_Key", how="left"
            )
            df_agent = pd.merge(
                df_agent, df_grp_sa, on="Agent_Key", how="left"
            )

            for kol_num in [
                "SO NOV",
                "PAID NOV",
                "SA NOV",
                "3 Monthly",
                "Monthly",
                "Semesterly",
                "Yearly",
            ]:
                df_agent[kol_num] = df_agent[kol_num].fillna(0).astype(int)
            df_agent["Total_Revenue"] = df_agent["Total_Revenue"].fillna(0.0)

            df_agent["MASA KERJA"] = df_agent["Masa Kerja"].fillna("-")
            df_agent["LEVEL"] = df_agent["Level"].fillna("-")

            # =================================================================
            # KALKULASI RUMUS PERSIS SESUAI GAMBAR 1 & KEBUTUHAN HARIAN PAID/SA
            # =================================================================

            # 1. GAP SA NOV = SA NOV - TARGET ALL
            df_agent["GAP SA NOV"] = (
                df_agent["SA NOV"] - df_agent["TARGET ALL"]
            ).astype(int)

            # 2. PERSENTASE = ROUND((SA NOV / TARGET ALL) * 100, 0)
            df_agent["PERSENTASE_FLOAT"] = np.where(
                df_agent["TARGET ALL"] > 0,
                (df_agent["SA NOV"] / df_agent["TARGET ALL"]) * 100.0,
                0.0,
            )
            df_agent["PERSENTASE_INT"] = [
                round_excel(v) for v in df_agent["PERSENTASE_FLOAT"]
            ]

            # 3. RUNRATE 30 HARI = ROUND((SA NOV * Total_Hari) / Hari_Berjalan, 0)
            df_agent["RUNRATE 30 HARI"] = [
                round_excel(
                    (float(sa) * float(total_hari_int))
                    / float(max(1, hari_berjalan_int))
                )
                for sa in df_agent["SA NOV"]
            ]

            # 4. EVALUASI TERHADAP TARGET PERSENTASE BERJALAN (MTD, misal 27%)
            df_agent["Target_SA_MTD"] = np.ceil(
                df_agent["TARGET ALL"]
                * (float(hari_berjalan_int) / float(max(1, total_hari_int)))
            ).astype(int)
            df_agent["Kurang_SA_MTD"] = np.maximum(
                0, df_agent["Target_SA_MTD"] - df_agent["SA NOV"]
            ).astype(int)

            # 5. KALKULASI HARUS PAID BERAPA / HARI & HARUS SA BERAPA / HARI
            df_agent["Sisa_SA_Bulanan"] = np.maximum(
                0, df_agent["TARGET ALL"] - df_agent["SA NOV"]
            ).astype(int)

            df_agent["Harus_SA_Per_Hari_Desimal"] = (
                df_agent["Sisa_SA_Bulanan"] / float(sisa_hari_int)
            )
            df_agent["Harus_SA_Per_Hari_Bulat"] = np.ceil(
                df_agent["Harus_SA_Per_Hari_Desimal"]
            ).astype(int)

            df_agent["Target_Paid_Bulanan"] = np.ceil(
                df_agent["TARGET ALL"] * rasio_paid_float
            ).astype(int)
            df_agent["Sisa_Paid_Bulanan"] = np.maximum(
                df_agent["Sisa_SA_Bulanan"],
                df_agent["Target_Paid_Bulanan"] - df_agent["PAID NOV"],
            ).astype(int)
            df_agent["Harus_Paid_Per_Hari_Desimal"] = (
                df_agent["Sisa_Paid_Bulanan"] / float(sisa_hari_int)
            )
            df_agent["Harus_Paid_Per_Hari_Bulat"] = np.maximum(
                df_agent["Harus_SA_Per_Hari_Bulat"],
                np.ceil(
                    df_agent["Harus_SA_Per_Hari_Desimal"] * rasio_paid_float
                ).astype(int),
            )

            df_agent["Harus_SO_Per_Hari_Bulat"] = np.ceil(
                df_agent["Harus_Paid_Per_Hari_Bulat"] * 1.25
            ).astype(int)
            df_agent["Catchup_SA_Mingguan"] = np.ceil(
                df_agent["Sisa_SA_Bulanan"] / float(sisa_minggu_int)
            ).astype(int)
            df_agent["Catchup_Paid_Mingguan"] = np.ceil(
                df_agent["Catchup_SA_Mingguan"] * rasio_paid_float
            ).astype(int)

            # 6. Estimasi Komisi Resmi Agent & Sales Leader (`Hitung Insentif FP - Okt 2026TL`)
            df_agent["Rev_FP"] = df_agent["Total_Revenue"].astype(float)
            df_agent["Revenue_Netto"] = df_agent["Rev_FP"]
            kom_res = [
                hitung_komisi_agen_resmi(int(sa), float(rv), int(yr))
                for sa, rv, yr in zip(
                    df_agent["SA NOV"], df_agent["Rev_FP"], df_agent["Yearly"]
                )
            ]
            df_agent["Tier_Label"] = [k["tier"] for k in kom_res]
            df_agent["Pct_Insentif"] = [k["pct_int"] for k in kom_res]
            df_agent["Tier_Komisi"] = [k["tier_komisi"] for k in kom_res]
            df_agent["Insentif_FP_Num"] = [k["insentif_fp"] for k in kom_res]
            df_agent["Insentif_Yearly_Num"] = [k["insentif_yearly"] for k in kom_res]
            df_agent["Estimasi_Komisi_Num"] = [k["est_komisi"] for k in kom_res]

            df_leader_komisi = hitung_komisi_leader_tabel_py(df_mtd_ini, df_agent)
            if leader_login != "Semua Leader":
                df_agent = df_agent[
                    df_agent["SALES LEADER"] == leader_login
                ].copy()
                df_leader_komisi_view = df_leader_komisi[
                    df_leader_komisi["leader"] == leader_login
                ].copy()
            else:
                df_leader_komisi_view = df_leader_komisi.copy()

            # Urutkan Leader berdasarkan persentase tim tertinggi (persis seperti Gambar 1)
            urutan_ldr_pct = (
                df_agent.groupby("SALES LEADER")
                .apply(
                    lambda g: (
                        float(g["SA NOV"].sum())
                        / float(max(1, g["TARGET ALL"].sum()))
                    ),
                    include_groups=False,
                )
                .to_dict()
            )
            df_agent["Ldr_Pct_Sort"] = df_agent["SALES LEADER"].map(
                urutan_ldr_pct
            )
            df_agent["Is_Vacant_Sort"] = (
                df_agent["SALES NAME"].str.upper() == "VACANT"
            ).astype(int)

            df_agent = df_agent.sort_values(
                by=[
                    "Ldr_Pct_Sort",
                    "SALES LEADER",
                    "Is_Vacant_Sort",
                    "PERSENTASE_INT",
                    "SA NOV",
                ],
                ascending=[False, True, True, False, False],
            ).reset_index(drop=True)

            # =================================================================
            # KARTU SPOTLIGHT KHUSUS JIKA LOGIN SEBAGAI AGEN ATAU FINANCE
            # =================================================================
            if role_akses == "Agen" and agen_fokus_key:
                baris_agen_login = df_agent[
                    df_agent["Agent_Key"] == agen_fokus_key
                ]
                if not baris_agen_login.empty:
                    ra = baris_agen_login.iloc[0]
                    pct_ag = int(ra["PERSENTASE_INT"])
                    kurang_flag = pct_ag < target_persen_mtd
                    kelas_warn = "agent-spotlight-warn" if kurang_flag else ""
                    status_badge_ag = (
                        f"⚠️ MASIH KURANG -{target_persen_mtd - pct_ag}% (Di Bawah Target MTD {target_persen_mtd}%)"
                        if kurang_flag
                        else f"✅ AMAN ON-TRACK (>= Target MTD {target_persen_mtd}%)"
                    )
                    st.markdown(
                        f"""
                        <div class="agent-spotlight {kelas_warn}">
                            <div style="font-size: 1.15rem; font-weight: 800; margin-bottom: 4px;">
                                👤 Kartu Performa &amp; Kuota Harian Pribadi: {escape_html_tg(ra['SALES NAME'])} ({escape_html_tg(ra['LEVEL'])})
                            </div>
                            <div style="font-size: 0.88rem; color: #cbd5e1; margin-bottom: 10px;">
                                Tim Sales Leader: <b>{escape_html_tg(ra['SALES LEADER'])}</b> &nbsp;|&nbsp; Masa Kerja: <b>{escape_html_tg(ra['MASA KERJA'])}</b> &nbsp;|&nbsp; Status: <b>{status_badge_ag}</b>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    ka1, ka2, ka3, ka4, ka5 = st.columns(5)
                    ka1.metric(
                        "Target Total Bulanan",
                        f"{int(ra['TARGET ALL'])} SA",
                        f"Wajib {int(ra['Target_Paid_Bulanan'])} Paid",
                    )
                    ka2.metric(
                        "Realisasi Saat Ini",
                        f"{int(ra['SA NOV'])} SA ({pct_ag}%)",
                        f"{int(ra['PAID NOV'])} Paid | {int(ra['SO NOV'])} SO",
                    )
                    ka3.metric(
                        "Wajib Paid / Hari",
                        f"{int(ra['Harus_Paid_Per_Hari_Bulat'])} Paid/hr",
                        f"Cetak {int(ra['Harus_SO_Per_Hari_Bulat'])} SO/hr",
                    )
                    ka4.metric(
                        "Wajib SA / Hari",
                        f"{int(ra['Harus_SA_Per_Hari_Bulat'])} SA/hr",
                        f"{float(ra['Harus_SA_Per_Hari_Desimal']):.2f} SA/hari",
                    )
                    ka5.metric(
                        f"Estimasi Komisi ({ra['Tier_Komisi']})",
                        format_rupiah(ra["Estimasi_Komisi_Num"]),
                        f"FP: {format_rupiah(ra['Insentif_FP_Num'])} | Yearly: {format_rupiah(ra['Insentif_Yearly_Num'])}",
                    )

            elif role_akses == "Finance":
                tot_rev_fp = float(df_agent["Rev_FP"].sum())
                tot_rev_kotor = tot_rev_fp * 1.11
                tot_komisi_ag = float(df_agent["Estimasi_Komisi_Num"].sum())
                if not df_leader_komisi_view.empty:
                    df_lk_non = df_leader_komisi_view[~df_leader_komisi_view["is_total"]]
                    tot_komisi_ldr = float(df_lk_non["insentif_leader"].sum())
                else:
                    tot_komisi_ldr = 0.0
                kf1, kf2, kf3, kf4 = st.columns(4)
                kf1.metric(
                    "Revenue First Payment (Excl. PPn 11%)",
                    format_rupiah(tot_rev_fp),
                    f"Incl. PPn 11%: {format_rupiah(tot_rev_kotor)}",
                )
                kf2.metric(
                    "Total Insentif Agent",
                    format_rupiah(tot_komisi_ag),
                )
                kf3.metric(
                    "Total Insentif Sales Leader",
                    format_rupiah(tot_komisi_ldr),
                    f"Total Gabungan: {format_rupiah(tot_komisi_ag + tot_komisi_ldr)}",
                )
                kf4.metric(
                    "Total SA Bulan Berjalan",
                    f"{int(df_agent['SA NOV'].sum()):,} SA".replace(",", "."),
                )

            if role_akses in ("Leader", "Admin", "Finance") and not df_leader_komisi_view.empty:
                st.markdown("#### 🏆 Rekap Komisi Resmi Sales Leader (Excl. PPn 11% — Khusus Leader, Tidak Dikirim ke Telegram)")
                st.caption(
                    "Rumus resmi Leader: Min 140 SA Tim & Rev FP >= Rp 35jt (Tier 1: 4%, Tier 2 >= 37,5jt: 5%, Tier 3 >= 45jt: 6%, Tier 4 >= 55jt: 8%). "
                    "Agent: Min 15 SA & Rev FP >= Rp 3,75jt (Tier 1: 25%, Tier 2 >= 4,5jt: 30%, Tier 3 >= 5,5jt: 35%) + Rp 200rb/Yearly."
                )
                df_lk_disp = pd.DataFrame(
                    [
                        {
                            "Sales Leader": lr["leader"],
                            "SA Tim": int(lr["sa_tim"]),
                            "Rev. FP Tim (Excl. PPn)": format_rupiah(lr["rev_fp_tim"]),
                            "Yearly Tim": int(lr["p_yr_tim"]),
                            "Tier Leader": lr["tier_komisi"],
                            "Insentif Leader": format_rupiah(lr["insentif_leader"]),
                            "Total Komisi Agent": format_rupiah(lr["total_komisi_agen"]),
                            "Total Komisi Tim": format_rupiah(lr["total_komisi_tim"]),
                        }
                        for _, lr in df_leader_komisi_view.iterrows()
                    ]
                )
                st.dataframe(df_lk_disp, width="stretch", hide_index=True)

            # =================================================================
            # 5. PENYUSUNAN TABEL UTAMA & SUB-TOTAL PER LEADER
            # =================================================================

            baris_final_list = []
            for nama_ldr, grp_ldr in df_agent.groupby(
                "SALES LEADER", sort=False
            ):
                for _, r in grp_ldr.iterrows():
                    pct_i = int(r["PERSENTASE_INT"])
                    if pct_i < target_persen_mtd:
                        selisih_pct = target_persen_mtd - pct_i
                        status_pct_str = (
                            f"⚠️ Kurang -{selisih_pct}% (< {target_persen_mtd}%)"
                        )
                    else:
                        status_pct_str = f"✅ Aman (>= {target_persen_mtd}%)"

                    sa_hr_b = int(r["Harus_SA_Per_Hari_Bulat"])
                    sa_hr_d = float(r["Harus_SA_Per_Hari_Desimal"])
                    paid_hr_b = int(r["Harus_Paid_Per_Hari_Bulat"])
                    paid_hr_d = float(r["Harus_Paid_Per_Hari_Desimal"])

                    baris_final_list.append(
                        {
                            "SALES LEADER": r["SALES LEADER"],
                            "SALES NAME": r["SALES NAME"],
                            "MASA KERJA": r["MASA KERJA"],
                            "LEVEL": r["LEVEL"],
                            "TARGET ALL": int(r["TARGET ALL"]),
                            "Reguler": int(r["Target Reguler"]),
                            "Yearly (Target)": int(r["Target Yearly"]),
                            "SA NOV": int(r["SA NOV"]),
                            "GAP SA NOV": int(r["GAP SA NOV"]),
                            "PERSENTASE": f"{pct_i}%",
                            "RUNRATE 30 HARI": int(r["RUNRATE 30 HARI"]),
                            "3 Monthly": int(r["3 Monthly"]),
                            "Monthly": int(r["Monthly"]),
                            "Semesterly": int(r["Semesterly"]),
                            "Yearly": int(r["Yearly"]),
                            "STATUS PERSENTASE": status_pct_str,
                            "Harus Paid / Hari": f"{paid_hr_b} Paid/hr ({paid_hr_d:.1f})",
                            "Harus SA / Hari": f"{sa_hr_b} SA/hr ({sa_hr_d:.1f})",
                            "Tier Komisi": r["Tier_Komisi"],
                            "Rev. FP (Excl. PPn)": format_rupiah(r["Rev_FP"]),
                            "Insentif FP": format_rupiah(r["Insentif_FP_Num"]),
                            "Ins. Yearly": format_rupiah(r["Insentif_Yearly_Num"]),
                            "Estimasi Komisi": format_rupiah(
                                r["Estimasi_Komisi_Num"]
                            ),
                        }
                    )

                # Hitung baris TOTAL per Leader (RUNRATE = ROUND(SUM_SA * Total_Hari / Hari_Berjalan, 0) sesuai Gambar 1)
                sum_target_all = int(grp_ldr["TARGET ALL"].sum())
                sum_reguler = int(grp_ldr["Target Reguler"].sum())
                sum_yearly_t = int(grp_ldr["Target Yearly"].sum())
                sum_sa_nov = int(grp_ldr["SA NOV"].sum())
                sum_gap_sa = int(grp_ldr["GAP SA NOV"].sum())
                persen_ldr_int = (
                    round_excel(
                        (float(sum_sa_nov) / float(sum_target_all)) * 100.0
                    )
                    if sum_target_all > 0
                    else 0
                )
                runrate_ldr_int = round_excel(
                    (float(sum_sa_nov) * float(total_hari_int))
                    / float(max(1, hari_berjalan_int))
                )
                sum_paid_hr = int(grp_ldr["Harus_Paid_Per_Hari_Bulat"].sum())
                sum_sa_hr = int(grp_ldr["Harus_SA_Per_Hari_Bulat"].sum())
                jml_kurang_ldr = int(
                    (grp_ldr["PERSENTASE_INT"] < target_persen_mtd).sum()
                )

                baris_final_list.append(
                    {
                        "SALES LEADER": "TOTAL",
                        "SALES NAME": nama_ldr,
                        "MASA KERJA": "-",
                        "LEVEL": "-",
                        "TARGET ALL": sum_target_all,
                        "Reguler": sum_reguler,
                        "Yearly (Target)": sum_yearly_t,
                        "SA NOV": sum_sa_nov,
                        "GAP SA NOV": sum_gap_sa,
                        "PERSENTASE": f"{persen_ldr_int}%",
                        "RUNRATE 30 HARI": runrate_ldr_int,
                        "3 Monthly": int(grp_ldr["3 Monthly"].sum()),
                        "Monthly": int(grp_ldr["Monthly"].sum()),
                        "Semesterly": int(grp_ldr["Semesterly"].sum()),
                        "Yearly": int(grp_ldr["Yearly"].sum()),
                        "STATUS PERSENTASE": f"{jml_kurang_ldr} Agen < {target_persen_mtd}%",
                        "Harus Paid / Hari": f"{sum_paid_hr} Paid/hr",
                        "Harus SA / Hari": f"{sum_sa_hr} SA/hr",
                        "Tier Komisi": "-",
                        "Rev. FP (Excl. PPn)": format_rupiah(grp_ldr["Rev_FP"].sum()),
                        "Insentif FP": format_rupiah(grp_ldr["Insentif_FP_Num"].sum()),
                        "Ins. Yearly": format_rupiah(grp_ldr["Insentif_Yearly_Num"].sum()),
                        "Estimasi Komisi": format_rupiah(
                            grp_ldr["Estimasi_Komisi_Num"].sum()
                        ),
                    }
                )

            # Aturan Visibilitas Kolom Berdasarkan Role:
            # - Admin & Finance melihat TARGET ALL, Reguler, dan Yearly (Target) persis seperti Gambar 1
            # - Leader & Agen hanya melihat TARGET ALL (Reguler + Yearly digabung)
            if role_akses in ("Admin", "Finance"):
                kolom_target_tampil = [
                    "TARGET ALL",
                    "Reguler",
                    "Yearly (Target)",
                ]
            else:
                kolom_target_tampil = ["TARGET ALL"]

            kolom_urutan_final = (
                [
                    "SALES LEADER",
                    "SALES NAME",
                    "MASA KERJA",
                    "LEVEL",
                ]
                + kolom_target_tampil
                + [
                    "SA NOV",
                    "GAP SA NOV",
                    "PERSENTASE",
                    "RUNRATE 30 HARI",
                    "3 Monthly",
                    "Monthly",
                    "Semesterly",
                    "Yearly",
                    "STATUS PERSENTASE",
                    "Harus Paid / Hari",
                    "Harus SA / Hari",
                    "Tier Komisi",
                    "Rev. FP (Excl. PPn)",
                    "Insentif FP",
                    "Ins. Yearly",
                    "Estimasi Komisi",
                ]
            )

            df_detail_final = pd.DataFrame(baris_final_list)[kolom_urutan_final]
            st.session_state["df_hasil_komisi"] = df_detail_final
            st.session_state["total_target_scope"] = int(
                df_agent["TARGET ALL"].sum()
            )

            def style_baris_detail_gambar1(row: pd.Series) -> list[str]:
                if str(row["SALES LEADER"]).strip().upper() == "TOTAL":
                    return [
                        "background-color: #b4a7d6; color: #0f172a; font-weight: bold;"
                    ] * len(row)
                if str(row["SALES NAME"]).strip().upper() == "VACANT":
                    return [
                        "background-color: #ffff00; color: #0f172a; font-weight: bold;"
                    ] * len(row)
                return [""] * len(row)

            def style_kolom_persentase(val: object) -> str:
                s = str(val).replace("%", "").strip()
                try:
                    angka = int(float(s))
                    if angka < target_persen_mtd:
                        return "background-color: #f4cccc; color: #990000; font-weight: bold;"
                    return "background-color: #d9ead3; color: #134f5c; font-weight: bold;"
                except Exception:
                    return ""

            def style_kolom_sa_nov(val: object) -> str:
                return "background-color: #c9daf8; color: #0f172a; font-weight: bold;"

            def style_kolom_status_kurang(val: object) -> str:
                if "Kurang" in str(val):
                    return "background-color: #f8d7da; color: #b91c1c; font-weight: bold;"
                elif "Aman" in str(val):
                    return "background-color: #d1fae5; color: #065f46; font-weight: bold;"
                return ""

            styler_detail_final = (
                df_detail_final.style.apply(style_baris_detail_gambar1, axis=1)
                .map(style_kolom_sa_nov, subset=["SA NOV"])
                .map(style_kolom_persentase, subset=["PERSENTASE"])
                .map(
                    style_kolom_status_kurang,
                    subset=["STATUS PERSENTASE"],
                )
            )

            st.dataframe(
                styler_detail_final,
                width="stretch",
                hide_index=True,
            )

            # =================================================================
            # TABEL KHUSUS: AGEN YANG SECARA PERSENTASE MASIH KURANG (< TARGET MTD %)
            # =================================================================
            df_agen_kurang = df_agent[
                df_agent["PERSENTASE_INT"] < target_persen_mtd
            ].copy()

            st.markdown(
                f"#### ⚠️ Tabel Fokus: Agen yang Secara Persentase Masih Kurang (Di Bawah Target Berjalan `{target_persen_mtd}%`)"
            )
            st.caption(
                f"Menampilkan daftar agen yang pencapaian `PERSENTASE`-nya masih di bawah **`{target_persen_mtd}%`** pada tanggal `{hari_berjalan_int}-{nama_bln_tampil}-{tahun_int}`, "
                f"beserta rincian **harus Paid berapa / hari** dan **harus SA berapa / hari** di sisa `{sisa_hari_int}` hari kerja."
            )

            if df_agen_kurang.empty:
                st.success(
                    f"🎉 Seluruh agen pada scope ini sudah mencapai minimal `{target_persen_mtd}%`!"
                )
            else:
                baris_kurang = []
                for _, r in df_agen_kurang.iterrows():
                    pct_now = int(r["PERSENTASE_INT"])
                    item_k = {
                        "SALES LEADER": r["SALES LEADER"],
                        "SALES NAME": r["SALES NAME"],
                        "LEVEL": r["LEVEL"],
                        "TARGET ALL": int(r["TARGET ALL"]),
                        "SA NOV Saat Ini": int(r["SA NOV"]),
                        "PAID NOV Saat Ini": int(r["PAID NOV"]),
                        "PERSENTASE Saat Ini": f"{pct_now}%",
                        f"Target MTD ({hari_berjalan_int} Nov)": f"{target_persen_mtd}% ({int(r['Target_SA_MTD'])} SA)",
                        "Kurang vs MTD": f"-{target_persen_mtd - pct_now}% (Kurang {int(r['Kurang_SA_MTD'])} SA)",
                        "Sisa SA ke 100%": int(r["Sisa_SA_Bulanan"]),
                        "Harus Paid / Hari": f"{int(r['Harus_Paid_Per_Hari_Bulat'])} Paid / Hari ({float(r['Harus_Paid_Per_Hari_Desimal']):.2f}/hr)",
                        "Harus SA / Hari": f"{int(r['Harus_SA_Per_Hari_Bulat'])} SA / Hari ({float(r['Harus_SA_Per_Hari_Desimal']):.2f}/hr)",
                        "Target Mingguan (Paid | SA)": f"{int(r['Catchup_Paid_Mingguan'])} Paid | {int(r['Catchup_SA_Mingguan'])} SA / minggu",
                    }
                    baris_kurang.append(item_k)

                df_tampil_kurang = pd.DataFrame(baris_kurang)
                st.dataframe(
                    df_tampil_kurang,
                    width="stretch",
                    hide_index=True,
                )

            # Tombol Download Excel & CSV
            col_dl1, col_dl2 = st.columns(2)
            buffer_excel = io.BytesIO()
            with pd.ExcelWriter(buffer_excel, engine="openpyxl") as writer:
                df_mtd_final.to_excel(
                    writer, index=False, sheet_name="Summary_MTD_SA"
                )
                if not df_daily_prod_export.empty:
                    df_daily_prod_export.to_excel(
                        writer, index=False, sheet_name="Rekap_Harian_Blm_Produktif"
                    )
                if not df_daily_agent_export.empty:
                    df_daily_agent_export.to_excel(
                        writer, index=False, sheet_name="Rincian_Harian_Agent"
                    )
                if role_akses != "Agen" and not df_leader_komisi_view.empty:
                    df_leader_komisi_view.to_excel(
                        writer, index=False, sheet_name="Komisi_Sales_Leader"
                    )
                if wo_summary and wo_summary.get("leader_summary"):
                    pd.DataFrame(wo_summary["leader_summary"]).to_excel(
                        writer, index=False, sheet_name="WO_Ringkasan"
                    )
                if wo_summary and wo_summary.get("wo_today_rows"):
                    pd.DataFrame(wo_summary["wo_today_rows"]).to_excel(
                        writer, index=False, sheet_name="WO_Today"
                    )
                if wo_summary and wo_summary.get("waiting_wo_rows"):
                    pd.DataFrame(wo_summary["waiting_wo_rows"]).to_excel(
                        writer, index=False, sheet_name="Waiting_WO"
                    )
                if wo_summary and wo_summary.get("wo_besok_rows"):
                    pd.DataFrame(wo_summary["wo_besok_rows"]).to_excel(
                        writer, index=False, sheet_name="WO_Besok"
                    )
                df_detail_final.to_excel(
                    writer, index=False, sheet_name="Detail_Target_Agent"
                )
                if not df_agen_kurang.empty:
                    df_tampil_kurang.to_excel(
                        writer,
                        index=False,
                        sheet_name="Agen_Kurang_Persentase",
                    )
            buffer_excel.seek(0)

            nama_ldr_file = re.sub(
                r"[^A-Za-z0-9]+", "_", leader_login
            ).strip("_")
            with col_dl1:
                st.download_button(
                    label="📥 Download Laporan Excel Multi-Sheet (.xlsx)",
                    data=buffer_excel.getvalue(),
                    file_name=f"Laporan_Dashboard_Telesales_{nama_ldr_file}_{hari_berjalan_int}_{kode_bln_ini}_{tahun_int}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    width="stretch",
                )
            with col_dl2:
                csv_bytes = df_detail_final.to_csv(index=False).encode(
                    "utf-8-sig"
                )
                st.download_button(
                    label="📥 Download Laporan CSV (.csv)",
                    data=csv_bytes,
                    file_name=f"Laporan_Dashboard_Telesales_{nama_ldr_file}_{hari_berjalan_int}_{kode_bln_ini}_{tahun_int}.csv",
                    mime="text/csv",
                    width="stretch",
                )

            # =================================================================
            # 6. MODUL KIRIM LAPORAN KE BOT TELEGRAM
            # =================================================================

            st.markdown(
                """
                <div class="section-card-header">
                    <div>
                        <div class="section-card-title">📲 DISTRIBUSI LAPORAN KE BOT TELEGRAM (GAMBAR PRESENTASI + TEKS DETAIL)</div>
                        <div class="section-card-sub">Kirim Otomatis Tabel Gambar Presentasi (.png) &amp; Rincian Target Harian ke Grup/Personal Telegram</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.caption(
                f"Laporan dikirim dalam 2 bentuk: **🖼️ Gambar Presentasi** (tabel MTD SA + Detail Agent per Leader, mudah dibaca sekilas) "
                f"dan **📝 Pesan Teks Detail** (tanpa tanda `*`). Keduanya hanya menampilkan **`Target Total`** (`Reguler + Yearly`) "
                f"serta menandai agen yang **secara persentase masih kurang (`< {target_persen_mtd}%`)** lengkap dengan **Paid / hari** dan **SA / hari** yang harus dikejar."
            )

            daftar_pesan_tg = susun_pesan_telegram(
                df_mtd_final=df_mtd_final,
                df_calc=df_agent,
                leader_login=leader_login,
                kode_bln_lalu=kode_bln_lalu,
                kode_bln_ini=kode_bln_ini,
                tahun_int=tahun_int,
                hari_berjalan_int=hari_berjalan_int,
                total_hari_int=total_hari_int,
                sisa_hari_int=sisa_hari_int,
                sisa_minggu_int=sisa_minggu_int,
                target_persen_mtd=target_persen_mtd,
                wo_summary=wo_summary if role_akses != "Agen" else None,
            )

            col_opsi1, col_opsi2, col_opsi3 = st.columns([1, 1, 1.4])
            with col_opsi1:
                opsi_kirim_gambar = st.checkbox(
                    "🖼️ Sertakan Gambar Presentasi",
                    value=True,
                )
                opsi_kirim_wo_agent = st.checkbox(
                    "👤 Lampirkan Foto Kartu Masing-Masing Agent WO",
                    value=False,
                    help="Bila dicentang, setiap agen juga dikirimkan foto kartu WO individual ke Telegram.",
                )
            with col_opsi2:
                opsi_kirim_teks = st.checkbox(
                    "📝 Sertakan Pesan Teks Detail",
                    value=True,
                )
            with col_opsi3:
                mode_gambar_tg = st.radio(
                    "Format Gambar Telegram:",
                    options=[
                        "Foto (langsung tampil di chat)",
                        "File / Dokumen (resolusi asli)",
                    ],
                    horizontal=True,
                    help="Mode Foto lebih praktis dibaca langsung di chat. Mode File menjaga resolusi asli (tidak dikompres Telegram) sehingga tabel lebar tetap tajam saat di-zoom.",
                )

            daftar_gambar_tg: list[tuple[str, bytes, str]] = []
            try:
                daftar_gambar_tg = buat_semua_gambar_laporan(
                    df_mtd_final=df_mtd_final,
                    df_agent=df_agent,
                    kol_oct=kol_sa_oct,
                    kol_nov=kol_sa_nov,
                    kol_gap=kol_gap_sa,
                    kode_bln_lalu=kode_bln_lalu,
                    kode_bln_ini=kode_bln_ini,
                    nama_bln_tampil=nama_bln_tampil,
                    tahun=tahun_int,
                    hari_berjalan=hari_berjalan_int,
                    total_hari=total_hari_int,
                    sisa_hari=sisa_hari_int,
                    target_persen_mtd=target_persen_mtd,
                    rasio_paid=rasio_paid_float,
                    daily_prod_rows=daily_prod_rows if role_akses != "Agen" else None,
                    daily_prod_date_label=daily_prod_date_label,
                    wo_summary=wo_summary if role_akses != "Agen" else None,
                    include_wo_detail=True,
                    include_wo_agent_cards=opsi_kirim_wo_agent,
                )
            except Exception as err_gambar:
                st.warning(
                    f"⚠️ Gambar presentasi laporan gagal dibuat (pesan teks tetap bisa dikirim): {err_gambar}"
                )

            with st.expander(
                f"🖼️ Lihat Pratinjau Gambar Presentasi Laporan ({len(daftar_gambar_tg)} gambar)"
            ):
                for nama_file_img, data_img, caption_img in daftar_gambar_tg:
                    st.image(
                        data_img,
                        caption=re.sub(r"<[^>]+>", "", caption_img),
                    )
                    st.download_button(
                        label=f"📥 Download {nama_file_img}",
                        data=data_img,
                        file_name=nama_file_img,
                        mime="image/png",
                        key=f"dl_img_{nama_file_img}",
                    )

            with st.expander("👁️ Lihat Pratinjau Pesan Teks Laporan Telegram"):
                teks_pratinjau = "\n\n--- [BAGIAN PESAN BERIKUTNYA] ---\n\n".join(
                    re.sub(
                        r"<[^>]+>",
                        "",
                        p.replace("&amp;", "&")
                        .replace("&lt;", "<")
                        .replace("&gt;", ">")
                        .replace("&ge;", ">="),
                    )
                    for p in daftar_pesan_tg
                )
                st.code(
                    teks_pratinjau,
                    language="text",
                )

            if st.button(
                "🚀 Kirim Laporan (Gambar Presentasi + Teks Detail) ke Telegram",
                type="primary",
                width="stretch",
            ):
                kirim_gambar_aktif = opsi_kirim_gambar and bool(daftar_gambar_tg)
                if not kirim_gambar_aktif and not opsi_kirim_teks:
                    st.warning(
                        "⚠️ Pilih minimal salah satu: Gambar Presentasi atau Pesan Teks Detail."
                    )
                else:
                    ringkasan_hasil: list[str] = []
                    semua_sukses = True
                    with st.spinner("Mengirim laporan ke Telegram..."):
                        if kirim_gambar_aktif:
                            sukses_img, respon_img = kirim_gambar_ke_telegram(
                                bot_token=telegram_bot_token,
                                chat_id=telegram_chat_id,
                                daftar_gambar=daftar_gambar_tg,
                                sebagai_dokumen=mode_gambar_tg.startswith("File"),
                            )
                            ringkasan_hasil.append(f"🖼️ {respon_img}")
                            semua_sukses = semua_sukses and sukses_img

                        if semua_sukses and opsi_kirim_teks:
                            sukses_tg, respon_tg = kirim_laporan_ke_telegram(
                                bot_token=telegram_bot_token,
                                chat_id=telegram_chat_id,
                                daftar_pesan=daftar_pesan_tg,
                            )
                            ringkasan_hasil.append(f"📝 {respon_tg}")
                            semua_sukses = semua_sukses and sukses_tg

                    if semua_sukses:
                        st.success("✅ " + "  \n".join(ringkasan_hasil))
                    else:
                        st.error("❌ " + "  \n".join(ringkasan_hasil))

# =============================================================================
# TAB 2: RINCIAN PERFORMA HARIAN (DAILY STAND-UP PRESENTATION)
# =============================================================================

with tab_harian:
    st.markdown(
        """
        <div class="section-card-header">
            <div>
                <div class="section-card-title">📅 RINCIAN PERFORMA HARIAN (SO TERCETAK vs PAID vs SA ACTIVE)</div>
                <div class="section-card-sub">Pelacakan Harian Tanggal 1 s/d Akhir Bulan untuk Evaluasi Daily Stand-Up Meeting</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if df_prospect_all is None or df_prospect_all.empty:
        st.info(
            "ℹ️ Silakan unggah file Prospect dan File Target terlebih dahulu di Sidebar."
        )
    else:
        df_harian_scope = (
            df_prospect_all[
                df_prospect_all["Sales Leader"].astype(str).str.strip()
                == leader_login
            ].copy()
            if leader_login != "Semua Leader"
            else df_prospect_all.copy()
        )

        jml_hari_kalender = calendar.monthrange(tahun_int, bulan_ini_int)[1]
        rentang_tgl = pd.date_range(
            start=f"{tahun_int}-{bulan_ini_int:02d}-01",
            end=f"{tahun_int}-{bulan_ini_int:02d}-{jml_hari_kalender:02d}",
            freq="D",
        )

        total_target_tim = st.session_state.get("total_target_scope", 0)
        target_sa_harian_tim = (
            math.ceil(float(total_target_tim) / float(total_hari_int))
            if total_hari_int > 0
            else 0
        )
        target_paid_harian_tim = math.ceil(
            target_sa_harian_tim * rasio_paid_float
        )

        s_create = (
            pd.to_datetime(df_harian_scope["Created Date"], errors="coerce").dt.date
            if "Created Date" in df_harian_scope.columns
            else pd.Series(dtype="object")
        )
        paid_mask_tab2 = (
            df_harian_scope["Status Payment"].astype(str).str.strip().str.upper() == "PAID"
            if "Status Payment" in df_harian_scope.columns
            else pd.Series(True, index=df_harian_scope.index)
        )
        s_paid = (
            pd.to_datetime(df_harian_scope["Payment Date"], errors="coerce").dt.date.where(paid_mask_tab2)
            if "Payment Date" in df_harian_scope.columns
            else pd.Series(dtype="object")
        )
        s_active = (
            pd.to_datetime(df_harian_scope["Active Date"], errors="coerce").dt.date
            if "Active Date" in df_harian_scope.columns
            else pd.Series(dtype="object")
        )

        rows_daily = []
        for tgl in rentang_tgl:
            d_obj = tgl.date()
            c_create = int((s_create == d_obj).sum())
            c_paid = int((s_paid == d_obj).sum())
            c_active = int((s_active == d_obj).sum())
            persen_sa = (
                (c_active / target_sa_harian_tim * 100.0)
                if target_sa_harian_tim > 0
                else 0.0
            )
            persen_paid = (
                (c_paid / target_paid_harian_tim * 100.0)
                if target_paid_harian_tim > 0
                else 0.0
            )
            rows_daily.append(
                {
                    "Tanggal": tgl.strftime("%Y-%m-%d"),
                    "SO Tercetak (Create)": c_create,
                    "Customer Paid": c_paid,
                    "Target Paid / Hari Tim": target_paid_harian_tim,
                    "Pencapaian Paid Harian": f"{persen_paid:.1f}%",
                    "Customer Active (SA)": c_active,
                    "Target SA / Hari Tim": target_sa_harian_tim,
                    "Pencapaian SA Harian": f"{persen_sa:.1f}%",
                }
            )

        df_daily = pd.DataFrame(rows_daily)
        st.dataframe(df_daily, width="stretch", hide_index=True)

# =============================================================================
# TAB 3: TANYA AI (CHATBOT ASSISTANT)
# =============================================================================

with tab_ai:
    st.markdown(
        """
        <div class="section-card-header">
            <div>
                <div class="section-card-title">🤖 TANYA AI (ASISTEN ANALITIK DATA TELESALES)</div>
                <div class="section-card-sub">Tanyakan Analisis Agen di Bawah Target MTD, Kuota Paid/SA Harian, Top Performa &amp; Estimasi Komisi</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if "riwayat_chat" not in st.session_state:
        st.session_state["riwayat_chat"] = [
            {
                "role": "assistant",
                "content": "Halo! Silakan tanyakan siapa saja agen yang secara persentase masih kurang, berapa Paid/hari & SA/hari yang harus dikejar, atau estimasi komisi tim ini.",
            }
        ]

    if "df_hasil_komisi" not in st.session_state:
        st.info(
            "ℹ️ Silakan unggah File Target dan File Prospect terlebih dahulu."
        )
    else:
        sdf = SmartDataframe(
            st.session_state["df_hasil_komisi"],
            config={
                "provider": llm_provider,
                "api_key": llm_api_key,
                "role_akses": role_akses,
            },
        )

        for msg in st.session_state["riwayat_chat"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        pertanyaan = st.chat_input(
            "Contoh: Siapa agen yang persentasenya masih kurang? atau Detail Askih..."
        )
        if pertanyaan:
            aman_chat, pesan_waf_chat = periksa_input_waf(
                pertanyaan, "Pertanyaan AI"
            )
            if not aman_chat:
                st.error(pesan_waf_chat)
            else:
                st.session_state["riwayat_chat"].append(
                    {"role": "user", "content": pertanyaan}
                )
                with st.chat_message("user"):
                    st.markdown(pertanyaan)

                jawaban = sdf.chat(pertanyaan)
                with st.chat_message("assistant"):
                    st.markdown(jawaban)
                st.session_state["riwayat_chat"].append(
                    {"role": "assistant", "content": jawaban}
                )
