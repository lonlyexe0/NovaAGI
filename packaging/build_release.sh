#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# packaging/build_release.sh — Taşınabilir macOS sürüm arşivi üretir
#
#   dist/NovaAGI-<sürüm>-macos-<arch>.tar.gz
#     ├─ build/Nova AGI.app   derlenmiş arayüz (.NET gerekmez)
#     ├─ *.py, web/, assets/, nova_headless_trainer/
#     └─ install.sh           kullanıcının Mac'inde Python ortamını kurar, .app'i ~/Applications'a ekler
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
VERSION="${1:-4.0}"
NAME="NovaAGI-$VERSION-macos-$(uname -m)"
STAGE="dist/$NAME"

packaging/build_app.sh
rm -rf "$STAGE" && mkdir -p "$STAGE/build"
ditto "build/Nova AGI.app" "$STAGE/build/Nova AGI.app"
cp -R *.py *.sh requirements*.txt README*.md LICENSE nova_vocab.json web assets packaging nova_headless_trainer "$STAGE/"
find "$STAGE" -name "__pycache__" -type d -prune -exec rm -rf {} +
# Proje yolu kurulumda yeniden yazılır
rm -f "$STAGE/build/Nova AGI.app/Contents/Resources/nova_home"
COPYFILE_DISABLE=1 tar -C dist -czf "dist/$NAME.tar.gz" "$NAME"
rm -rf "$STAGE"
echo "✓ dist/$NAME.tar.gz ($(du -h "dist/$NAME.tar.gz" | cut -f1))"
echo "  Kullanım: tar xzf $NAME.tar.gz && cd $NAME && ./install.sh && ./nova.sh"
