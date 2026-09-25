#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# nova.sh — Nova AGI başlatıcı (Windows'taki baslat_*.bat dosyalarının yerine)
# ═══════════════════════════════════════════════════════════════════════════════
#   ./nova.sh [gui]      Avalonia masaüstü arayüzü (yoksa Tk arayüzü)
#   ./nova.sh tk         Python/Tk arayüzü
#   ./nova.sh term       Terminal sohbeti (main.py)
#   ./nova.sh launcher   Gelişmiş terminal başlatıcı (HF akışı, istatistikler)
#   ./nova.sh web        Telefon / tarayıcı için web sunucusu
#   ./nova.sh tunnel     Web sunucusunu Cloudflare tüneliyle internete aç
#   ./nova.sh doctor     Donanım ve bağımlılık kontrolü
#   ./nova.sh build      Masaüstü arayüzünü yeniden derle
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

APP_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
cd "$APP_DIR"
export NOVA_HOME="$APP_DIR"

if [[ -x "$APP_DIR/.venv/bin/python" ]]; then
  PY="$APP_DIR/.venv/bin/python"
else
  PY="$(command -v python3 || true)"
  [[ -z "$PY" ]] && { echo "python3 bulunamadı. Önce ./install.sh çalıştırın."; exit 1; }
fi
export NOVA_PYTHON="$PY"

find_dotnet() {
  command -v dotnet 2>/dev/null || { [[ -x "$HOME/.dotnet/dotnet" ]] && echo "$HOME/.dotnet/dotnet"; } || true
}

build_desktop() {
  local dn; dn="$(find_dotnet)"
  [[ -z "$dn" ]] && { echo ".NET SDK bulunamadı (./install.sh --with-dotnet)."; return 1; }
  local rid="linux-x64"; [[ "$(uname -m)" =~ ^(aarch64|arm64)$ ]] && rid="linux-arm64"
  "$dn" publish NovaApp/NovaApp.csproj -c Release -r "$rid" --self-contained true -o build/desktop --nologo -v q
}

web_port() {
  "$PY" -c "import config_manager as c; print(c.get_setting('web_server_port'))" 2>/dev/null || echo 8080
}

cmd="${1:-gui}"; shift || true
case "$cmd" in
  gui|desktop)
    if [[ -x build/desktop/nova-agi ]]; then
      exec build/desktop/nova-agi "$@"
    elif [[ -n "$(find_dotnet)" ]]; then
      echo "Masaüstü arayüzü derleniyor (ilk açılış)…"
      build_desktop && exec build/desktop/nova-agi "$@"
    fi
    echo "Avalonia arayüzü yok; Tk arayüzü açılıyor."
    exec "$PY" nova_launcher.py --gui "$@"
    ;;
  tk)        exec "$PY" nova_launcher.py --gui "$@" ;;
  term)      exec "$PY" main.py "$@" ;;
  launcher)  exec "$PY" nova_launcher.py --term "$@" ;;
  web)       exec "$PY" web_server.py "$@" ;;
  bridge)    exec "$PY" nova_bridge.py "$@" ;;
  build)     build_desktop ;;
  tunnel)
    PORT="$(web_port)"
    CF="$(command -v cloudflared || true)"
    if [[ -z "$CF" ]]; then
      CF="$HOME/.local/bin/cloudflared"
      if [[ ! -x "$CF" ]]; then
        arch="amd64"; [[ "$(uname -m)" =~ ^(aarch64|arm64)$ ]] && arch="arm64"
        echo "cloudflared indiriliyor (tek seferlik)…"
        mkdir -p "$(dirname "$CF")"
        curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-$arch" -o "$CF"
        chmod +x "$CF"
      fi
    fi
    echo "Önce web sunucusunun açık olduğundan emin olun (./nova.sh web veya Ayarlar → Mobil & Web)."
    echo "Aşağıdaki https://….trycloudflare.com adresinin sonuna ?token=<erişim anahtarı> ekleyerek bağlanın."
    exec "$CF" tunnel --url "http://127.0.0.1:$PORT"
    ;;
  doctor)
    "$PY" gpu_setup.py
    echo
    for t in pw-play paplay ffplay espeak-ng tesseract xdotool wmctrl xclip wl-copy grim gnome-screenshot; do
      if command -v "$t" >/dev/null; then printf "  ✓ %s\n" "$t"; else printf "  · %s (yok)\n" "$t"; fi
    done
    "$PY" - <<'PY'
import importlib
for m in ("torch", "edge_tts", "mss", "PIL", "speech_recognition", "pyaudio", "pyautogui", "cv2", "pytesseract", "datasets"):
    try:
        importlib.import_module(m); print(f"  ✓ {m}")
    except Exception:
        print(f"  · {m} (yok)")
PY
    ;;
  -h|--help|help) sed -n '2,13p' "$0" ;;
  *) echo "Bilinmeyen komut: $cmd  (./nova.sh help)"; exit 1 ;;
esac
