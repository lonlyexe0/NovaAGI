@echo off
chcp 65001 > nul
echo 🚀 Nova AGI Windows Kurulum ve Baslatici...
echo.

echo 📦 Python gereksinimleri yukleniyor...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Pip yuklemesinde bir hata olustu.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo 🌟 Nova AGI Baslatiliyor...
python nova_launcher.py
pause
