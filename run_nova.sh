#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# run_nova.sh — Nova AGI Hızlı Başlatıcı Script
# ═══════════════════════════════════════════════════════════════════════════════
# Bu sürüm şu davranışı sağlar:
#   1) Nova ana uygulaması arka planda başlatılır
#   2) "Nova AI" terminali canlı çıktıyı izler
#   3) "Nova Info" terminali sistem akışını izler
#   4) Info terminaline Ctrl+C basınca sadece bilgi akışı durur

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR" || exit 1

AI_LOG="$DIR/nova_ai.log"
INFO_LOG="$DIR/nova.log"
: > "$AI_LOG"
touch "$INFO_LOG"

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

find_terminal() {
    for term in gnome-terminal x-terminal-emulator xfce4-terminal konsole mate-terminal lxterminal terminator xterm; do
        if command -v "$term" >/dev/null 2>&1; then
            echo "$term"
            return 0
        fi
    done
    return 1
}

start_nova_detached() {
    nohup env TERM=xterm "$PYTHON_CMD" "$DIR/main.py" "$@" > "$AI_LOG" 2>&1 &
    echo $! > "$DIR/.nova_pid"
}

open_terminal_window() {
    local term="$1"
    local title="$2"
    local cmd="$3"

    case "$term" in
        gnome-terminal)
            gnome-terminal --title="$title" -- bash -lc "$cmd" >/dev/null 2>&1 &
            ;;
        x-terminal-emulator)
            x-terminal-emulator -T "$title" -e bash -lc "$cmd" >/dev/null 2>&1 &
            ;;
        xfce4-terminal)
            xfce4-terminal --title="$title" --hold -e bash -lc "$cmd" >/dev/null 2>&1 &
            ;;
        mate-terminal)
            mate-terminal --title="$title" -- bash -lc "$cmd" >/dev/null 2>&1 &
            ;;
        lxterminal)
            lxterminal --title "$title" -e bash -lc "$cmd" >/dev/null 2>&1 &
            ;;
        terminator)
            terminator -T "$title" -x bash -lc "$cmd" >/dev/null 2>&1 &
            ;;
        konsole)
            konsole --new-tab -p tabtitle="$title" -e bash -lc "$cmd" >/dev/null 2>&1 &
            ;;
        xterm)
            xterm -title "$title" -e bash -lc "$cmd" >/dev/null 2>&1 &
            ;;
        *)
            echo "⚠️ Terminal emülatörü bulunamadı. Tek pencerede açıyorum..."
            return 1
            ;;
    esac
    return 0
}

# Normal başlatma: ana GUI paneli açılır.
# Ek terminal görünümü istenirse kullanıcı GUI içindeki "Dual Terminal" butonuna basar.
"$PYTHON_CMD" "$DIR/nova_launcher.py" "$@"
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo -e "\033[91m❌ Nova AGI ($EXIT_CODE) koduyla kapandı.\033[0m"
    echo -e "\033[93m💡 Hata detayları yukarıda listelenmiştir veya nova.log dosyasına kaydedilmiştir.\033[0m"
    echo ""
    read -r -p "Pencereyi kapatmak için [Enter] tuşuna basın..." _
fi

exit $EXIT_CODE

