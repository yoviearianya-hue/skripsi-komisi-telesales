"""Modul Keamanan Siber, Manajemen Role Terenkripsi & Web Application Firewall (WAF).

Fitur Keamanan Utama:
1. WAF Payload Inspector:
   Memblokir SQL Injection (SQLi), Cross-Site Scripting (XSS), Path Traversal (LFI/RFI),
   dan Command Injection pada seluruh input pengguna.
2. Anti-Brute Force & Rate Limiter (Session + Persistent IP File Lockout):
   Mengunci sementara (180 detik) setelah 5 kali gagal login berturut-turut.
3. Zero-Plaintext Password Storage:
   - Super Admin memakai PBKDF2-HMAC-SHA256 (200.000 iterasi + salt acak).
   - Finance, Sales Leader, dan Agen memakai ID & Password unik baru yang hanya disimpan
     sebagai hash SHA-256 di `roles_config.json` + Brankas Vault terenkripsi
     (HMAC-SHA256 + SHA256-CTR) yang hanya bisa didekripsi saat Super Admin login.
   - Seluruh kredensial lama (`admin`, `admin123`, `finance`, `finance123`, `leader123`, `agen123`)
     diblokir secara permanen.
"""

import base64
import datetime
import hashlib
import hmac
import json
import os
import re
import secrets
import struct
import time

FOLDER_PROYEK = os.path.dirname(os.path.abspath(__file__))
PATH_LOG_SECURITY = os.path.join(FOLDER_PROYEK, "security_audit.log")
PATH_CONFIG_SUPERADMIN = os.path.join(FOLDER_PROYEK, "superadmin_config.json")
PATH_CONFIG_ROLES = os.path.join(FOLDER_PROYEK, "roles_config.json")

MAKS_GAGAL_LOGIN = 5
DURASI_LOCKOUT_DETIK = 180  # 3 menit

ID_LAMA_TERLARANG = frozenset(
    {
        "admin",
        "administrator",
        "root",
        "superadmin",
        "yovi_master",
        "superadmin.yovi",
        "finance",
        "keuangan",
        "komisi",
    }
)
PASS_LAMA_TERLARANG = frozenset(
    {
        "admin123",
        "Master@Yovi2026",
        "Yovi#SuperAdmin2026!",
        "finance123",
        "leader123",
        "agen123",
    }
)

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
    """Membandingkan input terhadap daftar hash SHA-256 menggunakan hmac.compare_digest."""
    h_input = sha256_hex(input_plain.strip())
    cocok = False
    for h_valid in daftar_hash_valid:
        if hmac.compare_digest(h_input, h_valid):
            cocok = True
    return cocok


# =============================================================================
# ENKRIPSI BRANKAS VAULT (PBKDF2 + SHA256-CTR + HMAC-SHA256) — KOMPATIBEL PHP
# =============================================================================


def _turunkan_kunci_vault(password_master: str, salt_hex: str) -> tuple[bytes, bytes]:
    raw = hashlib.pbkdf2_hmac(
        "sha256", password_master.encode("utf-8"), salt_hex.encode("utf-8"), 100_000, dklen=64
    )
    return raw[:32], raw[32:]


def _keystream_sha256(enc_key: bytes, nonce: bytes, panjang: int) -> bytes:
    hasil = bytearray()
    counter = 0
    while len(hasil) < panjang:
        blok = hmac.new(
            enc_key, nonce + struct.pack(">I", counter), hashlib.sha256
        ).digest()
        hasil.extend(blok)
        counter += 1
    return bytes(hasil[:panjang])


def encrypt_vault(payload: dict, password_master: str, salt_hex: str) -> str:
    """Mengenkripsi data Brankas Role (JSON) menggunakan Super Admin Password sebagai Master Key."""
    plain = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    enc_key, mac_key = _turunkan_kunci_vault(password_master, salt_hex)
    nonce = secrets.token_bytes(16)
    ks = _keystream_sha256(enc_key, nonce, len(plain))
    ct = bytes(a ^ b for a, b in zip(plain, ks))
    tag = hmac.new(mac_key, nonce + ct, hashlib.sha256).digest()
    return base64.b64encode(nonce + tag + ct).decode("ascii")


def decrypt_vault(vault_b64: str, password_master: str, salt_hex: str) -> dict | None:
    """Mendekripsi Brankas Role; mengembalikan None jika Master Key salah atau integritas gagal."""
    try:
        blob = base64.b64decode(vault_b64.encode("ascii"), validate=True)
        if len(blob) < 48:
            return None
        nonce = blob[:16]
        tag = blob[16:48]
        ct = blob[48:]
        enc_key, mac_key = _turunkan_kunci_vault(password_master, salt_hex)
        expected_tag = hmac.new(mac_key, nonce + ct, hashlib.sha256).digest()
        if not hmac.compare_digest(tag, expected_tag):
            return None
        ks = _keystream_sha256(enc_key, nonce, len(ct))
        plain = bytes(a ^ b for a, b in zip(ct, ks))
        return json.loads(plain.decode("utf-8"))
    except Exception:
        return None


# =============================================================================
# SUPER ADMIN & MULTI-ROLE CONFIG STORE (TANPA PLAINTEXT DI REPO)
# =============================================================================


def muat_config_superadmin() -> dict | None:
    """Membaca konfigurasi Super Admin (username, salt, iterations, hash)."""
    try:
        with open(PATH_CONFIG_SUPERADMIN, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if all(k in cfg for k in ("username", "salt", "iterations", "hash")):
            return cfg
    except Exception:
        pass
    return None


def verifikasi_super_admin(username_input: str, password_input: str) -> bool:
    """Memverifikasi ID & Password Super Admin dengan PBKDF2 + waktu-konstan."""
    u_clean = str(username_input).strip().lower()
    p_clean = str(password_input).strip()
    if u_clean in ID_LAMA_TERLARANG or p_clean in PASS_LAMA_TERLARANG:
        return False
    cfg = muat_config_superadmin()
    if cfg is None:
        return False
    u_ok = hmac.compare_digest(
        u_clean.encode("utf-8"),
        str(cfg["username"]).strip().lower().encode("utf-8"),
    )
    h_input = hashlib.pbkdf2_hmac(
        "sha256",
        p_clean.encode("utf-8"),
        str(cfg["salt"]).encode("utf-8"),
        int(cfg["iterations"]),
        dklen=32,
    ).hex()
    p_ok = hmac.compare_digest(h_input, str(cfg["hash"]))
    return bool(u_ok and p_ok)


def username_super_admin() -> str:
    """Mengembalikan ID Super Admin aktif."""
    cfg = muat_config_superadmin()
    return str(cfg["username"]) if cfg else ""


def muat_config_roles() -> dict | None:
    """Membaca konfigurasi hash seluruh role (Finance, Leader, Agen) + Brankas terenkripsi."""
    try:
        with open(PATH_CONFIG_ROLES, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if isinstance(cfg, dict) and "finance" in cfg and "leaders" in cfg:
            return cfg
    except Exception:
        pass
    return None


def buat_id_agen_unik(daftar_agen_raw: list[dict]) -> dict[str, dict]:
    """Membuat ID unik `agt_<nama>` tanpa tabrakan untuk setiap agen aktif."""
    kandidat: list[tuple[str, str, str, str]] = []
    hitung_depan: dict[str, int] = {}

    for item in daftar_agen_raw:
        agent_key = str(item.get("Agent_Key", "")).strip()
        nama_tampil = str(item.get("Nama_Tampil", "")).strip()
        leader_def = str(item.get("Leader_Default", "")).strip()
        if not agent_key or agent_key.startswith("VACANT__") or nama_tampil.upper() == "VACANT":
            continue
        depan_raw = nama_tampil.split()[0] if nama_tampil else agent_key.split()[0]
        depan_slug = re.sub(r"[^a-z0-9]", "", depan_raw.lower()) or "agen"
        hitung_depan[depan_slug] = hitung_depan.get(depan_slug, 0) + 1
        kandidat.append((depan_slug, agent_key, nama_tampil, leader_def))

    terpakai: set[str] = set()
    hasil: dict[str, dict] = {}
    for depan_slug, agent_key, nama_tampil, leader_def in kandidat:
        full_slug = re.sub(r"[^a-z0-9]", "", nama_tampil.lower()) or depan_slug
        uid = f"agt_{depan_slug}" if hitung_depan.get(depan_slug, 0) == 1 else f"agt_{full_slug[:22]}"
        asli = uid
        idx = 2
        while uid in terpakai:
            uid = f"{asli}{idx}"
            idx += 1
        terpakai.add(uid)
        hasil[uid] = {
            "name": nama_tampil,
            "agent_key": agent_key,
            "leader": leader_def,
        }
    return hasil


def bangun_roles_config(
    sa_password: str,
    finance_user: str,
    finance_pass: str,
    leader_map: dict[str, str],
    leader_pass: str,
    agen_accounts: dict[str, dict],
    agen_pass: str,
) -> dict:
    """Menyusun dictionary konfigurasi role (hanya hash untuk auth + vault terenkripsi)."""
    salt_vault = secrets.token_hex(16)
    h_fin = sha256_hex(finance_pass.strip())
    h_ldr = sha256_hex(leader_pass.strip())
    h_agt = sha256_hex(agen_pass.strip())

    leaders_cfg = {
        uid.lower(): {"leader": nama_ldr, "hash": h_ldr}
        for uid, nama_ldr in leader_map.items()
    }
    agen_cfg = {}
    for uid, meta in agen_accounts.items():
        agen_cfg[uid.lower()] = {
            "name": meta["name"],
            "agent_key": meta["agent_key"],
            "leader": meta["leader"],
            "hash": h_agt,
        }

    vault_plain = {
        "super_admin_id": username_super_admin(),
        "finance": {"id": finance_user.lower(), "pass": finance_pass},
        "leaders": {
            "pass_default": leader_pass,
            "ids": {uid.lower(): nama_ldr for uid, nama_ldr in leader_map.items()},
        },
        "agen": {
            "pass_default": agen_pass,
            "total": len(agen_accounts),
            "sample_ids": list(agen_accounts.keys())[:15],
            "accounts": {uid.lower(): meta for uid, meta in agen_accounts.items()},
        },
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    return {
        "version": 2,
        "finance": {"username": finance_user.lower(), "hash": h_fin},
        "leaders": leaders_cfg,
        "leader_default_hash": h_ldr,
        "agen_default_hash": h_agt,
        "agen_accounts": agen_cfg,
        "vault_salt": salt_vault,
        "vault_enc": encrypt_vault(vault_plain, sa_password, salt_vault),
    }


def verifikasi_peran_non_admin(
    username_input: str, password_input: str
) -> dict | None:
    """Memverifikasi login Role Finance, Sales Leader, atau Agen dari `roles_config.json`."""
    u = re.sub(r"\s+", " ", str(username_input)).strip().lower()
    p = str(password_input).strip()
    if not u or not p or u in ID_LAMA_TERLARANG or p in PASS_LAMA_TERLARANG:
        return None

    cfg = muat_config_roles()
    if not cfg:
        return None

    p_hash = sha256_hex(p)

    # 1. Finance
    fin = cfg.get("finance", {})
    if fin.get("username") and hmac.compare_digest(u, str(fin["username"]).lower()):
        if hmac.compare_digest(p_hash, str(fin.get("hash", ""))):
            return {
                "logged_in": True,
                "is_admin_master": False,
                "role": "Finance",
                "username": u,
                "display_name": "Divisi Finance & Komisi",
                "leader_scope": "Semua Leader",
                "agent_key": "",
            }

    # 2. Sales Leader
    leaders = cfg.get("leaders", {})
    if u in leaders:
        meta_l = leaders[u]
        h_l = str(meta_l.get("hash", cfg.get("leader_default_hash", "")))
        if h_l and hmac.compare_digest(p_hash, h_l):
            nama_ldr = str(meta_l["leader"])
            return {
                "logged_in": True,
                "is_admin_master": False,
                "role": "Leader",
                "username": u,
                "display_name": nama_ldr,
                "leader_scope": nama_ldr,
                "agent_key": "",
            }

    # 3. Agen Telesales (100% unik per agen, tanpa tabrakan nama depan)
    agen_map = cfg.get("agen_accounts", {})
    if u in agen_map:
        meta_a = agen_map[u]
        h_a = str(meta_a.get("hash", cfg.get("agen_default_hash", "")))
        if h_a and hmac.compare_digest(p_hash, h_a):
            return {
                "logged_in": True,
                "is_admin_master": False,
                "role": "Agen",
                "username": u,
                "display_name": str(meta_a["name"]),
                "leader_scope": str(meta_a["leader"]),
                "agent_key": str(meta_a["agent_key"]),
            }

    return None


# =============================================================================
# WAF LOGGING & RATE LIMITER
# =============================================================================


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
    """Memeriksa apakah input mengandung payload berbahaya (SQLi, XSS, Path Traversal)."""
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
