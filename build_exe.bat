@echo off
title Nova AGI v3 — Windows Standalone EXE Derleyici
echo ============================================================
echo Nova AGI Windows Standalone EXE Paketi Olusturuluyor...
echo (Python 3.10 + PyTorch + DirectML GPU + Arayuz + Modeller)
echo ============================================================
echo.

py -3.10 build_exe.py
if errorlevel 1 (
    echo.
    echo [HATA] Derleme sirasinda bir sorun olustu.
    pause
    exit /b 1
)

echo.
echo Derleme tamamlandi! 'dist\NovaAGI\NovaAGI.exe' dosyasini calistirabilirsiniz.
pause
