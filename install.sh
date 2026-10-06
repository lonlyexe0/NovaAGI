#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# install.sh — Nova AGI macOS kurulumu (Apple Silicon)
# ═══════════════════════════════════════════════════════════════════════════════
#   ./install.sh                 # her şeyi otomatik kur
#   ./install.sh --no-brew       # Homebrew paketlerini kurma (mikrofon / OCR / Tk olmadan)
#   ./install.sh --no-desktop    # Nova AGI.app'i derleme / Uygulamalar'a ekleme
#   ./install.sh --with-dotnet   # .NET SDK yoksa Homebrew ile kur (app derlemek için)
#   ./install.sh --extras=vision,data,export   # ağır isteğe bağlı gruplar (varsayılan: voice,control,ocr)
#   ./install.sh --full          # tüm isteğe bağlı gruplar
#   ./install.sh --minimal       # yalnızca çekirdek (en az indirme: ~155 MB; ses tanıma / fare kontrolü / OCR yok)
#   ./install.sh --keep-torch-dev  # PyTorch başlık/test dosyalarını silme (C++ eklentisi / torch.compile için)
#   ./install.sh -y              # soru sorma
# ═══════════════════════════════════════════════════════════════════════════════
# Not: macOS'un bash'i 3.2'dir; bu betik ilişkisel dizi / ${x^^} gibi bash 4
# özelliklerini kullanmaz.
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$APP_DIR/.venv"
BREW_PKGS=1; DESKTOP=1; WITH_DOTNET=0; YES=0; STRIP_TORCH=1
EXTRAS="voice,control,ocr"

for arg in "$@"; do
  case "$arg" in
    --no-brew|--no-system) BREW_PKGS=0 ;;
    --no-desktop)   DESKTOP=0 ;;
    --with-dotnet)  WITH_DOTNET=1 ;;
    --extras=*)     EXTRAS="voice,control,ocr,${arg#*=}" ;;
    --full)         EXTRAS="voice,control,ocr,vision,data,export" ;;
    --minimal)      EXTRAS="" ;;
    --keep-torch-dev) STRIP_TORCH=0 ;;
    -y|--yes)       YES=1 ;;
    -h|--help)      sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "Bilinmeyen seçenek: $arg"; exit 1 ;;
  esac
done

c_ok=$'\e[32m'; c_warn=$'\e[33m'; c_err=$'\e[31m'; c_dim=$'\e[90m'; c_b=$'\e[1m'; c_0=$'\e[0m'
step() { echo -e "\n${c_b}▸ $*${c_0}"; }
ok()   { echo -e "  ${c_ok}✓${c_0} $*"; }
warn() { echo -e "  ${c_warn}!${c_0} $*"; }
die()  { echo -e "  ${c_err}✗ $*${c_0}"; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }
ask()  { # ask "soru" → 0 = evet
  (( YES )) && return 0
  local a; read -r -p "  $1 [Y/n] " a || a="y"; [[ ! "$a" =~ ^[Nn] ]]
}

echo -e "${c_b}Nova AGI — macOS kurulumu${c_0}  ${c_dim}($APP_DIR)${c_0}"
[[ "$(uname -s)" == "Darwin" ]] || die "Bu dal macOS içindir. Linux için 'claude-verison' dalını kullanın."
[[ "$(uname -m)" == "arm64" ]] || warn "Intel Mac algılandı: GPU (MPS) hızlandırması yok, CPU kullanılacak."

# Homebrew'un PATH'te olmadığı durumlar (yeni terminal / .app'ten çağrı)
for d in /opt/homebrew/bin /usr/local/bin; do
  [[ -x "$d/brew" && ":$PATH:" != *":$d:"* ]] && PATH="$d:$PATH"
done

# ── 1. Homebrew paketleri ────────────────────────────────────────────────────
if (( BREW_PKGS )); then
  step "Homebrew paketleri"
  if have brew; then
    # portaudio → mikrofon (pyaudio), tesseract → ekrandan yazı okuma, python-tk → yedek arayüz
    PY_MINOR="$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")' 2>/dev/null || echo "")"
    PKGS="portaudio tesseract tesseract-lang"
    [[ -n "$PY_MINOR" ]] && [[ "$(command -v python3)" == "$(brew --prefix)"/* ]] && PKGS="$PKGS python-tk@$PY_MINOR"
    MISSING=""
    for p in $PKGS; do brew list --formula "$p" >/dev/null 2>&1 || MISSING="$MISSING $p"; done
    if [[ -z "$MISSING" ]]; then
      ok "Zaten kurulu: $PKGS"
    else
      echo -e "  ${c_dim}Eksik:$MISSING  (tesseract-lang ~650 MB; Türkçe OCR için gerekli)${c_0}"
      if ask "Bu paketler kurulsun mu?"; then
        for p in $MISSING; do
          if brew install -q "$p" >/dev/null 2>&1; then ok "$p"; else warn "atlandı: $p"; fi
        done
      fi
    fi
  else
    warn "Homebrew yok → mikrofon, OCR ve Tk arayüzü olmadan devam ediliyor. Kurmak için: https://brew.sh"
  fi
fi

# ── 2. Python sanal ortamı ───────────────────────────────────────────────────
step "Python sanal ortamı"
have python3 || die "python3 bulunamadı (brew install python)."
python3 - <<'PY' || die "Python 3.10 veya üstü gerekli (brew install python)."
import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)
PY
if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV" || die "venv oluşturulamadı."
fi
PY="$VENV/bin/python"
ok "$("$PY" --version) → $VENV"

# ── 3. PyTorch (Metal / MPS dahil) ───────────────────────────────────────────
step "PyTorch"
if "$PY" -c "import torch" 2>/dev/null; then
  ok "PyTorch zaten kurulu: $("$PY" -c 'import torch; print(torch.__version__)') (indirme yok)"
else
  # macOS paketi tek tiptir (~130 MB) ve Apple GPU (MPS) desteğini içerir
  "$PY" -m pip install --no-cache-dir torch numpy || die "PyTorch kurulamadı."
  ok "PyTorch $("$PY" -c 'import torch; print(torch.__version__)')"
fi
"$PY" -c "import torch; print('  MPS (Apple GPU):', 'hazır' if torch.backends.mps.is_available() else 'yok → CPU')"
# PyTorch parça parça kurulamaz; Nova yalnızca torch.nn / optim kullandığı için
# çalışma zamanında gerekmeyen C++ test ikilileri ve başlık dosyaları silinir.
TORCH_DIR="$("$PY" -c 'import torch, os; print(os.path.dirname(torch.__file__))')"
if (( STRIP_TORCH )) && [[ "$TORCH_DIR" == "$VENV"/* ]] && [[ -d "$TORCH_DIR/include" ]]; then
  before=$(du -sm "$TORCH_DIR" | cut -f1)
  find "$TORCH_DIR/bin" -type f ! -name torch_shm_manager -delete 2>/dev/null || true
  rm -rf "$TORCH_DIR/test" "$TORCH_DIR/include" "$TORCH_DIR/share/cmake" \
         "$TORCH_DIR"/lib/libtorchbind_test.* "$TORCH_DIR"/lib/libjitbackend_test.* "$TORCH_DIR"/lib/libbackend_with_compiler.*
  "$PY" -c "import torch; torch.nn.Linear(4, 4)(torch.zeros(1, 4)).sum().backward()" || die "PyTorch temizliği sonrası test başarısız."
  ok "Gereksiz PyTorch dosyaları silindi: ${before} MB → $(du -sm "$TORCH_DIR" | cut -f1) MB"
fi

# ── 4. Python paketleri ──────────────────────────────────────────────────────
step "Python paketleri"
"$PY" -m pip install -q --no-cache-dir -r "$APP_DIR/requirements.txt" || die "Çekirdek paketler kurulamadı."
ok "Çekirdek paketler"
echo -e "  ${c_dim}İsteğe bağlı gruplar: ${EXTRAS:-yok (--minimal)}${c_0}"
# pyaudio, Homebrew'un portaudio'sunu bulabilsin
if have brew && brew list --formula portaudio >/dev/null 2>&1; then
  BP="$(brew --prefix)"; export CFLAGS="-I$BP/include ${CFLAGS:-}"; export LDFLAGS="-L$BP/lib ${LDFLAGS:-}"
fi
while read -r line; do
  pkg="${line%%#*}"; pkg="${pkg// /}"
  grp="$(sed -n 's/.*# *\[\([a-z]*\)\].*/\1/p' <<<"$line")"
  [[ -z "$pkg" || -z "$grp" ]] && continue
  [[ -n "$EXTRAS" && ",$EXTRAS," == *",$grp,"* ]] || continue
  if "$PY" -m pip install -q --no-cache-dir "$pkg" >/dev/null 2>&1; then ok "$pkg"; else warn "$pkg kurulamadı (isteğe bağlı)"; fi
done < "$APP_DIR/requirements-extra.txt"
ok "Python ortamı: $(du -sh "$VENV" | cut -f1)"

# ── 5. Masaüstü uygulaması (Nova AGI.app) ────────────────────────────────────
if (( DESKTOP )); then
  step "Masaüstü uygulaması"
  DOTNET="$(command -v dotnet || true)"
  [[ -z "$DOTNET" && -x "$HOME/.dotnet/dotnet" ]] && DOTNET="$HOME/.dotnet/dotnet"
  if [[ -z "$DOTNET" && $WITH_DOTNET -eq 1 ]]; then
    if have brew; then
      brew install -q dotnet >/dev/null && DOTNET="$(command -v dotnet || true)"
    else
      curl -sSL https://dot.net/v1/dotnet-install.sh -o "${TMPDIR:-/tmp}/dotnet-install.sh"
      bash "${TMPDIR:-/tmp}/dotnet-install.sh" --channel 9.0 --install-dir "$HOME/.dotnet" >/dev/null && DOTNET="$HOME/.dotnet/dotnet"
    fi
  fi
  # .NET yoksa ama sürüm arşivinden hazır gelen build/Nova AGI.app varsa o kurulur
  if [[ -n "$DOTNET" || -d "$APP_DIR/build/Nova AGI.app" ]]; then
    if DOTNET="$DOTNET" "$APP_DIR/packaging/build_app.sh" --install; then
      ok "Nova AGI.app → ~/Applications (Launchpad ve Spotlight'ta görünür)"
    else
      warn "Uygulama derlenemedi; ./nova.sh tk ile yedek arayüz kullanılabilir."
    fi
  else
    warn ".NET SDK yok → Nova AGI.app derlenmedi. Kurmak için: ./install.sh --with-dotnet"
  fi
  chmod +x "$APP_DIR/nova.sh" "$APP_DIR/uninstall.sh"
fi

# ── Özet ─────────────────────────────────────────────────────────────────────
step "Hazır!"
"$PY" "$APP_DIR/gpu_setup.py" 2>/dev/null | grep -E "Seçilen|GPU|CPU|PyTorch" | sed 's/^/  /' || true
cat <<EOF

  ${c_b}Başlatma${c_0}
    open ~/Applications/"Nova AGI.app"   masaüstü uygulaması (veya Launchpad / Spotlight)
    ./nova.sh term       terminal sohbeti
    ./nova.sh web        telefon / tarayıcı erişimi
    ./nova.sh doctor     donanım, bağımlılık ve izin kontrolü

  ${c_b}macOS izinleri${c_0} ${c_dim}(ilk kullanımda sorulur; Sistem Ayarları › Gizlilik ve Güvenlik)${c_0}
    Ekran Kaydı → ekran izleme · Erişilebilirlik → fare/klavye · Mikrofon → sesli komut
EOF
