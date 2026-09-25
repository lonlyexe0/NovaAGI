#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# packaging/build_release.sh — Taşınabilir Linux sürüm arşivi üretir
# (Windows'taki build_exe.py + Inno Setup kurulumunun karşılığı)
#
#   dist/NovaAGI-<sürüm>-linux-<arch>.tar.gz
#     ├─ build/desktop/   kendi kendine yeten Avalonia arayüzü (.NET gerekmez)
#     ├─ *.py, web/, assets/, nova_headless_trainer/
#     └─ install.sh       kullanıcının makinesinde Python ortamını kurar
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
VERSION="${1:-4.0}"
ARCH="$(uname -m)"
NAME="NovaAGI-$VERSION-linux-$ARCH"
STAGE="dist/$NAME"

./nova.sh build
rm -rf "$STAGE" && mkdir -p "$STAGE"
cp -r build *.py *.sh requirements*.txt README*.md LICENSE nova_vocab.json web assets packaging nova_headless_trainer "$STAGE/"
find "$STAGE" -name "__pycache__" -type d -prune -exec rm -rf {} +
tar -C dist -czf "dist/$NAME.tar.gz" "$NAME"
rm -rf "$STAGE"
echo "✓ dist/$NAME.tar.gz ($(du -h "dist/$NAME.tar.gz" | cut -f1))"
echo "  Kullanım: tar xzf $NAME.tar.gz && cd $NAME && ./install.sh --no-desktop && ./nova.sh"
