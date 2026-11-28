"""Modul pembuat Gambar Presentasi Laporan Super-HD (PNG) untuk Dashboard, WhatsApp & Telegram.

Menghasilkan gambar komposit gabungan beresolusi tinggi (anti-blur saat di-copy ke WhatsApp):
1. `01_Ringkasan_Eksekutif_*.png` : Gabungan MTD SA + Rekap Harian Blm Produktif + Ringkasan WO.
2. `02A_WO_TODAY_*.png`            : Pivot 1. WO TODAY multi-kolom (menyamping agar tidak memanjang & blur).
3. `02B_WO_BESOK_dan_WAITING_*.png`: Gabungan Pivot 2. WO BESOK + 3. WAITING WO.
4. `03_*_Laporan_Tim_*.png`        : Gabungan Detail Agent + Rincian Harian PAID/GP + Monitoring WO per Tim Leader.
5. `01E_WO_Agent_*.png`            : Kartu WO Pribadi per Agent (opsional).
"""

import datetime
import io
import math
import os
import re

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

# =============================================================================
# KONSTANTA TAMPILAN SUPER-HD
# =============================================================================

FOLDER_FONT = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
KANDIDAT_FONT_REGULER = ["arial.ttf", "segoeui.ttf", "calibri.ttf", "DejaVuSans.ttf"]
KANDIDAT_FONT_TEBAL = ["arialbd.ttf", "segoeuib.ttf", "calibrib.ttf", "DejaVuSans-Bold.ttf"]

MARGIN = 48
PAD_SEL = 18
TINGGI_BARIS = 50
PANEL_GAP = 32
ROW_GAP = 34

WARNA_NAVY = "#1f3864"
WARNA_GARIS_HEAD = "#5b6f99"
WARNA_MAROON = "#6b1d36"
WARNA_GARIS = "#94a3b8"
WARNA_TEKS = "#0f172a"
WARNA_TEKS_REDUP = "#334155"
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
    """Format angka bulat dengan pemisah ribuan titik."""
    try:
        return f"{int(nilai):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(nilai)


def _ke_angka(teks: object) -> float | None:
    """Mengubah teks sel kembali menjadi angka float bila valid."""
    s = str(teks).replace(".", "").replace("%", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _escape_html(teks: object) -> str:
    return str(teks).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _ukuran_font(font) -> int:
    return int(getattr(font, "size", 20))


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


def _partisi_blok_wo(rows_src: list[dict], n_kolom: int) -> list[list[dict]]:
    """Membagi baris pivot WO ke n_kolom bersebelahan secara seimbang tanpa memotong grup Leader."""
    non_gt = [r for r in rows_src if r.get("row_type") != "grand_total"]
    gt_rows = [r for r in rows_src if r.get("row_type") == "grand_total"]
    if not non_gt:
        return [list(rows_src)] if rows_src else []
    if n_kolom <= 1:
        return [non_gt + gt_rows]

    blocks: list[list[dict]] = []
    cur: list[dict] = []
    for r in non_gt:
        cur.append(r)
        if r.get("row_type") == "leader_total":
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)

    if len(blocks) < n_kolom:
        chunk_sz = max(1, math.ceil(len(non_gt) / n_kolom))
        hasil = [non_gt[i : i + chunk_sz] for i in range(0, len(non_gt), chunk_sz)]
        if hasil and gt_rows:
            hasil[-1] = hasil[-1] + gt_rows
        return [c for c in hasil if c]

    weights = [len(b) for b in blocks]
    nb = len(blocks)
    pref = [0] * (nb + 1)
    for i, w in enumerate(weights):
        pref[i + 1] = pref[i] + w

    inf = 10**9
    dp = [[inf] * (nb + 1) for _ in range(n_kolom + 1)]
    cut = [[0] * (nb + 1) for _ in range(n_kolom + 1)]
    dp[0][0] = 0
    for k in range(1, n_kolom + 1):
        for i in range(k, nb + 1):
            for j in range(k - 1, i):
                cost = max(dp[k - 1][j], pref[i] - pref[j])
                if cost < dp[k][i]:
                    dp[k][i] = cost
                    cut[k][i] = j

    bounds: list[tuple[int, int]] = []
    pos = nb
    for k in range(n_kolom, 0, -1):
        prev = cut[k][pos]
        bounds.append((prev, pos))
        pos = prev
    bounds.reverse()

    cols: list[list[dict]] = []
    for a, b in bounds:
        flat = [r for blk in blocks[a:b] for r in blk]
        if flat:
            cols.append(flat)
    if cols and gt_rows:
        cols[-1] = cols[-1] + gt_rows
    return cols


# =============================================================================
# RENDERER BOARD KOMPOSIT SUPER-HD
# =============================================================================


def render_komposit_png(
    judul: str,
    sub_judul: str,
    panel_rows: list[list[dict]],
    banner: tuple[str, str, str] | None = None,
    catatan: list[str] | None = None,
    hd_scale: float = 1.0,
) -> bytes:
    """Merender board berisi 1 atau banyak panel tabel sejajar ke dalam PNG Super-HD."""
    sc = hd_scale if hd_scale > 0 else 1.0
    m_px = int(round(MARGIN * sc))
    pad_s = int(round(PAD_SEL * sc))
    row_h = int(round(TINGGI_BARIS * sc))
    p_gap = int(round(PANEL_GAP * sc))
    r_gap = int(round(ROW_GAP * sc))

    f_judul = _font(int(round(46 * sc)), True)
    f_sub = _font(int(round(25 * sc)))
    f_sec = _font(int(round(26 * sc)), True)
    f_head = _font(int(round(23 * sc)), True)
    f_grup = _font(int(round(23 * sc)), True)
    f_sel = _font(int(round(24 * sc)))
    f_sel_tebal = _font(int(round(24 * sc)), True)
    f_cat = _font(int(round(22 * sc)))
    f_banner = _font(int(round(25 * sc)), True)

    catatan = catatan or []
    measured_rows: list[list[dict]] = []
    max_row_w = 0.0

    for prow in panel_rows:
        m_prow = []
        row_w = 0.0
        for p in prow:
            kolom = p["columns"]
            baris = p["rows"]
            n_kol = len(kolom)
            grup_header = p.get("group_headers") or []
            sec_title = p.get("section_title", "")

            lebar_kol: list[float] = []
            for c in range(n_kol):
                w = _lebar_teks(kolom[c], f_head)
                for r in baris:
                    w = max(w, _lebar_teks(r[c], f_sel_tebal))
                lebar_kol.append(w + 2 * pad_s)

            for grp in grup_header:
                label, a, b = grp[0], grp[1], grp[2]
                perlu = _lebar_teks(label, f_grup) + 2 * pad_s
                ada = sum(lebar_kol[a : b + 1])
                if perlu > ada:
                    tambah = (perlu - ada) / (b - a + 1)
                    for c in range(a, b + 1):
                        lebar_kol[c] += tambah

            w_nat = sum(lebar_kol)
            if sec_title:
                w_sec = _lebar_teks(sec_title, f_sec) + 2 * pad_s
                if w_sec > w_nat:
                    ratio_s = w_sec / w_nat
                    lebar_kol = [w * ratio_s for w in lebar_kol]
                    w_nat = w_sec

            n_baris_head = max((len(str(k).split("\n")) for k in kolom), default=1)
            tinggi_head = int(n_baris_head * _ukuran_font(f_head) * 1.18 + round(24 * sc))
            tinggi_grup = int(round(44 * sc)) if grup_header else 0
            tinggi_sec = int(round(46 * sc)) if sec_title else 0
            tinggi_tab = tinggi_sec + tinggi_grup + tinggi_head + len(baris) * row_h

            m_prow.append({
                "spec": p,
                "lebar_kol": lebar_kol,
                "w_nat": w_nat,
                "tinggi_sec": tinggi_sec,
                "tinggi_grup": tinggi_grup,
                "tinggi_head": tinggi_head,
                "tinggi_tab": tinggi_tab,
            })
            row_w += w_nat
        if len(m_prow) > 1:
            row_w += p_gap * (len(m_prow) - 1)
        max_row_w = max(max_row_w, row_w)
        measured_rows.append(m_prow)

    lebar_banner = 0.0
    lebar_banner_kiri = 0.0
    tinggi_banner = 0
    if banner:
        teks_atas, teks_kiri, teks_kanan = banner
        lebar_banner_kiri = _lebar_teks(teks_kiri, f_banner) + round(58 * sc)
        lebar_banner_kanan = _lebar_teks(teks_kanan, f_banner) + round(58 * sc)
        lebar_banner = max(
            lebar_banner_kiri + lebar_banner_kanan,
            _lebar_teks(teks_atas, f_banner) + round(58 * sc),
        )
        tinggi_banner = int(round(88 * sc))

    lebar_judul = max(_lebar_teks(judul, f_judul), _lebar_teks(sub_judul, f_sub))
    lebar_catatan = max((_lebar_teks(t, f_cat) for t in catatan), default=0.0)
    lebar_isi = int(math.ceil(max(
        max_row_w,
        lebar_judul + (lebar_banner + round(60 * sc) if banner else 0),
        lebar_catatan,
    )))

    # Samakan lebar setiap baris panel agar tepi kiri-kanan sejajar sempurna
    for m_prow in measured_rows:
        n_p = len(m_prow)
        avail_w = lebar_isi - p_gap * max(0, n_p - 1)
        sum_nat = sum(mp["w_nat"] for mp in m_prow) or 1.0
        scale = avail_w / sum_nat
        x_cur = m_px
        used_w = 0
        for idx_p, mp in enumerate(m_prow):
            cols_scaled = [int(math.floor(w * scale)) for w in mp["lebar_kol"]]
            target_pw = (avail_w - used_w) if idx_p == n_p - 1 else sum(cols_scaled)
            diff = target_pw - sum(cols_scaled)
            if diff != 0 and cols_scaled:
                widest_idx = max(range(len(cols_scaled)), key=lambda idx: cols_scaled[idx])
                cols_scaled[widest_idx] += diff
            mp["col_w_int"] = cols_scaled
            mp["pw"] = sum(cols_scaled)
            mp["x0"] = x_cur
            x_cur += mp["pw"] + p_gap
            used_w += mp["pw"]

    tinggi_blok_judul = max(int(round(96 * sc)), tinggi_banner) + int(round(28 * sc))
    tinggi_semua_panel = sum(max(mp["tinggi_tab"] for mp in m_prow) for m_prow in measured_rows)
    tinggi_semua_panel += r_gap * max(0, len(measured_rows) - 1)
    tinggi_catatan = (len(catatan) * int(round(32 * sc)) + int(round(24 * sc))) if catatan else 0

    bar_top = int(round(12 * sc))
    lebar_img = lebar_isi + 2 * m_px
    tinggi_img = m_px + bar_top + tinggi_blok_judul + tinggi_semua_panel + tinggi_catatan + m_px

    img = Image.new("RGB", (lebar_img, tinggi_img), "white")
    d = ImageDraw.Draw(img)

    # Aksen navy atas, judul & banner
    d.rectangle([0, 0, lebar_img, bar_top], fill=WARNA_NAVY)
    y0 = m_px + bar_top
    d.text((m_px, y0), judul, font=f_judul, fill=WARNA_TEKS, anchor="la")
    d.text((m_px, y0 + int(round(62 * sc))), sub_judul, font=f_sub, fill=WARNA_TEKS_REDUP, anchor="la")

    if banner:
        teks_atas, teks_kiri, teks_kanan = banner
        bx1 = m_px + lebar_isi
        bx0 = int(bx1 - lebar_banner)
        bxm = int(bx0 + lebar_banner_kiri)
        bh_top = int(round(42 * sc))
        bw_line = max(1, int(round(2 * sc)))
        d.rectangle([bx0, y0, bx1, y0 + bh_top], fill=WARNA_MAROON, outline="#4a1525", width=bw_line)
        _tulis(d, (bx0, y0, bx1, y0 + bh_top), teks_atas, f_banner, "white")
        d.rectangle([bx0, y0 + bh_top, bxm, y0 + tinggi_banner], fill=WARNA_MAROON, outline="#993355", width=bw_line)
        d.rectangle([bxm, y0 + bh_top, bx1, y0 + tinggi_banner], fill=WARNA_MAROON, outline="#993355", width=bw_line)
        _tulis(d, (bx0, y0 + bh_top, bxm, y0 + tinggi_banner), teks_kiri, f_banner, "white")
        _tulis(d, (bxm, y0 + bh_top, bx1, y0 + tinggi_banner), teks_kanan, f_banner, "#fde047")

    # Gambar semua baris panel
    def _draw_tulis(kotak, txt, font_u, warna_u, rata_u="c"):
        x0, y_a, x1, y_b = kotak
        lines = str(txt).split("\n")
        tb = _ukuran_font(font_u) * 1.18
        yy = (y_a + y_b) / 2 - (tb * len(lines)) / 2 + tb / 2
        for b in lines:
            if rata_u == "l":
                d.text((x0 + pad_s, yy), b, font=font_u, fill=warna_u, anchor="lm")
            elif rata_u == "r":
                d.text((x1 - pad_s, yy), b, font=font_u, fill=warna_u, anchor="rm")
            else:
                d.text(((x0 + x1) / 2, yy), b, font=font_u, fill=warna_u, anchor="mm")
            yy += tb

    bw_inner = max(1, int(round(sc)))
    bw_outer = max(2, int(round(3 * sc)))
    y_row = y0 + tinggi_blok_judul
    for m_prow in measured_rows:
        row_max_h = max(mp["tinggi_tab"] for mp in m_prow)
        for mp in m_prow:
            p = mp["spec"]
            x_left = mp["x0"]
            pw = mp["pw"]
            col_w = mp["col_w_int"]
            kolom = p["columns"]
            baris = p["rows"]
            n_kol = len(kolom)
            rata = p.get("align") or ["c"] * n_kol
            gaya_baris = p.get("row_styles") or [None] * len(baris)
            gaya_sel = p.get("cell_style")
            grup_header = p.get("group_headers") or []
            head_bg = p.get("head_bg", WARNA_NAVY)
            sec_title = p.get("section_title", "")
            sec_bg = p.get("section_bg", head_bg)

            y_cur = y_row
            if sec_title:
                d.rectangle([x_left, y_cur, x_left + pw, y_cur + mp["tinggi_sec"]], fill=sec_bg)
                _draw_tulis((x_left, y_cur, x_left + pw, y_cur + mp["tinggi_sec"]), sec_title, f_sec, "white", "l")
                y_cur += mp["tinggi_sec"]

            y_tab = y_cur
            xs = [x_left]
            for w in col_w:
                xs.append(xs[-1] + w)

            kolom_bergrup: set[int] = set()
            kolom_bg_head: dict[int, str] = {}
            for grp in grup_header:
                if len(grp) >= 4:
                    label, a, b, bg_grp = grp[0], grp[1], grp[2], grp[3]
                else:
                    label, a, b, bg_grp = grp[0], grp[1], grp[2], head_bg
                kolom_bergrup.update(range(a, b + 1))
                for c_idx in range(a, b + 1):
                    kolom_bg_head[c_idx] = bg_grp
                kotak = (xs[a], y_tab, xs[b + 1], y_tab + mp["tinggi_grup"])
                d.rectangle(kotak, fill=bg_grp, outline=WARNA_GARIS_HEAD, width=bw_inner)
                _draw_tulis(kotak, label, f_grup, "white")

            for c in range(n_kol):
                bg_h = kolom_bg_head.get(c, head_bg)
                if c in kolom_bergrup:
                    kotak = (xs[c], y_tab + mp["tinggi_grup"], xs[c + 1], y_tab + mp["tinggi_grup"] + mp["tinggi_head"])
                else:
                    kotak = (xs[c], y_tab, xs[c + 1], y_tab + mp["tinggi_grup"] + mp["tinggi_head"])
                d.rectangle(kotak, fill=bg_h, outline=WARNA_GARIS_HEAD, width=bw_inner)
                _draw_tulis(kotak, kolom[c], f_head, "white")

            y = y_tab + mp["tinggi_grup"] + mp["tinggi_head"]
            for i_baris, isi in enumerate(baris):
                gb = gaya_baris[i_baris] or {}
                bg_baris = gb.get("bg", WARNA_SELANG if i_baris % 2 else "white")
                for c in range(n_kol):
                    gs = (gaya_sel(i_baris, c, isi[c]) if gaya_sel else None) or {}
                    bg = gs.get("bg", bg_baris)
                    fg = gs.get("fg", gb.get("fg", WARNA_TEKS))
                    tebal = gs.get("bold", gb.get("bold", False))
                    kotak = (xs[c], y, xs[c + 1], y + row_h)
                    d.rectangle(kotak, fill=bg, outline=WARNA_GARIS, width=bw_inner)
                    _draw_tulis(kotak, isi[c], f_sel_tebal if tebal else f_sel, fg, gs.get("rata", rata[c]))
                y += row_h

            d.rectangle([x_left, y_tab, xs[-1], y], outline=head_bg, width=bw_outer)
        y_row += row_max_h + r_gap

    # Catatan kaki
    if catatan:
        y_cat = y_row - r_gap + int(round(24 * sc))
        step_cat = int(round(32 * sc))
        for teks in catatan:
            d.text((m_px, y_cat), teks, font=f_cat, fill=WARNA_TEKS_REDUP, anchor="la")
            y_cat += step_cat

    buffer = io.BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


# =============================================================================
# PANEL BUILDER UNTUK KOMPOSIT RINGKASAN, WO & TIM LEADER
# =============================================================================


def _spec_mtd_sa(
    df_mtd_final: pd.DataFrame,
    kol_oct: str,
    kol_nov: str,
    kol_gap: str,
    hari_berjalan: int,
    kode_bln_lalu: str,
    kode_bln_ini: str,
) -> dict:
    kolom = ["SALES LEADER", f"SA {kode_bln_lalu}\n1-{hari_berjalan}", f"SA {kode_bln_ini}\n1-{hari_berjalan}", "GAP SA"]
    baris, gaya = [], []
    tot_oct = tot_nov = 0
    for _, r in df_mtd_final.iterrows():
        nama = str(r["SALES LEADER"]).strip()
        if nama.upper() == "TOTAL":
            tot_oct, tot_nov = int(r[kol_oct]), int(r[kol_nov])
            baris.append(["Total", _fmt_angka(tot_oct), _fmt_angka(tot_nov), _fmt_angka(r[kol_gap])])
            gaya.append({"bg": WARNA_TOTAL_MTD, "bold": True})
        else:
            baris.append([nama, _fmt_angka(r[kol_oct]), _fmt_angka(r[kol_nov]), _fmt_angka(r[kol_gap])])
            gaya.append(None)

    acv = _round_excel(((tot_nov - tot_oct) / float(tot_oct)) * 100.0) if tot_oct > 0 else 0
    baris.append(["Note Acv SA", "", "↓" if acv < 0 else "↑", f"{acv}%"])
    gaya.append({"bg": WARNA_NOTE_MTD, "bold": True})
    idx_total, idx_note = len(baris) - 2, len(baris) - 1

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

    return {
        "section_title": f"1. MTD SA PER LEADER ({kode_bln_lalu} vs {kode_bln_ini} 1-{hari_berjalan})",
        "section_bg": WARNA_NAVY,
        "head_bg": WARNA_NAVY,
        "columns": kolom,
        "rows": baris,
        "align": ["l", "c", "c", "c"],
        "row_styles": gaya,
        "cell_style": gaya_sel,
    }


def _spec_harian_blm_produktif(rows_harian: list[dict], date_label: str) -> dict:
    kolom = ["Sales Leader", "SO / GP", "PAID", "SA", "SO / GP", "PAID", "SA"]
    grup_header = [
        (date_label, 1, 3, "#002060"),
        ("Agent Blm Produktif", 4, 6, "#dc0000"),
    ]
    baris, gaya = [], []
    idx_grand = -1
    for i, r in enumerate(rows_harian):
        is_gt = bool(r.get("is_grand_total")) or str(r.get("leader", "")).lower() == "grand total"
        if is_gt:
            idx_grand = i
        baris.append([
            str(r.get("leader", "")),
            _fmt_angka(r.get("so", 0)),
            _fmt_angka(r.get("paid", 0)),
            _fmt_angka(r.get("sa", 0)),
            _fmt_angka(r.get("blm_so", 0)),
            _fmt_angka(r.get("blm_paid", 0)),
            _fmt_angka(r.get("blm_sa", 0)),
        ])
        gaya.append({"bg": WARNA_NOTE_MTD, "bold": True} if is_gt else None)

    def gaya_sel(i: int, c: int, _teks: str) -> dict | None:
        if i == idx_grand and c in (4, 5, 6):
            return {"bg": "#fce4d6", "fg": "#9a3412", "bold": True}
        return None

    return {
        "section_title": f"1B. REKAP HARIAN ({date_label}) & AGENT BELUM PRODUKTIF",
        "section_bg": "#002060",
        "head_bg": "#002060",
        "columns": kolom,
        "group_headers": grup_header,
        "rows": baris,
        "align": ["l", "c", "c", "c", "c", "c", "c"],
        "row_styles": gaya,
        "cell_style": gaya_sel,
    }


def _spec_wo_ringkasan(wo_summary: dict) -> dict:
    today_lbl = str(wo_summary.get("today_label", ""))
    besok_lbl = str(wo_summary.get("besok_label", ""))
    rows_src = wo_summary.get("leader_summary") or []
    kolom = ["SALES LEADER", "TOTAL\nTODAY", "SA\n(ACTIVE)", "ON\nINSTALL", f"TOTAL\n({besok_lbl})", "ON\nINSTALL", "WAIT\nWO", "WAITING\nWO"]
    grup_header = [
        (f"1. WO TODAY ({today_lbl})", 1, 3, "#002060"),
        (f"2. WO BESOK ({besok_lbl})", 4, 6, "#065f46"),
        ("3. WAITING WO", 7, 7, "#92400e"),
    ]
    baris, gaya = [], []
    idx_grand = -1
    for r in rows_src:
        is_gt = bool(r.get("is_grand_total")) or str(r.get("leader", "")).strip().lower() == "grand total"
        if is_gt:
            idx_grand = len(baris)
        baris.append([
            str(r.get("leader", "")),
            _fmt_angka(r.get("today_total", 0)),
            _fmt_angka(r.get("today_sa", 0)),
            _fmt_angka(r.get("today_on_installation", 0)),
            _fmt_angka(r.get("wo_besok", 0)),
            _fmt_angka(r.get("besok_on_installation", 0)),
            _fmt_angka(r.get("besok_waiting_wo", 0)),
            _fmt_angka(r.get("waiting_wo", 0)),
        ])
        gaya.append({"bg": "#dbeafe", "bold": True} if is_gt else None)

    def gaya_sel(i: int, c: int, _teks: str) -> dict | None:
        if i == idx_grand:
            return {1: {"bg": "#c9daf8", "fg": "#1e3a8a", "bold": True}, 2: {"bg": "#bbf7d0", "fg": "#14532d", "bold": True}, 4: {"bg": "#d1fae5", "fg": "#065f46", "bold": True}, 7: {"bg": "#fde68a", "fg": "#92400e", "bold": True}}.get(c)
        return {1: {"bg": "#eff6ff", "bold": True}, 2: {"bg": "#f0fdf4", "fg": "#166534", "bold": True}, 4: {"bg": "#ecfdf5", "bold": True}, 7: {"bg": "#fffbeb", "bold": True}}.get(c)

    return {
        "section_title": f"1C. MONITORING WORK ORDER ({today_lbl} | BESOK {besok_lbl} | WAITING WO)",
        "section_bg": "#002060",
        "head_bg": "#002060",
        "columns": kolom,
        "group_headers": grup_header,
        "rows": baris,
        "align": ["l", "c", "c", "c", "c", "c", "c", "c"],
        "row_styles": gaya,
        "cell_style": gaya_sel,
    }


def _spec_wo_pivot_panel(
    rows_slice: list[dict],
    raw_cols: list[str],
    disp_cols: list[str],
    section_title: str,
    head_bg: str,
    rename_active: bool = False,
) -> dict:
    kolom = ["Salesname / Tim", *disp_cols, "Total"]
    idx_sa_col = (1 + disp_cols.index("Active (SA)")) if (rename_active and "Active (SA)" in disp_cols) else -1
    baris, gaya = [], []
    idx_gt = -1
    cur_ldr = None
    for r in rows_slice:
        rt = r.get("row_type", "agent")
        if rt == "agent":
            ldr_cur = str(r.get("leader", ""))
            if ldr_cur != cur_ldr:
                cur_ldr = ldr_cur
                baris.append([f"> {ldr_cur.upper()}", *[""] * (len(raw_cols) + 1)])
                gaya.append({"bg": "#e2e8f0", "fg": "#0f172a", "bold": True})
            gaya.append(None)
            nm_disp = f"   {r.get('salesname', '')}"
        elif rt == "leader_total":
            gaya.append({"bg": "#dbeafe", "bold": True})
            nm_disp = str(r.get("salesname", ""))
        else:
            idx_gt = len(baris)
            gaya.append({"bg": "#fef3c7", "bold": True})
            nm_disp = str(r.get("salesname", ""))

        st_map = r.get("statuses") or {}
        vals = []
        for cn in raw_cols:
            v = int(st_map.get(cn, r.get("total", 0) if len(raw_cols) == 1 and cn == "Waiting WO" else 0))
            vals.append(_fmt_angka(v) if (v > 0 or rt == "grand_total") else "")
        baris.append([nm_disp, *vals, _fmt_angka(r.get("total", 0))])

    def gaya_sel(i: int, c: int, _t: str, ig=idx_gt, nk=len(kolom), isc=idx_sa_col) -> dict | None:
        if gaya[i] and gaya[i].get("bg") == "#e2e8f0":
            return None
        if c == nk - 1:
            return {"bold": True, "bg": "#fef3c7"} if i == ig else {"bold": True}
        if isc >= 0 and c == isc:
            return {"bold": True, "bg": "#bbf7d0" if i == ig else "#f0fdf4", "fg": "#166534"}
        return None

    return {
        "section_title": section_title,
        "section_bg": head_bg,
        "head_bg": head_bg,
        "columns": kolom,
        "rows": baris,
        "align": ["l"] + ["c"] * (len(disp_cols) + 1),
        "row_styles": gaya,
        "cell_style": gaya_sel,
    }


def _spec_detail_leader(
    nama_leader: str,
    grp: pd.DataFrame,
    target_persen_mtd: int,
    hari_berjalan: int,
    total_hari: int,
    kode_bln_ini: str,
) -> dict:
    kolom = [
        "NO", "SALES NAME", "LEVEL", "TARGET\nTOTAL", f"SA\n{kode_bln_ini}", f"PAID\n{kode_bln_ini}",
        "GAP\nSA", "PERSEN-\nTASE", f"RUNRATE\n{total_hari} HARI", "M", "3M", "SEM", "Y",
        f"STATUS vs\nTARGET {target_persen_mtd}%", "PAID\n/ HARI", "SA\n/ HARI",
    ]
    grup_header = [("BREAKDOWN PAKET", 9, 12, WARNA_NAVY), ("KUOTA WAJIB / HARI", 14, 15, WARNA_NAVY)]
    baris, gaya = [], []
    baris_vacant, baris_kurang = set(), set()
    n_kurang = 0

    for no, (_, r) in enumerate(grp.iterrows(), start=1):
        nama = str(r["SALES NAME"]).strip()
        is_vacant = nama.upper() == "VACANT"
        pct = int(r["PERSENTASE_INT"])
        if is_vacant:
            status = "VACANT"
            baris_vacant.add(len(baris))
        elif pct < target_persen_mtd:
            status = f"KURANG -{target_persen_mtd - pct}%"
            n_kurang += 1
            baris_kurang.add(len(baris))
        else:
            status = "AMAN"

        baris.append([
            str(no), nama, str(r["LEVEL"]), _fmt_angka(r["TARGET ALL"]),
            _fmt_angka(r["SA NOV"]), _fmt_angka(r["PAID NOV"]), _fmt_angka(r["GAP SA NOV"]),
            f"{pct}%", _fmt_angka(r["RUNRATE 30 HARI"]), _fmt_angka(r["Monthly"]),
            _fmt_angka(r["3 Monthly"]), _fmt_angka(r["Semesterly"]), _fmt_angka(r["Yearly"]),
            status, _fmt_angka(r["Harus_Paid_Per_Hari_Bulat"]), _fmt_angka(r["Harus_SA_Per_Hari_Bulat"]),
        ])
        gaya.append(None)

    sum_target = int(grp["TARGET ALL"].sum())
    sum_sa = int(grp["SA NOV"].sum())
    pct_ldr = _round_excel((sum_sa / float(sum_target)) * 100.0) if sum_target > 0 else 0
    runrate_ldr = _round_excel((sum_sa * float(total_hari)) / float(max(1, hari_berjalan)))
    baris.append([
        "", f"TOTAL {nama_leader}", "", _fmt_angka(sum_target), _fmt_angka(sum_sa),
        _fmt_angka(grp["PAID NOV"].sum()), _fmt_angka(sum_sa - sum_target), f"{pct_ldr}%",
        _fmt_angka(runrate_ldr), _fmt_angka(grp["Monthly"].sum()), _fmt_angka(grp["3 Monthly"].sum()),
        _fmt_angka(grp["Semesterly"].sum()), _fmt_angka(grp["Yearly"].sum()),
        f"{n_kurang} agen kurang", _fmt_angka(grp["Harus_Paid_Per_Hari_Bulat"].sum()),
        _fmt_angka(grp["Harus_SA_Per_Hari_Bulat"].sum()),
    ])
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

    return {
        "section_title": f"1. DETAIL AGENT MTD, PAKET & KUOTA WAJIB ({nama_leader.upper()})",
        "section_bg": WARNA_NAVY,
        "head_bg": WARNA_NAVY,
        "columns": kolom,
        "group_headers": grup_header,
        "rows": baris,
        "align": ["c", "l"] + ["c"] * (len(kolom) - 2),
        "row_styles": gaya,
        "cell_style": gaya_sel,
    }


def _spec_rincian_harian_agent(agent_details: list[dict], date_label: str) -> dict:
    kolom = ["Salesname", "SO/GP", "PAID", "SA", "Status Harian"]
    baris, gaya = [], []
    sum_so = sum_paid = sum_sa = 0
    cnt_paid_ag = cnt_gp_blm_ag = cnt_tdk_paid_ag = 0
    for ad in agent_details:
        is_vac = bool(ad.get("is_vacant"))
        so_v, paid_v, sa_v = int(ad.get("so", 0)), int(ad.get("paid", 0)), int(ad.get("sa", 0))
        sum_so += so_v
        sum_paid += paid_v
        sum_sa += sa_v
        if not is_vac:
            if paid_v > 0:
                cnt_paid_ag += 1
            else:
                cnt_tdk_paid_ag += 1
                if so_v > 0:
                    cnt_gp_blm_ag += 1
        st_bersih = str(ad.get("status_harian", "")).replace("✅", "").replace("💳", "").replace("❌", "").replace("⏳", "").strip()
        st_bersih = re.sub(r"\s{2,}", " ", st_bersih)
        baris.append([str(ad.get("name", "")), _fmt_angka(so_v), _fmt_angka(paid_v), _fmt_angka(sa_v), st_bersih])
        gaya.append({"bg": WARNA_VACANT, "bold": True} if is_vac else None)

    baris.append([
        f"TOTAL ({len(agent_details)} slot)",
        _fmt_angka(sum_so),
        _fmt_angka(sum_paid),
        _fmt_angka(sum_sa),
        f"PAID:{cnt_paid_ag} | GP:{cnt_gp_blm_ag} | Tdk:{cnt_tdk_paid_ag}",
    ])
    gaya.append({"bg": WARNA_TOTAL_MTD, "bold": True})
    idx_tot = len(baris) - 1

    def gaya_sel(i: int, c: int, teks: str) -> dict | None:
        if i == idx_tot or c != 4:
            return None
        if "Sudah PAID" in teks:
            return {"bg": WARNA_HIJAU_BG, "fg": WARNA_HIJAU_TX, "bold": True}
        if "Sudah GP" in teks:
            return {"bg": WARNA_KUOTA_BG, "fg": WARNA_KUOTA_TX, "bold": True}
        if "Tidak PAID" in teks:
            return {"bg": WARNA_MERAH_BG, "fg": WARNA_MERAH_TX, "bold": True}
        return None

    return {
        "section_title": f"2. RINCIAN HARIAN ({date_label}) | PAID:{cnt_paid_ag} GP:{cnt_gp_blm_ag} Tdk:{cnt_tdk_paid_ag}",
        "section_bg": "#002060",
        "head_bg": "#002060",
        "columns": kolom,
        "rows": baris,
        "align": ["l", "c", "c", "c", "l"],
        "row_styles": gaya,
        "cell_style": gaya_sel,
    }


def _spec_wo_tim_leader(ldr: str, grp_wo: list[dict], today_lbl: str, besok_lbl: str) -> dict:
    kolom = ["NO", "SALESNAME", "TOT", "SA", "OI", f"{besok_lbl}", "OI", "WT", "WAIT"]
    grup_header = [
        (f"TODAY ({today_lbl})", 2, 4, "#002060"),
        (f"BESOK ({besok_lbl})", 5, 7, "#065f46"),
        ("WAIT", 8, 8, "#92400e"),
    ]
    baris, gaya = [], []
    s_tot = s_sa = s_on = s_bsk = s_bon = s_bwt = s_wwo = 0
    for no, r in enumerate(grp_wo, start=1):
        c_tot = int(r.get("today_total", 0))
        c_sa = int(r.get("today_sa", 0))
        c_on = int(r.get("today_on_installation", 0))
        c_bsk = int(r.get("wo_besok", 0))
        c_bon = int(r.get("besok_on_installation", 0))
        c_bwt = int(r.get("besok_waiting_wo", 0))
        c_wwo = int(r.get("waiting_wo", 0))
        s_tot += c_tot; s_sa += c_sa; s_on += c_on
        s_bsk += c_bsk; s_bon += c_bon; s_bwt += c_bwt; s_wwo += c_wwo
        baris.append([
            str(no), str(r.get("salesname", "")),
            _fmt_angka(c_tot), _fmt_angka(c_sa) if c_sa else "-", _fmt_angka(c_on) if c_on else "-",
            _fmt_angka(c_bsk), _fmt_angka(c_bon) if c_bon else "-", _fmt_angka(c_bwt) if c_bwt else "-",
            _fmt_angka(c_wwo),
        ])
        gaya.append(None)

    idx_tot = len(baris)
    baris.append(["", f"TOTAL {ldr}", _fmt_angka(s_tot), _fmt_angka(s_sa), _fmt_angka(s_on), _fmt_angka(s_bsk), _fmt_angka(s_bon), _fmt_angka(s_bwt), _fmt_angka(s_wwo)])
    gaya.append({"bg": "#dbeafe", "bold": True})

    def gaya_sel(i: int, c: int, _t: str) -> dict | None:
        if c == 2:
            return {"bg": "#c9daf8", "fg": "#1e3a8a", "bold": True} if i == idx_tot else {"bg": "#eff6ff", "bold": True}
        if c == 3:
            return {"bg": "#bbf7d0", "fg": "#14532d", "bold": True} if i == idx_tot else {"bg": "#f0fdf4", "fg": "#166534", "bold": True}
        if c == 5:
            return {"bg": "#d1fae5", "fg": "#065f46", "bold": True} if i == idx_tot else {"bg": "#ecfdf5", "bold": True}
        if c == 8:
            return {"bg": "#fde68a", "fg": "#92400e", "bold": True} if i == idx_tot else {"bg": "#fffbeb", "bold": True}
        return None

    return {
        "section_title": f"3. MONITORING WO TIM (Today:{s_tot} SA:{s_sa} | Besok:{s_bsk} | Wait:{s_wwo})",
        "section_bg": "#065f46",
        "head_bg": "#065f46",
        "columns": kolom,
        "group_headers": grup_header,
        "rows": baris,
        "align": ["c", "l", "c", "c", "c", "c", "c", "c", "c"],
        "row_styles": gaya,
        "cell_style": gaya_sel,
    }


# =============================================================================
# RENDERER GABUNGAN EKSEKUTIF, WO SUPER-HD, TIM LEADER & KARTU AGENT
# =============================================================================


def buat_gambar_ringkasan_eksekutif(
    df_mtd_final: pd.DataFrame,
    kol_oct: str,
    kol_nov: str,
    kol_gap: str,
    hari_berjalan: int,
    kode_bln_lalu: str,
    kode_bln_ini: str,
    tahun: int,
    daily_prod_rows: list[dict] | None = None,
    daily_date_label: str = "",
    wo_summary: dict | None = None,
) -> bytes:
    """Menggabungkan MTD SA, Rekap Harian Blm Produktif, dan Ringkasan WO ke dalam 1 gambar Super-HD."""
    top_row = [_spec_mtd_sa(df_mtd_final, kol_oct, kol_nov, kol_gap, hari_berjalan, kode_bln_lalu, kode_bln_ini)]
    if daily_prod_rows:
        top_row.append(_spec_harian_blm_produktif(daily_prod_rows, daily_date_label))

    panel_rows = [top_row]
    catatan = [
        f"GAP SA = SA {kode_bln_ini} - SA {kode_bln_lalu}. SO/GP = Sales Order / Generate Payment pada {daily_date_label}.",
    ]
    if wo_summary and wo_summary.get("leader_summary"):
        panel_rows.append([_spec_wo_ringkasan(wo_summary)])
        t_lbl = str(wo_summary.get("today_label", ""))
        b_lbl = str(wo_summary.get("besok_label", ""))
        catatan.append(
            f"1. WO TODAY ({t_lbl}): On Installation + Active(SA) | 2. WO BESOK ({b_lbl}): Instalasi Date = H+1 | 3. WAITING WO: Instalasi Blank bln aktif."
        )

    waktu = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
    catatan.append(f"Dibuat otomatis Super-HD: {waktu}")
    return render_komposit_png(
        judul=f"RINGKASAN EKSEKUTIF LAPORAN ({hari_berjalan}-{kode_bln_ini}-{tahun})",
        sub_judul=f"Gabungan MTD SA (1-{hari_berjalan} {kode_bln_lalu} vs {kode_bln_ini}) • Rekap Harian & Agent Blm Produktif" + (" • Monitoring Work Order" if len(panel_rows) > 1 else ""),
        panel_rows=panel_rows,
        catatan=catatan,
        hd_scale=1.45,
    )


def buat_gambar_wo_today_detail(wo_summary: dict) -> bytes:
    """Merender Pivot 1. WO TODAY ke layout multi-kolom (2-3 kolom sejajar) agar Super-HD & tajam di WA."""
    today_lbl = str(wo_summary.get("today_label", ""))
    src = wo_summary.get("wo_today_rows") or []
    raw_cols = list(wo_summary.get("wo_today_columns") or [])
    disp_cols = ["Active (SA)" if c.lower() == "active" else c for c in raw_cols]
    n_non_gt = sum(1 for r in src if r.get("row_type") != "grand_total")
    n_kol = 3 if n_non_gt > 54 else (2 if n_non_gt > 20 else 1)
    slices = _partisi_blok_wo(src, n_kol)

    panels = [
        _spec_wo_pivot_panel(
            sl, raw_cols, disp_cols,
            f"BAGIAN {idx + 1}/{len(slices)}" if len(slices) > 1 else f"1. WO TODAY ({today_lbl})",
            "#002060", rename_active=True,
        )
        for idx, sl in enumerate(slices)
    ]
    tot = wo_summary.get("wo_today_totals") or {}
    oth = wo_summary.get("wo_today_other_statuses") or {}
    oth_txt = (" | Status Lain: " + ", ".join(f"{k}: {v}" for k, v in oth.items())) if oth else ""
    waktu = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
    return render_komposit_png(
        judul=f"1. WO TODAY ({today_lbl}) — ON INSTALLATION & ACTIVE (SA)",
        sub_judul=f"Grand Total: {int(tot.get('total', 0))} Customer  •  SA (Active): {int(tot.get('sa', 0))}  •  On Installation: {int(tot.get('on_installation', 0))}{oth_txt}",
        panel_rows=[panels] if panels else [],
        catatan=[f"Total seluruh baris Tim & Agent: {len(src)} baris ditampilkan sejajar ({len(slices)} kolom Super-HD) | {waktu}"],
        hd_scale=1.25 if n_kol >= 2 else 1.5,
    )


def buat_gambar_wo_besok_waiting(wo_summary: dict, include_ringkasan: bool = False) -> bytes:
    """Menggabungkan Ringkasan WO (opsional) + 2. WO BESOK + 3. WAITING WO ke 1 gambar Super-HD."""
    today_lbl = str(wo_summary.get("today_label", ""))
    besok_lbl = str(wo_summary.get("besok_label", ""))
    panel_rows: list[list[dict]] = []

    if include_ringkasan and wo_summary.get("leader_summary"):
        panel_rows.append([_spec_wo_ringkasan(wo_summary)])

    bot_panels: list[dict] = []
    besok_src = wo_summary.get("wo_besok_rows") or []
    if besok_src:
        raw_b = list(wo_summary.get("wo_besok_columns") or [])
        n_b_non_gt = sum(1 for r in besok_src if r.get("row_type") != "grand_total")
        n_b_kol = 2 if n_b_non_gt > 22 else 1
        b_slices = _partisi_blok_wo(besok_src, n_b_kol)
        for idx, sl in enumerate(b_slices):
            ttl = f"2. WO BESOK ({besok_lbl}) — BAG. {idx + 1}/{len(b_slices)}" if len(b_slices) > 1 else f"2. WO BESOK ({besok_lbl})"
            bot_panels.append(_spec_wo_pivot_panel(sl, raw_b, raw_b, ttl, "#065f46"))

    wait_src = wo_summary.get("waiting_wo_rows") or []
    if wait_src:
        raw_w = list(wo_summary.get("waiting_wo_columns") or ["Waiting WO"])
        bot_panels.append(
            _spec_wo_pivot_panel(wait_src, raw_w, raw_w, "3. WAITING WO (INSTALASI BLANK)", "#92400e")
        )

    if bot_panels:
        panel_rows.append(bot_panels)

    bsk_tot = int(wo_summary.get("wo_besok_total", 0))
    wait_tot = int(wo_summary.get("waiting_wo_total", 0))
    waktu = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
    judul = f"MONITORING WO: RINGKASAN, BESOK ({besok_lbl}) & WAITING WO" if include_ringkasan else f"2. WO BESOK ({besok_lbl}) & 3. WAITING WO (GABUNGAN)"
    return render_komposit_png(
        judul=judul,
        sub_judul=f"WO Besok H+1 ({besok_lbl}): {bsk_tot} Customer  •  Waiting WO (Instalasi Blank, Status Back To Sales/READY/Reschedule/Waiting WO bln aktif): {wait_tot} Customer",
        panel_rows=panel_rows,
        catatan=[f"Seluruh tabel Besok & Waiting WO digabung dalam 1 lembar Super-HD agar tetap tajam di WhatsApp & Telegram | {waktu}"],
        hd_scale=1.25,
    )


def buat_gambar_laporan_tim(
    nama_leader: str,
    grp_agent: pd.DataFrame,
    target_persen_mtd: int,
    hari_berjalan: int,
    total_hari: int,
    sisa_hari: int,
    nama_bln_tampil: str,
    kode_bln_ini: str,
    tahun: int,
    rasio_paid: float,
    agent_details_harian: list[dict] | None = None,
    daily_date_label: str = "",
    wo_tim_agents: list[dict] | None = None,
    today_lbl: str = "",
    besok_lbl: str = "",
) -> bytes:
    """Menggabungkan Detail Agent MTD + Rincian Harian Agent + Monitoring WO Tim Leader dalam 1 gambar."""
    panel_rows = [[
        _spec_detail_leader(nama_leader, grp_agent, target_persen_mtd, hari_berjalan, total_hari, kode_bln_ini)
    ]]
    bottom_row: list[dict] = []
    if agent_details_harian:
        bottom_row.append(_spec_rincian_harian_agent(agent_details_harian, daily_date_label))
    if wo_tim_agents:
        bottom_row.append(_spec_wo_tim_leader(nama_leader, wo_tim_agents, today_lbl, besok_lbl))
    if bottom_row:
        panel_rows.append(bottom_row)

    n_agen = int((grp_agent["SALES NAME"].astype(str).str.upper() != "VACANT").sum())
    n_kurang = int(((grp_agent["SALES NAME"].astype(str).str.upper() != "VACANT") & (grp_agent["PERSENTASE_INT"] < target_persen_mtd)).sum())
    waktu = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
    return render_komposit_png(
        judul=f"LAPORAN LENGKAP TIM {nama_leader.upper()}",
        sub_judul=f"MTD 1-{hari_berjalan} {nama_bln_tampil} {tahun} (Sisa {sisa_hari}H)  •  {n_kurang} dari {n_agen} agen < target {target_persen_mtd}%  •  Detail MTD + Harian + WO",
        panel_rows=panel_rows,
        banner=("TARGET", f"{hari_berjalan}-{nama_bln_tampil}-{tahun}", f"{target_persen_mtd}%"),
        catatan=[
            f"PERSENTASE = SA ÷ Target Total. PAID/HARI mencakup buffer Paid→SA ({rasio_paid:.2f}x). RUNRATE = ROUND(SA × {total_hari} ÷ {hari_berjalan}).",
            f"Gabungan Detail MTD, Rincian Harian (SO=GP) & Monitoring WO Tim {nama_leader} | {waktu}",
        ],
        hd_scale=1.35,
    )


def buat_gambar_wo_kartu_agent(ag_row: dict, today_lbl: str, besok_lbl: str) -> bytes:
    """Merender kartu foto PNG Super-HD individual untuk 1 Agent."""
    sn = str(ag_row.get("salesname", "-"))
    ldr = str(ag_row.get("leader", "-"))
    tot_i, sa_i, on_i = int(ag_row.get("today_total", 0)), int(ag_row.get("today_sa", 0)), int(ag_row.get("today_on_installation", 0))
    bsk, bon, bwt = int(ag_row.get("wo_besok", 0)), int(ag_row.get("besok_on_installation", 0)), int(ag_row.get("besok_waiting_wo", 0))
    wwo = int(ag_row.get("waiting_wo", 0))

    def gaya_sel(_i: int, c: int, _t: str) -> dict | None:
        return {
            1: {"bg": "#dbeafe", "fg": "#1e3a8a", "bold": True},
            2: {"bg": "#bbf7d0", "fg": "#14532d", "bold": True},
            4: {"bg": "#dcfce7", "fg": "#065f46", "bold": True},
            7: {"bg": "#fef3c7", "fg": "#92400e", "bold": True},
        }.get(c)

    panel = {
        "head_bg": "#002060",
        "columns": ["SALESNAME", "TOTAL TODAY", "SA (ACTIVE)", "ON INSTALL", f"BESOK ({besok_lbl})", "BESOK OI", "BESOK WAIT", "WAITING WO"],
        "group_headers": [
            (f"1. WO TODAY ({today_lbl})", 1, 3, "#002060"),
            (f"2. WO BESOK ({besok_lbl})", 4, 6, "#065f46"),
            ("3. WAITING WO", 7, 7, "#92400e"),
        ],
        "rows": [[sn, _fmt_angka(tot_i), _fmt_angka(sa_i), _fmt_angka(on_i), _fmt_angka(bsk), _fmt_angka(bon), _fmt_angka(bwt), _fmt_angka(wwo)]],
        "align": ["l", "c", "c", "c", "c", "c", "c", "c"],
        "row_styles": [{"bg": "#ffffff", "bold": True}],
        "cell_style": gaya_sel,
    }
    return render_komposit_png(
        judul=f"KARTU WO AGENT — {sn.upper()}",
        sub_judul=f"Sales Leader: {ldr}  •  WO Today: {today_lbl}  •  WO Besok: {besok_lbl}",
        panel_rows=[[panel]],
        catatan=[f"Kartu Monitoring WO Pribadi — {sn} ({ldr})"],
        hd_scale=1.5,
    )


def buat_semua_gambar_wo(
    wo_summary: dict,
    include_detail: bool = True,
    include_kartu_agent: bool = False,
) -> list[tuple[str, bytes, str]]:
    """Menyusun paket gambar WO gabungan Super-HD (Ringkasan+Besok+Waiting dan Today 3-kolom)."""
    if not wo_summary or not wo_summary.get("leader_summary"):
        return []
    today_lbl = str(wo_summary.get("today_label", ""))
    besok_lbl = str(wo_summary.get("besok_label", ""))
    tot_map = wo_summary.get("wo_today_totals") or {}
    hasil: list[tuple[str, bytes, str]] = [
        (
            f"01C_Monitoring_WO_Gabungan_{today_lbl}.png",
            buat_gambar_wo_besok_waiting(wo_summary, include_ringkasan=True),
            f"🛠️ <b>Ringkasan WO, Besok ({_escape_html(besok_lbl)}) &amp; Waiting WO</b> | Besok: {int(wo_summary.get('wo_besok_total', 0))} | Waiting: {int(wo_summary.get('waiting_wo_total', 0))}",
        )
    ]
    if include_detail and wo_summary.get("wo_today_rows"):
        hasil.append((
            f"02A_WO_TODAY_Detail_{today_lbl}.png",
            buat_gambar_wo_today_detail(wo_summary),
            f"1️⃣ <b>WO TODAY ({_escape_html(today_lbl)}) — Total {int(tot_map.get('total', 0))} (SA {int(tot_map.get('sa', 0))})</b>",
        ))
    if include_kartu_agent:
        for ag in wo_summary.get("agent_summary") or []:
            sn = str(ag.get("salesname", "-"))
            ldr = str(ag.get("leader", "-"))
            safe_sn = re.sub(r"[^A-Za-z0-9]+", "_", sn).strip("_")
            hasil.append((
                f"01E_WO_Agent_{safe_sn}.png",
                buat_gambar_wo_kartu_agent(ag, today_lbl, besok_lbl),
                f"👤 <b>Kartu WO — {_escape_html(sn)}</b> ({_escape_html(ldr)}) | Today: {int(ag.get('today_total', 0))} (SA: {int(ag.get('today_sa', 0))}) | Besok ({_escape_html(besok_lbl)}): {int(ag.get('wo_besok', 0))} | Waiting: {int(ag.get('waiting_wo', 0))}",
            ))
    return hasil


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
    """Menghasilkan daftar gambar gabungan Super-HD (Ringkasan Eksekutif + WO Detail + Gabungan per Tim)."""
    hasil: list[tuple[str, bytes, str]] = []
    lbl_dl = daily_prod_date_label or f"{hari_berjalan}-{nama_bln_tampil}-{str(tahun)[-2:]}"

    # 1. GABUNGAN RINGKASAN EKSEKUTIF (MTD SA + Rekap Harian + Ringkasan WO)
    hasil.append((
        f"01_Ringkasan_Eksekutif_1-{hari_berjalan}_{kode_bln_ini}_{tahun}.png",
        buat_gambar_ringkasan_eksekutif(
            df_mtd_final=df_mtd_final, kol_oct=kol_oct, kol_nov=kol_nov, kol_gap=kol_gap,
            hari_berjalan=hari_berjalan, kode_bln_lalu=kode_bln_lalu, kode_bln_ini=kode_bln_ini, tahun=tahun,
            daily_prod_rows=daily_prod_rows, daily_date_label=lbl_dl,
            wo_summary=wo_summary if (wo_summary and wo_summary.get("leader_summary")) else None,
        ),
        f"📊 <b>Ringkasan Eksekutif (MTD 1-{hari_berjalan} {kode_bln_ini}, Rekap Harian {lbl_dl} &amp; Monitoring WO)</b>",
    ))

    # 2. WO DETAIL SUPER-HD (1. WO TODAY multi-kolom + 2/3. WO BESOK & WAITING WO gabungan)
    if wo_summary and wo_summary.get("leader_summary") and include_wo_detail:
        today_lbl = str(wo_summary.get("today_label", ""))
        besok_lbl = str(wo_summary.get("besok_label", ""))
        tot_map = wo_summary.get("wo_today_totals") or {}
        if wo_summary.get("wo_today_rows"):
            hasil.append((
                f"02A_WO_TODAY_Detail_{today_lbl}.png",
                buat_gambar_wo_today_detail(wo_summary),
                f"1️⃣ <b>WO TODAY ({_escape_html(today_lbl)}) — Total {int(tot_map.get('total', 0))} (SA {int(tot_map.get('sa', 0))})</b>",
            ))
        if wo_summary.get("wo_besok_rows") or wo_summary.get("waiting_wo_rows"):
            hasil.append((
                f"02B_WO_BESOK_dan_WAITING_{today_lbl}.png",
                buat_gambar_wo_besok_waiting(wo_summary, include_ringkasan=False),
                f"2️⃣3️⃣ <b>WO BESOK ({_escape_html(besok_lbl)}: {int(wo_summary.get('wo_besok_total', 0))}) &amp; WAITING WO ({int(wo_summary.get('waiting_wo_total', 0))})</b>",
            ))

    # 3. GABUNGAN PER TIM LEADER (Detail Agent MTD + Rincian Harian + Monitoring WO Tim)
    harian_by_ldr = {
        str(r.get("leader", "")): list(r.get("agent_details") or [])
        for r in (daily_prod_rows or [])
        if not r.get("is_grand_total") and r.get("agent_details")
    }
    wo_by_ldr: dict[str, list[dict]] = {}
    today_wo_lbl = str((wo_summary or {}).get("today_label", ""))
    besok_wo_lbl = str((wo_summary or {}).get("besok_label", ""))
    for wag in (wo_summary or {}).get("agent_summary") or []:
        wo_by_ldr.setdefault(str(wag.get("leader", "")), []).append(wag)

    df_valid = df_agent[
        ~df_agent["SALES NAME"].astype(str).str.strip().str.upper().isin(["", "NAN", "NONE", "TOTAL", "-"])
    ]
    for no, (nama_ldr, grp) in enumerate(df_valid.groupby("SALES LEADER", sort=False), start=1):
        if grp.empty:
            continue
        ldr_str = str(nama_ldr)
        safe_ldr = re.sub(r"[^A-Za-z0-9]+", "_", ldr_str).strip("_")
        png_tim = buat_gambar_laporan_tim(
            nama_leader=ldr_str, grp_agent=grp, target_persen_mtd=target_persen_mtd,
            hari_berjalan=hari_berjalan, total_hari=total_hari, sisa_hari=sisa_hari,
            nama_bln_tampil=nama_bln_tampil, kode_bln_ini=kode_bln_ini, tahun=tahun, rasio_paid=rasio_paid,
            agent_details_harian=harian_by_ldr.get(ldr_str), daily_date_label=lbl_dl,
            wo_tim_agents=wo_by_ldr.get(ldr_str), today_lbl=today_wo_lbl, besok_lbl=besok_wo_lbl,
        )
        hasil.append((
            f"03_{no:02d}_Laporan_Tim_{safe_ldr}.png",
            png_tim,
            f"📋 <b>Laporan Lengkap Tim {_escape_html(ldr_str)}</b> | {hari_berjalan}-{nama_bln_tampil}-{tahun} | Target MTD {target_persen_mtd}%",
        ))

    if wo_summary and include_wo_agent_cards:
        for ag in wo_summary.get("agent_summary") or []:
            sn = str(ag.get("salesname", "-"))
            ldr = str(ag.get("leader", "-"))
            safe_sn = re.sub(r"[^A-Za-z0-9]+", "_", sn).strip("_")
            hasil.append((
                f"01E_WO_Agent_{safe_sn}.png",
                buat_gambar_wo_kartu_agent(ag, today_wo_lbl, besok_wo_lbl),
                f"👤 <b>Kartu WO — {_escape_html(sn)}</b> ({_escape_html(ldr)})",
            ))
    return hasil
