@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% neq 0 (
  echo Python launcher not found. Install Python 3.10+.
  pause
  exit /b 1
)
py -3 "%~dp0ai_desktop.py"
if errorlevel 1 pause
