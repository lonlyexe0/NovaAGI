# ═══════════════════════════════════════════════════════════════════════════════
# mac_desktop.py  —  Nova AGI macOS Masaüstü Entegrasyonu
# ═══════════════════════════════════════════════════════════════════════════════
#
# Linux sürümündeki pipewire / espeak-ng / grim / wpctl / loginctl / xdotool
# çağrılarının macOS karşılıkları. Hepsi sistemle birlikte gelir; Homebrew gerekmez.
#
#   Ses çalma   : afplay
#   TTS yedeği  : say  (tr: Yelda · en: Moira / Samantha)
#   Ekran       : mss (CoreGraphics) · screencapture
#   Ses düzeyi  : osascript (set volume)
#   Kilit       : ⌃⌘Q (Erişilebilirlik izni) · pmset displaysleepnow
#   Pencere     : lsappinfo · osascript (System Events)
#
# macOS izinleri (Sistem Ayarları → Gizlilik ve Güvenlik):
#   Ekran Kaydı      → ekran görüntüsü / !watch
#   Erişilebilirlik  → fare-klavye kontrolü, pencere başlığı, ⌃⌘Q kilidi
#   Mikrofon         → sesli komut
# İzin yoksa fonksiyonlar çökmez; None / "" / False döner ve log'a nereden
# açılacağını yazar.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import re
import shlex
import shutil
import ctypes
import logging
import tempfile
import subprocess
from functools import lru_cache
from typing import Dict, List, Optional, Sequence

logger = logging.getLogger("nova.mac")

# GUI'den (.app) açıldığında PATH yalnızca /usr/bin:/bin içerir; Homebrew araçları
# (tesseract, ffmpeg, cloudflared) bulunabilsin diye standart dizinler eklenir.
for _d in ("/opt/homebrew/bin", "/usr/local/bin"):
    if os.path.isdir(_d) and _d not in os.environ.get("PATH", "").split(os.pathsep):
        os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + _d


def oturum_turu() -> str:
    """'aqua' (grafik oturum) veya 'tty' (SSH vb. — ekran / klavye kontrolü yok)."""
    if os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_TTY"):
        return "tty"
    return "aqua"


def ilk_bulunan(*adaylar: str) -> Optional[str]:
    for a in adaylar:
        if shutil.which(a):
            return a
    return None


def _calistir(cmd: Sequence[str], timeout: float = 10) -> bool:
    try:
        return subprocess.run(list(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              timeout=timeout).returncode == 0
    except Exception:
        return False


def _cikti(cmd: Sequence[str], timeout: float = 3) -> str:
    try:
        return subprocess.run(list(cmd), capture_output=True, text=True, timeout=timeout,
                              errors="ignore").stdout.strip()
    except Exception:
        return ""


def _arka_planda(cmd: Sequence[str]) -> bool:
    try:
        subprocess.Popen(list(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        return True
    except Exception:
        return False


def _osascript(betik: str, timeout: float = 5) -> bool:
    return _calistir(["osascript", "-e", betik], timeout=timeout)


# ── İzinler (TCC) ─────────────────────────────────────────────────────────────

@lru_cache(maxsize=None)
def _framework(ad: str):
    try:
        return ctypes.cdll.LoadLibrary(f"/System/Library/Frameworks/{ad}.framework/{ad}")
    except OSError:
        return None


def ekran_kaydi_izni() -> bool:
    """Ekran Kaydı izni verilmiş mi? (İzin yoksa ekran görüntüsünde yalnızca duvar kağıdı görünür.)"""
    cg = _framework("CoreGraphics")
    if cg is None or not hasattr(cg, "CGPreflightScreenCaptureAccess"):
        return True
    cg.CGPreflightScreenCaptureAccess.restype = ctypes.c_bool
    return bool(cg.CGPreflightScreenCaptureAccess())


def ekran_kaydi_izni_iste() -> None:
    """Sistem izin penceresini bir kez gösterir (kullanıcı reddettiyse Ayarlar'dan açılmalı)."""
    cg = _framework("CoreGraphics")
    if cg is not None and hasattr(cg, "CGRequestScreenCaptureAccess"):
        cg.CGRequestScreenCaptureAccess.restype = ctypes.c_bool
        cg.CGRequestScreenCaptureAccess()


def erisilebilirlik_izni() -> bool:
    """Erişilebilirlik izni (fare / klavye kontrolü, pencere başlığı) verilmiş mi?"""
    ax = _framework("ApplicationServices")
    if ax is None:
        return False
    ax.AXIsProcessTrusted.restype = ctypes.c_bool
    return bool(ax.AXIsProcessTrusted())


_IZIN_SAYFALARI = {
    "screen":        "Privacy_ScreenCapture",
    "accessibility": "Privacy_Accessibility",
    "microphone":    "Privacy_Microphone",
    "automation":    "Privacy_Automation",
}


def izin_ayarlarini_ac(tur: str) -> bool:
    """Sistem Ayarları'nda ilgili gizlilik sayfasını açar (tur: screen / accessibility / microphone)."""
    sayfa = _IZIN_SAYFALARI.get(tur)
    if not sayfa:
        return False
    return _arka_planda(["open", f"x-apple.systempreferences:com.apple.preference.security?{sayfa}"])


def izin_durumu() -> Dict[str, bool]:
    return {"screen": ekran_kaydi_izni(), "accessibility": erisilebilirlik_izni()}


# ── Ses ───────────────────────────────────────────────────────────────────────

def ses_cal(yol: str) -> Optional[subprocess.Popen]:
    """Ses dosyasını (mp3 / wav / aiff / m4a) afplay ile çalar; çağıran bekleyebilir veya sonlandırabilir."""
    if not os.path.isfile(yol):
        return None
    prog = ilk_bulunan("afplay", "ffplay", "mpv")
    if not prog:
        logger.warning("[Ses] afplay bulunamadı.")
        return None
    args = {"afplay": [], "ffplay": ["-nodisp", "-autoexit", "-loglevel", "quiet"],
            "mpv": ["--no-video", "--really-quiet"]}[prog]
    try:
        return subprocess.Popen([prog, *args, yol], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        logger.debug(f"[Ses] Çalma hatası: {e}")
        return None


@lru_cache(maxsize=1)
def _yuklu_sesler() -> frozenset:
    adlar = set()
    for satir in _cikti(["say", "-v", "?"], timeout=5).splitlines():
        # "Moira               en_IE    # …"  /  "Yelda (Türkçe (Türkiye)) tr_TR    # …"
        m = re.match(r"^(.+?)\s+[a-z]{2,3}_[A-Z0-9]{2,3}\s+#", satir)
        if m:
            adlar.add(m.group(1).split(" (")[0].strip())
    return frozenset(adlar)


def _say_sesi(lang: str) -> Optional[str]:
    adaylar = ("Yelda",) if lang == "tr" else ("Moira", "Samantha", "Daniel", "Karen")
    yuklu = _yuklu_sesler()
    return next((s for s in adaylar if s in yuklu), None)


def yerel_tts_komutu(metin: str, lang: str = "tr") -> Optional[List[str]]:
    """Çevrimdışı TTS komutu (macOS 'say')."""
    if not shutil.which("say"):
        return None
    ses = _say_sesi(lang)
    return ["say", *(["-v", ses] if ses else []), "-r", "185", metin]


def tts_dosyaya(metin: str, lang: str, wav_yolu: str) -> bool:
    """'say' ile WAV dosyası üretir (web / telefon arayüzü için)."""
    cmd = yerel_tts_komutu(metin, lang)
    if not cmd:
        return False
    cmd = cmd[:-1] + ["--file-format=WAVE", "--data-format=LEI16@22050", "-o", wav_yolu, metin]
    return _calistir(cmd, timeout=30) and os.path.getsize(wav_yolu) > 0


# ── Ekran ─────────────────────────────────────────────────────────────────────

_izin_uyarildi = False


def ekran_goruntusu():
    """Tüm ekranların görüntüsünü PIL.Image (RGB) olarak döner; alınamazsa None.

    mss nokta (point) çözünürlüğünde, screencapture Retina pikseliyle döner; fare
    koordinatlarına çevirmek için oran görüntü boyutundan hesaplanmalıdır (body._olcek).
    """
    global _izin_uyarildi
    try:
        from PIL import Image
    except ImportError:
        logger.warning("[Ekran] Pillow kurulu değil (pip install pillow).")
        return None
    if oturum_turu() == "tty":
        return None

    if not ekran_kaydi_izni():
        if not _izin_uyarildi:
            _izin_uyarildi = True
            logger.warning("[Ekran] Ekran Kaydı izni yok → Sistem Ayarları › Gizlilik ve Güvenlik › "
                           "Ekran ve Sistem Sesi Kaydı'ndan Nova AGI'ye (veya Terminal'e) izin verin.")
            ekran_kaydi_izni_iste()
        return None

    try:
        import mss
        with mss.mss() as sct:
            shot = sct.grab(sct.monitors[0])
            return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    except Exception as e:
        logger.debug(f"[Ekran] mss başarısız: {e}")

    fd, tmp = tempfile.mkstemp(suffix=".png", prefix="nova_ekran_")
    os.close(fd)
    try:
        if _calistir(["screencapture", "-x", "-t", "png", tmp], timeout=8) and os.path.getsize(tmp) > 0:
            with Image.open(tmp) as img:
                return img.convert("RGB")
    except Exception as e:
        logger.debug(f"[Ekran] screencapture hatası: {e}")
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    logger.warning("[Ekran] Ekran görüntüsü alınamadı.")
    return None


def aktif_pencere_basligi() -> str:
    """Öndeki uygulamanın adı; Erişilebilirlik izni varsa 'Uygulama — Pencere başlığı'."""
    if oturum_turu() == "tty":
        return ""
    m = re.match(r'^"([^"]+)"', _cikti(["lsappinfo", "info", "-only", "name", _cikti(["lsappinfo", "front"])]))
    uygulama = m.group(1) if m else ""
    if uygulama and erisilebilirlik_izni():
        baslik = _cikti(["osascript", "-e",
                         'tell application "System Events" to tell (first application process whose frontmost is true) '
                         'to get name of front window'])
        if baslik and baslik != uygulama:
            return f"{uygulama} — {baslik}"
    return uygulama


# ── Sistem Eylemleri ──────────────────────────────────────────────────────────

def _ses_duzeyi(islem: str) -> bool:
    """islem: 'up' / 'down' / 'mute'"""
    betik = {
        "up":   "set volume output volume ((output volume of (get volume settings)) + 10) without output muted",
        "down": "set volume output volume ((output volume of (get volume settings)) - 10)",
        "mute": "set volume output muted (not (output muted of (get volume settings)))",
    }[islem]
    return _osascript(betik)


def _kilitle() -> bool:
    # ⌃⌘Q gerçek kilit ekranıdır ama Erişilebilirlik izni ister; yoksa ekranı uyut
    # (varsayılan "uyku sonrası hemen parola iste" ayarıyla kilitlenir).
    if erisilebilirlik_izni() and _osascript(
            'tell application "System Events" to keystroke "q" using {control down, command down}'):
        return True
    return _calistir(["pmset", "displaysleepnow"])


def _masaustu_goster() -> bool:
    # Finder dışındaki görünür uygulamaları gizler (⌥⌘H + Finder'ı öne alma ile aynı etki)
    return _osascript('tell application "System Events" to set visible of '
                      '(every process whose visible is true and name is not "Finder") to false') and \
        _osascript('tell application "Finder" to activate')


def _gorev_yoneticisi() -> bool:
    return _calistir(["open", "-a", "Activity Monitor"])


def sistem_eylemi(eylem: str, en: bool = False) -> str:
    """Web/GUI'den gelen sistem eylemlerini çalıştırır."""
    e = eylem.lower().strip()
    tablo = {
        ("lock", "kilitle"):                    (_kilitle, "🔒 Ekran kilitlendi.", "🔒 Screen locked."),
        ("mute", "sessiz"):                     (lambda: _ses_duzeyi("mute"), "🔇 Ses açıldı/kapatıldı.", "🔇 Mute toggled."),
        ("vol_up", "ses_artir"):                (lambda: _ses_duzeyi("up"), "🔊 Ses artırıldı.", "🔊 Volume up."),
        ("vol_down", "ses_azalt"):              (lambda: _ses_duzeyi("down"), "🔉 Ses azaltıldı.", "🔉 Volume down."),
        ("desktop", "masaustu", "minimize_all"): (_masaustu_goster, "🖥️ Masaüstü gösterildi.", "🖥️ Showing desktop."),
        ("taskmgr", "gorev_yoneticisi"):        (_gorev_yoneticisi, "⚙️ Etkinlik Monitörü açıldı.", "⚙️ Activity Monitor opened."),
    }
    for anahtarlar, (fn, tr_msg, en_msg) in tablo.items():
        if e in anahtarlar:
            if fn():
                return en_msg if en else tr_msg
            return (f"⚠️ '{e}' could not be run (macOS may be blocking it: System Settings › Privacy & Security › "
                    f"Accessibility / Automation)." if en else
                    f"⚠️ '{e}' çalıştırılamadı (macOS engelliyor olabilir: Sistem Ayarları › Gizlilik ve Güvenlik › "
                    f"Erişilebilirlik / Otomasyon).")
    return f"Unknown action: {e}" if en else f"Bilinmeyen eylem: {e}"


def uygulama_ac(komut: str) -> str:
    """Uygulama, dosya veya URL açar. Örn: 'Safari', 'https://…', '~/Belgeler', 'code .'"""
    komut = komut.strip()
    if not komut:
        return "Komut boş."
    hedef = os.path.expanduser(komut)
    if re.match(r"^[a-z][a-z0-9+.-]*://", komut) or os.path.exists(hedef):
        return f"Açıldı: {komut}" if _calistir(["open", hedef]) else f"Açılamadı: {komut}"
    # Uygulama adı (Safari, "Visual Studio Code", Notes …)
    if _calistir(["open", "-Ra", komut], timeout=5):
        return f"Açıldı: {komut}" if _calistir(["open", "-a", komut]) else f"Açılamadı: {komut}"
    try:
        parcalar = shlex.split(komut)
    except ValueError as e:
        return f"Hata: {e}"
    if not shutil.which(parcalar[0]):
        return f"Bulunamadı: {parcalar[0]}"
    return f"Açıldı: {komut}" if _arka_planda(parcalar) else f"Açılamadı: {komut}"
