"""Orchestrator Go-Live Server (Kompatibel Docker Linux & Windows Lokal):

Menjalankan secara bersamaan di dalam 1 container / environment:
1. Streamlit Web Dashboard (app.py) pada port 8501 (terbuka untuk LAN & Tunnel).
2. Bot Telegram Interaktif (bot_interaktif.py).
3. Cloudflare Quick Tunnel (cloudflared) agar aplikasi memiliki URL HTTPS Publik
   yang dapat diakses oleh seluruh staf dari mana saja (HP/Laptop).
"""

import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time

FOLDER_PROYEK = os.path.dirname(os.path.abspath(__file__))

# Deteksi otomatis interpreter Python (Windows .venv vs Docker Linux)
_VENV_PY_WIN = os.path.join(FOLDER_PROYEK, ".venv", "Scripts", "python.exe")
PATH_PYTHON = _VENV_PY_WIN if (os.name == "nt" and os.path.isfile(_VENV_PY_WIN)) else sys.executable

# Deteksi otomatis binary cloudflared (Windows .exe vs Linux binary di Docker)
_CF_WIN = os.path.join(FOLDER_PROYEK, "cloudflared.exe")
_CF_SYS = shutil.which("cloudflared") or "/usr/local/bin/cloudflared"
PATH_CLOUDFLARED = (
    _CF_WIN
    if (os.name == "nt" and os.path.isfile(_CF_WIN))
    else (_CF_SYS if os.path.isfile(_CF_SYS) else "")
)

PATH_URL_AKTIF = os.path.join(FOLDER_PROYEK, "url_publik_aktif.txt")
PATH_INFO_GOLIVE = os.path.join(FOLDER_PROYEK, "LINK_GOLIVE_PUBLIK.txt")


def dapatkan_ip_lan() -> str:
    """Mendapatkan alamat IPv4 LAN komputer host (mendukung variabel HOST_LAN_IP di Docker)."""
    env_ip = os.environ.get("HOST_LAN_IP", "").strip()
    if env_ip:
        return env_ip
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def simpan_url_publik(url_publik: str, ip_lan: str) -> None:
    """Menyimpan URL publik aktif ke file agar dapat dibaca oleh app.py dan bot_interaktif.py."""
    with open(PATH_URL_AKTIF, "w", encoding="utf-8") as f:
        f.write(url_publik.strip())

    info_lengkap = (
        "====================================================================\n"
        "🌐 LINK GO-LIVE DASHBOARD TELESALES ISP (DOCKER CONTAINER AKTIF)\n"
        "====================================================================\n\n"
        f"1. LINK PUBLIK INTERNET (Bisa diakses dari HP / Luar Kantor / Mana Saja):\n"
        f"   👉 {url_publik.strip()}\n\n"
        f"2. LINK JARINGAN KANTOR / LAN (Wi-Fi / Jaringan Lokal yang Sama):\n"
        f"   👉 http://{ip_lan}:8501\n\n"
        f"3. LINK LOKAL (Komputer Server / Port Forwarding Docker):\n"
        f"   👉 http://localhost:8501\n\n"
        "--------------------------------------------------------------------\n"
        "🐳 INFO CONTAINER DOCKER:\n"
        "- Nama Project   : skripsi-komisi-telesales (Terisolasi & Aman)\n"
        "- Nama Container : skripsi-komisi-telesales-app\n"
        "- Port Mapping   : 0.0.0.0:8501 -> 8501/tcp (Tidak menabrak port lain)\n"
        "--------------------------------------------------------------------\n"
        "🔑 AKUN LOGIN MULTI-ROLE:\n"
        "- Admin   : username 'admin'   | password 'admin123'\n"
        "- Finance : username 'finance' | password 'finance123'\n"
        "- Leader  : username 'yovi', 'fahrul', 'firli', 'tika', 'yudha', dll. | password 'leader123'\n"
        "- Agen    : username nama depan agen (misal 'askih', 'sisca', 'nafa') | password 'agen123'\n"
        "====================================================================\n"
    )
    with open(PATH_INFO_GOLIVE, "w", encoding="utf-8") as f:
        f.write(info_lengkap)


def pantau_output_tunnel(proc: subprocess.Popen, ip_lan: str) -> None:
    """Membaca baris output dari cloudflared/ssh untuk menangkap URL publik https://..."""
    pola_cf = re.compile(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com")
    pola_lhr = re.compile(r"https://[a-zA-Z0-9\-]+\.lhr\.life")

    if proc.stdout is None:
        return

    for raw_line in iter(proc.stdout.readline, ""):
        if not raw_line:
            break
        line = raw_line.strip()
        m_cf = pola_cf.search(line)
        m_lhr = pola_lhr.search(line)
        url_ditemukan = m_cf.group(0) if m_cf else (m_lhr.group(0) if m_lhr else None)
        if url_ditemukan:
            simpan_url_publik(url_ditemukan, ip_lan)
            print("\n" + "=" * 70, flush=True)
            print("🚀 APLIKASI TELAH GO-LIVE & DAPAT DIAKSES OLEH SELURUH STAFF!", flush=True)
            print(f"🌐 URL Publik Internet : {url_ditemukan}", flush=True)
            print(f"🏢 URL Jaringan LAN    : http://{ip_lan}:8501", flush=True)
            print(f"💻 URL Lokal           : http://localhost:8501", flush=True)
            print("=" * 70 + "\n", flush=True)


def buat_cmd_streamlit() -> list[str]:
    """Menyusun command line Streamlit yang kompatibel di Windows & Linux Docker."""
    return [
        PATH_PYTHON,
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.port",
        "8501",
        "--server.address",
        "0.0.0.0",
        "--server.headless",
        "true",
        "--server.enableCORS",
        "false",
        "--server.enableXsrfProtection",
        "false",
    ]


def buat_cmd_tunnel() -> list[str]:
    """Menyusun command line Cloudflare Tunnel (atau fallback SSH localhost.run)."""
    if PATH_CLOUDFLARED and os.path.isfile(PATH_CLOUDFLARED):
        return [
            PATH_CLOUDFLARED,
            "tunnel",
            "--url",
            "http://localhost:8501",
            "--no-autoupdate",
        ]
    return [
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "ServerAliveInterval=30",
        "-R",
        "80:localhost:8501",
        "nokey@localhost.run",
    ]


def main() -> None:
    os.chdir(FOLDER_PROYEK)
    ip_lan = dapatkan_ip_lan()

    # 1. Jalankan Bot Telegram Interaktif
    print("🤖 [1/3] Menyalakan Bot Telegram ALPHA WOLF SQUAD...", flush=True)
    proc_bot = subprocess.Popen(
        [PATH_PYTHON, "-u", "bot_interaktif.py"],
        cwd=FOLDER_PROYEK,
    )

    # 2. Jalankan Streamlit Server (CORS & XSRF dinonaktifkan agar WebSocket tunnel stabil)
    print("📊 [2/3] Menyalakan Server Web Streamlit pada port 8501...", flush=True)
    cmd_st = buat_cmd_streamlit()
    proc_st = subprocess.Popen(
        cmd_st,
        cwd=FOLDER_PROYEK,
    )

    time.sleep(2)

    # 3. Jalankan Tunnel Publik (Cloudflare Quick Tunnel)
    print("🌐 [3/3] Membuka Jalur Akses Publik HTTPS (Go-Live Tunnel)...", flush=True)
    cmd_tunnel = buat_cmd_tunnel()
    proc_tunnel = subprocess.Popen(
        cmd_tunnel,
        cwd=FOLDER_PROYEK,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    t_monitor = threading.Thread(
        target=pantau_output_tunnel,
        args=(proc_tunnel, ip_lan),
        daemon=True,
    )
    t_monitor.start()

    try:
        while True:
            time.sleep(3)
            # Auto-recovery Watchdog: hidupkan ulang otomatis jika ada proses yang mati
            if proc_st.poll() is not None:
                print("⚠️ Server Streamlit terhenti, menghidupkan ulang otomatis...", flush=True)
                proc_st = subprocess.Popen(cmd_st, cwd=FOLDER_PROYEK)
            if proc_bot.poll() is not None:
                print("⚠️ Bot Telegram terhenti, menghidupkan ulang otomatis...", flush=True)
                proc_bot = subprocess.Popen(
                    [PATH_PYTHON, "-u", "bot_interaktif.py"],
                    cwd=FOLDER_PROYEK,
                )
            if proc_tunnel.poll() is not None:
                print("⚠️ Tunnel Publik terputus, menyambungkan ulang otomatis...", flush=True)
                proc_tunnel = subprocess.Popen(
                    cmd_tunnel,
                    cwd=FOLDER_PROYEK,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                t_monitor = threading.Thread(
                    target=pantau_output_tunnel,
                    args=(proc_tunnel, ip_lan),
                    daemon=True,
                )
                t_monitor.start()
    except KeyboardInterrupt:
        pass
    finally:
        for p in (proc_tunnel, proc_st, proc_bot):
            try:
                p.terminate()
            except Exception:
                pass


if __name__ == "__main__":
    main()
