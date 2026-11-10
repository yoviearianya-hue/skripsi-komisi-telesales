@echo off
title Docker Manager - Skripsi Komisi Telesales (Terisolasi & Aman)
cd /d "%~dp0"
echo ============================================================================
echo   MENJALANKAN CONTAINER DOCKER: SKRIPSI-KOMISI-TELESALES-APP (PORT 8501)
echo   (Aman & Terisolasi — Tidak mengganggu container Docker lainnya)
echo ============================================================================
echo.

REM Hentikan proses python/streamlit/cloudflared di Windows lokal jika ada agar port 8501 & Bot tidak bentrok
taskkill /F /IM streamlit.exe >nul 2>&1
taskkill /F /IM cloudflared.exe >nul 2>&1

REM Jalankan container khusus project skripsi-komisi-telesales
docker compose -p skripsi-komisi-telesales up -d --build

echo.
echo Menunggu Link Go-Live Publik siap (sekitar 8 detik)...
timeout /t 8 /nobreak >nul
echo.
if exist "LINK_GOLIVE_PUBLIK.txt" (
    type "LINK_GOLIVE_PUBLIK.txt"
)
echo.
echo Container Docker skripsi-komisi-telesales-app sudah berjalan di background (24/7)!
pause
