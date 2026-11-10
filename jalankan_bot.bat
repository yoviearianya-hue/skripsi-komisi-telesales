@echo off   
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" bot_interaktif.py
) else (
    python bot_interaktif.py
)
if errorlevel 1 pause

