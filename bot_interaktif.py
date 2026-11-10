import math
import os
import re
import pandas as pd
import telebot

# Konfigurasi Token Bot Telegram
TOKEN = "9242894728:AAF2oYVZlpfcHEIFcC9PdoeFQA6KuwF-njs"
bot = telebot.TeleBot(TOKEN)

# Daftar Eksklusif Anggota Tim ALPHA WOLF SQUAD (Data Access Control)
tim_alpha_wolf = [
    "Askih Milli Priyanto",
    "Sisca Permata Sucy",
    "Ali Yusup Ramadhan",
    "Dwi Afriyani",
    "Sandra Monica",
    "Anisa Rahmawati",
    "Yayang Ardi Purnama",
    "Andri Darmawan",
    "Diana Yasmin",
    "Naffa Destiana Putri",
]

FOLDER_PROYEK = os.path.dirname(os.path.abspath(__file__))
PATH_DATA_TARGET = os.path.join(FOLDER_PROYEK, "data_target.xlsx")
FILE_URL_PUBLIK = os.path.join(FOLDER_PROYEK, "url_publik_aktif.txt")
DAFTAR_FILE_PROSPECT = [
    os.path.join(FOLDER_PROYEK, "list_prospect Oktober.xls"),
    os.path.join(FOLDER_PROYEK, "list_prospect November.xls"),
    os.path.join(FOLDER_PROYEK, "list_prospect Nov.xls"),
]


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


RASIO_PAID_PER_SA = 1.25
RASIO_SO_PER_PAID = 1.25
TOTAL_HARI_BULAN = 30
HARI_BERJALAN_DEFAULT = 8

# Data Target Total (Target Reguler + Target Yearly = Target Total)
# Detail Reguler & Yearly disembunyikan dari agen (hanya untuk Admin)
DATA_DEFAULT_ALPHA_WOLF = [
    {
        "Nama_Agen": "Askih Milli Priyanto",
        "Level": "SENIOR",
        "Target_Bulan_Ini": 55,
        "Daily_Paid_Normal": 3,
    },
    {
        "Nama_Agen": "Sisca Permata Sucy",
        "Level": "SENIOR",
        "Target_Bulan_Ini": 55,
        "Daily_Paid_Normal": 3,
    },
    {
        "Nama_Agen": "Ali Yusup Ramadhan",
        "Level": "ASSOCIATE",
        "Target_Bulan_Ini": 50,
        "Daily_Paid_Normal": 2,
    },
    {
        "Nama_Agen": "Dwi Afriyani",
        "Level": "SENIOR",
        "Target_Bulan_Ini": 55,
        "Daily_Paid_Normal": 3,
    },
    {
        "Nama_Agen": "Sandra Monica",
        "Level": "SENIOR",
        "Target_Bulan_Ini": 55,
        "Daily_Paid_Normal": 3,
    },
    {
        "Nama_Agen": "Anisa Rahmawati",
        "Level": "ASSOCIATE",
        "Target_Bulan_Ini": 50,
        "Daily_Paid_Normal": 2,
    },
    {
        "Nama_Agen": "Yayang Ardi Purnama",
        "Level": "ASSOCIATE",
        "Target_Bulan_Ini": 50,
        "Daily_Paid_Normal": 2,
    },
    {
        "Nama_Agen": "Andri Darmawan",
        "Level": "SENIOR",
        "Target_Bulan_Ini": 55,
        "Daily_Paid_Normal": 3,
    },
    {
        "Nama_Agen": "Diana Yasmin",
        "Level": "SENIOR",
        "Target_Bulan_Ini": 55,
        "Daily_Paid_Normal": 3,
    },
    {
        "Nama_Agen": "Naffa Destiana Putri",
        "Level": "TRAINEE",
        "Target_Bulan_Ini": 42,
        "Daily_Paid_Normal": 2,
    },
]


def round_excel(nilai: float | int) -> int:
    """Pembulatan half-up standar Excel: =ROUND(x, 0)."""
    if pd.isna(nilai):
        return 0
    val = float(nilai)
    if val >= 0:
        return int(math.floor(val + 0.5))
    return int(math.ceil(val - 0.5))


def pastikan_file_data_target() -> None:
    """Membuat atau menyinkronkan file data_target.xlsx dengan Target Total (Reguler + Yearly)."""
    df_init = pd.DataFrame(DATA_DEFAULT_ALPHA_WOLF)
    if not os.path.isfile(PATH_DATA_TARGET):
        df_init.to_excel(PATH_DATA_TARGET, index=False)
    else:
        try:
            df_existing = pd.read_excel(PATH_DATA_TARGET)
            if (
                "Daily_Paid_Normal" not in df_existing.columns
                or int(df_existing["Target_Bulan_Ini"].sum()) != 522
            ):
                df_init.to_excel(PATH_DATA_TARGET, index=False)
        except Exception:
            df_init.to_excel(PATH_DATA_TARGET, index=False)


def ambil_realisasi_prospect_nov() -> dict[str, dict[str, int]]:
    """Membaca realisasi SA, Paid, dan SO Tercetak bulan November (1-8 Nov 2026) untuk Tim Yovi Arian."""
    hasil: dict[str, dict[str, int]] = {}
    list_df = []
    for path_f in DAFTAR_FILE_PROSPECT:
        if os.path.isfile(path_f):
            try:
                list_df.append(pd.read_html(path_f, header=0)[0])
            except Exception:
                pass

    if not list_df:
        return hasil

    try:
        df = (
            pd.concat(list_df, ignore_index=True)
            .drop_duplicates()
            .reset_index(drop=True)
        )

        df_yovi = df[
            df["Sales Leader"].astype(str).str.strip().str.lower()
            == "yovi arian"
        ].copy()
        if df_yovi.empty:
            return hasil

        alias_map = {
            "sandra monica aprilia bendsneyder": "sandra monica",
            "nafa destiana putri": "naffa destiana putri",
        }

        def norm_nama(n: object) -> str:
            s = re.sub(r"\s+", " ", str(n)).strip().lower()
            return alias_map.get(s, s)

        df_yovi["nama_key"] = df_yovi["Salesname"].apply(norm_nama)
        df_yovi["Active Date"] = pd.to_datetime(
            df_yovi["Active Date"], errors="coerce"
        )
        df_yovi["Payment Date"] = pd.to_datetime(
            df_yovi["Payment Date"], errors="coerce"
        )
        df_yovi["Created Date"] = pd.to_datetime(
            df_yovi["Created Date"], errors="coerce"
        )

        mask_sa = (
            df_yovi["Active Date"].notna()
            & (df_yovi["Active Date"].dt.month == 11)
            & (df_yovi["Active Date"].dt.year == 2026)
            & (df_yovi["Active Date"].dt.day <= HARI_BERJALAN_DEFAULT)
        )
        status_paid = (
            df_yovi["Status Payment"].astype(str).str.strip().str.upper()
            == "PAID"
        )
        mask_paid = (
            status_paid
            & df_yovi["Payment Date"].notna()
            & (df_yovi["Payment Date"].dt.month == 11)
            & (df_yovi["Payment Date"].dt.year == 2026)
            & (df_yovi["Payment Date"].dt.day <= HARI_BERJALAN_DEFAULT)
        )
        mask_so = (
            df_yovi["Created Date"].notna()
            & (df_yovi["Created Date"].dt.month == 11)
            & (df_yovi["Created Date"].dt.year == 2026)
            & (df_yovi["Created Date"].dt.day <= HARI_BERJALAN_DEFAULT)
        )

        for key, grp in df_yovi.groupby("nama_key"):
            jml_sa = int(mask_sa.loc[grp.index].sum())
            jml_paid = int(mask_paid.loc[grp.index].sum())
            jml_so = int(mask_so.loc[grp.index].sum())
            hasil[str(key)] = {
                "sa": jml_sa,
                "paid": jml_paid,
                "so": jml_so,
            }
    except Exception:
        pass
    return hasil


def baca_target_alpha_wolf() -> pd.DataFrame:
    """Membaca data_target.xlsx dengan pd.read_excel() dan memfilter HANYA anggota tim_alpha_wolf."""
    pastikan_file_data_target()
    df = pd.read_excel(PATH_DATA_TARGET)

    if "Nama_Agen" not in df.columns and len(df.columns) >= 2:
        df = df.rename(
            columns={
                df.columns[0]: "Nama_Agen",
                df.columns[1]: "Target_Bulan_Ini",
            }
        )

    df["Nama_Agen"] = df["Nama_Agen"].astype(str).str.strip()
    df["Nama_Agen"] = df["Nama_Agen"].replace(
        {
            "NAFA DESTIANA PUTRI": "Naffa Destiana Putri",
            "Nafa Destiana Putri": "Naffa Destiana Putri",
        }
    )

    tim_alpha_wolf_lower = [nama.lower().strip() for nama in tim_alpha_wolf]
    df_filtered = df[
        df["Nama_Agen"].str.lower().isin(tim_alpha_wolf_lower)
    ].copy()

    peta_nama_resmi = {nama.lower().strip(): nama for nama in tim_alpha_wolf}
    df_filtered["Nama_Agen"] = (
        df_filtered["Nama_Agen"].str.lower().map(peta_nama_resmi)
    )
    df_filtered["Target_Bulan_Ini"] = (
        pd.to_numeric(df_filtered["Target_Bulan_Ini"], errors="coerce")
        .fillna(0)
        .astype(int)
    )
    if "Level" not in df_filtered.columns:
        df_filtered["Level"] = df_filtered["Target_Bulan_Ini"].apply(
            lambda t: "SENIOR"
            if t >= 55
            else ("ASSOCIATE" if t >= 50 else "TRAINEE")
        )
    if "Daily_Paid_Normal" not in df_filtered.columns:
        df_filtered["Daily_Paid_Normal"] = df_filtered[
            "Target_Bulan_Ini"
        ].apply(lambda t: 3 if t >= 55 else 2)

    return df_filtered.reset_index(drop=True)


@bot.message_handler(commands=["start", "help"])
def handle_start(message: telebot.types.Message) -> None:
    """Menampilkan panduan penggunaan Bot Eksklusif ALPHA WOLF SQUAD."""
    url_pub = ambil_url_publik_aktif()
    info_web = (
        f"\n🌐 <b>Link Web Dashboard Go-Live:</b>\n<a href=\"{url_pub}\">{url_pub}</a>\n"
        if url_pub
        else ""
    )
    teks_bantuan = (
        "🐺 <b>ALPHA WOLF SQUAD — EXCLUSIVE BOT</b>\n"
        "🔒 <b>Data Access Control: Aktif</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Perintah yang tersedia:\n"
        "• <code>/web</code> atau <code>/link</code> — Menampilkan Link Go-Live Dashboard Web (bisa diakses dari HP/Laptop oleh seluruh staff).\n"
        "• <code>/target</code> — Menampilkan daftar Target Total, Status Persentase MTD (27%), serta kuota <b>Harus Paid / Hari &amp; Harus SA / Hari</b> seluruh anggota ALPHA WOLF SQUAD.\n"
        "• <code>/cektarget [nama_agen]</code> — Mengecek rincian target Paid &amp; SA harian, mingguan, dan bulanan agen (contoh: <code>/cektarget Naffa</code> atau <code>/cektarget Askih</code>).\n"
        "• <code>/id</code> — Menampilkan Chat ID grup/personal."
        f"{info_web}"
    )
    bot.reply_to(message, teks_bantuan, parse_mode="HTML")


@bot.message_handler(commands=["web", "link", "dashboard"])
def handle_web_link(message: telebot.types.Message) -> None:
    """Menampilkan Link Go-Live Publik & LAN beserta panduan login Multi-Role untuk Staff."""
    url_pub = ambil_url_publik_aktif()
    url_lan = ambil_url_lan_aktif(8501)
    if url_pub:
        teks_url = (
            f"🌐 <b>LINK PUBLIK (HP / Luar Kantor / Internet):</b>\n"
            f"👉 <a href=\"{url_pub}\">{url_pub}</a>\n\n"
            f"📶 <b>LINK WI-FI / LAN KANTOR:</b>\n"
            f"👉 <code>{url_lan}</code>"
        )
    else:
        teks_url = (
            f"📶 <b>LINK WI-FI / LAN KANTOR:</b>\n"
            f"👉 <code>{url_lan}</code>"
        )

    pesan = (
        "🚀 <b>AKSES GO-LIVE DASHBOARD TELESALES ISP</b>\n"
        "🛡️ <b>Proteksi WAF &amp; Firewall: AKTIF</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{teks_url}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔒 <b>Keamanan Akses Login:</b>\n"
        "• Seluruh ID &amp; Password terenkripsi (SHA-256) dan disembunyikan dari publik.\n"
        "• Silakan hubungi <b>Admin Master (Yovi Arian)</b> untuk mendapatkan hak akses sesuai Role Anda."
    )
    bot.reply_to(message, pesan, parse_mode="HTML")



@bot.message_handler(commands=["id"])
def handle_id(message: telebot.types.Message) -> None:
    """Menampilkan Chat ID grup/personal."""
    bot.reply_to(
        message,
        f"🆔 <b>TELEGRAM_CHAT_ID</b> ruangan ini adalah:\n<code>{message.chat.id}</code>",
        parse_mode="HTML",
    )


@bot.message_handler(commands=["target"])
def handle_target(message: telebot.types.Message) -> None:
    """Handler /target: Menampilkan Target Total, Persentase vs Target MTD (27%), serta Harus Paid/hari & SA/hari."""
    df_tim = baca_target_alpha_wolf()
    realisasi_map = ambil_realisasi_prospect_nov()

    if df_tim.empty:
        bot.reply_to(
            message,
            "⚠️ Data target anggota ALPHA WOLF SQUAD belum ditemukan di <code>data_target.xlsx</code>.",
            parse_mode="HTML",
        )
        return

    sisa_hari = max(1, TOTAL_HARI_BULAN - HARI_BERJALAN_DEFAULT)
    sisa_minggu = max(1, math.ceil(sisa_hari / 7.0))
    target_persen_mtd = round_excel(
        (float(HARI_BERJALAN_DEFAULT) / float(TOTAL_HARI_BULAN)) * 100.0
    )

    # Susun dan urutkan berdasarkan PERSENTASE tertinggi (sesuai Gambar 1)
    rows_enriched = []
    for _, row in df_tim.iterrows():
        nama = str(row["Nama_Agen"])
        level = str(row["Level"])
        target_all = int(row["Target_Bulan_Ini"])
        stat = realisasi_map.get(
            nama.lower().strip(), {"sa": 0, "paid": 0, "so": 0}
        )
        sa_now = stat["sa"]
        paid_now = stat["paid"]
        so_now = stat["so"]
        persen_int = (
            round_excel((float(sa_now) / float(target_all)) * 100.0)
            if target_all > 0
            else 0
        )
        rows_enriched.append(
            {
                "nama": nama,
                "level": level,
                "target_all": target_all,
                "sa_now": sa_now,
                "paid_now": paid_now,
                "so_now": so_now,
                "persen_int": persen_int,
            }
        )

    rows_enriched.sort(
        key=lambda x: (x["persen_int"], x["sa_now"]), reverse=True
    )

    baris_daftar = []
    tot_target_all = 0
    tot_sa_now = 0
    tot_paid_now = 0
    tot_so_now = 0
    jml_agen_kurang = 0

    for idx, r in enumerate(rows_enriched, start=1):
        nama = r["nama"]
        level = r["level"]
        target_all = r["target_all"]
        sa_now = r["sa_now"]
        paid_now = r["paid_now"]
        so_now = r["so_now"]
        persen_int = r["persen_int"]
        gap_sa = sa_now - target_all
        runrate_30 = round_excel(
            (float(sa_now) * float(TOTAL_HARI_BULAN))
            / float(HARI_BERJALAN_DEFAULT)
        )

        sisa_sa = max(0, target_all - sa_now)
        harus_sa_des = sisa_sa / float(sisa_hari)
        harus_sa_hr = math.ceil(harus_sa_des)
        harus_paid_hr = max(
            harus_sa_hr, math.ceil(harus_sa_des * RASIO_PAID_PER_SA)
        )
        harus_so_hr = math.ceil(harus_paid_hr * RASIO_SO_PER_PAID)

        harus_sa_mgg = math.ceil(sisa_sa / float(sisa_minggu))
        harus_paid_mgg = math.ceil(harus_sa_mgg * RASIO_PAID_PER_SA)

        if persen_int < target_persen_mtd:
            jml_agen_kurang += 1
            selisih_pct = target_persen_mtd - persen_int
            status_mtd = f"⚠️ <b>MASIH KURANG -{selisih_pct}%</b> ({persen_int}% &lt; {target_persen_mtd}%)"
        else:
            status_mtd = f"✅ <b>AMAN ON-TRACK</b> ({persen_int}% &ge; {target_persen_mtd}%)"

        tot_target_all += target_all
        tot_sa_now += sa_now
        tot_paid_now += paid_now
        tot_so_now += so_now

        baris_daftar.append(
            f"<b>{idx}. 👤 {nama}</b> ({level})\n"
            f"├ 📌 Status MTD       : {status_mtd}\n"
            f"├ ✅ Realisasi        : <b>{sa_now} SA</b> | <b>{paid_now} Paid</b> | <b>{so_now} SO</b> (Gap: {gap_sa} | RR: {runrate_30})\n"
            f"├ ⚡ <b>Harus Kejar Harian</b>   : Wajib <b>{harus_paid_hr} Paid/hari</b> &amp; <b>{harus_sa_hr} SA/hari</b> ({harus_sa_des:.1f} SA | Cetak {harus_so_hr} SO)\n"
            f"├ 📅 <b>Harus Kejar Mingguan</b> : Wajib <b>{harus_paid_mgg} Paid/minggu</b> &amp; <b>{harus_sa_mgg} SA/minggu</b>\n"
            f"└ 🎯 <b>Target Total Bulanan</b> : <b>{target_all} SA</b>"
        )

    isi_daftar = "\n\n".join(baris_daftar)
    persen_tim = (
        round_excel((float(tot_sa_now) / float(tot_target_all)) * 100.0)
        if tot_target_all > 0
        else 0
    )
    runrate_tim = round_excel(
        (float(tot_sa_now) * float(TOTAL_HARI_BULAN))
        / float(HARI_BERJALAN_DEFAULT)
    )

    pesan_balasan = (
        "🐺 <b>DAFTAR TARGET &amp; KUOTA HARIAN — ALPHA WOLF SQUAD</b>\n"
        f"🗓 <b>Periode: {HARI_BERJALAN_DEFAULT}-Nov-2026 | Target MTD: {target_persen_mtd}%</b> (Sisa {sisa_hari} Hari)\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{isi_daftar}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🏆 <b>TOTAL TIM YOVI ARIAN (ALPHA WOLF SQUAD)</b>\n"
        f"├ 🎯 Target Total Tim  : <b>{tot_target_all} SA</b>\n"
        f"├ ✅ Realisasi Tim     : <b>{tot_sa_now} SA</b> | <b>{tot_paid_now} Paid</b> | <b>{tot_so_now} SO</b>\n"
        f"├ 📊 Pencapaian Tim    : <b>{persen_tim}%</b> (Gap: {tot_sa_now - tot_target_all} SA | Runrate: {runrate_tim} SA)\n"
        f"└ ⚠️ Agen &lt; {target_persen_mtd}% MTD    : <b>{jml_agen_kurang} Agen</b> wajib kejar kuota Paid/hari &amp; SA/hari\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔥 <i>Pantang pulang sebelum kuota Paid/hari &amp; SA/hari tercapai, ALPHA WOLF SQUAD!</i> 💪🚀"
    )
    bot.reply_to(message, pesan_balasan, parse_mode="HTML")


@bot.message_handler(commands=["cektarget"])
def handle_cektarget(message: telebot.types.Message) -> None:
    """Handler /cektarget [nama_agen]: Mencari agen secara case-insensitive dengan Data Access Control."""
    teks_pesan = (message.text or "").strip()
    bagian = teks_pesan.split(maxsplit=1)

    if len(bagian) < 2 or not bagian[1].strip():
        bot.reply_to(
            message,
            "ℹ️ Silakan ketik nama agen setelah perintah.\nContoh: <code>/cektarget Naffa</code> atau <code>/cektarget Askih</code>",
            parse_mode="HTML",
        )
        return

    kata_kunci = bagian[1].strip()
    df_tim = baca_target_alpha_wolf()
    realisasi_map = ambil_realisasi_prospect_nov()

    hasil_cari = df_tim[
        df_tim["Nama_Agen"].str.contains(
            kata_kunci, case=False, na=False, regex=False
        )
    ]

    if hasil_cari.empty:
        bot.reply_to(
            message,
            "❌ Akses Ditolak: Agen tersebut bukan bagian dari ALPHA WOLF SQUAD atau data tidak valid.",
        )
        return

    sisa_hari = max(1, TOTAL_HARI_BULAN - HARI_BERJALAN_DEFAULT)
    sisa_minggu = max(1, math.ceil(sisa_hari / 7.0))
    target_persen_mtd = round_excel(
        (float(HARI_BERJALAN_DEFAULT) / float(TOTAL_HARI_BULAN)) * 100.0
    )

    balasan_list = []
    for _, row in hasil_cari.iterrows():
        nama = str(row["Nama_Agen"])
        level = str(row["Level"])
        target_all = int(row["Target_Bulan_Ini"])
        daily_paid_norm = int(row["Daily_Paid_Normal"])

        stat = realisasi_map.get(
            nama.lower().strip(), {"sa": 0, "paid": 0, "so": 0}
        )
        sa_now = stat["sa"]
        paid_now = stat["paid"]
        so_now = stat["so"]
        gap_sa = sa_now - target_all
        persen_int = (
            round_excel((float(sa_now) / float(target_all)) * 100.0)
            if target_all > 0
            else 0
        )
        runrate_30 = round_excel(
            (float(sa_now) * float(TOTAL_HARI_BULAN))
            / float(HARI_BERJALAN_DEFAULT)
        )

        sisa_sa = max(0, target_all - sa_now)
        harus_sa_des = sisa_sa / float(sisa_hari)
        harus_sa_hr = math.ceil(harus_sa_des)
        harus_paid_hr = max(
            harus_sa_hr, math.ceil(harus_sa_des * RASIO_PAID_PER_SA)
        )
        harus_so_hr = math.ceil(harus_paid_hr * RASIO_SO_PER_PAID)

        harus_sa_mgg = math.ceil(sisa_sa / float(sisa_minggu))
        harus_paid_mgg = math.ceil(harus_sa_mgg * RASIO_PAID_PER_SA)

        if persen_int < target_persen_mtd:
            selisih_pct = target_persen_mtd - persen_int
            status_mtd = f"⚠️ <b>MASIH KURANG -{selisih_pct}%</b> ({persen_int}% &lt; Target MTD {target_persen_mtd}%)"
        else:
            status_mtd = f"✅ <b>AMAN ON-TRACK</b> ({persen_int}% &ge; Target MTD {target_persen_mtd}%)"

        balasan_list.append(
            f"🐺 <b>RINCIAN TARGET &amp; KUOTA HARIAN — ALPHA WOLF SQUAD</b>\n"
            f"👤 Nama Agen : <b>{nama}</b> ({level})\n"
            f"📌 Status MTD : {status_mtd}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>Pencapaian Saat Ini (1–{HARI_BERJALAN_DEFAULT} Nov):</b>\n"
            f"├ ✅ Active (SA) : <b>{sa_now} SA</b> dari Target <b>{target_all} SA</b> ({persen_int}% | Gap: {gap_sa})\n"
            f"├ 💳 Paid        : <b>{paid_now} Paid</b> | 📝 SO Tercetak: <b>{so_now} SO</b>\n"
            f"└ 🚀 Runrate 30H : <b>{runrate_30} SA</b>\n\n"
            f"⚡ <b>1. KUOTA WAJIB HARIAN (Sisa {sisa_hari} Hari)</b>\n"
            f"├ Harus Paid / Hari : <b>{harus_paid_hr} Paid / hari</b> (Normal: {daily_paid_norm} Paid/hr)\n"
            f"├ Harus SA / Hari   : <b>{harus_sa_hr} SA / hari</b> ({harus_sa_des:.2f} SA/hr)\n"
            f"└ Harus Cetak SO    : <b>{harus_so_hr} SO / hari</b>\n\n"
            f"📅 <b>2. KUOTA WAJIB MINGGUAN (Sisa {sisa_minggu} Minggu)</b>\n"
            f"├ Harus Paid / Mgg  : <b>{harus_paid_mgg} Paid / minggu</b>\n"
            f"└ Harus SA / Mgg    : <b>{harus_sa_mgg} SA / minggu</b>\n\n"
            f"🎯 <b>3. TARGET TOTAL BULANAN</b>\n"
            f"└ Target Total      : <b>{target_all} SA</b> (Sisa <b>{sisa_sa} SA</b> lagi untuk Komisi 35%)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔥 <i>Semangat {nama}, kejar {harus_paid_hr} Paid/hari &amp; {harus_sa_hr} SA/hari agar tembus target!</i>"
        )

    bot.reply_to(message, "\n\n".join(balasan_list), parse_mode="HTML")


if __name__ == "__main__":
    pastikan_file_data_target()
    print("Bot ALPHA WOLF SQUAD sedang menyala...")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
