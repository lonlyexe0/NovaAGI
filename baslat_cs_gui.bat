@echo off
title Nova AGI (Modern C# GUI + Multi-GPU)
echo ======================================================================
echo   🌟 Nova AGI — Modern C# WPF GUI Baslatiliyor (.NET 9)
echo ======================================================================

cd /d "%~dp0"

echo [1/2] .NET 9 WPF Arayuzu kontrol ediliyor / derleniyor...
dotnet build NovaApp\NovaApp.csproj -c Release -v q --nologo
if errorlevel 1 (
    echo Derleme hatasi olustu. Hata ayiklama surumu deneniyor...
    if exist "NovaApp\bin\Release\net9.0-windows\NovaAGI.exe" (
        start "" "NovaApp\bin\Release\net9.0-windows\NovaAGI.exe"
        exit /b 0
    )
    pause
    exit /b 1
)

echo [2/2] Nova AGI WPF Baslatiliyor...
start "" "NovaApp\bin\Release\net9.0-windows\NovaAGI.exe"
exit /b 0
