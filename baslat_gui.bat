@echo off
chcp 65001 >nul 2>&1
title Nova AGI (Modern C# WPF GUI)
echo ======================================================================
echo   🌟 Nova AGI - Modern C# WPF Masaustu Uygulamasi Baslatiliyor (.NET 9)
echo ======================================================================

cd /d "%~dp0"

if exist "NovaApp\bin\Release\net9.0-windows\NovaAGI.exe" (
    start "" "NovaApp\bin\Release\net9.0-windows\NovaAGI.exe"
    exit /b 0
)

echo [*] C# .NET 9 Arayuzu derleniyor...
dotnet build NovaApp\NovaApp.csproj -c Release -v q --nologo
if errorlevel 1 (
    echo [!] C# derleme hatasi. Python Tkinter arayuzune geciliyor...
    py -3.10 nova_launcher.py --gui
    exit /b 0
)

start "" "NovaApp\bin\Release\net9.0-windows\NovaAGI.exe"
exit /b 0
