#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# packaging/build_app.sh — "Nova AGI.app" paketini üretir (macOS)
#
#   packaging/build_app.sh             → build/Nova AGI.app
#   packaging/build_app.sh --install   → derle + ~/Applications'a kur
#
# .app, Avalonia arayüzünü (kendi kendine yeten .NET, ayrıca .NET gerekmez) içerir.
# Python motoru (nova_bridge.py + .venv) proje klasöründe kalır; yolu
# Contents/Resources/nova_home dosyasına yazılır.
# .NET SDK yoksa ve build/Nova AGI.app hazır geliyorsa (sürüm arşivi) derleme
# atlanır, yalnızca yol ve imza güncellenip kurulur.
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

INSTALL=0
for a in "$@"; do
  case "$a" in
    --install) INSTALL=1 ;;
    *) echo "Bilinmeyen seçenek: $a"; exit 1 ;;
  esac
done

VERSION="4.0"
BUNDLE_ID="com.lonlyexe0.nova-agi"
NAME="Nova AGI"
APP="build/$NAME.app"
case "$(uname -m)" in arm64) RID="osx-arm64" ;; *) RID="osx-x64" ;; esac

DOTNET="${DOTNET:-$(command -v dotnet || true)}"
[[ -z "$DOTNET" && -x "$HOME/.dotnet/dotnet" ]] && DOTNET="$HOME/.dotnet/dotnet"

if [[ -n "$DOTNET" ]]; then
  echo "▸ Avalonia arayüzü derleniyor ($RID)…"
  rm -rf build/publish
  "$DOTNET" publish NovaApp/NovaApp.csproj -c Release -r "$RID" --self-contained true \
    -p:PublishSingleFile=false -p:UseAppHost=true -o build/publish --nologo -v q

  echo "▸ $NAME.app oluşturuluyor…"
  rm -rf "$APP"
  mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
  cp -R build/publish/. "$APP/Contents/MacOS/"

  # ── Simge (.icns) ──────────────────────────────────────────────────────────
  ICONSET="build/nova.iconset"
  rm -rf "$ICONSET" && mkdir -p "$ICONSET"
  SRC_PNG="assets/nova_icon.png"
  # SVG'den 1024 px üret (Quick Look); olmazsa 512 px PNG'yi kullan
  if qlmanage -t -s 1024 -o build assets/nova_icon.svg >/dev/null 2>&1 && [[ -f build/nova_icon.svg.png ]]; then
    SRC_PNG="build/nova_icon.svg.png"
  fi
  for s in 16 32 128 256 512; do
    sips -z $s $s "$SRC_PNG" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
    d=$((s * 2)); sips -z $d $d "$SRC_PNG" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null
  done
  iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/nova.icns"
  rm -rf "$ICONSET" build/nova_icon.svg.png

  # ── Info.plist ─────────────────────────────────────────────────────────────
  cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>                 <string>$NAME</string>
  <key>CFBundleDisplayName</key>          <string>$NAME</string>
  <key>CFBundleIdentifier</key>           <string>$BUNDLE_ID</string>
  <key>CFBundleExecutable</key>           <string>nova-agi</string>
  <key>CFBundleIconFile</key>             <string>nova.icns</string>
  <key>CFBundlePackageType</key>          <string>APPL</string>
  <key>CFBundleShortVersionString</key>   <string>$VERSION</string>
  <key>CFBundleVersion</key>              <string>$VERSION</string>
  <key>CFBundleDevelopmentRegion</key>    <string>tr</string>
  <key>CFBundleLocalizations</key>        <array><string>tr</string><string>en</string></array>
  <key>LSMinimumSystemVersion</key>       <string>13.0</string>
  <key>LSApplicationCategoryType</key>    <string>public.app-category.productivity</string>
  <key>NSHighResolutionCapable</key>      <true/>
  <key>NSSupportsAutomaticGraphicsSwitching</key> <true/>
  <key>NSMicrophoneUsageDescription</key>
  <string>Nova sesli komutlarınızı dinlemek için mikrofonu kullanır. / Nova uses the microphone to hear your voice commands.</string>
  <key>NSAppleEventsUsageDescription</key>
  <string>Nova ses düzeyi, ekran kilidi ve masaüstü gibi sistem eylemleri için System Events'i kullanır. / Nova uses System Events for volume, lock screen and show-desktop actions.</string>
  <key>NSScreenCaptureUsageDescription</key>
  <string>Nova ekranınızı yalnızca siz istediğinizde analiz eder. / Nova analyses your screen only when you ask it to.</string>
</dict>
</plist>
PLIST
  printf 'APPL????' > "$APP/Contents/PkgInfo"
elif [[ -d "$APP" ]]; then
  echo "▸ .NET SDK yok; hazır $APP kullanılıyor."
else
  echo "✗ .NET SDK bulunamadı (./install.sh --with-dotnet veya brew install dotnet)."; exit 1
fi

# Python motorunun yeri (uygulama ~/Applications'a taşınsa da bulunabilsin)
printf '%s\n' "$ROOT" > "$APP/Contents/Resources/nova_home"

# İnternetten indirilen arşivden gelirse karantina işaretini kaldır (yoksa "hasarlı" uyarısı çıkar)
xattr -dr com.apple.quarantine "$APP" 2>/dev/null || true

# Yerel (ad-hoc) imza: Apple Silicon imzasız kodu çalıştırmaz; Gatekeeper uyarısı da önlenir
codesign --force --deep --sign - --identifier "$BUNDLE_ID" "$APP" >/dev/null 2>&1 \
  && echo "✓ $APP (ad-hoc imzalı)" || echo "! codesign başarısız; uygulama yine de açılabilir"

if (( INSTALL )); then
  DEST="$HOME/Applications/$NAME.app"
  mkdir -p "$HOME/Applications"
  rm -rf "$DEST"
  ditto "$APP" "$DEST"
  /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$DEST" 2>/dev/null || true
  echo "✓ Kuruldu: $DEST"
fi

