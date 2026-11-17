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

    for grp in grup_header:
        if len(grp) >= 4:
            label, a, b, bg_grp = grp[0], grp[1], grp[2], grp[3]
        else:
            label, a, b, bg_grp = grp[0], grp[1], grp[2], WARNA_NAVY
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
    kolom_bg_head: dict[int, str] = {}
    for grp in grup_header:
        if len(grp) >= 4:
            label, a, b, bg_grp = grp[0], grp[1], grp[2], grp[3]
        else:
            label, a, b, bg_grp = grp[0], grp[1], grp[2], WARNA_NAVY
        kolom_bergrup.update(range(a, b + 1))
        for c_idx in range(a, b + 1):
            kolom_bg_head[c_idx] = bg_grp
        kotak = (xs[a], y_tab, xs[b + 1], y_tab + tinggi_grup)
        d.rectangle(kotak, fill=bg_grp, outline=WARNA_GARIS_HEAD)
        _tulis(d, kotak, label, f_grup, "white")

    for c in range(n_kol):
        bg_h = kolom_bg_head.get(c, WARNA_NAVY)
        if c in kolom_bergrup:
            kotak = (xs[c], y_tab + tinggi_grup, xs[c + 1], y_tab + tinggi_grup + tinggi_head)
        else:
            kotak = (xs[c], y_tab, xs[c + 1], y_tab + tinggi_grup + tinggi_head)
        d.rectangle(kotak, fill=bg_h, outline=WARNA_GARIS_HEAD)
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
# GAMBAR 1B: REKAP HARIAN SO / PAID / SA & JUMLAH AGENT BLM PRODUKTIF
# =============================================================================


def buat_gambar_harian_blm_produktif(
    rows_harian: list[dict],
    date_label: str,
) -> bytes:
    """Membuat gambar tabel Performa Harian (SO, PAID, SA) & Jumlah Agent Blm Produktif."""
    kolom = [
        "Sales Leader",
        "SO",
        "PAID",
        "SA",
        "SO",
        "PAID",
        "SA",
    ]
    grup_header = [
        (date_label, 1, 3, WARNA_NAVY),
        ("Jumlah Agent Blm Produktif", 4, 6, "#d90000"),
    ]
    baris: list[list[str]] = []
    gaya: list[dict | None] = []
    idx_grand = -1
    for i, r in enumerate(rows_harian):
        is_gt = bool(r.get("is_grand_total")) or str(r.get("leader", "")).lower() == "grand total"
        if is_gt:
            idx_grand = i
        baris.append(
            [
                str(r.get("leader", "")),
                _fmt_angka(r.get("so", 0)),
                _fmt_angka(r.get("paid", 0)),
                _fmt_angka(r.get("sa", 0)),
                _fmt_angka(r.get("blm_so", 0)),
                _fmt_angka(r.get("blm_paid", 0)),
                _fmt_angka(r.get("blm_sa", 0)),
            ]
        )
        gaya.append({"bg": "white", "bold": True} if is_gt else None)

    def gaya_sel(i: int, c: int, _teks: str) -> dict | None:
        if i == idx_grand and c in (4, 5, 6):
            return {"bg": "#fce4d6", "bold": True}
        return None

    waktu = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
    return render_tabel_png(
        judul=f"REKAP HARIAN ({date_label}) & AGENT BELUM PRODUKTIF",
        sub_judul="Realisasi SO, PAID, SA Harian vs Jumlah Agent Aktif yang Belum Produktif (0 SO / 0 PAID / 0 SA)",
        kolom=kolom,
        baris=baris,
        rata=["l", "c", "c", "c", "c", "c", "c"],
        gaya_baris=gaya,
        gaya_sel=gaya_sel,
        grup_header=grup_header,
        catatan=[
            f"Kolom {date_label}: Total SO (Created Date), PAID (Payment Date PAID), SA (Active Date) tepat pada tanggal {date_label}.",
            f"Kolom Merah (Jumlah Agent Blm Produktif): Banyaknya agen aktif non-Vacant dengan nilai 0 pada {date_label}. Dibuat otomatis: {waktu}",
        ],
    )


def buat_gambar_wo_ringkasan(wo_summary: dict) -> bytes:
    """Merender tabel PNG Ringkasan WO Today (beserta SA/Active), WO Besok & Waiting WO per Sales Leader."""
    today_lbl = str(wo_summary.get("today_label", ""))
    besok_lbl = str(wo_summary.get("besok_label", ""))
    besok_rng = str(wo_summary.get("besok_range_label", f">= {besok_lbl}"))
    rows_src = wo_summary.get("leader_summary") or []

    kolom = [
        "SALES LEADER",
        "TOTAL\nTODAY",
        "SA\n(ACTIVE)",
        "ON\nINSTALL",
        "RESCHED",
        "WAIT\nWO",
        "LAINNYA",
        f"WO BESOK\n({besok_rng})",
        "WAITING WO\n(BLANK)",
    ]
    grup_header = [
        (f"1. WO TODAY ({today_lbl})", 1, 6, "#002060"),
        ("2. BESOK & 3. WAITING WO", 7, 8, "#065f46"),
    ]

    baris = []
    gaya = []
    idx_grand = -1
    for r in rows_src:
        is_gt = bool(r.get("is_grand_total")) or str(r.get("leader", "")).strip().lower() == "grand total"
        if is_gt:
            idx_grand = len(baris)
        baris.append(
            [
                str(r.get("leader", "")),
                _fmt_angka(r.get("today_total", 0)),
                _fmt_angka(r.get("today_sa", 0)),
                _fmt_angka(r.get("today_on_installation", 0)),
                _fmt_angka(r.get("today_reschedule", 0)),
                _fmt_angka(r.get("today_waiting_wo", 0)),
                _fmt_angka(r.get("today_other", 0)),
                _fmt_angka(r.get("wo_besok", 0)),
                _fmt_angka(r.get("waiting_wo", 0)),
            ]
        )
        gaya.append({"bg": "#dbeafe", "bold": True} if is_gt else None)

    def gaya_sel(i: int, c: int, _teks: str) -> dict | None:
        if i == idx_grand:
            if c == 1:
                return {"bg": "#c9daf8", "fg": "#1e3a8a", "bold": True}
            if c == 2:
                return {"bg": "#bbf7d0", "fg": "#14532d", "bold": True}
            if c == 7:
                return {"bg": "#d1fae5", "fg": "#065f46", "bold": True}
            if c == 8:
                return {"bg": "#fde68a", "fg": "#92400e", "bold": True}
        else:
            if c == 1:
                return {"bg": "#eff6ff", "bold": True}
            if c == 2:
                return {"bg": "#f0fdf4", "fg": "#166534", "bold": True}
            if c == 7:
                return {"bg": "#ecfdf5", "bold": True}
            if c == 8:
                return {"bg": "#fffbeb", "bold": True}
        return None

    waktu = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
    return render_tabel_png(
        judul=f"MONITORING WORK ORDER ({today_lbl} | WO BESOK | WAITING WO)",
        sub_judul=f"1. WO TODAY ({today_lbl} + SA Active)  •  2. WO BESOK ({besok_rng}, Semua Status)  •  3. WAITING WO (Instalasi Blank)",
        kolom=kolom,
        baris=baris,
        rata=["l", "c", "c", "c", "c", "c", "c", "c", "c"],
        gaya_baris=gaya,
        gaya_sel=gaya_sel,
        grup_header=grup_header,
        catatan=[
            f"1. WO TODAY: Semua status pd Instalasi Date {today_lbl} (SA = Active). 2. WO BESOK: Semua Instalasi Date > {today_lbl}. 3. WAITING WO: Instalasi Blank (Back To Sales/READY/Reschedule/Waiting WO).",
            f"Dibuat otomatis: {waktu}",
        ],
    )


def buat_gambar_wo_pivot(wo_summary: dict, mode: str) -> bytes:
    """Merender tabel Pivot lengkap (Leader -> Salesname -> Total) untuk 'today', 'besok', atau 'waiting'."""
    today_lbl = str(wo_summary.get("today_label", ""))
    besok_lbl = str(wo_summary.get("besok_label", ""))
    besok_rng = str(wo_summary.get("besok_range_label", f">= {besok_lbl}"))
    waktu = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")

    today_cols = list(wo_summary.get("wo_today_columns") or [])
    idx_sa_col = -1

    if mode == "today":
        src = wo_summary.get("wo_today_rows") or []
        disp_status_cols = ["Active (SA)" if c.lower() == "active" else c for c in today_cols]
        kolom = ["Sales Leader", "Salesname", *disp_status_cols, "Grand Total"]
        if "Active (SA)" in disp_status_cols:
            idx_sa_col = 2 + disp_status_cols.index("Active (SA)")
        rata = ["l", "l"] + ["c"] * (len(disp_status_cols) + 1)
        judul = f"1. WO TODAY ({today_lbl}) — DETAIL PER AGENT & SA"
        sub = f"Pivot Count of Customer Name pada Instalasi Date {today_lbl} (Status = ALL, Active = SA)"
        hdr_bg = "#002060"
    elif mode == "besok":
        src = wo_summary.get("wo_besok_rows") or []
        kolom = ["Sales Leader", "Salesname", "Grand Total"]
        rata = ["l", "l", "c"]
        judul = f"2. WO BESOK ({besok_rng}) — JADWAL INSTALASI"
        sub = f"Pivot Count of Customer Name untuk Instalasi Date > {today_lbl} (Multiple Items, Status = ALL)"
        hdr_bg = "#065f46"
    else:
        src = wo_summary.get("waiting_wo_rows") or []
        kolom = ["Sales Leader", "Salesname", "Grand Total"]
        rata = ["l", "l", "c"]
        judul = "3. WAITING WO (INSTALASI BLANK) — DETAIL PER AGENT"
        sub = "Instalasi Date = (blank) | Status: Back To Sales, READY, Reschedule, Waiting WO"
        hdr_bg = "#92400e"

    baris = []
    gaya = []
    idx_gt = -1
    for r in src:
        rt = r.get("row_type", "agent")
        ldr_txt = str(r.get("leader", "")) if rt == "agent" else ""
        sn_txt = str(r.get("salesname", ""))
        if rt == "grand_total":
            idx_gt = len(baris)
            gaya.append({"bg": "#fef3c7", "bold": True})
        elif rt == "leader_total":
            gaya.append({"bg": "#dbeafe", "bold": True})
        else:
            gaya.append(None)

        if mode == "today":
            st_map = r.get("statuses") or {}
            vals = []
            for cn in today_cols:
                v = int(st_map.get(cn, 0))
                vals.append(_fmt_angka(v) if (v > 0 or rt == "grand_total") else "")
            baris.append([ldr_txt, sn_txt, *vals, _fmt_angka(r.get("total", 0))])
        else:
            baris.append([ldr_txt, sn_txt, _fmt_angka(r.get("total", 0))])

    def gaya_sel(i: int, c: int, _t: str) -> dict | None:
        if c == len(kolom) - 1:
            return {"bold": True, "bg": "#fef3c7"} if i == idx_gt else {"bold": True}
        if idx_sa_col >= 0 and c == idx_sa_col:
            return {"bold": True, "bg": "#bbf7d0" if i == idx_gt else "#f0fdf4", "fg": "#166534"}
        return None

    return render_tabel_png(
        judul=judul,
        sub_judul=sub,
        kolom=kolom,
        baris=baris,
        rata=rata,
        gaya_baris=gaya,
        gaya_sel=gaya_sel,
        grup_header=[(judul.split(" — ")[0], 0, len(kolom) - 1, hdr_bg)] if len(kolom) >= 3 else None,
        catatan=[f"Dicetak otomatis: {waktu}"],
    )


def buat_gambar_wo_per_leader(wo_summary: dict) -> list[tuple[str, bytes, str]]:
    """Menghasilkan 1 gambar tabel WO lengkap (Today & SA, WO Besok, Waiting WO) untuk tiap Leader & tim agent-nya."""
    ag_rows = wo_summary.get("agent_summary") or []
    if not ag_rows:
        return []
    today_lbl = str(wo_summary.get("today_label", ""))
    besok_lbl = str(wo_summary.get("besok_label", ""))
    besok_rng = str(wo_summary.get("besok_range_label", f">= {besok_lbl}"))
    waktu = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")

    by_ldr: dict[str, list[dict]] = {}
    for ag in ag_rows:
        by_ldr.setdefault(str(ag.get("leader", "")), []).append(ag)

    out: list[tuple[str, bytes, str]] = []
    for idx, ldr in enumerate(sorted(by_ldr.keys(), key=lambda s: s.lower()), start=1):
        grp = by_ldr[ldr]
        baris = []
        gaya = []
        s_tot = s_sa = s_on = s_resch = s_wt = s_oth = s_bsk = s_wwo = 0
        for no, r in enumerate(grp, start=1):
            c_tot = int(r.get("today_total", 0))
            c_sa = int(r.get("today_sa", 0))
            c_on = int(r.get("today_on_installation", 0))
            c_res = int(r.get("today_reschedule", 0))
            c_wt = int(r.get("today_waiting_wo", 0))
            c_oth = int(r.get("today_other", 0))
            c_bsk = int(r.get("wo_besok", 0))
            c_wwo = int(r.get("waiting_wo", 0))
            s_tot += c_tot; s_sa += c_sa; s_on += c_on; s_resch += c_res; s_wt += c_wt; s_oth += c_oth; s_bsk += c_bsk; s_wwo += c_wwo
            baris.append([
                str(no),
                str(r.get("salesname", "")),
                _fmt_angka(c_tot),
                _fmt_angka(c_sa) if c_sa else "-",
                _fmt_angka(c_on) if c_on else "-",
                _fmt_angka(c_res) if c_res else "-",
                _fmt_angka(c_wt) if c_wt else "-",
                _fmt_angka(c_oth) if c_oth else "-",
                _fmt_angka(c_bsk),
                _fmt_angka(c_wwo),
            ])
            gaya.append(None)

        idx_tot = len(baris)
        baris.append([
            "", f"TOTAL {ldr}", _fmt_angka(s_tot), _fmt_angka(s_sa), _fmt_angka(s_on),
            _fmt_angka(s_resch), _fmt_angka(s_wt), _fmt_angka(s_oth), _fmt_angka(s_bsk), _fmt_angka(s_wwo),
        ])
        gaya.append({"bg": "#dbeafe", "bold": True})

        def gaya_sel(i: int, c: int, _t: str, it=idx_tot) -> dict | None:
            if c == 2:
                return {"bg": "#c9daf8", "fg": "#1e3a8a", "bold": True} if i == it else {"bg": "#eff6ff", "bold": True}
            if c == 3:
                return {"bg": "#bbf7d0", "fg": "#14532d", "bold": True} if i == it else {"bg": "#f0fdf4", "fg": "#166534", "bold": True}
            if c == 8:
                return {"bg": "#d1fae5", "fg": "#065f46", "bold": True} if i == it else {"bg": "#ecfdf5", "bold": True}
            if c == 9:
                return {"bg": "#fde68a", "fg": "#92400e", "bold": True} if i == it else {"bg": "#fffbeb", "bold": True}
            return None

        png_b = render_tabel_png(
            judul=f"WORK ORDER AGENT — TIM {ldr.upper()}",
            sub_judul=f"1. WO Today ({today_lbl} + SA)  •  2. WO Besok ({besok_rng})  •  3. Waiting WO (Blank)",
            kolom=["NO", "SALESNAME", "TOTAL\nTODAY", "SA\n(ACTIVE)", "ON\nINSTALL", "RESCHED", "WAIT\nWO", "LAINNYA", f"BESOK\n({besok_rng})", "WAITING\nWO"],
            baris=baris,
            rata=["c", "l", "c", "c", "c", "c", "c", "c", "c", "c"],
            gaya_baris=gaya,
            gaya_sel=gaya_sel,
            grup_header=[
                (f"1. WO TODAY ({today_lbl})", 2, 7, "#002060"),
                ("2. BESOK & 3. WAITING WO", 8, 9, "#065f46"),
            ],
            catatan=[f"Tim {ldr}: WO Today={s_tot} (SA={s_sa}) | WO Besok={s_bsk} | Waiting WO={s_wwo} | {waktu}"],
        )
        safe_l = re.sub(r"[^A-Za-z0-9]+", "_", ldr).strip("_")
        out.append((
            f"01D_{idx:02d}_WO_Tim_{safe_l}.png",
            png_b,
            f"🛠️ <b>WO Detail Agent — Tim {_escape_html(ldr)}</b> | Today ({_escape_html(today_lbl)}): {s_tot} (SA {s_sa}) | Besok: {s_bsk} | Waiting: {s_wwo}",
        ))
    return out


def buat_gambar_wo_kartu_agent(ag_row: dict, today_lbl: str, besok_lbl: str) -> bytes:
    """Merender kartu foto PNG individual untuk 1 Agent (WO Today + SA, WO Besok, Waiting WO)."""
    sn = str(ag_row.get("salesname", "-"))
    ldr = str(ag_row.get("leader", "-"))
    tot_i = int(ag_row.get("today_total", 0))
    sa_i = int(ag_row.get("today_sa", 0))
    on_i = int(ag_row.get("today_on_installation", 0))
    res_i = int(ag_row.get("today_reschedule", 0))
    wt_i = int(ag_row.get("today_waiting_wo", 0))
    oth_i = int(ag_row.get("today_other", 0))
    bsk = int(ag_row.get("wo_besok", 0))
    w_wo = int(ag_row.get("waiting_wo", 0))

    return render_tabel_png(
        judul=f"KARTU WO AGENT — {sn.upper()}",
        sub_judul=f"Sales Leader: {ldr}  •  WO Today: {today_lbl}  •  WO Besok: >= {besok_lbl}",
        kolom=["SALESNAME", "TOTAL TODAY", "SA (ACTIVE)", "ON INSTALL", "RESCHED", "WAIT WO", "LAINNYA", f"WO BESOK (>={besok_lbl})", "WAITING WO"],
        baris=[[sn, _fmt_angka(tot_i), _fmt_angka(sa_i), _fmt_angka(on_i), _fmt_angka(res_i), _fmt_angka(wt_i), _fmt_angka(oth_i), _fmt_angka(bsk), _fmt_angka(w_wo)]],
        rata=["l", "c", "c", "c", "c", "c", "c", "c", "c"],
        gaya_baris=[{"bg": "#ffffff", "bold": True}],
        gaya_sel=lambda i, c, _t: (
            {"bg": "#dbeafe", "fg": "#1e3a8a", "bold": True} if c == 1
            else ({"bg": "#bbf7d0", "fg": "#14532d", "bold": True} if c == 2
                  else ({"bg": "#dcfce7", "fg": "#065f46", "bold": True} if c == 7
                        else ({"bg": "#fef3c7", "fg": "#92400e", "bold": True} if c == 8 else None)))
        ),
        grup_header=[
            (f"1. WO TODAY ({today_lbl})", 1, 6, "#002060"),
            ("2. BESOK & 3. WAITING WO", 7, 8, "#065f46"),
        ],
        catatan=[f"Kartu Monitoring WO Pribadi — {sn} ({ldr})"],
    )


def buat_semua_gambar_wo(
    wo_summary: dict,
    include_pivot: bool = True,
    include_tim: bool = True,
    include_kartu_agent: bool = False,
) -> list[tuple[str, bytes, str]]:
    """Menyusun paket lengkap gambar PNG WO: Ringkasan, Pivot 1/2/3, per-Leader & opsi Kartu Masing-Masing Agent."""
    if not wo_summary or not wo_summary.get("leader_summary"):
        return []
    today_lbl = str(wo_summary.get("today_label", ""))
    besok_lbl = str(wo_summary.get("besok_label", ""))
    tot_map = wo_summary.get("wo_today_totals") or {}
    hasil: list[tuple[str, bytes, str]] = []

    hasil.append((
        f"01C_Monitoring_WO_{today_lbl}.png",
        buat_gambar_wo_ringkasan(wo_summary),
        f"🛠️ <b>Ringkasan Work Order</b> | 1. WO Today ({_escape_html(today_lbl)}): {int(tot_map.get('total', 0))} (SA: {int(tot_map.get('sa', 0))}) | 2. WO Besok: {int(wo_summary.get('wo_besok_total', 0))} | 3. Waiting WO: {int(wo_summary.get('waiting_wo_total', 0))}",
    ))
    if include_pivot:
        if wo_summary.get("wo_today_rows"):
            hasil.append((f"01C1_WO_TODAY_{today_lbl}.png", buat_gambar_wo_pivot(wo_summary, "today"), f"1️⃣ <b>WO TODAY ({_escape_html(today_lbl)}) — Total {int(tot_map.get('total', 0))} (SA {int(tot_map.get('sa', 0))})</b>"))
        if wo_summary.get("wo_besok_rows"):
            hasil.append((f"01C2_WO_BESOK_{besok_lbl}.png", buat_gambar_wo_pivot(wo_summary, "besok"), f"2️⃣ <b>WO BESOK (&gt;= {_escape_html(besok_lbl)}) — Total {int(wo_summary.get('wo_besok_total', 0))}</b>"))
        if wo_summary.get("waiting_wo_rows"):
            hasil.append((f"01C3_WAITING_WO_{today_lbl}.png", buat_gambar_wo_pivot(wo_summary, "waiting"), f"3️⃣ <b>WAITING WO (Instalasi Blank) — Total {int(wo_summary.get('waiting_wo_total', 0))}</b>"))
    if include_tim:
        hasil.extend(buat_gambar_wo_per_leader(wo_summary))
    if include_kartu_agent:
        for ag in wo_summary.get("agent_summary") or []:
            sn = str(ag.get("salesname", "-"))
            ldr = str(ag.get("leader", "-"))
            safe_sn = re.sub(r"[^A-Za-z0-9]+", "_", sn).strip("_")
            hasil.append((
                f"01E_WO_Agent_{safe_sn}.png",
                buat_gambar_wo_kartu_agent(ag, today_lbl, besok_lbl),
                f"👤 <b>Kartu WO — {_escape_html(sn)}</b> ({_escape_html(ldr)}) | Today: {int(ag.get('today_total', 0))} (SA: {int(ag.get('today_sa', 0))}) | Besok: {int(ag.get('wo_besok', 0))} | Waiting: {int(ag.get('waiting_wo', 0))}",
            ))
    return hasil


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
    daily_prod_rows: list[dict] | None = None,
    daily_prod_date_label: str = "",
    wo_summary: dict | None = None,
    include_wo_detail: bool = True,
    include_wo_agent_cards: bool = False,
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

    if daily_prod_rows:
        lbl_dl = daily_prod_date_label or f"{hari_berjalan}-{nama_bln_tampil}-{str(tahun)[-2:]}"
        png_dp = buat_gambar_harian_blm_produktif(daily_prod_rows, lbl_dl)
        hasil.append(
            (
                f"01B_Harian_Blm_Produktif_{lbl_dl}.png",
                png_dp,
                f"📊 <b>Rekap Harian ({_escape_html(lbl_dl)}) &amp; Jumlah Agent Belum Produktif</b>",
            )
        )

    if wo_summary and wo_summary.get("leader_summary"):
        hasil.extend(
            buat_semua_gambar_wo(
                wo_summary,
                include_pivot=include_wo_detail,
                include_tim=include_wo_detail,
                include_kartu_agent=include_wo_agent_cards,
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

