"""Modul pembuat Gambar Presentasi Laporan (PNG) untuk dikirim ke Bot Telegram.

Menghasilkan gambar tabel bergaya laporan Excel perusahaan:
1. MTD SA per Sales Leader (format Gambar 2: SA OCT 1-n vs SA NOV 1-n, GAP SA, Note Acv SA).
2. Detail Agent per Leader (format Gambar 1: banner TARGET tanggal | %, Target Total,
   SA, Paid, GAP, Persentase, Runrate, Breakdown Paket, Status vs Target MTD,
   serta Kuota Wajib Paid / Hari & SA / Hari).

Hanya menggunakan Pillow (tanpa matplotlib) agar ringan.
Catatan: sesuai aturan akses, gambar Telegram hanya menampilkan TARGET TOTAL
(Reguler + Yearly digabung), tanpa rincian Reguler / Yearly.
"""

import datetime
import io
import math
import os
import re

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

# =============================================================================
# KONSTANTA TAMPILAN
# =============================================================================

FOLDER_FONT = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
KANDIDAT_FONT_REGULER = ["arial.ttf", "segoeui.ttf", "calibri.ttf", "DejaVuSans.ttf"]
KANDIDAT_FONT_TEBAL = ["arialbd.ttf", "segoeuib.ttf", "calibrib.ttf", "DejaVuSans-Bold.ttf"]

MARGIN = 40
PAD_SEL = 16
TINGGI_BARIS = 48

WARNA_NAVY = "#1f3864"
WARNA_GARIS_HEAD = "#5b6f99"
WARNA_MAROON = "#6b1d36"
WARNA_GARIS = "#a7b1c2"
WARNA_TEKS = "#0f172a"
WARNA_TEKS_REDUP = "#475569"
WARNA_SELANG = "#f5f7fb"
WARNA_TOTAL_DETAIL = "#b4a7d6"
WARNA_TOTAL_MTD = "#c9daf8"
WARNA_NOTE_MTD = "#dbe5f1"
WARNA_VACANT = "#ffff00"
WARNA_SA = "#c9daf8"
WARNA_MERAH_BG = "#f4cccc"
WARNA_MERAH_TX = "#990000"
WARNA_HIJAU_BG = "#d9ead3"
WARNA_HIJAU_TX = "#134f5c"
WARNA_KUOTA_BG = "#fff2cc"
WARNA_KUOTA_TX = "#7f4f00"

_cache_font: dict[tuple[int, bool], ImageFont.FreeTypeFont] = {}


# =============================================================================
# FUNGSI BANTU
# =============================================================================


def _font(ukuran: int, tebal: bool = False):
    """Mengambil font TrueType (Arial/Segoe/Calibri) dengan fallback font bawaan Pillow."""
    kunci = (ukuran, tebal)
    if kunci in _cache_font:
        return _cache_font[kunci]
    kandidat = KANDIDAT_FONT_TEBAL if tebal else KANDIDAT_FONT_REGULER
    for nama in kandidat:
        for path in (os.path.join(FOLDER_FONT, nama), nama):
            try:
                f = ImageFont.truetype(path, ukuran)
                _cache_font[kunci] = f
                return f
            except OSError:
                continue
    try:
        f = ImageFont.load_default(size=ukuran)
    except TypeError:
        f = ImageFont.load_default()
    _cache_font[kunci] = f
    return f


def _round_excel(nilai: float | int) -> int:
    """Pembulatan half-up standar Excel: =ROUND(x, 0)."""
    if pd.isna(nilai):
        return 0
    val = float(nilai)
    if val >= 0:
        return int(math.floor(val + 0.5))
    return int(math.ceil(val - 0.5))


def _fmt_angka(nilai: object) -> str:
    """Format angka bulat dengan pemisah ribuan titik (contoh: 1.471, -136)."""
    try:
        return f"{int(nilai):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(nilai)


def _ke_angka(teks: object) -> float | None:
    """Mengubah teks sel (misal '-136', '27%', '1.471') kembali menjadi angka."""
    s = str(teks).replace(".", "").replace("%", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _escape_html(teks: object) -> str:
    return (
        str(teks).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def _ukuran_font(font) -> int:
    return int(getattr(font, "size", 16))


def _lebar_teks(teks: object, font) -> float:
    return max((font.getlength(b) for b in str(teks).split("\n")), default=0.0)


def _tulis(draw: ImageDraw.ImageDraw, kotak, teks: object, font, warna: str, rata: str = "c") -> None:
    """Menulis teks (mendukung multi-baris) di tengah vertikal sebuah kotak sel."""
    x0, y0, x1, y1 = kotak
    baris = str(teks).split("\n")
    tinggi_baris = _ukuran_font(font) * 1.18
    y = (y0 + y1) / 2 - (tinggi_baris * len(baris)) / 2 + tinggi_baris / 2
    for b in baris:
        if rata == "l":
            draw.text((x0 + PAD_SEL, y), b, font=font, fill=warna, anchor="lm")
        elif rata == "r":
            draw.text((x1 - PAD_SEL, y), b, font=font, fill=warna, anchor="rm")
        else:
            draw.text(((x0 + x1) / 2, y), b, font=font, fill=warna, anchor="mm")
        y += tinggi_baris


# =============================================================================
# RENDERER TABEL GENERIK
# =============================================================================


def render_tabel_png(
    judul: str,
    sub_judul: str,
    kolom: list[str],
    baris: list[list[str]],
    rata: list[str] | None = None,
    gaya_baris: list[dict | None] | None = None,
    gaya_sel=None,
    grup_header: list[tuple[str, int, int]] | None = None,
    banner: tuple[str, str, str] | None = None,
    catatan: list[str] | None = None,
) -> bytes:
    """Merender tabel laporan bergaya Excel menjadi gambar PNG (bytes).

    - gaya_baris: daftar dict per baris {'bg', 'fg', 'bold'}.
    - gaya_sel: callable(idx_baris, idx_kolom, teks) -> dict {'bg', 'fg', 'bold', 'rata'} atau None.
    - grup_header: daftar (label, kolom_awal, kolom_akhir) untuk header bertingkat.
    - banner: (teks_atas, teks_kiri, teks_kanan), misal ('TARGET', '8-Nov-2026', '27%').
    """
    f_judul = _font(40, True)
    f_sub = _font(24)
    f_head = _font(22, True)
    f_grup = _font(22, True)
    f_sel = _font(24)
    f_sel_tebal = _font(24, True)
    f_cat = _font(21)
    f_banner = _font(24, True)

    n_kol = len(kolom)
    rata = rata or ["c"] * n_kol
    gaya_baris = gaya_baris or [None] * len(baris)
    grup_header = grup_header or []
    catatan = catatan or []

    # 1. Hitung lebar setiap kolom berdasarkan teks terpanjang
    lebar_kol: list[float] = []
    for c in range(n_kol):
        w = _lebar_teks(kolom[c], f_head)
        for r in baris:
            w = max(w, _lebar_teks(r[c], f_sel_tebal))
        lebar_kol.append(w + 2 * PAD_SEL)

    for label, a, b in grup_header:
        perlu = _lebar_teks(label, f_grup) + 2 * PAD_SEL
        ada = sum(lebar_kol[a : b + 1])
        if perlu > ada:
            tambah = (perlu - ada) / (b - a + 1)
            for c in range(a, b + 1):
                lebar_kol[c] += tambah

    # 2. Hitung ukuran area judul + banner
    lebar_banner = 0.0
    lebar_banner_kiri = 0.0
    tinggi_banner = 0
    if banner:
        teks_atas, teks_kiri, teks_kanan = banner
        lebar_banner_kiri = _lebar_teks(teks_kiri, f_banner) + 56
        lebar_banner_kanan = _lebar_teks(teks_kanan, f_banner) + 56
        lebar_banner = max(
            lebar_banner_kiri + lebar_banner_kanan,
            _lebar_teks(teks_atas, f_banner) + 56,
        )
        tinggi_banner = 84

    lebar_judul = max(_lebar_teks(judul, f_judul), _lebar_teks(sub_judul, f_sub))
    lebar_catatan = max((_lebar_teks(t, f_cat) for t in catatan), default=0.0)
    lebar_tabel = sum(lebar_kol)
    lebar_isi = max(
        lebar_tabel,
        lebar_judul + (lebar_banner + 60 if banner else 0),
        lebar_catatan,
    )

    # Jika judul lebih lebar dari tabel, lebarkan kolom secara proporsional
    if lebar_isi > lebar_tabel:
        faktor = lebar_isi / lebar_tabel
        lebar_kol = [w * faktor for w in lebar_kol]
    lebar_kol = [int(math.ceil(w)) for w in lebar_kol]
    lebar_isi = sum(lebar_kol)

    n_baris_head = max(len(str(k).split("\n")) for k in kolom)
    tinggi_head = int(n_baris_head * _ukuran_font(f_head) * 1.18 + 22)
    tinggi_grup = 42 if grup_header else 0
    tinggi_blok_judul = max(46 + 10 + 30, tinggi_banner) + 26
    tinggi_catatan = (len(catatan) * 30 + 22) if catatan else 0

    lebar_img = lebar_isi + 2 * MARGIN
    tinggi_img = (
        MARGIN + 10
        + tinggi_blok_judul
        + tinggi_grup
        + tinggi_head
        + len(baris) * TINGGI_BARIS
        + tinggi_catatan
        + MARGIN
    )

    img = Image.new("RGB", (lebar_img, tinggi_img), "white")
    d = ImageDraw.Draw(img)

    # 3. Garis aksen atas, judul & sub-judul
    d.rectangle([0, 0, lebar_img, 10], fill=WARNA_NAVY)
    y0 = MARGIN + 10
    d.text((MARGIN, y0), judul, font=f_judul, fill=WARNA_TEKS, anchor="la")
    d.text((MARGIN, y0 + 56), sub_judul, font=f_sub, fill=WARNA_TEKS_REDUP, anchor="la")

    # 4. Banner TARGET (tanggal | persentase) di pojok kanan atas
    if banner:
        teks_atas, teks_kiri, teks_kanan = banner
        bx1 = MARGIN + lebar_isi
        bx0 = int(bx1 - lebar_banner)
        bxm = int(bx0 + lebar_banner_kiri)
        d.rectangle([bx0, y0, bx1, y0 + 40], fill=WARNA_MAROON, outline="#4a1525")
        _tulis(d, (bx0, y0, bx1, y0 + 40), teks_atas, f_banner, "white")
        d.rectangle([bx0, y0 + 40, bxm, y0 + 84], fill=WARNA_MAROON, outline="#993355")
        d.rectangle([bxm, y0 + 40, bx1, y0 + 84], fill=WARNA_MAROON, outline="#993355")
        _tulis(d, (bx0, y0 + 40, bxm, y0 + 84), teks_kiri, f_banner, "white")
        _tulis(d, (bxm, y0 + 40, bx1, y0 + 84), teks_kanan, f_banner, "white")

    # 5. Header tabel (mendukung header bertingkat / grup)
    y_tab = y0 + tinggi_blok_judul
    xs = [MARGIN]
    for w in lebar_kol:
        xs.append(xs[-1] + w)

    kolom_bergrup: set[int] = set()
    for label, a, b in grup_header:
        kolom_bergrup.update(range(a, b + 1))
        kotak = (xs[a], y_tab, xs[b + 1], y_tab + tinggi_grup)
        d.rectangle(kotak, fill=WARNA_NAVY, outline=WARNA_GARIS_HEAD)
        _tulis(d, kotak, label, f_grup, "white")

    for c in range(n_kol):
        if c in kolom_bergrup:
            kotak = (xs[c], y_tab + tinggi_grup, xs[c + 1], y_tab + tinggi_grup + tinggi_head)
        else:
            kotak = (xs[c], y_tab, xs[c + 1], y_tab + tinggi_grup + tinggi_head)
        d.rectangle(kotak, fill=WARNA_NAVY, outline=WARNA_GARIS_HEAD)
        _tulis(d, kotak, kolom[c], f_head, "white")

    # 6. Isi tabel
    y = y_tab + tinggi_grup + tinggi_head
    for i_baris, isi in enumerate(baris):
        gb = gaya_baris[i_baris] or {}
        bg_baris = gb.get("bg", WARNA_SELANG if i_baris % 2 else "white")
        for c in range(n_kol):
            gs = (gaya_sel(i_baris, c, isi[c]) if gaya_sel else None) or {}
            bg = gs.get("bg", bg_baris)
            fg = gs.get("fg", gb.get("fg", WARNA_TEKS))
            tebal = gs.get("bold", gb.get("bold", False))
            kotak = (xs[c], y, xs[c + 1], y + TINGGI_BARIS)
            d.rectangle(kotak, fill=bg, outline=WARNA_GARIS)
            _tulis(d, kotak, isi[c], f_sel_tebal if tebal else f_sel, fg, gs.get("rata", rata[c]))
        y += TINGGI_BARIS

    d.rectangle([MARGIN, y_tab, xs[-1], y], outline=WARNA_NAVY, width=2)

    # 7. Catatan / keterangan rumus di bawah tabel
    y += 22
    for teks in catatan:
        d.text((MARGIN, y), teks, font=f_cat, fill=WARNA_TEKS_REDUP, anchor="la")
        y += 30

    buffer = io.BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


# =============================================================================
# GAMBAR 1: MTD SA PER SALES LEADER (FORMAT GAMBAR 2)
# =============================================================================


def buat_gambar_mtd_sa(
    df_mtd_final: pd.DataFrame,
    kol_oct: str,
    kol_nov: str,
    kol_gap: str,
    hari_berjalan: int,
    kode_bln_lalu: str,
    kode_bln_ini: str,
    tahun: int,
) -> bytes:
    """Membuat gambar tabel MTD SA (SA Bulan Lalu vs Bulan Ini, GAP SA, Total & Note Acv SA)."""
    kolom = [
        "SALES LEADER",
        f"SA {kode_bln_lalu}\n1-{hari_berjalan}",
        f"SA {kode_bln_ini}\n1-{hari_berjalan}",
        "GAP SA",
    ]
    baris: list[list[str]] = []
    gaya: list[dict | None] = []
    tot_oct = tot_nov = 0

    for _, r in df_mtd_final.iterrows():
        nama = str(r["SALES LEADER"]).strip()
        if nama.upper() == "TOTAL":
            tot_oct = int(r[kol_oct])
            tot_nov = int(r[kol_nov])
            baris.append(["Total", _fmt_angka(tot_oct), _fmt_angka(tot_nov), _fmt_angka(r[kol_gap])])
            gaya.append({"bg": WARNA_TOTAL_MTD, "bold": True})
        else:
            baris.append([nama, _fmt_angka(r[kol_oct]), _fmt_angka(r[kol_nov]), _fmt_angka(r[kol_gap])])
            gaya.append(None)

    acv = _round_excel(((tot_nov - tot_oct) / float(tot_oct)) * 100.0) if tot_oct > 0 else 0
    baris.append(["Note Acv SA", "", "↓" if acv < 0 else "↑", f"{acv}%"])
    gaya.append({"bg": WARNA_NOTE_MTD, "bold": True})
    idx_total = len(baris) - 2
    idx_note = len(baris) - 1

    def gaya_sel(i: int, c: int, teks: str) -> dict | None:
        if c == 0 and i in (idx_total, idx_note):
            return {"rata": "c"}
        if c == 3:
            angka = _ke_angka(teks)
            if angka is not None and angka < 0:
                return {"bg": WARNA_MERAH_BG, "fg": WARNA_MERAH_TX, "bold": True}
            if angka is not None and angka > 0:
                return {"fg": "#15803d", "bold": True}
        return None

    waktu = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
    return render_tabel_png(
        judul="MTD SA — RINGKASAN PENCAPAIAN LEADER",
        sub_judul=f"Apple-to-apple tanggal 1-{hari_berjalan} {kode_bln_lalu} vs {kode_bln_ini} {tahun}",
        kolom=kolom,
        baris=baris,
        rata=["l", "c", "c", "c"],
        gaya_baris=gaya,
        gaya_sel=gaya_sel,
        catatan=[
            f"GAP SA = SA {kode_bln_ini} - SA {kode_bln_lalu} (rentang tanggal sama). Merah = turun dibanding bulan lalu.",
            f"Note Acv SA = (Total {kode_bln_ini} - Total {kode_bln_lalu}) ÷ Total {kode_bln_lalu}.  Dibuat otomatis: {waktu}",
        ],
    )


# =============================================================================
# GAMBAR 2: DETAIL AGENT PER LEADER (FORMAT GAMBAR 1 + KUOTA HARIAN)
# =============================================================================


def buat_gambar_detail_leader(
    nama_leader: str,
    grp: pd.DataFrame,
    target_persen_mtd: int,
    hari_berjalan: int,
    total_hari: int,
    sisa_hari: int,
    nama_bln_tampil: str,
    kode_bln_ini: str,
    tahun: int,
    rasio_paid: float,
) -> bytes:
    """Membuat gambar Detail Agent satu Leader lengkap dengan Status vs Target MTD & Kuota Paid/SA per Hari."""
    kolom = [
        "NO",
        "SALES NAME",
        "LEVEL",
        "TARGET\nTOTAL",
        f"SA\n{kode_bln_ini}",
        f"PAID\n{kode_bln_ini}",
        "GAP\nSA",
        "PERSEN-\nTASE",
        f"RUNRATE\n{total_hari} HARI",
        "M",
        "3M",
        "SEM",
        "Y",
        f"STATUS vs\nTARGET {target_persen_mtd}%",
        "PAID\n/ HARI",
        "SA\n/ HARI",
    ]
    grup_header = [("BREAKDOWN PAKET", 9, 12), ("KUOTA WAJIB / HARI", 14, 15)]

    baris: list[list[str]] = []
    gaya: list[dict | None] = []
    baris_vacant: set[int] = set()
    baris_kurang: set[int] = set()
    n_kurang = 0

    for no, (_, r) in enumerate(grp.iterrows(), start=1):
        nama = str(r["SALES NAME"]).strip()
        is_vacant = nama.upper() == "VACANT"
        pct = int(r["PERSENTASE_INT"])
        if is_vacant:
            status = "VACANT"
        elif pct < target_persen_mtd:
            status = f"KURANG -{target_persen_mtd - pct}%"
            n_kurang += 1
            baris_kurang.add(len(baris))
        else:
            status = "AMAN"
        if is_vacant:
            baris_vacant.add(len(baris))

        baris.append(
            [
                str(no),
                nama,
                str(r["LEVEL"]),
                _fmt_angka(r["TARGET ALL"]),
                _fmt_angka(r["SA NOV"]),
                _fmt_angka(r["PAID NOV"]),
                _fmt_angka(r["GAP SA NOV"]),
                f"{pct}%",
                _fmt_angka(r["RUNRATE 30 HARI"]),
                _fmt_angka(r["Monthly"]),
                _fmt_angka(r["3 Monthly"]),
                _fmt_angka(r["Semesterly"]),
                _fmt_angka(r["Yearly"]),
                status,
                _fmt_angka(r["Harus_Paid_Per_Hari_Bulat"]),
                _fmt_angka(r["Harus_SA_Per_Hari_Bulat"]),
            ]
        )
        gaya.append(None)

    # Baris TOTAL Leader (Runrate = ROUND(SUM_SA * Total_Hari / Hari_Berjalan, 0) sesuai Gambar 1)
    sum_target = int(grp["TARGET ALL"].sum())
    sum_sa = int(grp["SA NOV"].sum())
    pct_ldr = _round_excel((sum_sa / float(sum_target)) * 100.0) if sum_target > 0 else 0
    runrate_ldr = _round_excel((sum_sa * float(total_hari)) / float(max(1, hari_berjalan)))
    baris.append(
        [
            "",
            f"TOTAL {nama_leader}",
            "",
            _fmt_angka(sum_target),
            _fmt_angka(sum_sa),
            _fmt_angka(grp["PAID NOV"].sum()),
            _fmt_angka(sum_sa - sum_target),
            f"{pct_ldr}%",
            _fmt_angka(runrate_ldr),
            _fmt_angka(grp["Monthly"].sum()),
            _fmt_angka(grp["3 Monthly"].sum()),
            _fmt_angka(grp["Semesterly"].sum()),
            _fmt_angka(grp["Yearly"].sum()),
            f"{n_kurang} agen kurang",
            _fmt_angka(grp["Harus_Paid_Per_Hari_Bulat"].sum()),
            _fmt_angka(grp["Harus_SA_Per_Hari_Bulat"].sum()),
        ]
    )
    gaya.append({"bg": WARNA_TOTAL_DETAIL, "bold": True})
    idx_total = len(baris) - 1

    def gaya_sel(i: int, c: int, teks: str) -> dict | None:
        is_total = i == idx_total
        if c == 1 and i in baris_vacant:
            return {"bg": WARNA_VACANT, "bold": True}
        if c == 4 and not is_total:
            return {"bg": WARNA_SA, "bold": True}
        if c == 6 and not is_total:
            angka = _ke_angka(teks)
            if angka is not None and angka < 0:
                return {"fg": WARNA_MERAH_TX}
        if c == 7:
            angka = _ke_angka(teks)
            if angka is not None and angka < target_persen_mtd:
                return {"bg": WARNA_MERAH_BG, "fg": WARNA_MERAH_TX, "bold": True}
            return {"bg": WARNA_HIJAU_BG, "fg": WARNA_HIJAU_TX, "bold": True}
        if c == 13 and not is_total:
            if teks.startswith("KURANG"):
                return {"bg": WARNA_MERAH_BG, "fg": WARNA_MERAH_TX, "bold": True}
            if teks == "AMAN":
                return {"bg": WARNA_HIJAU_BG, "fg": WARNA_HIJAU_TX, "bold": True}
        if c in (14, 15) and i in baris_kurang:
            return {"bg": WARNA_KUOTA_BG, "fg": WARNA_KUOTA_TX, "bold": True}
        if c in (14, 15):
            return {"bold": True}
        return None

    n_agen = int((grp["SALES NAME"].astype(str).str.upper() != "VACANT").sum())
    waktu = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
    return render_tabel_png(
        judul=f"DETAIL AGENT — TIM {nama_leader.upper()}",
        sub_judul=(
            f"Realisasi MTD 1-{hari_berjalan} {nama_bln_tampil} {tahun}  •  Sisa {sisa_hari} hari  •  "
            f"{n_kurang} dari {n_agen} agen di bawah target {target_persen_mtd}%"
        ),
        kolom=kolom,
        baris=baris,
        rata=["c", "l"] + ["c"] * (len(kolom) - 2),
        gaya_baris=gaya,
        gaya_sel=gaya_sel,
        grup_header=grup_header,
        banner=("TARGET", f"{hari_berjalan}-{nama_bln_tampil}-{tahun}", f"{target_persen_mtd}%"),
        catatan=[
            f"PERSENTASE = SA ÷ Target Total. Merah = di bawah target berjalan {target_persen_mtd}% ({hari_berjalan}/{total_hari} hari), hijau = aman.",
            f"Kuota wajib / hari = (Target Total - SA saat ini) ÷ sisa {sisa_hari} hari. PAID / HARI sudah termasuk buffer rasio Paid→SA ({rasio_paid:.2f}x).",
            f"RUNRATE = ROUND(SA × {total_hari} ÷ {hari_berjalan}).  Dibuat otomatis: {waktu}",
        ],
    )


# =============================================================================
# FUNGSI UTAMA: SUSUN SEMUA GAMBAR LAPORAN UNTUK TELEGRAM
# =============================================================================


def buat_semua_gambar_laporan(
    df_mtd_final: pd.DataFrame,
    df_agent: pd.DataFrame,
    kol_oct: str,
    kol_nov: str,
    kol_gap: str,
    kode_bln_lalu: str,
    kode_bln_ini: str,
    nama_bln_tampil: str,
    tahun: int,
    hari_berjalan: int,
    total_hari: int,
    sisa_hari: int,
    target_persen_mtd: int,
    rasio_paid: float,
) -> list[tuple[str, bytes, str]]:
    """Menghasilkan daftar (nama_file, png_bytes, caption_html) untuk dikirim ke Telegram."""
    hasil: list[tuple[str, bytes, str]] = []

    png_mtd = buat_gambar_mtd_sa(
        df_mtd_final, kol_oct, kol_nov, kol_gap,
        hari_berjalan, kode_bln_lalu, kode_bln_ini, tahun,
    )
    hasil.append(
        (
            f"01_MTD_SA_1-{hari_berjalan}_{kode_bln_ini}_{tahun}.png",
            png_mtd,
            f"📈 <b>MTD SA 1-{hari_berjalan} {kode_bln_lalu} vs {kode_bln_ini} {tahun}</b>",
        )
    )

    df_valid = df_agent[
        ~df_agent["SALES NAME"].astype(str).str.strip().str.upper().isin(["", "NAN", "NONE", "TOTAL", "-"])
    ]
    for no, (nama_ldr, grp) in enumerate(df_valid.groupby("SALES LEADER", sort=False), start=2):
        if grp.empty:
            continue
        png_ldr = buat_gambar_detail_leader(
            str(nama_ldr), grp, target_persen_mtd, hari_berjalan, total_hari,
            sisa_hari, nama_bln_tampil, kode_bln_ini, tahun, rasio_paid,
        )
        nama_file_ldr = re.sub(r"[^A-Za-z0-9]+", "_", str(nama_ldr)).strip("_")
        hasil.append(
            (
                f"{no:02d}_Detail_Agent_{nama_file_ldr}.png",
                png_ldr,
                f"📋 <b>Detail Agent — Tim {_escape_html(nama_ldr)}</b> | "
                f"{hari_berjalan}-{nama_bln_tampil}-{tahun} | Target MTD {target_persen_mtd}%",
            )
        )
    return hasil

