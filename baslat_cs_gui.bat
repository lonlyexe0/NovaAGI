@echo off
title Nova AGI (Modern C# GUI + Multi-GPU)
echo ======================================================================
echo   🌟 Nova AGI — Modern C# WPF GUI Baslatiliyor (.NET 9)
echo ======================================================================

cd /d "%~dp0"

if exist "NovaApp\bin\Release\net9.0-windows\NovaAGI.exe" (
    start "" "NovaApp\bin\Release\net9.0-windows\NovaAGI.exe"
    exit /b 0
)

if exist "NovaApp\bin\Debug\net9.0-windows\NovaAGI.exe" (
    start "" "NovaApp\bin\Debug\net9.0-windows\NovaAGI.exe"
    exit /b 0
)

echo [1/2] .NET 9 WPF Arayuzu derleniyor...
dotnet build NovaApp\NovaApp.csproj -c Release
if errorlevel 1 (
    echo Derleme hatasi olustu.
    pause
    exit /b 1
)

start "" "NovaApp\bin\Release\net9.0-windows\NovaAGI.exe"
exit /b 0
