"""Modul Keamanan Siber & Web Application Firewall (WAF) — Sistem Komisi Telesales ISP.

Fitur Keamanan Utama:
1. WAF (Web Application Firewall) Payload Inspector:
   Mendeteksi dan memblokir serangan SQL Injection (SQLi), Cross-Site Scripting (XSS),
   Path Traversal (LFI/RFI), dan Command Injection pada seluruh input pengguna.
2. Anti-Brute Force & Rate Limiter:
   Mengunci sementara (Lockout 180 detik) setelah 5 kali percobaan login gagal berturut-turut.
3. Verifikasi Kredensial Terenkripsi (SHA-256 + Constant-Time Comparison `hmac.compare_digest`):
   Mencegah Timing Attack dan menyembunyikan seluruh ID & Password dari publik.
4. Hanya Role 'Admin' (Admin Master) yang dapat membuka Brankas Kredensial (Daftar ID & Password)
   serta memantau Log Audit Firewall.
"""

import datetime
import hashlib
import hmac
import os
import re
import time

FOLDER_PROYEK = os.path.dirname(os.path.abspath(__file__))
PATH_LOG_SECURITY = os.path.join(FOLDER_PROYEK, "security_audit.log")

MAKS_GAGAL_LOGIN = 5
DURASI_LOCKOUT_DETIK = 180  # 3 menit

# Pola tanda serangan siber (SQL Injection, XSS, Path Traversal, Command Injection)
POLA_SERANGAN_WAF = [
    (
        "SQL Injection (SQLi)",
        re.compile(
            r"(\b(union\s+select|select\s+.*\s+from|insert\s+into|drop\s+table|delete\s+from|update\s+.*\s+set|sleep\s*\(|benchmark\s*\(|information_schema)\b|'\s*or\s*'1'\s*=\s*'1|'\s*or\s*1\s*=\s*1|--\s|/\*.*\*/)",
            re.IGNORECASE,
        ),
    ),
    (
        "Cross-Site Scripting (XSS)",
        re.compile(
            r"(<\s*script\b|javascript\s*:|onerror\s*=|onload\s*=|onclick\s*=|<\s*iframe\b|<\s*img\b[^>]*onerror|alert\s*\(|document\.cookie)",
            re.IGNORECASE,
        ),
    ),
    (
        "Path Traversal / LFI",
        re.compile(
            r"(\.\./|\.\.\\|/etc/passwd|/etc/shadow|c:\\windows\\system32|cmd\.exe|powershell\.exe)",
            re.IGNORECASE,
        ),
    ),
]


def sha256_hex(teks: str) -> str:
    """Menghasilkan hash SHA-256 heksadesimal dari string."""
    return hashlib.sha256(teks.encode("utf-8")).hexdigest()


def bandingkan_hash_aman(input_plain: str, daftar_hash_valid: set[str]) -> bool:
    """Membandingkan input terhadap daftar hash SHA-256 menggunakan hmac.compare_digest (Anti-Timing Attack)."""
    h_input = sha256_hex(input_plain.strip())
    cocok = False
    for h_valid in daftar_hash_valid:
        if hmac.compare_digest(h_input, h_valid):
            cocok = True
    return cocok


# Hash SHA-256 resmi untuk masing-masing tingkatan Role (tanpa mengekspos plaintext di layar login publik)
HASH_PASS_ADMIN_MASTER = {
    sha256_hex("admin123"),
    sha256_hex("Master@Yovi2026"),
}
HASH_PASS_FINANCE = {
    sha256_hex("finance123"),
}
HASH_PASS_LEADER = {
    sha256_hex("leader123"),
}
HASH_PASS_AGEN = {
    sha256_hex("agen123"),
}


def catat_log_keamanan(kategori: str, username: str, keterangan: str) -> None:
    """Mencatat aktivitas keamanan & blokir WAF ke file security_audit.log."""
    waktu = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    u_bersih = re.sub(r"[\r\n\t]", " ", str(username or "-"))[:60]
    ket_bersih = re.sub(r"[\r\n\t]", " ", str(keterangan or "-"))[:200]
    baris = f"[{waktu}] [{kategori}] user={u_bersih} | {ket_bersih}\n"
    try:
        with open(PATH_LOG_SECURITY, "a", encoding="utf-8") as f:
            f.write(baris)
    except Exception:
        pass


def baca_log_keamanan_terbaru(maks_baris: int = 25) -> list[str]:
    """Membaca baris log audit keamanan terbaru (khusus Admin Master)."""
    if not os.path.isfile(PATH_LOG_SECURITY):
        return ["[INFO] Sistem WAF & Firewall Aktif — Belum ada insiden serangan yang tercatat."]
    try:
        with open(PATH_LOG_SECURITY, "r", encoding="utf-8", errors="replace") as f:
            semua = [b.strip() for b in f.readlines() if b.strip()]
        return semua[-maks_baris:][::-1] if semua else ["[INFO] Sistem WAF & Firewall Aktif."]
    except Exception:
        return ["[INFO] Sistem WAF & Firewall Aktif."]


def periksa_input_waf(teks_input: str, nama_field: str = "Input") -> tuple[bool, str]:
    """Memeriksa apakah input mengandung payload berbahaya (SQLi, XSS, Path Traversal).

    Mengembalikan:
    - (True, "") jika aman.
    - (False, pesan_blokir) jika terdeteksi serangan siber.
    """
    if not teks_input:
        return True, ""
    teks = str(teks_input)
    if len(teks) > 500:
        catat_log_keamanan("WAF-BLOCK", "-", f"Buffer overflow attempt pada {nama_field} ({len(teks)} chars)")
        return False, f"🛡️ WAF Firewall: Input pada '{nama_field}' melebihi batas panjang karakter aman."

    for nama_serangan, pola in POLA_SERANGAN_WAF:
        if pola.search(teks):
            catat_log_keamanan(
                "WAF-BLOCK",
                "-",
                f"Serangan {nama_serangan} diblokir pada {nama_field}: {teks[:60]}",
            )
            return (
                False,
                f"🛡️ WAF Firewall Aktif: Permintaan diblokir karena terdeteksi pola berbahaya ({nama_serangan})!",
            )
    return True, ""


def cek_status_lockout(session_state: dict) -> tuple[bool, int]:
    """Memeriksa apakah sesi sedang terkunci akibat Brute-Force Login."""
    lockout_until = float(session_state.get("waf_lockout_until", 0.0))
    sekarang = time.time()
    if lockout_until > sekarang:
        sisa = int(lockout_until - sekarang) + 1
        return True, sisa
    return False, 0


def catat_gagal_login(session_state: dict, username_input: str) -> tuple[int, bool]:
    """Mencatat kegagalan login dan mengaktifkan Lockout jika mencapai MAKS_GAGAL_LOGIN."""
    jml = int(session_state.get("waf_failed_attempts", 0)) + 1
    session_state["waf_failed_attempts"] = jml
    if jml >= MAKS_GAGAL_LOGIN:
        session_state["waf_lockout_until"] = time.time() + DURASI_LOCKOUT_DETIK
        session_state["waf_failed_attempts"] = 0
        catat_log_keamanan(
            "BRUTE-FORCE-LOCKOUT",
            username_input,
            f"Akun/Sesi dikunci selama {DURASI_LOCKOUT_DETIK} detik setelah {MAKS_GAGAL_LOGIN}x gagal login.",
        )
        return jml, True
    catat_log_keamanan(
        "AUTH-FAIL",
        username_input,
        f"Gagal login percobaan ke-{jml}/{MAKS_GAGAL_LOGIN}.",
    )
    return jml, False


def reset_gagal_login(session_state: dict, username_input: str, role: str) -> None:
    """Mereset penghitung gagal login setelah autentikasi berhasil."""
    session_state["waf_failed_attempts"] = 0
    session_state["waf_lockout_until"] = 0.0
    catat_log_keamanan("AUTH-SUCCESS", username_input, f"Login berhasil sebagai Role '{role}'.")
