# ═══════════════════════════════════════════════════════════════════════════════
# linux_desktop.py  —  Nova AGI Linux Masaüstü Entegrasyonu
# ═══════════════════════════════════════════════════════════════════════════════
#
# Windows sürümündeki winsound / winmm / GDI / user32 / Windows OCR çağrılarının
# Linux karşılıkları. X11 ve Wayland (GNOME, KDE, wlroots) oturumlarında
# mevcut araçları sırayla dener; hiçbiri yoksa sessizce None / "" döner.
#
#   Ses çalma   : pw-play · paplay · ffplay · mpv · mpg123 · aplay
#   TTS yedeği  : espeak-ng · espeak · spd-say
#   Ekran       : mss (X11) · Pillow ImageGrab · grim · gnome-screenshot · spectacle · scrot · maim
#   Ses düzeyi  : wpctl (PipeWire) · pactl (PulseAudio) · amixer (ALSA)
#   Kilit       : loginctl · xdg-screensaver · dm-tool · xflock4
# ═══════════════════════════════════════════════════════════════════════════════

import os
import shlex
import shutil
import logging
import tempfile
import subprocess
from typing import List, Optional, Sequence

logger = logging.getLogger("nova.linux")


def oturum_turu() -> str:
    """'wayland', 'x11' veya 'tty'."""
    tur = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if tur in ("wayland", "x11"):
        return tur
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("DISPLAY"):
        return "x11"
    return "tty"


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


def _arka_planda(cmd: Sequence[str]) -> bool:
    try:
        subprocess.Popen(list(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        return True
    except Exception:
        return False


# ── Ses ───────────────────────────────────────────────────────────────────────

def _oynatici_komutu(yol: str) -> Optional[List[str]]:
    mp3 = yol.lower().endswith((".mp3", ".ogg", ".opus"))
    adaylar = (
        [("ffplay", ["-nodisp", "-autoexit", "-loglevel", "quiet"]), ("mpv", ["--no-video", "--really-quiet"]),
         ("mpg123", ["-q"]), ("pw-play", []), ("paplay", [])]
        if mp3 else
        [("pw-play", []), ("paplay", []), ("aplay", ["-q"]), ("ffplay", ["-nodisp", "-autoexit", "-loglevel", "quiet"]),
         ("mpv", ["--no-video", "--really-quiet"])]
    )
    for prog, args in adaylar:
        if shutil.which(prog):
            return [prog, *args, yol]
    return None


def ses_cal(yol: str) -> Optional[subprocess.Popen]:
    """Ses dosyasını çalan süreci başlatır (çağıran bekleyebilir veya sonlandırabilir)."""
    if not os.path.isfile(yol):
        return None
    cmd = _oynatici_komutu(yol)
    if not cmd:
        logger.warning("[Ses] Oynatıcı bulunamadı (pipewire / pulseaudio-utils / ffmpeg / mpv kurun).")
        return None
    try:
        return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        logger.debug(f"[Ses] Çalma hatası: {e}")
        return None


def yerel_tts_komutu(metin: str, lang: str = "tr") -> Optional[List[str]]:
    """Çevrimdışı TTS komutu (espeak-ng / spd-say)."""
    prog = ilk_bulunan("espeak-ng", "espeak")
    if prog:
        return [prog, "-v", "tr" if lang == "tr" else "en-us", "-s", "165", metin]
    if shutil.which("spd-say"):
        return ["spd-say", "-w", "-l", lang, metin]
    return None


# ── Ekran ─────────────────────────────────────────────────────────────────────

def ekran_goruntusu():
    """Masaüstü ekran görüntüsünü PIL.Image (RGB) olarak döner; alınamazsa None."""
    try:
        from PIL import Image
    except ImportError:
        logger.warning("[Ekran] Pillow kurulu değil (pip install pillow).")
        return None

    tur = oturum_turu()
    if tur == "x11":
        try:
            import mss
            with mss.mss() as sct:
                shot = sct.grab(sct.monitors[0])
                return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        except Exception:
            pass

    if tur != "tty":
        try:
            from PIL import ImageGrab
            return ImageGrab.grab().convert("RGB")
        except Exception:
            pass

    fd, tmp = tempfile.mkstemp(suffix=".png", prefix="nova_ekran_")
    os.close(fd)
    komutlar = [
        ["grim", tmp],
        ["gnome-screenshot", "-f", tmp],
        ["spectacle", "-b", "-n", "-f", "-o", tmp],
        ["scrot", "-o", tmp],
        ["maim", tmp],
        ["import", "-window", "root", tmp],
    ]
    try:
        for cmd in komutlar:
            if shutil.which(cmd[0]) and _calistir(cmd, timeout=8) and os.path.getsize(tmp) > 0:
                with Image.open(tmp) as img:
                    return img.convert("RGB")
    except Exception as e:
        logger.debug(f"[Ekran] Yakalama hatası: {e}")
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    logger.warning("[Ekran] Ekran görüntüsü alınamadı (X11: python-mss, Wayland: grim / gnome-screenshot).")
    return None


def aktif_pencere_basligi() -> str:
    """Odaktaki pencerenin başlığı (X11: xdotool / xprop). Wayland'de boş döner."""
    if oturum_turu() != "x11":
        return ""
    try:
        if shutil.which("xdotool"):
            out = subprocess.run(["xdotool", "getactivewindow", "getwindowname"],
                                 capture_output=True, text=True, timeout=2).stdout.strip()
            if out:
                return out
        if shutil.which("xprop"):
            wid = subprocess.run(["xprop", "-root", "_NET_ACTIVE_WINDOW"], capture_output=True,
                                 text=True, timeout=2).stdout.strip().split()[-1]
            out = subprocess.run(["xprop", "-id", wid, "_NET_WM_NAME"], capture_output=True,
                                 text=True, timeout=2).stdout
            if "=" in out:
                return out.split("=", 1)[1].strip().strip('"')
    except Exception:
        pass
    return ""


# ── Sistem Eylemleri ──────────────────────────────────────────────────────────

def _ses_duzeyi(islem: str) -> bool:
    """islem: 'up' / 'down' / 'mute'"""
    if shutil.which("wpctl"):
        cmd = {"up": ["wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", "10%+"],
               "down": ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "10%-"],
               "mute": ["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"]}[islem]
        if _calistir(cmd):
            return True
    if shutil.which("pactl"):
        cmd = {"up": ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+10%"],
               "down": ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-10%"],
               "mute": ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"]}[islem]
        if _calistir(cmd):
            return True
    if shutil.which("amixer"):
        arg = {"up": "10%+", "down": "10%-", "mute": "toggle"}[islem]
        return _calistir(["amixer", "-q", "-D", "pulse", "sset", "Master", arg]) or \
            _calistir(["amixer", "-q", "sset", "Master", arg])
    return False


def _kilitle() -> bool:
    for cmd in (["loginctl", "lock-session"], ["xdg-screensaver", "lock"], ["dm-tool", "lock"],
                ["xflock4"], ["gnome-screensaver-command", "-l"]):
        if shutil.which(cmd[0]) and _calistir(cmd):
            return True
    return False


def _masaustu_goster() -> bool:
    if oturum_turu() == "x11":
        if shutil.which("wmctrl") and _calistir(["wmctrl", "-k", "on"]):
            return True
        if shutil.which("xdotool") and _calistir(["xdotool", "key", "super+d"]):
            return True
    return False


def _gorev_yoneticisi() -> bool:
    prog = ilk_bulunan("gnome-system-monitor", "plasma-systemmonitor", "ksysguard",
                       "xfce4-taskmanager", "mate-system-monitor", "lxtask", "mission-center")
    if prog:
        return _arka_planda([prog])
    term = ilk_bulunan("x-terminal-emulator", "gnome-terminal", "konsole", "xfce4-terminal", "kitty", "alacritty", "xterm")
    top = ilk_bulunan("btop", "htop", "top")
    if term and top:
        return _arka_planda([term, "--", top] if term == "gnome-terminal" else [term, "-e", top])
    return False


def sistem_eylemi(eylem: str, en: bool = False) -> str:
    """Web/GUI'den gelen sistem eylemlerini çalıştırır."""
    e = eylem.lower().strip()
    tablo = {
        ("lock", "kilitle"):                    (_kilitle, "🔒 Ekran kilitlendi.", "🔒 Screen locked."),
        ("mute", "sessiz"):                     (lambda: _ses_duzeyi("mute"), "🔇 Ses açıldı/kapatıldı.", "🔇 Mute toggled."),
        ("vol_up", "ses_artir"):                (lambda: _ses_duzeyi("up"), "🔊 Ses artırıldı.", "🔊 Volume up."),
        ("vol_down", "ses_azalt"):              (lambda: _ses_duzeyi("down"), "🔉 Ses azaltıldı.", "🔉 Volume down."),
        ("desktop", "masaustu", "minimize_all"): (_masaustu_goster, "🖥️ Masaüstü gösterildi.", "🖥️ Showing desktop."),
        ("taskmgr", "gorev_yoneticisi"):        (_gorev_yoneticisi, "⚙️ Sistem izleyici açıldı.", "⚙️ System monitor opened."),
    }
    for anahtarlar, (fn, tr_msg, en_msg) in tablo.items():
        if e in anahtarlar:
            if fn():
                return en_msg if en else tr_msg
            return (f"⚠️ '{e}' could not be run on this desktop ({oturum_turu()})." if en else
                    f"⚠️ '{e}' bu masaüstünde çalıştırılamadı ({oturum_turu()}); gerekli araç eksik olabilir.")
    return f"Unknown action: {e}" if en else f"Bilinmeyen eylem: {e}"


def uygulama_ac(komut: str) -> str:
    """Uygulama, dosya veya URL açar (xdg-open desteği ile)."""
    komut = komut.strip()
    if not komut:
        return "Komut boş."
    hedef = os.path.expanduser(komut)
    if komut.startswith(("http://", "https://")) or os.path.exists(hedef):
        return f"Açıldı: {komut}" if _arka_planda(["xdg-open", hedef]) else f"Açılamadı: {komut}"
    try:
        parcalar = shlex.split(komut)
    except ValueError as e:
        return f"Hata: {e}"
    if not shutil.which(parcalar[0]):
        return f"Bulunamadı: {parcalar[0]}"
    return f"Açıldı: {komut}" if _arka_planda(parcalar) else f"Açılamadı: {komut}"
