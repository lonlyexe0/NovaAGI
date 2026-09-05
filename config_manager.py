# ═══════════════════════════════════════════════════════════════════════════════
# config_manager.py  —  Nova AGI Konfigürasyon ve Dil Yöneticisi
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("nova.config")

CONFIG_DOSYASI = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".nova_config.json")


def get_data_dir() -> str:
    """Kullanıcı verisi için yazılabilir dizin döner."""
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    if os.access(base_dir, os.W_OK):
        return base_dir

    if sys.platform == "win32":
        user_data = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        user_data = os.environ.get("XDG_DATA_HOME") or os.path.join(
            os.path.expanduser("~"), ".local", "share"
        )
    fallback = os.path.join(user_data, "NovaAGI")
    os.makedirs(fallback, exist_ok=True)
    return fallback


def get_data_path(filename: str) -> str:
    """Veri dosyası için tam yol döner."""
    return os.path.join(get_data_dir(), filename)


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
    """
    İlk açılışta kullanıcıya İngilizce mi Türkçe mi kullanmak istediğini sorar (İngilizce olarak sorulur).
    Sonraki girişlerde tekrar sormaz, kayıtlı seçimi kullanır.
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

    # 3. Terminal etkileşimli değilse varsayılan 'en' ata
    if not sys.stdin.isatty():
        set_language("en")
        return "en"

    # 4. İlk açılış: Kullanıcıya İngilizce olarak sor
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
    print(f"{cyan}║{yesil}  [1] English (en){sifir} → Global knowledge & English Wikipedia  {cyan}║{sifir}")
    print(f"{cyan}║{sari}  [2] Türkçe  (tr){sifir} → Türkçe bilgi akışı & Türkçe Wikipedia  {cyan}║{sifir}")
    print(f"{cyan}║                                                              {cyan}║{sifir}")
    print(f"{cyan}║{gri}  (This selection will be saved for future launches)          {sifir}{cyan}║{sifir}")
    print(f"{cyan}╚══════════════════════════════════════════════════════════════╝{sifir}")

    try:
        istek = f"  Select language / Dil seçin [{kalin}1=English{sifir} / {kalin}2=Türkçe{sifir}] (Default: 1): "
        secim = input(istek).strip().lower()

        if secim in ("2", "tr", "tur", "turkce", "türkçe", "turkish"):
            secilen_dil = "tr"
            print(f"  {yesil}✅ Türkçe modu seçildi! Bilgi akışı Türkçe Wikipedia (20231101.tr) olarak ayarlandı.{sifir}\n")
        else:
            secilen_dil = "en"
            print(f"  {yesil}✅ English mode selected! Knowledge stream set to English Wikipedia (20231101.en).{sifir}\n")

        set_language(secilen_dil)
        return secilen_dil

    except (EOFError, KeyboardInterrupt):
        print(f"\n  {gri}Defaulting to English mode.{sifir}\n")
        set_language("en")
        return "en"
