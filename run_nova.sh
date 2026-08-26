#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# run_nova.sh — Nova AGI Hızlı Başlatıcı Script
# ═══════════════════════════════════════════════════════════════════════════════

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR" || exit 1

# Venv varsa aktifleştir
if [ -d "$DIR/venv" ] && [ -f "$DIR/venv/bin/activate" ]; then
    source "$DIR/venv/bin/activate"
fi

# Python ile Nova Launcher'ı başlat
python3 "$DIR/nova_launcher.py" "$@"
