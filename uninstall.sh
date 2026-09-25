#!/usr/bin/env bash
# uninstall.sh — Nova AGI menü girdisini, derlemeleri ve (isteğe bağlı) verileri kaldırır.
set -euo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"

rm -f "$DATA/applications/nova-agi.desktop" "$DATA/icons/hicolor/512x512/apps/nova-agi.png"
rm -rf "$APP_DIR/build" "$APP_DIR/NovaApp/bin" "$APP_DIR/NovaApp/obj"
echo "✓ Menü girdisi ve derlemeler kaldırıldı."

read -r -p "Python ortamı (.venv) silinsin mi? [y/N] " a || a=""
[[ "$a" =~ ^[YyEe] ]] && rm -rf "$APP_DIR/.venv" && echo "✓ .venv silindi."

read -r -p "Nova'nın hafızası ve model ağırlıkları ($DATA/nova-agi) silinsin mi? [y/N] " a || a=""
[[ "$a" =~ ^[YyEe] ]] && rm -rf "$DATA/nova-agi" && echo "✓ Veriler silindi."
