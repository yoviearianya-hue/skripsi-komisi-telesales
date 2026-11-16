"""Pembuat / Pengganti Kredensial SUPER ADMIN (Admin Master) & Pengelola Role.

Kredensial Super Admin disimpan sebagai hash PBKDF2-HMAC-SHA256 (200.000 iterasi + salt acak)
di `superadmin_config.json` (dikecualikan dari GitHub via `.gitignore`).
Akun lama (`admin`, `admin123`, `superadmin`, `yovi_master`, dll.) diblokir permanen.
"""

import argparse
import getpass
import hashlib
import json
import os
import re
import secrets
import string
import sys

FOLDER_PROYEK = os.path.dirname(os.path.abspath(__file__))
PATH_CONFIG = os.path.join(FOLDER_PROYEK, "superadmin_config.json")
ITERASI = 200_000
ID_TERLARANG = ("admin", "administrator", "root", "superadmin", "yovi_master")


def hash_password(password: str, salt_hex: str, iterasi: int = ITERASI) -> str:
    """PBKDF2-HMAC-SHA256 -> 64 karakter heksadesimal (identik dengan hash_pbkdf2() di PHP)."""
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt_hex.encode("utf-8"), iterasi, dklen=32
    ).hex()


def buat_password_acak(panjang: int = 18) -> str:
    huruf = string.ascii_letters + string.digits + "@#%+=_-!"
    while True:
        pw = "".join(secrets.choice(huruf) for _ in range(panjang))
        if (
            re.search(r"[a-z]", pw)
            and re.search(r"[A-Z]", pw)
            and re.search(r"\d", pw)
            and re.search(r"[@#%+=_\-!]", pw)
        ):
            return pw


def password_cukup_kuat(pw: str) -> bool:
    return (
        len(pw) >= 10
        and re.search(r"[a-z]", pw) is not None
        and re.search(r"[A-Z]", pw) is not None
        and re.search(r"\d", pw) is not None
    )


def simpan_config(username: str, password: str) -> None:
    u = username.strip().lower()
    if u in ID_TERLARANG:
        raise ValueError(f"ID '{u}' terlarang karena terlalu mudah ditebak.")
    salt_hex = secrets.token_hex(16)
    data = {
        "username": u,
        "salt": salt_hex,
        "iterations": ITERASI,
        "hash": hash_password(password, salt_hex),
    }
    with open(PATH_CONFIG, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Buat/ganti kredensial Super Admin")
    parser.add_argument("--random", action="store_true", help="buat password acak kuat")
    parser.add_argument("--user", default="", help="ID Super Admin")
    args = parser.parse_args()

    username = args.user.strip().lower()
    if not username:
        username = input("ID Super Admin baru [sa_yovi_2026]: ").strip().lower() or "sa_yovi_2026"
    if not re.fullmatch(r"[a-z0-9._-]{6,40}", username):
        sys.exit("ID harus 6-40 karakter: huruf kecil, angka, titik, strip, atau underscore.")
    if username in ID_TERLARANG:
        sys.exit("ID terlalu umum/mudah ditebak. Pilih ID lain.")

    if args.random:
        password = buat_password_acak()
        tampil_password = True
    else:
        password = getpass.getpass("Password baru (min 10 karakter, huruf besar+kecil+angka): ")
        ulang = getpass.getpass("Ulangi password: ")
        if password != ulang:
            sys.exit("Password tidak sama.")
        if not password_cukup_kuat(password):
            sys.exit("Password kurang kuat (min 10 karakter, wajib huruf besar, huruf kecil, dan angka).")
        tampil_password = False

    simpan_config(username, password)
    print(f"Super Admin tersimpan di: {PATH_CONFIG}")
    print(f"ID Super Admin : {username}")
    if tampil_password:
        print(f"Password       : {password}")
        print("(Catat sekarang — password tidak disimpan dalam bentuk teks.)")


if __name__ == "__main__":
    main()
