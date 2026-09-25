#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# install.sh — Nova AGI Linux kurulumu
# ═══════════════════════════════════════════════════════════════════════════════
#   ./install.sh                 # her şeyi otomatik kur
#   ./install.sh --gpu=rocm      # PyTorch arka ucunu zorla (auto|cuda|rocm|xpu|cpu)
#   ./install.sh --no-system     # sudo ile sistem paketi kurma
#   ./install.sh --no-desktop    # masaüstü uygulamasını derleme / menüye ekleme
#   ./install.sh --with-dotnet   # .NET SDK yoksa ~/.dotnet altına kur
#   ./install.sh -y              # soru sorma
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$APP_DIR/.venv"
GPU="auto"; SYSTEM=1; DESKTOP=1; WITH_DOTNET=0; YES=0

for arg in "$@"; do
  case "$arg" in
    --gpu=*)        GPU="${arg#*=}" ;;
    --no-system)    SYSTEM=0 ;;
    --no-desktop)   DESKTOP=0 ;;
    --with-dotnet)  WITH_DOTNET=1 ;;
    -y|--yes)       YES=1 ;;
    -h|--help)      sed -n '2,11p' "$0"; exit 0 ;;
    *) echo "Bilinmeyen seçenek: $arg"; exit 1 ;;
  esac
done

c_ok=$'\e[32m'; c_warn=$'\e[33m'; c_err=$'\e[31m'; c_dim=$'\e[90m'; c_b=$'\e[1m'; c_0=$'\e[0m'
step() { echo -e "\n${c_b}▸ $*${c_0}"; }
ok()   { echo -e "  ${c_ok}✓${c_0} $*"; }
warn() { echo -e "  ${c_warn}!${c_0} $*"; }
die()  { echo -e "  ${c_err}✗ $*${c_0}"; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

echo -e "${c_b}Nova AGI — Linux kurulumu${c_0}  ${c_dim}($APP_DIR)${c_0}"

# ── 1. Sistem paketleri ──────────────────────────────────────────────────────
if (( SYSTEM )); then
  step "Sistem paketleri"
  SUDO=""; (( EUID != 0 )) && have sudo && SUDO="sudo"
  if have apt-get; then
    PKGS="python3 python3-venv python3-pip python3-tk python3-dev portaudio19-dev espeak-ng ffmpeg
          tesseract-ocr tesseract-ocr-tur xdotool wmctrl xclip wl-clipboard libnotify-bin pciutils"
    INSTALL="$SUDO apt-get install -y --no-install-recommends"; UPDATE="$SUDO apt-get update"
  elif have dnf; then
    PKGS="python3 python3-pip python3-tkinter python3-devel portaudio-devel espeak-ng ffmpeg-free
          tesseract tesseract-langpack-tur xdotool wmctrl xclip wl-clipboard pciutils"
    INSTALL="$SUDO dnf install -y"; UPDATE=":"
  elif have pacman; then
    PKGS="python python-pip tk portaudio espeak-ng ffmpeg tesseract tesseract-data-tur xdotool wmctrl xclip wl-clipboard pciutils"
    INSTALL="$SUDO pacman -S --needed --noconfirm"; UPDATE=":"
  elif have zypper; then
    PKGS="python3 python3-pip python3-tk python3-devel portaudio-devel espeak-ng ffmpeg tesseract-ocr
          tesseract-ocr-traineddata-turkish xdotool wmctrl xclip wl-clipboard pciutils"
    INSTALL="$SUDO zypper --non-interactive install"; UPDATE=":"
  else
    INSTALL=""
    warn "Paket yöneticisi tanınmadı; python3-venv, espeak-ng, ffmpeg ve tesseract'ı elle kurun."
  fi
  if [[ -n "$INSTALL" ]]; then
    answer="y"
    if (( ! YES )); then
      echo -e "  ${c_dim}$(echo $PKGS)${c_0}"
      read -r -p "  Bu paketler kurulsun mu? [Y/n] " answer || answer="y"
    fi
    if [[ ! "$answer" =~ ^[Nn] ]]; then
      $UPDATE >/dev/null 2>&1 || true
      # Tek tek dene: dağıtımda olmayan bir paket kurulumu durdurmasın
      $INSTALL $PKGS 2>/dev/null || for p in $PKGS; do $INSTALL "$p" >/dev/null 2>&1 || warn "atlandı: $p"; done
      ok "Sistem paketleri hazır"
    fi
  fi
fi

# ── 2. Python sanal ortamı ───────────────────────────────────────────────────
step "Python sanal ortamı"
have python3 || die "python3 bulunamadı."
python3 - <<'PY' || die "Python 3.10 veya üstü gerekli."
import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)
PY
if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV" || die "venv oluşturulamadı (python3-venv paketini kurun)."
fi
PY="$VENV/bin/python"
"$PY" -m pip install -q --upgrade pip wheel
ok "$("$PY" --version) → $VENV"

# ── 3. PyTorch (GPU'ya göre) ─────────────────────────────────────────────────
step "PyTorch"
if [[ "$GPU" == "auto" ]]; then
  PCI="$(lspci 2>/dev/null | grep -Ei 'vga|3d|display' || true)"
  if have nvidia-smi && nvidia-smi -L >/dev/null 2>&1 || grep -qi nvidia <<<"$PCI"; then
    GPU="cuda"
  elif grep -qiE 'amd|ati|radeon' <<<"$PCI" && [[ -e /dev/kfd ]]; then
    GPU="rocm"
  elif grep -qiE 'intel.*(arc|dg2|battlemage)' <<<"$PCI"; then
    GPU="xpu"
  else
    GPU="cpu"
  fi
fi
case "$GPU" in
  cuda) INDEX="" ;;
  rocm) INDEX="https://download.pytorch.org/whl/${NOVA_ROCM_INDEX:-rocm6.4}" ;;
  xpu)  INDEX="https://download.pytorch.org/whl/xpu" ;;
  cpu)  INDEX="https://download.pytorch.org/whl/cpu" ;;
  *) die "Geçersiz --gpu değeri: $GPU (auto|cuda|rocm|xpu|cpu)" ;;
esac
echo -e "  ${c_dim}Arka uç: $GPU${INDEX:+ ($INDEX)}${c_0}"
if "$PY" -c "import torch" 2>/dev/null; then
  ok "PyTorch zaten kurulu: $("$PY" -c 'import torch; print(torch.__version__)')"
else
  "$PY" -m pip install ${INDEX:+--index-url "$INDEX"} torch numpy || die "PyTorch kurulamadı."
  ok "PyTorch $("$PY" -c 'import torch; print(torch.__version__)')"
fi

# ── 4. Python paketleri ──────────────────────────────────────────────────────
step "Python paketleri"
"$PY" -m pip install -q -r "$APP_DIR/requirements.txt" || die "Çekirdek paketler kurulamadı."
ok "Çekirdek paketler"
while read -r line; do
  pkg="${line%%#*}"; pkg="${pkg// /}"
  [[ -z "$pkg" ]] && continue
  if "$PY" -m pip install -q "$pkg" >/dev/null 2>&1; then ok "$pkg"; else warn "$pkg kurulamadı (isteğe bağlı)"; fi
done < "$APP_DIR/requirements-extra.txt"

# ── 5. Masaüstü uygulaması (Avalonia / .NET) ─────────────────────────────────
if (( DESKTOP )); then
  step "Masaüstü uygulaması"
  DOTNET="$(command -v dotnet || true)"
  [[ -z "$DOTNET" && -x "$HOME/.dotnet/dotnet" ]] && DOTNET="$HOME/.dotnet/dotnet"
  if [[ -z "$DOTNET" && $WITH_DOTNET -eq 1 ]]; then
    curl -sSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh
    bash /tmp/dotnet-install.sh --channel 9.0 --install-dir "$HOME/.dotnet" >/dev/null && DOTNET="$HOME/.dotnet/dotnet"
  fi
  if [[ -n "$DOTNET" ]]; then
    case "$(uname -m)" in aarch64|arm64) RID="linux-arm64" ;; *) RID="linux-x64" ;; esac
    if "$DOTNET" publish "$APP_DIR/NovaApp/NovaApp.csproj" -c Release -r "$RID" --self-contained true \
         -p:PublishSingleFile=false -o "$APP_DIR/build/desktop" --nologo -v q >/dev/null; then
      ok "Avalonia arayüzü derlendi → build/desktop/nova-agi"
    else
      warn "Derleme başarısız; yedek Tk arayüzü kullanılacak."
    fi
  else
    warn ".NET SDK yok → yedek Tk arayüzü kullanılacak. Modern arayüz için: ./install.sh --with-dotnet"
  fi

  APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
  ICONS="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/512x512/apps"
  mkdir -p "$APPS" "$ICONS"
  cp "$APP_DIR/assets/nova_icon.png" "$ICONS/nova-agi.png"
  sed "s|@APP_DIR@|$APP_DIR|g" "$APP_DIR/packaging/nova-agi.desktop" > "$APPS/nova-agi.desktop"
  chmod +x "$APPS/nova-agi.desktop" "$APP_DIR/nova.sh"
  have update-desktop-database && update-desktop-database "$APPS" >/dev/null 2>&1 || true
  have gtk-update-icon-cache && gtk-update-icon-cache -q "${ICONS%/512x512/apps}" >/dev/null 2>&1 || true
  ok "Uygulama menüsüne eklendi (Nova AGI)"
fi

# ── Özet ─────────────────────────────────────────────────────────────────────
step "Hazır!"
"$PY" "$APP_DIR/gpu_setup.py" 2>/dev/null | grep -E "Seçilen|GPU|CPU|PyTorch" | sed 's/^/  /' || true
cat <<EOF

  ${c_b}Başlatma${c_0}
    ./nova.sh            masaüstü arayüzü
    ./nova.sh term       terminal sohbeti
    ./nova.sh web        telefon / tarayıcı erişimi
    ./nova.sh doctor     donanım ve bağımlılık kontrolü
EOF
