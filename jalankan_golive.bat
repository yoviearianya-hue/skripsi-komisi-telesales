@echo off
title Sistem Komisi Telesales - GO-LIVE SERVER (Publik + LAN + Bot Telegram)
cd /d "%~dp0"
echo ============================================================================
echo   MEMULAI SERVER GO-LIVE DASHBOARD TELESALES + BOT TELEGRAM + TUNNEL PUBLIK
echo ============================================================================
echo.

REM Hentikan proses lama jika ada agar tidak bentrok port 8501 atau konflik Bot
taskkill /F /IM streamlit.exe >nul 2>&1
taskkill /F /IM cloudflared.exe >nul 2>&1

REM Jalankan orchestrator Go-Live Server (otomatis membuat Link Publik *.trycloudflare.com)
".venv\Scripts\python.exe" -u golive_server.py
pause

