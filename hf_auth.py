# ═══════════════════════════════════════════════════════════════════════════════
# hf_auth.py  —  Nova AGI Hugging Face Kimlik ve Token Yöneticisi
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys
import stat
import logging
from typing import Optional, Tuple
from config_manager import get_data_path

logger = logging.getLogger("nova.hf_auth")

TOKEN_DOSYASI = get_data_path(".hf_token")


def _maskeli_token(token: str) -> str:
    """Token'ın başını ve sonunu gösterip ortasını gizler."""
    if not token:
        return ""
    if len(token) <= 8:
        return "***"
    return f"{token[:6]}...{token[-4:]}"


def hf_token_al() -> Optional[str]:
    """
    Sırasıyla ortam değişkeni, yerel .hf_token dosyası ve huggingface_hub cache'inden
    Hugging Face token'ını arar ve döner.
    """
    # 1. Ortam değişkeni kontrolü
    env_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if env_token and env_token.strip():
        return env_token.strip()

    # 2. Yerel .hf_token dosyası
    if os.path.exists(TOKEN_DOSYASI):
        try:
            with open(TOKEN_DOSYASI, "r", encoding="utf-8") as f:
                token = f.read().strip()
                if token:
                    return token
        except Exception as e:
            logger.debug(f"[HF Auth] .hf_token okunamadı: {e}")

    # 3. huggingface_hub yerel cache'i (~/.cache/huggingface/token)
    try:
        from huggingface_hub import get_token
        hub_token = get_token()
        if hub_token and hub_token.strip():
            return hub_token.strip()
    except Exception:
        pass

    return None


def hf_token_kaydet(token: str) -> bool:
    """Token'ı güvenli izinlerle (0o600) yerel .hf_token dosyasına kaydeder."""
    try:
        with open(TOKEN_DOSYASI, "w", encoding="utf-8") as f:
            f.write(token.strip())
        try:
            os.chmod(TOKEN_DOSYASI, stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            pass
        return True
    except Exception as e:
        logger.error(f"[HF Auth] Token kaydedilemedi: {e}")
        return False


def hf_token_sil() -> bool:
    """Yerel token dosyasını siler ve ortam değişkenini temizler."""
    if "HF_TOKEN" in os.environ:
        del os.environ["HF_TOKEN"]
    if "HUGGING_FACE_HUB_TOKEN" in os.environ:
        del os.environ["HUGGING_FACE_HUB_TOKEN"]
    if os.path.exists(TOKEN_DOSYASI):
        try:
            os.remove(TOKEN_DOSYASI)
            return True
        except Exception as e:
            logger.error(f"[HF Auth] Token silinemedi: {e}")
            return False
    return True


def hf_token_kaydet_ve_giris(token: str) -> Tuple[bool, str]:
    """Verilen token'ı doğrular, ortam değişkenine ekler, kaydeder ve login yapar."""
    token = token.strip()
    if not token:
        return False, "Token boş olamaz."

    os.environ["HF_TOKEN"] = token
    hf_token_kaydet(token)

    try:
        from huggingface_hub import login
        login(token=token, add_to_git_credential=False)
        return True, f"✅ Hugging Face girişi başarılı! ({_maskeli_token(token)})"
    except ImportError:
        return True, f"✅ HF_TOKEN ayarlandı ({_maskeli_token(token)}). (huggingface_hub kurulu değil)"
    except Exception as e:
        return True, f"⚠️ HF_TOKEN kaydedildi ancak hub login uyarısı: {e}"


def hf_durum_metni() -> str:
    """Mevcut HF bağlantı durumunu metin olarak döner."""
    token = hf_token_al()
    if token:
        return f"🤗 Hugging Face: 🔑 Giriş yapıldı ({_maskeli_token(token)})"
    return "🤗 Hugging Face: 🔓 Anonim Mod (HF Token girilmedi)"


def hf_giris_sor(arg_token: Optional[str] = None) -> Optional[str]:
    """
    Uygulama açılırken kullanıcıya Hugging Face ID / Token sorar.
    Varsa kaydeder veya kayıtlı olanı kullanır.
    """
    # 1. CLI argümanı verildiyse direkt kullan
    if arg_token and arg_token.strip():
        token = arg_token.strip()
        hf_token_kaydet_ve_giris(token)
        print(f"\033[92m[HF] CLI üzerinden Hugging Face token'ı yüklendi ({_maskeli_token(token)}).\033[0m")
        return token

    mevcut_token = hf_token_al()

    # 2. Terminal etkileşimli değilse (pipe, background, windowed GUI exe, vs.) mevcut token'ı ayarla ve devam et
    if sys.stdin is None or not hasattr(sys.stdin, "isatty") or not sys.stdin.isatty():
        if mevcut_token:
            os.environ["HF_TOKEN"] = mevcut_token
            try:
                from huggingface_hub import login
                login(token=mevcut_token, add_to_git_credential=False)
            except Exception:
                pass
        return mevcut_token

    # 3. Terminal etkileşimli ise kullanıcıya sor
    from config_manager import is_english
    eng = is_english()

    sari   = "\033[93m"
    yesil  = "\033[92m"
    cyan   = "\033[96m"
    gri    = "\033[90m"
    sifir  = "\033[0m"
    kalin  = "\033[1m"

    if eng:
        print(f"\n{cyan}╔══════════════════════════════════════════════════════════════╗{sifir}")
        print(f"{cyan}║{kalin}             🤗 HUGGING FACE LOGIN (HF TOKEN / ID)            {sifir}{cyan}║{sifir}")
        print(f"{cyan}╠══════════════════════════════════════════════════════════════╣{sifir}")
        print(f"{cyan}║{sifir}  Enter your Hugging Face Access Token to enable faster       {cyan}║{sifir}")
        print(f"{cyan}║{sifir}  downloads and higher API rate limits for Wikipedia streams.  {cyan}║{sifir}")
        print(f"{cyan}║{gri}  (Get your token at: https://huggingface.co/settings/tokens) {sifir}{cyan}║{sifir}")
        print(f"{cyan}╚══════════════════════════════════════════════════════════════╝{sifir}")
    else:
        print(f"\n{cyan}╔══════════════════════════════════════════════════════════════╗{sifir}")
        print(f"{cyan}║{kalin}             🤗 HUGGING FACE GİRİŞİ (HF TOKEN / ID)           {sifir}{cyan}║{sifir}")
        print(f"{cyan}╠══════════════════════════════════════════════════════════════╣{sifir}")
        print(f"{cyan}║{sifir}  Wikipedia veri akışı ve modeller için yüksek hız ve API     {cyan}║{sifir}")
        print(f"{cyan}║{sifir}  limitlerinden yararlanmak için HF Access Token girebilirsiniz.{cyan}║{sifir}")
        print(f"{cyan}║{gri}  (https://huggingface.co/settings/tokens adresinden alınabilir){sifir}{cyan}║{sifir}")
        print(f"{cyan}╚══════════════════════════════════════════════════════════════╝{sifir}")

    try:
        if mevcut_token:
            if eng:
                print(f"  {sari}Saved Token:{sifir} {yesil}{_maskeli_token(mevcut_token)}{sifir}")
                istek = (f"  Hugging Face Token/ID [{gri}Enter: Use Saved{sifir} / "
                         f"{gri}'delete': Logout{sifir} / {gri}New Token{sifir}]: ")
            else:
                print(f"  {sari}Mevcut Token:{sifir} {yesil}{_maskeli_token(mevcut_token)}{sifir}")
                istek = (f"  Hugging Face Token/ID [{gri}Enter: Kayıtlıyı Kullan{sifir} / "
                         f"{gri}'sil': Çıkış Yap{sifir} / {gri}Yeni Token{sifir}]: ")
            giris = input(istek).strip()

            if not giris:
                # Enter basıldı, mevcut olanı kullan
                os.environ["HF_TOKEN"] = mevcut_token
                try:
                    from huggingface_hub import login
                    login(token=mevcut_token, add_to_git_credential=False)
                except Exception:
                    pass
                msg_ok = f"✅ Using saved Hugging Face account ({_maskeli_token(mevcut_token)})." if eng else f"✅ Kayıtlı Hugging Face hesabı kullanılıyor ({_maskeli_token(mevcut_token)})."
                print(f"  {yesil}{msg_ok}{sifir}\n")
                return mevcut_token
            elif giris.lower() in ("sil", "cikis", "çıkış", "logout", "delete", "remove", "none", "yok"):
                hf_token_sil()
                msg_del = "ℹ️ Hugging Face token removed. Continuing in anonymous mode." if eng else "ℹ️ Hugging Face token'ı silindi. Anonim modda devam ediliyor."
                print(f"  {sari}{msg_del}{sifir}\n")
                return None
            else:
                # Yeni token girildi
                _, msg = hf_token_kaydet_ve_giris(giris)
                print(f"  {yesil}{msg}{sifir}\n")
                return giris
        else:
            istek = f"  Hugging Face Token/ID ({gri}Enter if available, or press Enter to skip{sifir}): " if eng else f"  Hugging Face Token/ID ({gri}Varsa girin, yoksa Enter ile geçin{sifir}): "
            giris = input(istek).strip()

            if not giris:
                msg_anon = "ℹ️ Continuing in anonymous mode without Hugging Face token." if eng else "ℹ️ Hugging Face anonim (tokensiz) modda devam ediliyor."
                print(f"  {gri}{msg_anon}{sifir}\n")
                return None
            else:
                _, msg = hf_token_kaydet_ve_giris(giris)
                print(f"  {yesil}{msg}{sifir}\n")
                return giris

    except (EOFError, KeyboardInterrupt):
        msg_skip = "Hugging Face login skipped." if eng else "Hugging Face girişi atlandı."
        print(f"\n  {gri}{msg_skip}{sifir}\n")
        if mevcut_token:
            os.environ["HF_TOKEN"] = mevcut_token
        return mevcut_token
