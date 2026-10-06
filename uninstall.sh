#!/usr/bin/env bash
# uninstall.sh — Nova AGI.app'i, derlemeleri ve (isteğe bağlı) verileri kaldırır (macOS).
set -euo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="$HOME/Library/Application Support/NovaAGI"

rm -rf "$HOME/Applications/Nova AGI.app"
rm -rf "$APP_DIR/build" "$APP_DIR/NovaApp/bin" "$APP_DIR/NovaApp/obj"
echo "✓ Nova AGI.app ve derlemeler kaldırıldı."

read -r -p "Python ortamı (.venv) silinsin mi? [y/N] " a || a=""
[[ "$a" =~ ^[YyEe] ]] && rm -rf "$APP_DIR/.venv" && echo "✓ .venv silindi."

read -r -p "Nova'nın hafızası ve model ağırlıkları ($DATA) silinsin mi? [y/N] " a || a=""
[[ "$a" =~ ^[YyEe] ]] && rm -rf "$DATA" && echo "✓ Veriler silindi."

echo "Not: verilen macOS izinlerini sıfırlamak için: tccutil reset All com.lonlyexe0.nova-agi"
