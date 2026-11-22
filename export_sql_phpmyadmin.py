"""Generator File SQL Database (MySQL / MariaDB - cPanel phpMyAdmin Compatible)

Menghasilkan:
1. database_komisi_telesales.sql : File SQL lengkap (siap di-Import di phpMyAdmin cPanel).
2. query_phpmyadmin_cepat.sql    : Query SQL ringkas untuk Copy-Paste ke tab SQL phpMyAdmin.

Catatan Keamanan:
- Tidak menyimpan password plaintext di file SQL maupun GitHub; seluruh akun di `users_multi_role`
  menggunakan ID Role terbaru (`sa_yovi_2026`, `fin_oxygen26`, `ldr_*`, `agt_*`) & hash terenkripsi.
"""

import logging
import math
import os
import warnings
import pandas as pd

warnings.filterwarnings("ignore")
logging.disable(logging.WARNING)

import app as modul_app
import security_firewall as sf

FOLDER_PROYEK = os.path.dirname(os.path.abspath(__file__))
PATH_SQL_FULL = os.path.join(FOLDER_PROYEK, "database_komisi_telesales.sql")
PATH_SQL_CEPAT = os.path.join(FOLDER_PROYEK, "query_phpmyadmin_cepat.sql")


def sql_str(val: object) -> str:
    """Escape nilai string agar aman untuk sintaks MySQL/MariaDB."""
    if val is None or (isinstance(val, float) and math.isnan(val)) or pd.isna(val):
        return "NULL"
    teks = str(val).strip()
    teks = (
        teks.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\r", " ")
        .replace("\n", " ")
    )
    return f"'{teks}'"


def sql_num(val: object, is_float: bool = False) -> str:
    """Konversi nilai numerik untuk sintaks SQL."""
    if val is None or pd.isna(val):
        return "0"
    try:
        if is_float:
            return f"{float(val):.2f}"
        return str(int(round(float(val))))
    except Exception:
        return "0"


def generate_sql_files() -> None:
    df_mtd_final = modul_app.df_mtd_final.copy()
    df_agent = modul_app.df_agent.copy()
    df_leader_komisi = getattr(modul_app, "df_leader_komisi", pd.DataFrame())
    df_mtd_ini = modul_app.df_mtd_ini.copy()
    daily_prod_rows = list(getattr(modul_app, "daily_prod_rows", []))
    daily_prod_label = str(getattr(modul_app, "daily_prod_date_label", "22-Nov-26"))
    wo_summary = dict(getattr(modul_app, "wo_summary", {}) or {})
    kol_oct = modul_app.kol_sa_oct
    kol_nov = modul_app.kol_sa_nov
    kol_gap = modul_app.kol_gap_sa
    hari_berjalan = int(modul_app.hari_berjalan_int)
    kode_bln = str(modul_app.kode_bln_ini)
    tahun_int = int(modul_app.tahun_int)

    # 1. Susun Data Users Multi-Role (HANYA Hash PBKDF2/SHA-256 — TANPA Plaintext!)
    cfg_sa = sf.muat_config_superadmin() or {"username": "sa_yovi_2026", "hash": "PBKDF2_PROTECTED"}
    cfg_roles = sf.muat_config_roles() or {}
    rows_users = [
        (cfg_sa["username"], f"pbkdf2_sha256${cfg_sa.get('iterations', 200000)}${cfg_sa.get('hash', '')[:32]}...", "Admin", "Yovi Arian (Super Admin)", "Semua Leader"),
    ]
    fin = cfg_roles.get("finance", {})
    if fin:
        rows_users.append((fin.get("username", "fin_oxygen26"), str(fin.get("hash", "")), "Finance", "Divisi Finance & Komisi", "Semua Leader"))

    for u_ldr, meta_l in sorted(cfg_roles.get("leaders", {}).items()):
        rows_users.append((u_ldr, str(meta_l.get("hash", "")), "Leader", str(meta_l.get("leader", "")), str(meta_l.get("leader", ""))))

    for u_ag, meta_a in sorted(cfg_roles.get("agen_accounts", {}).items()):
        rows_users.append((u_ag, str(meta_a.get("hash", "")), "Agen", str(meta_a.get("name", "")), str(meta_a.get("leader", ""))))

    periode_mtd_str = f"1-{hari_berjalan} {kode_bln.title()} {tahun_int}"

    lines = [
        "-- ============================================================================",
        "-- DATABASE SQL DUMP: SISTEM KOMISI & MONITORING PERFORMA TELESALES ISP",
        "-- Kompatibel 100% dengan MySQL / MariaDB (cPanel phpMyAdmin)",
        "-- Kredensial hanya disimpan dalam bentuk hash kriptografis (Zero Plaintext).",
        "-- ============================================================================",
        "",
        "SET SQL_MODE = \"NO_AUTO_VALUE_ON_ZERO\";",
        "START TRANSACTION;",
        "SET time_zone = \"+07:00\";",
        "SET NAMES utf8mb4;",
        "",
        "-- ----------------------------------------------------------------------------",
        "-- 1. TABEL: users_multi_role (Akun Baru Super Admin, Finance, Leader, Agen)",
        "-- ----------------------------------------------------------------------------",
        "DROP TABLE IF EXISTS `users_multi_role`;",
        "CREATE TABLE `users_multi_role` (",
        "  `id` int(11) NOT NULL AUTO_INCREMENT,",
        "  `username` varchar(60) NOT NULL,",
        "  `password_hash` varchar(128) NOT NULL,",
        "  `role` enum('Admin','Leader','Agen','Finance') NOT NULL,",
        "  `display_name` varchar(120) NOT NULL,",
        "  `leader_scope` varchar(120) NOT NULL,",
        "  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,",
        "  PRIMARY KEY (`id`),",
        "  UNIQUE KEY `uk_username` (`username`)",
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;",
        "",
        "INSERT INTO `users_multi_role` (`username`, `password_hash`, `role`, `display_name`, `leader_scope`) VALUES",
    ]

    val_users = [
        f"({sql_str(u)}, {sql_str(h)}, {sql_str(rl)}, {sql_str(dn)}, {sql_str(sc)})"
        for u, h, rl, dn, sc in rows_users
    ]
    lines.append(",\n".join(val_users) + ";\n")

    lines.extend(
        [
            "-- ----------------------------------------------------------------------------",
            "-- 2. TABEL: rekap_mtd_sa_leader (Perbandingan SA Bulan Lalu vs Bulan Ini)",
            "-- ----------------------------------------------------------------------------",
            "DROP TABLE IF EXISTS `rekap_mtd_sa_leader`;",
            "CREATE TABLE `rekap_mtd_sa_leader` (",
            "  `id` int(11) NOT NULL AUTO_INCREMENT,",
            "  `sales_leader` varchar(120) NOT NULL,",
            "  `periode_mtd` varchar(30) NOT NULL,",
            "  `sa_oct_mtd` int(11) NOT NULL DEFAULT 0,",
            "  `sa_nov_mtd` int(11) NOT NULL DEFAULT 0,",
            "  `gap_sa` int(11) NOT NULL DEFAULT 0,",
            "  PRIMARY KEY (`id`)",
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;",
            "",
            "INSERT INTO `rekap_mtd_sa_leader` (`sales_leader`, `periode_mtd`, `sa_oct_mtd`, `sa_nov_mtd`, `gap_sa`) VALUES",
        ]
    )

    val_mtd = [
        f"({sql_str(r['SALES LEADER'])}, {sql_str(periode_mtd_str)}, {sql_num(r[kol_oct])}, {sql_num(r[kol_nov])}, {sql_num(r[kol_gap])})"
        for _, r in df_mtd_final.iterrows()
    ]
    lines.append(",\n".join(val_mtd) + ";\n")

    if daily_prod_rows:
        lines.extend(
            [
                "-- ----------------------------------------------------------------------------",
                "-- 2B. TABEL: rekap_harian_blm_produktif (SO/PAID/SA Harian & Agent Blm Produktif)",
                "-- ----------------------------------------------------------------------------",
                "DROP TABLE IF EXISTS `rekap_harian_blm_produktif`;",
                "CREATE TABLE `rekap_harian_blm_produktif` (",
                "  `id` int(11) NOT NULL AUTO_INCREMENT,",
                "  `tanggal_label` varchar(30) NOT NULL,",
                "  `sales_leader` varchar(120) NOT NULL,",
                "  `harian_so` int(11) NOT NULL DEFAULT 0,",
                "  `harian_gp` int(11) NOT NULL DEFAULT 0,",
                "  `harian_paid` int(11) NOT NULL DEFAULT 0,",
                "  `harian_sa` int(11) NOT NULL DEFAULT 0,",
                "  `blm_produktif_so` int(11) NOT NULL DEFAULT 0,",
                "  `blm_produktif_paid` int(11) NOT NULL DEFAULT 0,",
                "  `blm_produktif_sa` int(11) NOT NULL DEFAULT 0,",
                "  PRIMARY KEY (`id`)",
                ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;",
                "",
                "INSERT INTO `rekap_harian_blm_produktif` (`tanggal_label`, `sales_leader`, `harian_so`, `harian_gp`, `harian_paid`, `harian_sa`, `blm_produktif_so`, `blm_produktif_paid`, `blm_produktif_sa`) VALUES",
            ]
        )
        val_dp = [
            f"({sql_str(daily_prod_label)}, {sql_str(r['leader'])}, {sql_num(r['so'])}, {sql_num(r.get('gp', 0))}, {sql_num(r['paid'])}, {sql_num(r['sa'])}, {sql_num(r['blm_so'])}, {sql_num(r['blm_paid'])}, {sql_num(r['blm_sa'])})"
            for r in daily_prod_rows
        ]
        lines.append(",\n".join(val_dp) + ";\n")

    wo_sum_rows = list(wo_summary.get("leader_summary", []))
    if wo_sum_rows:
        wo_t_lbl = str(wo_summary.get("today_label", ""))
        wo_b_lbl = str(wo_summary.get("besok_label", ""))
        lines.extend(
            [
                "-- ----------------------------------------------------------------------------",
                "-- 2C. TABEL: rekap_wo_monitoring (WO TODAY | WAITING WO | WO BESOK)",
                "-- ----------------------------------------------------------------------------",
                "DROP TABLE IF EXISTS `rekap_wo_monitoring`;",
                "CREATE TABLE `rekap_wo_monitoring` (",
                "  `id` int(11) NOT NULL AUTO_INCREMENT,",
                "  `tgl_wo_today` varchar(30) NOT NULL,",
                "  `tgl_wo_besok` varchar(30) NOT NULL,",
                "  `sales_leader` varchar(120) NOT NULL,",
                "  `today_on_installation` int(11) NOT NULL DEFAULT 0,",
                "  `today_refund` int(11) NOT NULL DEFAULT 0,",
                "  `today_waiting_wo` int(11) NOT NULL DEFAULT 0,",
                "  `today_total` int(11) NOT NULL DEFAULT 0,",
                "  `waiting_wo` int(11) NOT NULL DEFAULT 0,",
                "  `wo_besok` int(11) NOT NULL DEFAULT 0,",
                "  PRIMARY KEY (`id`)",
                ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;",
                "",
                "INSERT INTO `rekap_wo_monitoring` (`tgl_wo_today`, `tgl_wo_besok`, `sales_leader`, `today_on_installation`, `today_refund`, `today_waiting_wo`, `today_total`, `waiting_wo`, `wo_besok`) VALUES",
            ]
        )
        val_wo = [
            f"({sql_str(wo_t_lbl)}, {sql_str(wo_b_lbl)}, {sql_str(r['leader'])}, {sql_num(r['today_on_installation'])}, {sql_num(r['today_refund'])}, {sql_num(r['today_waiting_wo'])}, {sql_num(r['today_total'])}, {sql_num(r['waiting_wo'])}, {sql_num(r['wo_besok'])})"
            for r in wo_sum_rows
        ]
        lines.append(",\n".join(val_wo) + ";\n")

    lines.extend(
        [
            "-- ----------------------------------------------------------------------------",
            "-- 3. TABEL: detail_komisi_dan_kuota_agen (Detail Performa, Kuota Harian & Komisi)",
            "-- ----------------------------------------------------------------------------",
            "DROP TABLE IF EXISTS `detail_komisi_dan_kuota_agen`;",
            "CREATE TABLE `detail_komisi_dan_kuota_agen` (",
            "  `id` int(11) NOT NULL AUTO_INCREMENT,",
            "  `sales_leader` varchar(120) NOT NULL,",
            "  `sales_name` varchar(120) NOT NULL,",
            "  `masa_kerja` varchar(60) NOT NULL,",
            "  `level_agen` varchar(40) NOT NULL,",
            "  `target_all` int(11) NOT NULL DEFAULT 0,",
            "  `target_reguler` int(11) NOT NULL DEFAULT 0,",
            "  `target_yearly` int(11) NOT NULL DEFAULT 0,",
            "  `sa_nov` int(11) NOT NULL DEFAULT 0,",
            "  `paid_nov` int(11) NOT NULL DEFAULT 0,",
            "  `so_nov` int(11) NOT NULL DEFAULT 0,",
            "  `gap_sa_nov` int(11) NOT NULL DEFAULT 0,",
            "  `persentase_capai` int(11) NOT NULL DEFAULT 0,",
            "  `status_persentase_mtd` varchar(100) NOT NULL,",
            "  `harus_paid_per_hari` int(11) NOT NULL DEFAULT 0,",
            "  `harus_sa_per_hari` int(11) NOT NULL DEFAULT 0,",
            "  `harus_sa_per_hari_desimal` decimal(8,2) NOT NULL DEFAULT 0.00,",
            "  `harus_so_per_hari` int(11) NOT NULL DEFAULT 0,",
            "  `daily_paid_normal` int(11) NOT NULL DEFAULT 0,",
            "  `runrate_30_hari` int(11) NOT NULL DEFAULT 0,",
            "  `paket_3_monthly` int(11) NOT NULL DEFAULT 0,",
            "  `paket_monthly` int(11) NOT NULL DEFAULT 0,",
            "  `paket_semesterly` int(11) NOT NULL DEFAULT 0,",
            "  `paket_yearly` int(11) NOT NULL DEFAULT 0,",
            "  `revenue_kotor` decimal(16,2) NOT NULL DEFAULT 0.00,",
            "  `revenue_netto_ppn11` decimal(16,2) NOT NULL DEFAULT 0.00,",
            "  `tier_komisi` varchar(40) NOT NULL,",
            "  `estimasi_komisi` decimal(16,2) NOT NULL DEFAULT 0.00,",
            "  PRIMARY KEY (`id`),",
            "  KEY `idx_leader` (`sales_leader`),",
            "  KEY `idx_sales_name` (`sales_name`)",
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;",
            "",
            "INSERT INTO `detail_komisi_dan_kuota_agen` (`sales_leader`, `sales_name`, `masa_kerja`, `level_agen`, `target_all`, `target_reguler`, `target_yearly`, `sa_nov`, `paid_nov`, `so_nov`, `gap_sa_nov`, `persentase_capai`, `status_persentase_mtd`, `harus_paid_per_hari`, `harus_sa_per_hari`, `harus_sa_per_hari_desimal`, `harus_so_per_hari`, `daily_paid_normal`, `runrate_30_hari`, `paket_3_monthly`, `paket_monthly`, `paket_semesterly`, `paket_yearly`, `revenue_kotor`, `revenue_netto_ppn11`, `tier_komisi`, `estimasi_komisi`) VALUES",
        ]
    )

    val_agen = []
    for _, r in df_agent.iterrows():
        pct_i = int(r["PERSENTASE_INT"])
        status_mtd_str = (
            f"MASIH KURANG ({pct_i}% < {modul_app.target_persen_mtd}%)"
            if pct_i < modul_app.target_persen_mtd
            else f"ON-TRACK ({pct_i}% >= {modul_app.target_persen_mtd}%)"
        )
        tier_str = str(r.get("Tier_Komisi", "Tier 0 (0%)"))
        val_agen.append(
            "("
            + ", ".join(
                [
                    sql_str(r["SALES LEADER"]),
                    sql_str(r["SALES NAME"]),
                    sql_str(r["MASA KERJA"]),
                    sql_str(r["LEVEL"]),
                    sql_num(r["TARGET ALL"]),
                    sql_num(r["Target Reguler"]),
                    sql_num(r["Target Yearly"]),
                    sql_num(r["SA NOV"]),
                    sql_num(r["PAID NOV"]),
                    sql_num(r["SO NOV"]),
                    sql_num(r["GAP SA NOV"]),
                    sql_num(pct_i),
                    sql_str(status_mtd_str),
                    sql_num(r["Harus_Paid_Per_Hari_Bulat"]),
                    sql_num(r["Harus_SA_Per_Hari_Bulat"]),
                    sql_num(r["Harus_SA_Per_Hari_Desimal"], is_float=True),
                    sql_num(r["Harus_SO_Per_Hari_Bulat"]),
                    sql_num(r["Daily Paid Normal"]),
                    sql_num(r["RUNRATE 30 HARI"]),
                    sql_num(r["3 Monthly"]),
                    sql_num(r["Monthly"]),
                    sql_num(r["Semesterly"]),
                    sql_num(r["Yearly"]),
                    sql_num(r["Total_Revenue"], is_float=True),
                    sql_num(r["Revenue_Netto"], is_float=True),
                    sql_str(tier_str),
                    sql_num(r["Estimasi_Komisi_Num"], is_float=True),
                ]
            )
            + ")"
        )
    lines.append(",\n".join(val_agen) + ";\n")

    if df_leader_komisi is not None and not df_leader_komisi.empty:
        lines.extend(
            [
                "-- ----------------------------------------------------------------------------",
                "-- 3B. TABEL: komisi_sales_leader (Insentif Resmi Sales Leader Excl. PPn 11%)",
                "-- ----------------------------------------------------------------------------",
                "DROP TABLE IF EXISTS `komisi_sales_leader`;",
                "CREATE TABLE `komisi_sales_leader` (",
                "  `id` int(11) NOT NULL AUTO_INCREMENT,",
                "  `sales_leader` varchar(120) NOT NULL,",
                "  `sa_tim` int(11) NOT NULL DEFAULT 0,",
                "  `rev_fp_tim` decimal(16,2) NOT NULL DEFAULT 0.00,",
                "  `tier_komisi` varchar(40) NOT NULL,",
                "  `insentif_leader` decimal(16,2) NOT NULL DEFAULT 0.00,",
                "  `total_komisi_agen` decimal(16,2) NOT NULL DEFAULT 0.00,",
                "  `total_komisi_tim` decimal(16,2) NOT NULL DEFAULT 0.00,",
                "  PRIMARY KEY (`id`)",
                ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;",
                "",
                "INSERT INTO `komisi_sales_leader` (`sales_leader`, `sa_tim`, `rev_fp_tim`, `tier_komisi`, `insentif_leader`, `total_komisi_agen`, `total_komisi_tim`) VALUES",
            ]
        )
        val_ldr = [
            f"({sql_str(lr['leader'])}, {sql_num(lr['sa_tim'])}, {sql_num(lr['rev_fp_tim'], is_float=True)}, {sql_str(lr['tier_komisi'])}, {sql_num(lr['insentif_leader'], is_float=True)}, {sql_num(lr['total_komisi_agen'], is_float=True)}, {sql_num(lr['total_komisi_tim'], is_float=True)})"
            for _, lr in df_leader_komisi.iterrows()
        ]
        lines.append(",\n".join(val_ldr) + ";\n")

    lines_cepat = list(lines) + ["COMMIT;\n"]
    with open(PATH_SQL_CEPAT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines_cepat))

    # 4. Tambahkan tabel transaksi_prospect_november ke file SQL Full
    lines.extend(
        [
            "-- ----------------------------------------------------------------------------",
            "-- 4. TABEL: transaksi_prospect_november (Data Realisasi Active SA November 2026)",
            "-- ----------------------------------------------------------------------------",
            "DROP TABLE IF EXISTS `transaksi_prospect_november`;",
            "CREATE TABLE `transaksi_prospect_november` (",
            "  `id` int(11) NOT NULL AUTO_INCREMENT,",
            "  `sales_leader` varchar(120) DEFAULT NULL,",
            "  `sales_name` varchar(120) DEFAULT NULL,",
            "  `customer_name` varchar(180) DEFAULT NULL,",
            "  `package_name` varchar(180) DEFAULT NULL,",
            "  `tipe_paket` varchar(40) DEFAULT NULL,",
            "  `status_payment` varchar(40) DEFAULT NULL,",
            "  `service_price` decimal(16,2) NOT NULL DEFAULT 0.00,",
            "  `created_date` date DEFAULT NULL,",
            "  `payment_date` date DEFAULT NULL,",
            "  `active_date` date DEFAULT NULL,",
            "  PRIMARY KEY (`id`),",
            "  KEY `idx_active_date` (`active_date`),",
            "  KEY `idx_leader_nov` (`sales_leader`)",
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;",
            "",
        ]
    )

    if not df_mtd_ini.empty:
        batch_size = 250
        records_nov = []
        for _, r in df_mtd_ini.iterrows():
            c_dt = pd.to_datetime(r.get("Created Date"), errors="coerce")
            p_dt = pd.to_datetime(r.get("Payment Date"), errors="coerce")
            a_dt = pd.to_datetime(r.get("Active Date"), errors="coerce")
            records_nov.append(
                "("
                + ", ".join(
                    [
                        sql_str(r.get("Sales Leader", "")),
                        sql_str(r.get("Salesname", "")),
                        sql_str(r.get("Customer Name", r.get("Full Name", ""))),
                        sql_str(r.get("Service Package", r.get("Package Name", ""))),
                        sql_str(r.get("Tipe Paket", "Monthly")),
                        sql_str(r.get("Status Payment", "PAID")),
                        sql_num(r.get("Service Price", 0), is_float=True),
                        sql_str(c_dt.strftime("%Y-%m-%d")) if pd.notna(c_dt) else "NULL",
                        sql_str(p_dt.strftime("%Y-%m-%d")) if pd.notna(p_dt) else "NULL",
                        sql_str(a_dt.strftime("%Y-%m-%d")) if pd.notna(a_dt) else "NULL",
                    ]
                )
                + ")"
            )
        for i in range(0, len(records_nov), batch_size):
            chunk = records_nov[i : i + batch_size]
            lines.append(
                "INSERT INTO `transaksi_prospect_november` (`sales_leader`, `sales_name`, `customer_name`, `package_name`, `tipe_paket`, `status_payment`, `service_price`, `created_date`, `payment_date`, `active_date`) VALUES\n"
                + ",\n".join(chunk)
                + ";\n"
            )

    lines.append("COMMIT;\n")
    with open(PATH_SQL_FULL, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(
        f"SUCCESS_SQL:\n"
        f"- {PATH_SQL_FULL} ({os.path.getsize(PATH_SQL_FULL):,} bytes | {len(rows_users)} users, {len(df_mtd_final)} baris MTD, {len(daily_prod_rows)} baris Harian, {len(df_agent)} baris Detail Agent, {len(df_mtd_ini)} transaksi SA)\n"
        f"- {PATH_SQL_CEPAT} ({os.path.getsize(PATH_SQL_CEPAT):,} bytes)"
    )


if __name__ == "__main__":
    generate_sql_files()
