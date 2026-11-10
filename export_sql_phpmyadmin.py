"""Generator File SQL Database (MySQL / MariaDB - cPanel phpMyAdmin Compatible)

Menghasilkan:
1. database_komisi_telesales.sql : File SQL lengkap (siap di-Import di phpMyAdmin cPanel kasuari.kencang.com).
2. query_phpmyadmin_cepat.sql    : Query SQL ringkas yang bisa langsung di-Copy-Paste ke tab SQL phpMyAdmin.
"""

import logging
import math
import os
import warnings
import pandas as pd

warnings.filterwarnings("ignore")
logging.disable(logging.WARNING)

import app as modul_app

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
    df_mtd_ini = modul_app.df_mtd_ini.copy()
    kol_oct = modul_app.kol_sa_oct
    kol_nov = modul_app.kol_sa_nov
    kol_gap = modul_app.kol_gap_sa

    # 1. Susun Data Users Multi-Role
    rows_users = [
        ("admin", "admin123", "Admin", "Administrator Operasional", "Semua Leader"),
        ("finance", "finance123", "Finance", "Divisi Finance & Komisi", "Semua Leader"),
    ]
    ldr_added = set()
    for u_ldr, nama_ldr in sorted(modul_app.USERNAME_KE_LEADER.items()):
        if nama_ldr not in ldr_added:
            rows_users.append((u_ldr, "leader123", "Leader", nama_ldr, nama_ldr))
            ldr_added.add(nama_ldr)

    user_added = {r[0] for r in rows_users}
    for _, r in df_agent.iterrows():
        nama_ag = str(r["SALES NAME"]).strip()
        if nama_ag.upper() == "VACANT":
            continue
        u_ag = nama_ag.split()[0].lower()
        if u_ag in user_added:
            u_ag = "".join(ch for ch in nama_ag.lower() if ch.isalnum())[:20]
        user_added.add(u_ag)
        rows_users.append((u_ag, "agen123", "Agen", nama_ag, str(r["SALES LEADER"]).strip()))

    lines = [
        "-- ============================================================================",
        "-- DATABASE SQL DUMP: SISTEM KOMISI & MONITORING PERFORMA TELESALES ISP",
        "-- Kompatibel 100% dengan MySQL / MariaDB (cPanel phpMyAdmin kasuari.kencang.com)",
        "-- ============================================================================",
        "-- CARA PAKAI DI PHPMYADMIN (kasuari.kencang.com):",
        "-- 1. Klik nama Database Anda di panel sebelah kiri phpMyAdmin.",
        "-- 2. Buka tab 'SQL' (atau tab 'Import' / 'Impor').",
        "-- 3. Paste isi file ini (atau upload file database_komisi_telesales.sql) lalu klik 'Kirim' / 'Go'.",
        "-- ============================================================================",
        "",
        "SET SQL_MODE = \"NO_AUTO_VALUE_ON_ZERO\";",
        "START TRANSACTION;",
        "SET time_zone = \"+07:00\";",
        "SET NAMES utf8mb4;",
        "",
        "-- ----------------------------------------------------------------------------",
        "-- 1. TABEL: users_multi_role (Akun Login Admin, Leader, Agen, Finance)",
        "-- ----------------------------------------------------------------------------",
        "DROP TABLE IF EXISTS `users_multi_role`;",
        "CREATE TABLE `users_multi_role` (",
        "  `id` int(11) NOT NULL AUTO_INCREMENT,",
        "  `username` varchar(60) NOT NULL,",
        "  `password_plain` varchar(60) NOT NULL,",
        "  `role` enum('Admin','Leader','Agen','Finance') NOT NULL,",
        "  `display_name` varchar(120) NOT NULL,",
        "  `leader_scope` varchar(120) NOT NULL,",
        "  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,",
        "  PRIMARY KEY (`id`),",
        "  UNIQUE KEY `uk_username` (`username`)",
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;",
        "",
        "INSERT INTO `users_multi_role` (`username`, `password_plain`, `role`, `display_name`, `leader_scope`) VALUES",
    ]

    val_users = [
        f"({sql_str(u)}, {sql_str(p)}, {sql_str(rl)}, {sql_str(dn)}, {sql_str(sc)})"
        for u, p, rl, dn, sc in rows_users
    ]
    lines.append(",\n".join(val_users) + ";\n")

    lines.extend(
        [
            "-- ----------------------------------------------------------------------------",
            "-- 2. TABEL: rekap_mtd_sa_leader (Perbandingan SA OCT 1-8 vs SA NOV 1-8 & GAP SA)",
            "-- ----------------------------------------------------------------------------",
            "DROP TABLE IF EXISTS `rekap_mtd_sa_leader`;",
            "CREATE TABLE `rekap_mtd_sa_leader` (",
            "  `id` int(11) NOT NULL AUTO_INCREMENT,",
            "  `sales_leader` varchar(120) NOT NULL,",
            "  `periode_mtd` varchar(30) NOT NULL DEFAULT '1-8 Nov 2026',",
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
        f"({sql_str(r['SALES LEADER'])}, '1-8 Nov 2026', {sql_num(r[kol_oct])}, {sql_num(r[kol_nov])}, {sql_num(r[kol_gap])})"
        for _, r in df_mtd_final.iterrows()
    ]
    lines.append(",\n".join(val_mtd) + ";\n")

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
        tier_str = (
            "35% (Capai Target)"
            if (int(r["TARGET ALL"]) > 0 and int(r["SA NOV"]) >= int(r["TARGET ALL"]))
            else "20% (Belum Capai)"
        )
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
        f"- {PATH_SQL_FULL} ({os.path.getsize(PATH_SQL_FULL):,} bytes | {len(rows_users)} users, {len(df_mtd_final)} baris MTD, {len(df_agent)} baris Detail Agent, {len(df_mtd_ini)} transaksi SA Nov)\n"
        f"- {PATH_SQL_CEPAT} ({os.path.getsize(PATH_SQL_CEPAT):,} bytes)"
    )


if __name__ == "__main__":
    generate_sql_files()
