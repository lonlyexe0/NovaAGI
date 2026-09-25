# ═══════════════════════════════════════════════════════════════════════════════
# ayarlar.py  —  ayarlar.json dosyasını okur (platformdan bağımsız, elle ayarlanır)
# ═══════════════════════════════════════════════════════════════════════════════
import os
import json

KLASOR = os.path.dirname(os.path.abspath(__file__))
DOSYA = os.path.join(KLASOR, "ayarlar.json")

VARSAYILAN = {
    "cihaz": "auto",
    "cpu_thread": 0,
    "batch_size": 16,
    "ogrenme_hizi": 3e-4,
    "max_seq_len": 256,
    "kayit_araligi": 50,
    "buyume_esigi": 0.003,
    "agirlik_dosyasi": "nova_weights.pth",
    "vocab_dosyasi": "nova_vocab.json",
    "veritabani": "nova.db",
}


def _yukle() -> dict:
    ayar = dict(VARSAYILAN)
    try:
        with open(DOSYA, "r", encoding="utf-8") as f:
            ayar.update({k: v for k, v in json.load(f).items() if not k.startswith("_")})
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as e:
        print(f"[Ayarlar] ayarlar.json okunamadı ({e}), varsayılanlar kullanılıyor.")
    return ayar


AYAR = _yukle()


def yol(anahtar: str) -> str:
    """Göreli dosya yollarını proje klasörüne göre çözer."""
    p = AYAR[anahtar]
    return p if os.path.isabs(p) else os.path.join(KLASOR, p)


def thread_sayisi() -> int:
    return int(AYAR["cpu_thread"]) or (os.cpu_count() or 4)


# CPU iş parçacığı ayarı torch import edilmeden önce yapılmalı
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_v, str(thread_sayisi()))


def cihaz() -> str:
    """ayarlar.json'daki 'cihaz' değerini çözer (auto → cuda / mps / cpu)."""
    istenen = str(AYAR["cihaz"]).lower()
    if istenen != "auto":
        return istenen
    import torch
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"
