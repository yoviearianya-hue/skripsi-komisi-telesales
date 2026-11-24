"""Alat Auto-Sync Langsung ke Server Live (https://laporantelesalesoxygen.my.id/index.php)
Tanpa Docker, tanpa cPanel File Manager manual — cukup jalankan script ini kapan saja
Anda memperbarui file TARGET PER MONTH.xlsx atau list_prospect *.xls di folder lokal.

Contoh pakai:
    python sync_ke_server.py --user sa_yovi_2026
    python sync_ke_server.py --user sa_yovi_2026 --hari 16 --hari-harian 16
"""

import argparse
import getpass
import json
import os
import sys
import requests

FOLDER_PROYEK = os.path.dirname(os.path.abspath(__file__))
URL_SERVER_DEFAULT = "https://laporantelesalesoxygen.my.id/index.php"


def sync_files_ke_server(
    url_server: str,
    api_user: str,
    api_pass: str,
    target_path: str | None = None,
    prospect_paths: list[str] | None = None,
    sheet_name: str = "NOVEMBER'26",
    bulan_lalu: int = 10,
    bulan_ini: int = 11,
    tahun: int = 2026,
    total_hari: int = 30,
    hari_berjalan: int = 24,
    hari_harian: int = 24,
    hari_wo: int | None = None,
    rasio_paid: float = 1.25,
    mode_prospect: str = "merge",
) -> dict:
    """Mengirim pembaruan Excel & parameter langsung ke endpoint `api_sync` server live."""
    data = {
        "action": "api_sync",
        "api_user": api_user.strip(),
        "api_pass": api_pass.strip(),
        "sheet_name": sheet_name,
        "bulan_lalu": str(bulan_lalu),
        "bulan_ini": str(bulan_ini),
        "tahun": str(tahun),
        "total_hari": str(total_hari),
        "hari_berjalan": str(hari_berjalan),
        "hari_harian": str(hari_harian),
        "hari_wo": str(hari_wo if hari_wo is not None else hari_berjalan),
        "rasio_paid": str(rasio_paid),
        "mode_prospect": mode_prospect,
    }

    opened = []
    files = []
    try:
        if target_path and os.path.isfile(target_path):
            ft = open(target_path, "rb")
            opened.append(ft)
            files.append(
                (
                    "file_target",
                    (
                        os.path.basename(target_path),
                        ft,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    ),
                )
            )
        for idx, pp in enumerate(prospect_paths or []):
            if os.path.isfile(pp):
                fp = open(pp, "rb")
                opened.append(fp)
                files.append(
                    (
                        f"file_prospect[{idx}]",
                        (os.path.basename(pp), fp, "application/octet-stream"),
                    )
                )

        resp = requests.post(url_server, data=data, files=files or None, timeout=120)
        try:
            res_json = resp.json()
        except Exception:
            res_json = {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
        return res_json
    finally:
        for f in opened:
            try:
                f.close()
            except Exception:
                pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync langsung ke laporantelesalesoxygen.my.id")
    parser.add_argument("--url", default=URL_SERVER_DEFAULT)
    parser.add_argument("--user", default="sa_yovi_2026")
    parser.add_argument("--sheet", default="NOVEMBER'26")
    parser.add_argument("--bulan-lalu", type=int, default=10)
    parser.add_argument("--bulan-ini", type=int, default=11)
    parser.add_argument("--tahun", type=int, default=2026)
    parser.add_argument("--total-hari", type=int, default=30)
    parser.add_argument("--hari", type=int, default=24)
    parser.add_argument("--hari-harian", type=int, default=24)
    parser.add_argument("--hari-wo", type=int, default=24)
    parser.add_argument("--rasio", type=float, default=1.25)
    parser.add_argument("--mode", choices=["merge", "replace"], default="merge")
    parser.add_argument("--target", default=os.path.join(FOLDER_PROYEK, "TARGET PER MONTH.xlsx"))
    parser.add_argument(
        "--prospect",
        nargs="*",
        default=[os.path.join(FOLDER_PROYEK, "list_prospect November.xlsx")],
    )
    args = parser.parse_args()

    pw = getpass.getpass(f"Password Super Admin ({args.user}): ")
    res = sync_files_ke_server(
        url_server=args.url,
        api_user=args.user,
        api_pass=pw,
        target_path=args.target,
        prospect_paths=args.prospect,
        sheet_name=args.sheet,
        bulan_lalu=args.bulan_lalu,
        bulan_ini=args.bulan_ini,
        tahun=args.tahun,
        total_hari=args.total_hari,
        hari_berjalan=args.hari,
        hari_harian=args.hari_harian,
        hari_wo=args.hari_wo,
        rasio_paid=args.rasio,
        mode_prospect=args.mode,
    )
    print(json.dumps(res, indent=2, ensure_ascii=False))
    if not res.get("ok"):
        sys.exit(1)


if __name__ == "__main__":
    main()
