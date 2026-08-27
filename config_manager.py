# ═══════════════════════════════════════════════════════════════════════════════
# config_manager.py  —  Nova AGI Konfigürasyon ve Dil Yöneticisi
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("nova.config")


def get_data_dir() -> str:
    r"""
    Kullanici veri dizinini doner.
    Mevcut dizin yazilabilirse orayi (tasinabilir mod), degilse
    APPDATA/NovaAGI dizinini kullanir.
    """
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    test_file = os.path.join(base_dir, ".perm_test")
    try:
        with open(test_file, "w") as f:
            f.write("1")
        os.remove(test_file)
        return base_dir
    except (PermissionError, OSError):
        appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
        nova_dir = os.path.join(appdata, "NovaAGI")
        os.makedirs(nova_dir, exist_ok=True)
        return nova_dir


def get_data_path(dosya_adi: str) -> str:
    """Belirtilen dosya adı için yazılabilir veri yolu döner."""
    return os.path.join(get_data_dir(), dosya_adi)


CONFIG_DOSYASI = get_data_path(".nova_config.json")


def _config_oku() -> Dict[str, Any]:
    """Konfigürasyon dosyasını okur."""
    if os.path.exists(CONFIG_DOSYASI):
        try:
            with open(CONFIG_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"[Config] Dosya okunamadı: {e}")
    return {}


def _config_yaz(cfg: Dict[str, Any]) -> bool:
    """Konfigürasyon dosyasını kaydeder."""
    try:
        with open(CONFIG_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"[Config] Dosya yazılamadı: {e}")
        return False


def get_setting(key: str, default: Any = None) -> Any:
    """Genel bir ayar değerini okur."""
    cfg = _config_oku()
    return cfg.get(key, default)


def set_setting(key: str, val: Any) -> bool:
    """Genel bir ayar değerini kaydeder."""
    cfg = _config_oku()
    cfg[key] = val
    return _config_yaz(cfg)



def get_language() -> Optional[str]:
    """Kayıtlı dili döner ('en' veya 'tr'), henüz ayarlanmamışsa None döner."""
    cfg = _config_oku()
    lang = cfg.get("language")
    if lang in ("en", "tr"):
        return lang
    return None


def set_language(lang: str) -> bool:
    """Dili 'en' veya 'tr' olarak kaydeder."""
    lang_clean = lang.strip().lower()
    if lang_clean not in ("en", "tr"):
        if "eng" in lang_clean or "1" == lang_clean:
            lang_clean = "en"
        elif "tr" in lang_clean or "tur" in lang_clean or "2" == lang_clean:
            lang_clean = "tr"
        else:
            lang_clean = "en"

    cfg = _config_oku()
    cfg["language"] = lang_clean
    return _config_yaz(cfg)


def is_english() -> bool:
    """Mevcut dil İngilizce mi?"""
    return get_language() == "en"


def ask_language_on_first_launch(arg_lang: Optional[str] = None) -> str:
    r"""
    İlk açılışta kullanıcıya dil seçtirir.
    - exe (windowed) modda: Tkinter popup ile sorar.
    - terminal modda: konsol menüsü ile sorar.
    Sonraki açılışlarda kayıtlı seçimi kullanır.
    """
    # 1. CLI argümanı verildiyse kaydet ve dön
    if arg_lang and arg_lang.strip().lower() in ("en", "tr"):
        lang = arg_lang.strip().lower()
        set_language(lang)
        return lang

    # 2. Daha önce kaydedilmişse tekrar sorma
    kayitli_dil = get_language()
    if kayitli_dil is not None:
        return kayitli_dil

    # 3. stdin yoksa (windowed exe modu) → Tkinter GUI diyaloğu
    if sys.stdin is None or not hasattr(sys.stdin, "isatty") or not sys.stdin.isatty():
        return _ask_language_gui()

    # 4. Terminal modu: konsol menüsü
    return _ask_language_terminal()


def _ask_language_gui() -> str:
    """Tkinter ile dil seçim penceresi açar (windowed exe için)."""
    try:
        import tkinter as tk

        secim = ["en"]  # mutable container

        root = tk.Tk()
        root.title("Nova AGI — Language / Dil Seçimi")
        root.resizable(False, False)
        root.configure(bg="#1a1a2e")

        # Pencereyi ekran ortasına al
        root.update_idletasks()
        w, h = 480, 290
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        # Başlık
        tk.Label(
            root, text="🌐  Language / Dil Seçimi",
            bg="#1a1a2e", fg="#e0e0ff",
            font=("Segoe UI", 14, "bold")
        ).pack(pady=(24, 6))

        tk.Label(
            root,
            text="Select the operating language for Nova AGI\nNova AGI için çalışma dilini seçin",
            bg="#1a1a2e", fg="#9090b0",
            font=("Segoe UI", 10), justify="center"
        ).pack(pady=(0, 20))

        btn_frame = tk.Frame(root, bg="#1a1a2e")
        btn_frame.pack()

        def secen(dil: str):
            secim[0] = dil
            root.destroy()

        tk.Button(
            btn_frame, text="🇬🇧  English",
            bg="#16213e", fg="#64b5f6",
            activebackground="#0f3460", activeforeground="white",
            relief="flat", font=("Segoe UI", 12, "bold"),
            width=14, height=2, cursor="hand2",
            command=lambda: secen("en")
        ).grid(row=0, column=0, padx=14, pady=6)

        tk.Button(
            btn_frame, text="🇹🇷  Türkçe",
            bg="#16213e", fg="#81c784",
            activebackground="#0f3460", activeforeground="white",
            relief="flat", font=("Segoe UI", 12, "bold"),
            width=14, height=2, cursor="hand2",
            command=lambda: secen("tr")
        ).grid(row=0, column=1, padx=14, pady=6)

        tk.Label(
            root,
            text="(This selection is saved for future launches / Bu seçim kaydedilir)",
            bg="#1a1a2e", fg="#505070",
            font=("Segoe UI", 8)
        ).pack(pady=(16, 0))

        root.mainloop()

        set_language(secim[0])
        return secim[0]

    except Exception as e:
        logger.warning(f"[Config] GUI dil seçimi başarısız, varsayılan 'en': {e}")
        set_language("en")
        return "en"


def _ask_language_terminal() -> str:
    """Konsol üzerinden dil seçim menüsü."""
    cyan  = "\033[96m"
    yesil = "\033[92m"
    sari  = "\033[93m"
    gri   = "\033[90m"
    sifir = "\033[0m"
    kalin = "\033[1m"

    print(f"\n{cyan}╔══════════════════════════════════════════════════════════════╗{sifir}")
    print(f"{cyan}║{kalin}             🌐 LANGUAGE SELECTION / DİL SEÇİMİ               {sifir}{cyan}║{sifir}")
    print(f"{cyan}╠══════════════════════════════════════════════════════════════╣{sifir}")
    print(f"{cyan}║{sifir}  Please select the operating language for Nova AGI:          {cyan}║{sifir}")
    print(f"{cyan}║                                                              {cyan}║{sifir}")
    print(f"{cyan}║{yesil}  [1] English (en){sifir} -> Global knowledge & English Wikipedia  {cyan}║{sifir}")
    print(f"{cyan}║{sari}  [2] Türkçe  (tr){sifir} -> Türkçe bilgi akisi & Türkçe Wikipedia {cyan}║{sifir}")
    print(f"{cyan}║                                                              {cyan}║{sifir}")
    print(f"{cyan}║{gri}  (This selection will be saved for future launches)          {sifir}{cyan}║{sifir}")
    print(f"{cyan}╚══════════════════════════════════════════════════════════════╝{sifir}")

    try:
        istek = f"  Select language / Dil seçin [{kalin}1=English{sifir} / {kalin}2=Türkçe{sifir}] (Default: 1): "
        secim = input(istek).strip().lower()

        if secim in ("2", "tr", "tur", "turkce", "turkish"):
            secilen_dil = "tr"
            print(f"  {yesil}Türkçe modu secildi!{sifir}\n")
        else:
            secilen_dil = "en"
            print(f"  {yesil}English mode selected!{sifir}\n")

        set_language(secilen_dil)
        return secilen_dil

    except (EOFError, KeyboardInterrupt):
        print(f"\n  {gri}Defaulting to English mode.{sifir}\n")
        set_language("en")
        return "en"
