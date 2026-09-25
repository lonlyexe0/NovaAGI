# ═══════════════════════════════════════════════════════════════════════════════
# config_manager.py  —  Nova AGI Konfigürasyon ve Dil Yöneticisi (Linux)
# ═══════════════════════════════════════════════════════════════════════════════
#
# Veri dizini önceliği:
#   1. $NOVA_DATA_DIR
#   2. Kaynak dizininde zaten veri varsa (nova.db / .nova_config.json) → taşınabilir mod
#   3. $XDG_DATA_HOME/nova-agi  (varsayılan: ~/.local/share/nova-agi)
#
# Ayarlar dosyası mtime tabanlı önbelleklenir; yazma işlemleri atomiktir.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys
import json
import stat
import secrets
import logging
import threading
from functools import lru_cache
from typing import Optional, Dict, Any

logger = logging.getLogger("nova.config")

APP_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULTS: Dict[str, Any] = {
    "language": None,
    "device": "auto",
    "multi_gpu_enabled": True,
    "worker_threads": 4,
    "learning_rate": 3e-4,
    "batch_size": 32,
    "growth_threshold": 0.003,
    "hf_token": "",
    "curiosity_enabled": True,
    "curiosity_topics": "",
    "curiosity_interval": 20,
    "web_server_enabled": False,
    "web_server_port": 8080,
    "web_access_token": "",
    "continuous_training_enabled": True,
    "theme": "Nebula",
}


@lru_cache(maxsize=1)
def get_data_dir() -> str:
    """Yazılabilir kullanıcı veri dizinini döner (bir kez hesaplanır)."""
    env_dir = os.environ.get("NOVA_DATA_DIR")
    if env_dir:
        os.makedirs(env_dir, exist_ok=True)
        return env_dir

    if not getattr(sys, "frozen", False):
        has_data = any(os.path.exists(os.path.join(APP_DIR, f)) for f in ("nova.db", ".nova_config.json"))
        if has_data and os.access(APP_DIR, os.W_OK):
            return APP_DIR

    xdg = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    nova_dir = os.path.join(xdg, "nova-agi")
    os.makedirs(nova_dir, exist_ok=True)
    return nova_dir


def get_data_path(dosya_adi: str) -> str:
    """Belirtilen dosya adı için yazılabilir veri yolu döner."""
    return os.path.join(get_data_dir(), dosya_adi)


CONFIG_DOSYASI = get_data_path(".nova_config.json")

_lock = threading.RLock()
_cache: Dict[str, Any] = {}
_cache_mtime: float = -1.0


def _config_oku() -> Dict[str, Any]:
    """Konfigürasyonu okur (dosya değişmediyse önbellekten)."""
    global _cache, _cache_mtime
    with _lock:
        try:
            mtime = os.path.getmtime(CONFIG_DOSYASI)
        except OSError:
            _cache, _cache_mtime = {}, -1.0
            return {}
        if mtime != _cache_mtime:
            try:
                with open(CONFIG_DOSYASI, "r", encoding="utf-8") as f:
                    data = json.load(f)
                _cache = data if isinstance(data, dict) else {}
            except Exception as e:
                logger.debug(f"[Config] Dosya okunamadı: {e}")
                _cache = {}
            _cache_mtime = mtime
        return dict(_cache)


def _config_yaz(cfg: Dict[str, Any]) -> bool:
    """Konfigürasyonu atomik olarak yazar (0600 izinli; token içerir)."""
    global _cache, _cache_mtime
    with _lock:
        tmp = CONFIG_DOSYASI + ".tmp"
        try:
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, stat.S_IRUSR | stat.S_IWUSR)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            os.replace(tmp, CONFIG_DOSYASI)
            _cache, _cache_mtime = dict(cfg), os.path.getmtime(CONFIG_DOSYASI)
            return True
        except Exception as e:
            logger.error(f"[Config] Dosya yazılamadı ({CONFIG_DOSYASI}): {e}")
            return False


def get_setting(key: str, default: Any = None) -> Any:
    """Ayar değerini okur; yoksa verilen varsayılanı, o da yoksa DEFAULTS değerini döner."""
    cfg = _config_oku()
    if key in cfg:
        return cfg[key]
    return default if default is not None else DEFAULTS.get(key)


def get_all_settings() -> Dict[str, Any]:
    """Varsayılanlarla birleştirilmiş tam ayar sözlüğü."""
    merged = dict(DEFAULTS)
    merged.update(_config_oku())
    return merged


def set_setting(key: str, val: Any) -> bool:
    return update_settings({key: val})


def update_settings(values: Dict[str, Any]) -> bool:
    """Verilen anahtarları mevcut ayarlarla birleştirerek kaydeder."""
    with _lock:
        cfg = _config_oku()
        cfg.update(values)
        return _config_yaz(cfg)


def is_continuous_training_enabled() -> bool:
    return bool(get_setting("continuous_training_enabled"))


def set_continuous_training(enabled: bool) -> bool:
    return set_setting("continuous_training_enabled", bool(enabled))


def get_web_token() -> str:
    """Web/mobil erişim anahtarını döner; yoksa üretip kaydeder."""
    token = get_setting("web_access_token") or ""
    if not token:
        token = secrets.token_urlsafe(12)
        set_setting("web_access_token", token)
    return token


def get_weights_file() -> str:
    """Kullanılacak ağırlık dosyasının yolu (nova_weights_400m.pth öncelikli)."""
    cfg_val = get_setting("weights_file")
    if cfg_val:
        p = cfg_val if os.path.isabs(cfg_val) else get_data_path(cfg_val)
        if os.path.isfile(p) and os.path.getsize(p) > 0:
            return p

    for base in dict.fromkeys((get_data_dir(), APP_DIR)):
        for candidate in ("nova_weights_400m.pth", "nova_weights.pth"):
            cp = os.path.join(base, candidate)
            if os.path.isfile(cp) and os.path.getsize(cp) > 0:
                return cp
    return get_data_path("nova_weights.pth")


def set_weights_file(filename_or_path: str) -> bool:
    return set_setting("weights_file", filename_or_path)


# ── Dil ───────────────────────────────────────────────────────────────────────

def _normalize_lang(lang: str) -> str:
    l = lang.strip().lower()
    if l in ("en", "tr"):
        return l
    if l.startswith(("tr", "tur")) or l == "2":
        return "tr"
    return "en"


def get_language() -> Optional[str]:
    """Kayıtlı dil ('en' / 'tr'); ayarlanmamışsa None."""
    lang = _config_oku().get("language")
    return lang if lang in ("en", "tr") else None


def set_language(lang: str) -> bool:
    return set_setting("language", _normalize_lang(lang))


def is_english() -> bool:
    return get_language() == "en"


def ask_language_on_first_launch(arg_lang: Optional[str] = None) -> str:
    """İlk açılışta dil sorar (terminal veya Tk penceresi), sonra kayıtlı olanı kullanır."""
    if arg_lang and arg_lang.strip().lower() in ("en", "tr"):
        set_language(arg_lang)
        return arg_lang.strip().lower()

    kayitli = get_language()
    if kayitli:
        return kayitli

    if sys.stdin is not None and hasattr(sys.stdin, "isatty") and sys.stdin.isatty():
        return _ask_language_terminal()
    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        return _ask_language_gui()

    # Başsız ortam (servis, pipe): sistem yereline göre seç
    lang = "tr" if os.environ.get("LANG", "").lower().startswith("tr") else "en"
    set_language(lang)
    return lang


def _ask_language_gui() -> str:
    """Tkinter ile küçük dil seçim penceresi."""
    try:
        import tkinter as tk

        secim = ["en"]
        root = tk.Tk()
        root.title("Nova AGI — Language / Dil")
        root.resizable(False, False)
        bg, card = "#0b0e16", "#151a27"
        root.configure(bg=bg)
        w, h = 460, 250
        root.geometry(f"{w}x{h}+{(root.winfo_screenwidth() - w) // 2}+{(root.winfo_screenheight() - h) // 2}")

        tk.Label(root, text="Language / Dil", bg=bg, fg="#eef1f8",
                 font=("Sans", 15, "bold")).pack(pady=(26, 4))
        tk.Label(root, text="Select Nova's working language\nNova'nın çalışma dilini seçin",
                 bg=bg, fg="#8b93a8", font=("Sans", 10), justify="center").pack(pady=(0, 18))

        frame = tk.Frame(root, bg=bg)
        frame.pack()

        def sec(dil: str):
            secim[0] = dil
            root.destroy()

        for col, (text, dil, fg) in enumerate((("English", "en", "#7aa2ff"), ("Türkçe", "tr", "#34d399"))):
            tk.Button(frame, text=text, bg=card, fg=fg, activebackground="#1f2638",
                      activeforeground="#ffffff", relief="flat", bd=0, highlightthickness=0,
                      font=("Sans", 12, "bold"), width=12, height=2, cursor="hand2",
                      command=lambda d=dil: sec(d)).grid(row=0, column=col, padx=10)

        root.mainloop()
        set_language(secim[0])
        return secim[0]
    except Exception as e:
        logger.warning(f"[Config] GUI dil seçimi başarısız, varsayılan 'en': {e}")
        set_language("en")
        return "en"


def _ask_language_terminal() -> str:
    c, g, y, d, z, b = "\033[96m", "\033[92m", "\033[93m", "\033[90m", "\033[0m", "\033[1m"
    print(f"\n{c}{b}  🌐 LANGUAGE / DİL{z}")
    print(f"  {g}[1]{z} English   {d}— English Wikipedia & UI{z}")
    print(f"  {y}[2]{z} Türkçe    {d}— Türkçe Wikipedia & arayüz{z}")
    try:
        secim = input(f"  {b}Select / Seçin{z} [1/2] (1): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        secim = ""
    lang = "tr" if secim in ("2", "tr", "tur", "turkce", "türkçe", "turkish") else "en"
    set_language(lang)
    print(f"  {g}{'Türkçe modu seçildi.' if lang == 'tr' else 'English mode selected.'}{z}\n")
    return lang
