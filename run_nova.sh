#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# run_nova.sh — Nova AGI Hızlı Başlatıcı Script
# ═══════════════════════════════════════════════════════════════════════════════

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR" || exit 1

# Venv varsa pyvenv.cfg site-packages ayarını doğrula ve aktifleştir
if [ -d "$DIR/venv" ]; then
    if [ -f "$DIR/venv/pyvenv.cfg" ]; then
        if grep -q "include-system-site-packages = false" "$DIR/venv/pyvenv.cfg" 2>/dev/null; then
            sed -i 's/include-system-site-packages = false/include-system-site-packages = true/' "$DIR/venv/pyvenv.cfg" 2>/dev/null || true
        fi
    fi
    if [ -f "$DIR/venv/bin/activate" ]; then
        source "$DIR/venv/bin/activate"
    fi
fi

# Uygun Python yorumlayıcısını belirle
PYTHON_CMD="python3"
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
fi

# PyTorch ve temel modüllerin varlığını kontrol et
if ! $PYTHON_CMD -c "import torch" >/dev/null 2>&1; then
    echo "⚠️ PyTorch veya gerekli kütüphaneler eksik görünüyor. Yükleme deneniyor..."
    $PYTHON_CMD -m pip install -r "$DIR/requirements.txt" --break-system-packages 2>/dev/null || \
    $PYTHON_CMD -m pip install -r "$DIR/requirements.txt" 2>/dev/null || true
fi

# Python ile Nova Launcher'ı başlat ve hata durumunda ekranı açık tut
$PYTHON_CMD "$DIR/nova_launcher.py" "$@"
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo -e "\033[91m❌ Nova AGI ($EXIT_CODE) koduyla kapandı.\033[0m"
    echo -e "\033[93m💡 Hata detayları yukarıda listelenmiştir veya nova.log dosyasına kaydedilmiştir.\033[0m"
    echo ""
    read -r -p "Pencereyi kapatmak için [Enter] tuşuna basın..." _
fi

exit $EXIT_CODE

