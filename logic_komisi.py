import io
import os
import re
import pandas as pd

NAMA_BULAN_ID = {
    1: "JANUARI",
    2: "FEBRUARI",
    3: "MARET",
    4: "APRIL",
    5: "MEI",
    6: "JUNI",
    7: "JULI",
    8: "AGUSTUS",
    9: "SEPTEMBER",
    10: "OKTOBER",
    11: "NOVEMBER",
    12: "DESEMBER",
}

TIM_ALPHA_WOLF_SET = {
    "ASKIH MILLI PRIYANTO",
    "DWI AFRIYANI",
    "SISCA PERMATA SUCY",
    "SANDRA MONICA",
    "DIANA YASMIN",
    "ANDRI DARMAWAN",
    "YAYANG ARDI PURNAMA",
    "ANISA RAHMAWATI",
    "ALI YUSUP RAMADHAN",
    "NAFFA DESTIANA PUTRI",
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
    "NAFA DESTIANA PUTRI": "NAFFA DESTIANA PUTRI",
    "PUNGKAS MUGO PRAKSOSO": "PUNGKAS MUGO PRAKOSO",
    "DENY R HIDAYAT": "DENY RAHMAT HIDAYAT",
    "DEFA DELVIANTY": "DEFA DELVIANTHY",
    "RIZKI DWI PUJI ASTUTI": "RIZKY DWI PUJI ASTUTI",
    "DEWI RATANASARI": "DEWI RATNASARI",
    "KHAIRANNY": "KHAIRRANY",
}


def bersihkan_nama(nama: object) -> str:
    """Membersihkan spasi berlebih, karakter tak terlihat, serta menyamakan variasi nama agen."""
    if pd.isna(nama):
        return ""
    teks = str(nama)
    teks = re.sub(r"[\u200b-\u200f\u2060\ufeff]", "", teks)
    teks = re.sub(r"\s+", " ", teks).strip().upper()
    return ALIAS_NAMA_AGEN.get(teks, teks)


def normalisasi_nama_leader(teks_raw: object) -> str:
    """Merapikan nama Team Leader di kolom TEAM pada file TARGET PER MONTH.xlsx.

    Contoh: 'A N I S' -> 'ANIS', 'F A H R U L' -> 'FAHRUL', 'YOVI' -> 'YOVI'.
    """
    if pd.isna(teks_raw):
        return ""
    teks = str(teks_raw).strip()
    if not teks:
        return ""
    bagian = teks.split()
    if len(bagian) > 1 and all(len(b) == 1 for b in bagian):
        return "".join(bagian).upper()
    return re.sub(r"\s+", " ", teks).strip().upper()


def baca_file_excel_fleksibel(
    sumber_file, sheet_name: str | int = 0
) -> pd.DataFrame:
    """Membaca file Excel (.xlsx/.xls) dari path maupun UploadedFile Streamlit.

    Mendukung:
    1. File Excel standar menggunakan pd.read_excel()
    2. File .xls yang berisi tabel HTML hasil ekspor CRM (seperti list_prospect *.xls)
    """
    try:
        if isinstance(sumber_file, str):
            with open(sumber_file, "rb") as f:
                raw_bytes = f.read()
        else:
            sumber_file.seek(0)
            raw_bytes = sumber_file.read()
            sumber_file.seek(0)

        awal = raw_bytes[:512].lstrip().lower()
        if (
            awal.startswith(b"<table")
            or awal.startswith(b"<html")
            or awal.startswith(b"<!doctype")
        ):
            html_text = raw_bytes.decode("utf-8", errors="ignore")
            baris_html = re.findall(
                r"<tr[^>]*>(.*?)</tr>", html_text, flags=re.S | re.I
            )
            baris_terurai = []
            for baris in baris_html:
                kolom = [
                    re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", sel)).strip()
                    for sel in re.findall(
                        r"<t[dh][^>]*>(.*?)</t[dh]>", baris, flags=re.S | re.I
                    )
                ]
                if kolom:
                    baris_terurai.append(kolom)

            if not baris_terurai:
                raise ValueError("File HTML (.xls) tidak memiliki tabel data yang valid.")

            header = baris_terurai[0]
            data = [r for r in baris_terurai[1:] if len(r) == len(header)]
            return pd.DataFrame(data, columns=header)

        return pd.read_excel(io.BytesIO(raw_bytes), sheet_name=sheet_name)
    except Exception:
        if not isinstance(sumber_file, str):
            sumber_file.seek(0)
        return pd.read_excel(sumber_file, sheet_name=sheet_name)


def normalisasi_df_penjualan(df: pd.DataFrame) -> pd.DataFrame:
    """Menyeragamkan nama kolom DataFrame Penjualan."""
    pemetaan_kolom = {}
    for kol in df.columns:
        kol_bersih = str(kol).strip()
        if kol_bersih in ("Active Date", "Active_Date"):
            pemetaan_kolom[kol] = "Active_Date"
        elif kol_bersih in ("Salesname", "Nama Agen", "Nama_Agen"):
            pemetaan_kolom[kol] = "Nama_Agen"
        elif kol_bersih in ("Sales Leader", "Nama Leader", "Nama_Leader"):
            pemetaan_kolom[kol] = "Nama_Leader"
        elif kol_bersih == "Harga_Layanan":
            pemetaan_kolom[kol] = "Harga_Layanan"

    df = df.rename(columns=pemetaan_kolom)

    if "Harga_Layanan" not in df.columns:
        if "Amount" in df.columns:
            df["Harga_Layanan"] = df["Amount"]
        elif "Service Price" in df.columns:
            df["Harga_Layanan"] = df["Service Price"]

    return df


def siapkan_df_target(
    sumber_target,
    bulan_aktif: int | None = None,
    tahun_aktif: int | None = None,
    jenis_target: str = "REGULER",
) -> pd.DataFrame:
    """Membaca dan menormalisasi Data Target Agen beserta Nama_Leader dari TARGET PER MONTH.xlsx.

    Selalu mengembalikan DataFrame dengan kolom lengkap:
    ['Nama_Leader', 'Level_Agen', 'Nama_Agen', 'Target_Bulan_Ini', 'Target_Reguler', 'Target_KPI']
    """
    df_awal = baca_file_excel_fleksibel(sumber_target)

    # 1. Jika file target sudah berbentuk tabel datar standar (seperti data_target.xlsx)
    kolom_standar = {str(k).strip(): k for k in df_awal.columns}
    if "Nama_Agen" in kolom_standar and "Target_Bulan_Ini" in kolom_standar:
        rename_map = {
            kolom_standar["Nama_Agen"]: "Nama_Agen",
            kolom_standar["Target_Bulan_Ini"]: "Target_Bulan_Ini",
        }
        if "Nama_Leader" in kolom_standar:
            rename_map[kolom_standar["Nama_Leader"]] = "Nama_Leader"
        elif "TEAM" in kolom_standar:
            rename_map[kolom_standar["TEAM"]] = "Nama_Leader"
        if "Level_Agen" in kolom_standar:
            rename_map[kolom_standar["Level_Agen"]] = "Level_Agen"
        elif "LEVEL" in kolom_standar:
            rename_map[kolom_standar["LEVEL"]] = "Level_Agen"

        df_awal = df_awal.rename(columns=rename_map)
        df_awal["Nama_Agen"] = df_awal["Nama_Agen"].apply(bersihkan_nama)

        if "Nama_Leader" not in df_awal.columns:
            df_awal["Nama_Leader"] = df_awal["Nama_Agen"].apply(
                lambda n: "YOVI" if n in TIM_ALPHA_WOLF_SET else "SEMUA TIM"
            )
        if "Level_Agen" not in df_awal.columns:
            df_awal["Level_Agen"] = "-"
        df_awal["Target_Reguler"] = df_awal["Target_Bulan_Ini"]
        df_awal["Target_KPI"] = df_awal["Target_Bulan_Ini"]
        return df_awal[
            [
                "Nama_Leader",
                "Level_Agen",
                "Nama_Agen",
                "Target_Bulan_Ini",
                "Target_Reguler",
                "Target_KPI",
            ]
        ].copy()

    # 2. Jika berupa workbook multi-sheet seperti 'TARGET PER MONTH.xlsx'
    if isinstance(sumber_target, str):
        xl = pd.ExcelFile(sumber_target)
    else:
        sumber_target.seek(0)
        xl = pd.ExcelFile(io.BytesIO(sumber_target.read()))
        sumber_target.seek(0)

    sheet_terpilih = None
    if bulan_aktif is not None and tahun_aktif is not None:
        nama_bulan_str = NAMA_BULAN_ID.get(int(bulan_aktif), "")
        tahun_2digit = str(tahun_aktif)[-2:]

        for s in xl.sheet_names:
            s_upper = s.upper().strip()
            if (
                "ACHIEVEMENT" in s_upper
                or "PERFORMANCE" in s_upper
                or "SCHEDULE" in s_upper
            ):
                continue
            if nama_bulan_str in s_upper and tahun_2digit in s_upper:
                sheet_terpilih = s
                break
            if (
                int(bulan_aktif) == 8
                and "AGUTUS" in s_upper
                and tahun_2digit in s_upper
            ):
                sheet_terpilih = s
                break

    if sheet_terpilih is None:
        kandidat_sheet = [
            s
            for s in xl.sheet_names
            if not s.upper().startswith("SHEET")
            and "ACHIEVEMENT" not in s.upper()
            and "PERFORMANCE" not in s.upper()
            and "SCHEDULE" not in s.upper()
            and "NO NAME" not in s.upper()
        ]
        sheet_terpilih = kandidat_sheet[-1] if kandidat_sheet else xl.sheet_names[-1]

    df_sheet = pd.read_excel(xl, sheet_name=sheet_terpilih)

    # Ekstrak blok TEAM (Nama_Leader), LEVEL, NAMA (Nama_Agen), REGULER, dan TARGET KPI
    if df_sheet.shape[1] >= 7:
        data_agen = []
        abaikan_nama = {
            "",
            "NAN",
            "NAMA",
            "TOTAL",
            "VACANT",
            "1 BULAN",
            "2 BULAN",
            "3 BULAN",
            "> 3 BULAN",
            "> 6 BULAN",
            "> 9 BULAN",
        }

        curr_leader = ""
        in_team_block = False

        for _, row in df_sheet.iterrows():
            c0 = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
            c2 = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""
            c3 = str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else ""

            # Deteksi awal tabel blok tim (Baris header 'TEAM | ... | LEVEL | NAMA')
            if c0.upper() == "TEAM" and c3.upper() == "NAMA":
                in_team_block = True
                curr_leader = ""
                continue

            if not in_team_block:
                continue

            # Deteksi akhir blok tim (Baris 'TOTAL')
            if (
                c0.upper() == "TOTAL"
                or c3.upper() == "TOTAL"
                or "TARGET " in c2.upper()
            ):
                in_team_block = False
                continue

            # Tangkap nama Leader dari kolom pertama (TEAM) pada baris pertama blok
            if c0 and c0.upper() not in ("NAN", "TEAM", "TOTAL"):
                curr_leader = normalisasi_nama_leader(c0)

            nama_bersih = bersihkan_nama(c3)
            if not nama_bersih or nama_bersih in abaikan_nama:
                continue

            target_reguler = pd.to_numeric(row.iloc[4], errors="coerce")
            target_yearly = pd.to_numeric(row.iloc[5], errors="coerce")
            target_kpi = pd.to_numeric(row.iloc[6], errors="coerce")

            reg_val = float(target_reguler) if pd.notna(target_reguler) else 0.0
            yr_val = float(target_yearly) if pd.notna(target_yearly) else 0.0
            c2_upper = c2.upper().strip() if c2 else "-"
            if c2_upper == "PROBATION III" and int(round(reg_val)) == 33:
                reg_val = 38.0
            elif c2_upper == "PROBATION II" and int(round(reg_val)) == 23:
                reg_val = 32.0 if "DENSON" in c3.upper() else 33.0
            target_total = reg_val + yr_val

            # Pilih nilai target utama berdasarkan parameter jenis_target
            if "KPI" in str(jenis_target).upper():
                nilai_target = (
                    target_kpi if pd.notna(target_kpi) else target_total
                )
            else:
                nilai_target = (
                    target_total if target_total > 0 else target_kpi
                )

            if pd.notna(nilai_target) and float(nilai_target) > 0:
                data_agen.append(
                    {
                        "Nama_Leader": curr_leader
                        if curr_leader
                        else "TANPA LEADER",
                        "Level_Agen": c2.upper() if c2 else "-",
                        "Nama_Agen": nama_bersih,
                        "Target_Bulan_Ini": int(round(float(nilai_target))),
                        "Target_Reguler": int(round(reg_val))
                        if reg_val > 0
                        else int(round(float(nilai_target))),
                        "Target_Yearly": int(round(yr_val)),
                        "Target_KPI": int(round(float(target_kpi)))
                        if pd.notna(target_kpi)
                        else int(round(float(nilai_target))),
                    }
                )

        if data_agen:
            return pd.DataFrame(data_agen).drop_duplicates(
                subset=["Nama_Agen"], keep="first"
            )

    # Fallback aman: pastikan kolom wajib selalu tersedia
    if "Nama_Leader" not in df_awal.columns:
        df_awal["Nama_Leader"] = "YOVI"
    if "Level_Agen" not in df_awal.columns:
        df_awal["Level_Agen"] = "-"
    if "Nama_Agen" not in df_awal.columns:
        df_awal["Nama_Agen"] = ""
    if "Target_Bulan_Ini" not in df_awal.columns:
        df_awal["Target_Bulan_Ini"] = 50
    if "Target_Reguler" not in df_awal.columns:
        df_awal["Target_Reguler"] = df_awal["Target_Bulan_Ini"]
    if "Target_KPI" not in df_awal.columns:
        df_awal["Target_KPI"] = df_awal["Target_Bulan_Ini"]
    return df_awal[
        [
            "Nama_Leader",
            "Level_Agen",
            "Nama_Agen",
            "Target_Bulan_Ini",
            "Target_Reguler",
            "Target_KPI",
        ]
    ].copy()


def hitung_komisi(
    path_data_penjualan: str,
    path_data_target: str,
    bulan_aktif: int,
    tahun_aktif: int,
) -> str:
    """Fungsi perhitungan komisi untuk aplikasi Desktop (main.py)."""
    try:
        if not path_data_penjualan or not os.path.isfile(path_data_penjualan):
            return "Error: File Data Penjualan tidak ditemukan."
        if not path_data_target or not os.path.isfile(path_data_target):
            return "Error: File Data Target Agen tidak ditemukan."

        df_penjualan = normalisasi_df_penjualan(
            baca_file_excel_fleksibel(path_data_penjualan)
        )
        df_target = siapkan_df_target(path_data_target, bulan_aktif, tahun_aktif)

        kolom_wajib_penjualan = {"Active_Date", "Nama_Agen", "Harga_Layanan"}
        if not kolom_wajib_penjualan.issubset(df_penjualan.columns):
            kolom_kurang = kolom_wajib_penjualan - set(df_penjualan.columns)
            return (
                f"Error: Kolom berikut tidak ditemukan di Data Penjualan: "
                f"{', '.join(sorted(kolom_kurang))}"
            )

        kolom_wajib_target = {"Nama_Agen", "Target_Bulan_Ini"}
        if not kolom_wajib_target.issubset(df_target.columns):
            kolom_kurang = kolom_wajib_target - set(df_target.columns)
            return (
                f"Error: Kolom berikut tidak ditemukan di Data Target Agen: "
                f"{', '.join(sorted(kolom_kurang))}"
            )

        df_penjualan["Nama_Agen"] = df_penjualan["Nama_Agen"].apply(bersihkan_nama)
        df_target["Nama_Agen"] = df_target["Nama_Agen"].apply(bersihkan_nama)

        df_penjualan["Active_Date"] = pd.to_datetime(
            df_penjualan["Active_Date"], errors="coerce"
        )
        df_filtered = df_penjualan[
            (df_penjualan["Active_Date"].dt.month == int(bulan_aktif))
            & (df_penjualan["Active_Date"].dt.year == int(tahun_aktif))
            & (df_penjualan["Nama_Agen"] != "")
        ].copy()

        if df_filtered.empty:
            nama_bln = NAMA_BULAN_ID.get(int(bulan_aktif), str(bulan_aktif)).title()
            return (
                f"Error: Tidak ditemukan transaksi dengan Active_Date pada "
                f"periode {nama_bln} ({bulan_aktif}) tahun {tahun_aktif}."
            )

        df_filtered["Harga_Layanan"] = pd.to_numeric(
            df_filtered["Harga_Layanan"], errors="coerce"
        ).fillna(0)
        df_filtered["Harga_Netto"] = df_filtered["Harga_Layanan"] * 0.89

        df_closing = (
            df_filtered.groupby("Nama_Agen", as_index=False)
            .size()
            .rename(columns={"size": "Total_Closing"})
        )

        df_gabungan = pd.merge(
            df_closing,
            df_target[["Nama_Agen", "Target_Bulan_Ini"]],
            on="Nama_Agen",
            how="left",
        )
        df_gabungan["Target_Bulan_Ini"] = pd.to_numeric(
            df_gabungan["Target_Bulan_Ini"], errors="coerce"
        ).fillna(0)

        def hitung_persentase_komisi(row: pd.Series) -> float:
            if (
                row["Target_Bulan_Ini"] > 0
                and row["Total_Closing"] >= row["Target_Bulan_Ini"]
            ):
                return 0.35
            else:
                return 0.20

        df_gabungan["Persentase_Komisi"] = df_gabungan.apply(
            hitung_persentase_komisi, axis=1
        )

        df_detail = pd.merge(
            df_filtered,
            df_gabungan[
                ["Nama_Agen", "Total_Closing", "Target_Bulan_Ini", "Persentase_Komisi"]
            ],
            on="Nama_Agen",
            how="left",
        )
        df_detail["Komisi_Final"] = (
            df_detail["Harga_Netto"] * df_detail["Persentase_Komisi"]
        )

        df_laporan_final = df_detail.groupby(
            ["Nama_Agen", "Total_Closing", "Target_Bulan_Ini", "Persentase_Komisi"],
            as_index=False,
        ).agg(
            Harga_Layanan=("Harga_Layanan", "sum"),
            Harga_Netto=("Harga_Netto", "sum"),
            Komisi_Final=("Komisi_Final", "sum"),
        )

        df_laporan_final = df_laporan_final.sort_values(
            by=["Komisi_Final", "Total_Closing"], ascending=[False, False]
        ).reset_index(drop=True)

        output_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "Laporan_Komisi_Final.xlsx",
        )
        df_laporan_final.to_excel(output_path, index=False)
        return "sukses"

    except PermissionError:
        return (
            "Error: File 'Laporan_Komisi_Final.xlsx' sedang terbuka di Microsoft Excel. "
            "Silakan tutup file tersebut terlebih dahulu."
        )
    except Exception as err:
        return f"Error: {err}"
