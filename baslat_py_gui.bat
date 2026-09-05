@echo off
chcp 65001 >nul 2>&1
title Nova AGI (Python Tkinter GUI Modu)
echo Nova AGI baslatiliyor (Python 3.10 + Tkinter)...
cd /d "%~dp0"
py -3.10 nova_launcher.py --gui
if errorlevel 1 (
    echo.
    echo Bir hata olustu.
    pause
)
