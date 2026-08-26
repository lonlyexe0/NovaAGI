@echo off
title Nova AGI v3 (GPU Terminal Modu)
echo Nova AGI baslatiliyor (Python 3.10 + AMD DirectML GPU)...
py -3.10 main.py
if errorlevel 1 (
    echo.
    echo Bir hata olustu.
    pause
)
