#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# nova.sh — Nova AGI başlatıcı (macOS)
# ═══════════════════════════════════════════════════════════════════════════════
#   ./nova.sh [gui]      Nova AGI.app (yoksa Tk arayüzü)
#   ./nova.sh tk         Python/Tk arayüzü
#   ./nova.sh term       Terminal sohbeti (main.py)
#   ./nova.sh launcher   Gelişmiş terminal başlatıcı (HF akışı, istatistikler)
#   ./nova.sh web        Telefon / tarayıcı için web sunucusu
#   ./nova.sh tunnel     Web sunucusunu Cloudflare tüneliyle internete aç
#   ./nova.sh doctor     Donanım, bağımlılık ve macOS izin kontrolü
#   ./nova.sh build      Nova AGI.app'i yeniden derle ve ~/Applications'a kur
#   ./nova.sh permissions  macOS gizlilik ayarlarını aç (Ekran Kaydı, Erişilebilirlik, Mikrofon)
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

# Sembolik bağlantı üzerinden çağrılsa da gerçek dizini bul (macOS'ta readlink -f eski sürümlerde yok)
SRC="${BASH_SOURCE[0]}"
while [[ -L "$SRC" ]]; do
  DIR="$(cd "$(dirname "$SRC")" && pwd)"; SRC="$(readlink "$SRC")"; [[ "$SRC" != /* ]] && SRC="$DIR/$SRC"
done
APP_DIR="$(cd "$(dirname "$SRC")" && pwd)"
cd "$APP_DIR"
export NOVA_HOME="$APP_DIR"
for d in /opt/homebrew/bin /usr/local/bin; do
  [[ -d "$d" && ":$PATH:" != *":$d:"* ]] && PATH="$PATH:$d"
done

if [[ -x "$APP_DIR/.venv/bin/python" ]]; then
  PY="$APP_DIR/.venv/bin/python"
else
  PY="$(command -v python3 || true)"
  [[ -z "$PY" ]] && { echo "python3 bulunamadı. Önce ./install.sh çalıştırın."; exit 1; }
fi
export NOVA_PYTHON="$PY"

APP_BUNDLE="$HOME/Applications/Nova AGI.app"
BUILT_BUNDLE="$APP_DIR/build/Nova AGI.app"

web_port() {
  "$PY" -c "import config_manager as c; print(c.get_setting('web_server_port'))" 2>/dev/null || echo 8080
}

cmd="${1:-gui}"; shift || true
case "$cmd" in
  gui|desktop|app)
    for b in "$APP_BUNDLE" "$BUILT_BUNDLE"; do
      [[ -d "$b" ]] && exec open "$b" --args "$@"
    done
    if command -v dotnet >/dev/null || [[ -x "$HOME/.dotnet/dotnet" ]]; then
      echo "Nova AGI.app derleniyor (ilk açılış)…"
      packaging/build_app.sh --install && exec open "$APP_BUNDLE" --args "$@"
    fi
    echo "Nova AGI.app yok (.NET SDK gerekli: ./install.sh --with-dotnet); Tk arayüzü açılıyor."
    exec "$PY" nova_launcher.py --gui "$@"
    ;;
  tk)        exec "$PY" nova_launcher.py --gui "$@" ;;
  term)      exec "$PY" main.py "$@" ;;
  launcher)  exec "$PY" nova_launcher.py --term "$@" ;;
  web)       exec "$PY" web_server.py "$@" ;;
  bridge)    exec "$PY" nova_bridge.py "$@" ;;
  build)     exec packaging/build_app.sh --install ;;
  permissions|izinler)
    for p in ScreenCapture Accessibility Microphone; do
      open "x-apple.systempreferences:com.apple.preference.security?Privacy_$p"; sleep 1
    done
    ;;
  tunnel)
    PORT="$(web_port)"
    CF="$(command -v cloudflared || true)"
    if [[ -z "$CF" ]]; then
      if command -v brew >/dev/null; then
        echo "cloudflared kuruluyor (tek seferlik, Homebrew)…"
        brew install -q cloudflared && CF="$(command -v cloudflared)"
      else
        CF="$HOME/.local/bin/cloudflared"
        if [[ ! -x "$CF" ]]; then
          arch="amd64"; [[ "$(uname -m)" == "arm64" ]] && arch="arm64"
          echo "cloudflared indiriliyor (tek seferlik)…"
          mkdir -p "$(dirname "$CF")"
          curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-$arch.tgz" \
            | tar -xz -C "$(dirname "$CF")" cloudflared
          chmod +x "$CF"
        fi
      fi
    fi
    echo "Önce web sunucusunun açık olduğundan emin olun (./nova.sh web veya Ayarlar → Mobil & Web)."
    echo "Aşağıdaki https://….trycloudflare.com adresinin sonuna ?token=<erişim anahtarı> ekleyerek bağlanın."
    exec "$CF" tunnel --url "http://127.0.0.1:$PORT"
    ;;
  doctor)
    "$PY" gpu_setup.py
    echo
    for t in afplay say screencapture osascript tesseract brew dotnet cloudflared; do
      if command -v "$t" >/dev/null; then printf "  ✓ %s\n" "$t"; else printf "  · %s (yok)\n" "$t"; fi
    done
    [[ -d "$APP_BUNDLE" ]] && echo "  ✓ $APP_BUNDLE" || echo "  · Nova AGI.app kurulu değil (./nova.sh build)"
    "$PY" - <<'PY'
import importlib
for m in ("torch", "edge_tts", "mss", "PIL", "speech_recognition", "pyaudio", "pyautogui", "cv2", "pytesseract", "datasets", "tkinter"):
    try:
        importlib.import_module(m); print(f"  ✓ {m}")
    except Exception:
        print(f"  · {m} (yok)")
import mac_desktop
iz = mac_desktop.izin_durumu()
print("\n  macOS izinleri (bu terminal için; uygulama kendi izinlerini ayrıca ister):")
print(f"  {'✓' if iz['screen'] else '·'} Ekran Kaydı      {'' if iz['screen'] else '→ ./nova.sh permissions'}")
print(f"  {'✓' if iz['accessibility'] else '·'} Erişilebilirlik  {'' if iz['accessibility'] else '→ ./nova.sh permissions'}")
PY
    ;;
  -h|--help|help) sed -n '2,14p' "$0" ;;
  *) echo "Bilinmeyen komut: $cmd  (./nova.sh help)"; exit 1 ;;
esac
