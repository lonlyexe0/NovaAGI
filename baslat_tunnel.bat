@echo off
chcp 65001 >nul
title Nova AGI v3.5 — Güvenli Dış Ağ Tüneli (Cloudflare)
color 0B

echo.
echo  ============================================================
echo   NOVA AGI v3.5 — Dış Ağdan Güvenli Erişim (Cloudflare Tunnel)
echo   Evde değilken mobil veriden / internetten Nova'ya bağlanın!
echo  ============================================================
echo.

set "PORT=8080"
if exist ".nova_config.json" (
    for /f "tokens=2 delims=:, " %%a in ('findstr "web_server_port" .nova_config.json 2^>nul') do (
        set "PORT=%%~a"
    )
)

echo [*] Hedef yerel sunucu portu: %PORT%
echo [*] Cloudflare Tunnel kontrol ediliyor...

where cloudflared >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "CF_CMD=cloudflared"
) else (
    if exist "cloudflared.exe" (
        set "CF_CMD=cloudflared.exe"
    ) else (
        echo [*] cloudflared.exe indiriliyor (Tek seferlik kurulum)...
        powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile 'cloudflared.exe'"
        if exist "cloudflared.exe" (
            set "CF_CMD=cloudflared.exe"
        ) else (
            echo [!] Cloudflared indirilemedi. Alternatif olarak localtunnel başlatılıyor...
            npx -y localtunnel --port %PORT%
            goto end
        )
    )
)

echo.
echo  ============================================================
echo   ✅ Tünel başlatılıyor!
echo   Aşağıda görünecek 'https://....trycloudflare.com' adresini
echo   telefonunuzda açarak her yerden güvenle bağlanabilirsiniz.
echo  ============================================================
echo.

%CF_CMD% tunnel --url http://127.0.0.1:%PORT%

:end
pause
