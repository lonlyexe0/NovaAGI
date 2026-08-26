@echo off
setlocal enabledelayedexpansion
title Nova AGI v3 — Otomatik Kurulum ve Baslatici
chcp 65001 >nul

echo ======================================================================
echo          🚀 NOVA AGI v3 — WINDOWS OTOMATİK KURULUM SİHİRBAZI
echo ======================================================================
echo.

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

:: 1. Python 3.10 Kontrolü
echo [1/4] Python ortamı kontrol ediliyor...
py -3.10 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [BILGI] Python 3.10 bulunamadi. Otomatik olarak indiriliyor ve kuruluyor...
    set "PY_INSTALLER=%TEMP%\python-3.10.11-amd64.exe"
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe', '$env:TEMP\python-3.10.11-amd64.exe')"
    
    if exist "!PY_INSTALLER!" (
        echo [BILGI] Python 3.10 yukleniyor, lutfen bekleyin...
        "!PY_INSTALLER!" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_pip=1
        timeout /t 5 >nul
    ) else (
        echo [HATA] Python indirilemedi. Lutfen https://www.python.org/downloads/ adresinden Python 3.10 kurun.
        pause
        exit /b 1
    )
)

echo [✓] Python 3.10 hazir.
echo.

:: 2. Pip ve Kütüphanelerin Kurulumu
echo [2/4] Gerekli yapay zeka ve derin ogrenme paketleri kuruluyor...
echo (PyTorch, DirectML GPU, Transformers, Arayuz, Ses ve Goruntu)...
py -3.10 -m pip install --upgrade pip >nul 2>&1
py -3.10 -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo [UYARI] Bazi paketler kurulurken uyari verdi, devam ediliyor...
)
echo.

:: 3. Masaüstü Kısayolu Oluşturma
echo [3/4] Masaüstü kısayolu oluşturuluyor...
set "SHORTCUT_SCRIPT=%TEMP%\create_nova_shortcut.vbs"
set "DESKTOP_DIR=%USERPROFILE%\Desktop"
set "TARGET_BAT=%PROJECT_DIR%baslat_gui.bat"

echo Set oWS = WScript.CreateObject("WScript.Shell") > "%SHORTCUT_SCRIPT%"
echo sLinkFile = "%DESKTOP_DIR%\Nova AGI.lnk" >> "%SHORTCUT_SCRIPT%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%SHORTCUT_SCRIPT%"
echo oLink.TargetPath = "%TARGET_BAT%" >> "%SHORTCUT_SCRIPT%"
echo oLink.WorkingDirectory = "%PROJECT_DIR%" >> "%SHORTCUT_SCRIPT%"
echo oLink.Description = "Nova AGI - Otonom Büyüyen Yapay Zeka" >> "%SHORTCUT_SCRIPT%"
echo oLink.IconLocation = "%PROJECT_DIR%nova_icon.ico,0" >> "%SHORTCUT_SCRIPT%"
echo oLink.Save >> "%SHORTCUT_SCRIPT%"

cscript //nologo "%SHORTCUT_SCRIPT%" >nul 2>&1
if exist "%SHORTCUT_SCRIPT%" del /f /q "%SHORTCUT_SCRIPT%"

echo [✓] Masaüstünüze 'Nova AGI' kısayolu başarıyla eklendi!
echo.

:: 4. Başlatma
echo ======================================================================
echo [4/4] Kurulum tamamlandı! Nova AGI başlatılıyor...
echo ======================================================================
echo.

py -3.10 nova_launcher.py --gui
if errorlevel 1 (
    echo.
    echo Bir hata olustu.
    pause
)
