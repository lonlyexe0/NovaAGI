@echo off
chcp 65001 >nul
title Nova AGI v3.5 — Mobil & Web Sunucusu
color 0B

echo.
echo  ============================================================
echo   NOVA AGI v3.5 — Mobil & Web Sunucusu
echo   Bilgisayarınızdaki yapay zekaya telefondan erişin!
echo  ============================================================
echo.

where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PY_CMD=py -3.10"
) else (
    set "PY_CMD=python"
)

echo [*] Web sunucusu başlatılıyor...
%PY_CMD% web_server.py

pause
