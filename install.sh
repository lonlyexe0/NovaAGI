#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# install.sh — Nova AGI Kurulum, Sistem Entegrasyonu ve Başlatıcı
# ═══════════════════════════════════════════════════════════════════════════════

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR" || exit 1

echo "🚀 Nova AGI Kurulum ve Başlatma Sihirbazı..."
echo "📂 Proje Dizini: $DIR"
echo ""

# 1. Sistem Paket Yöneticisi, Tkinter (GUI) ve TTS (espeak-ng) Kontrolü
if [ -x "$(command -v pacman)" ]; then
    echo "📦 Arch / CachyOS / Manjaro algılandı. Sistem paketleri kontrol ediliyor..."
    sudo pacman -Sy --needed --noconfirm python python-pip tk espeak-ng 2>/dev/null || true
elif [ -x "$(command -v apt-get)" ]; then
    echo "📦 Debian / Ubuntu algılandı. Sistem paketleri kontrol ediliyor..."
    sudo apt-get update -qq
    sudo apt-get install -y python3 python3-pip python3-tk espeak-ng 2>/dev/null || true
elif [ -x "$(command -v dnf)" ]; then
    echo "📦 Fedora / RHEL algılandı. Sistem paketleri kontrol ediliyor..."
    sudo dnf install -y python3 python3-pip python3-tkinter espeak-ng 2>/dev/null || true
fi

# 2. Python Kütüphaneleri
echo "📦 Python gereksinimleri yükleniyor..."
pip3 install -r requirements.txt --break-system-packages 2>/dev/null || pip3 install -r requirements.txt || true

# 3. Masaüstü Uygulaması Olarak Tanıtma (Desktop Application & Shortcut)
echo "🖥️  Nova AGI masaüstü uygulaması olarak sisteme kaydediliyor..."

chmod +x "$DIR/run_nova.sh" 2>/dev/null || true

# İkonları ve menü dizinlerini hazırla
mkdir -p "$HOME/.local/share/applications"
mkdir -p "$HOME/.local/share/icons/hicolor/scalable/apps"

if [ -f "$DIR/nova_icon.svg" ]; then
    cp "$DIR/nova_icon.svg" "$HOME/.local/share/icons/nova_icon.svg" 2>/dev/null || true
    cp "$DIR/nova_icon.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/nova-agi.svg" 2>/dev/null || true
fi

# .desktop dosyasını mevcut dizin yoluyla otomatik oluştur
cat <<EOF > "$DIR/nova-agi.desktop"
[Desktop Entry]
Version=1.0
Type=Application
Name=Nova AGI
GenericName=Yapay Genel Zeka Asistanı
Comment=Nova AGI - Otonom Öğrenen ve Büyüyen Yapay Zeka Sistemi
Exec=$DIR/run_nova.sh
Icon=$DIR/nova_icon.svg
Path=$DIR
Terminal=true
Categories=Development;Science;ArtificialIntelligence;Utility;
Keywords=AI;AGI;Nova;GPT;MachineLearning;NeuralNetwork;
StartupNotify=true
Actions=GUI;Terminal;Both;

[Desktop Action GUI]
Name=Nova AGI (Grafik Arayüz)
Exec=$DIR/run_nova.sh --gui

[Desktop Action Terminal]
Name=Nova AGI (Terminal Modu)
Exec=$DIR/run_nova.sh --term

[Desktop Action Both]
Name=Nova AGI (GUI + Terminal Modu)
Exec=$DIR/run_nova.sh --both
EOF

# Uygulama menüsüne ve Masaüstüne yerleştir
cp "$DIR/nova-agi.desktop" "$HOME/.local/share/applications/nova-agi.desktop"
chmod +x "$DIR/nova-agi.desktop" "$HOME/.local/share/applications/nova-agi.desktop"

DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
if [ -d "$DESKTOP_DIR" ]; then
    cp "$DIR/nova-agi.desktop" "$DESKTOP_DIR/Nova-AGI.desktop"
    chmod +x "$DESKTOP_DIR/Nova-AGI.desktop"
fi

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

echo "✅ Nova AGI başarıyla sisteminize bir masaüstü uygulaması olarak eklendi!"
echo "   • Uygulama Menüsü: Arama çubuğunda 'Nova AGI'"
if [ -d "$DESKTOP_DIR" ]; then
    echo "   • Masaüstü Kısayolu: $DESKTOP_DIR/Nova-AGI.desktop"
fi
echo ""

# 4. Başlatma
echo "🌟 Nova AGI Başlatılıyor..."
python3 "$DIR/nova_launcher.py" "$@"