@echo off
title AI Khao Thi Antigravity (100%% Offline)

echo ===============================================================================
echo                HE THONG AI KHAO THI SU PHAM DA DANG (100%% OFFLINE)
echo        Toi uu cho Intel Core i5-14500 (14 Nhan, 20 Luong) - 16GB RAM
echo             Van hanh Non-Admin va Loopback An Toan (127.0.0.1)
echo ===============================================================================
echo.

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

:: 1. Kiem tra moi truong ao .venv cuc bo
if exist "%ROOT_DIR%.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%ROOT_DIR%.venv\Scripts\python.exe"
    goto START_APP
)

:: 2. Tim kiem Python neu chua co .venv
echo [*] Dang kiem tra moi truong Python tren he thong...

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "SYS_PYTHON=python"
    goto MAKE_VENV
)

if exist "C:\Program Files\Odoo 20.0.20260927\python\python.exe" (
    set "SYS_PYTHON=C:\Program Files\Odoo 20.0.20260927\python\python.exe"
    goto MAKE_VENV
)

echo [!] Khong tim thay Python kha dung tren may tinh.
pause
exit /b 1

:MAKE_VENV
echo [*] Dang thiet lap moi truong ao .venv cuc bo...
"%SYS_PYTHON%" -m venv "%ROOT_DIR%.venv"
set "PYTHON_EXE=%ROOT_DIR%.venv\Scripts\python.exe"

echo [*] Dang cai dat thu vien (FastAPI, python-docx, pypdfium2)...
"%PYTHON_EXE%" -m pip install -r "%ROOT_DIR%requirements.txt"

:START_APP
echo.
echo [*] Moi truong san sang!
echo [*] Dang khoi chay may chu tai http://127.0.0.1:8000 ...
echo [*] Tu dong mo trinh duyet web...
echo.

:: Mo trinh duyet web bang PowerShell chay ngam sau 2 giay
powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:8000'"

:: Khoi chay Uvicorn Server tai 127.0.0.1:8000 (kem auto-reload)
"%PYTHON_EXE%" -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload

pause
