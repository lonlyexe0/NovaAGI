# ═══════════════════════════════════════════════════════════════════════════════
# gpu_setup.py  —  Nova AGI macOS GPU / CPU Hazırlık Katmanı
# ═══════════════════════════════════════════════════════════════════════════════
#
# PyTorch import edilmeden ÖNCE çağrılmalıdır (ortam değişkenleri torch
# başlatılırken okunur). Desteklenen arka uçlar:
#   1. MPS  — Apple Silicon GPU (Metal)   pip install torch  (macOS paketi MPS içerir)
#   2. CPU  — Fallback
#
# Ayarlardaki "device" (auto / mps / cpu) değeri tercih olarak kullanılır.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import logging

import hardware

logger = logging.getLogger("nova.gpu")

_threads = str(hardware.get_optimal_cpu_threads())
for _var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS",
             "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_var, _threads)
# MPS'te henüz olmayan bir işlem çıkarsa hata vermek yerine o işlem CPU'da çalışsın
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")


def _tercih_edilen_cihaz() -> str:
    try:
        import config_manager
        return str(config_manager.get_setting("device", "auto")).lower()
    except Exception:
        return "auto"


def _cpu_hazirla(torch) -> None:
    n = hardware.get_optimal_cpu_threads()
    torch.set_num_threads(n)
    try:
        torch.set_num_interop_threads(max(1, min(4, n // 2)))
    except RuntimeError:
        pass  # interop thread sayısı yalnızca bir kez ayarlanabilir
    logger.info(f"[GPU] 💻 CPU modu — {hardware.get_cpu_info()['full_name']} ({n} thread)")


def gpu_hazirla() -> str:
    """
    GPU'yu algılar ve yapılandırır. Sonucu NOVA_DEVICE ortam değişkenine yazar.
    Döner: "mps" veya "cpu".
    """
    if os.environ.get("NOVA_DEVICE"):
        return os.environ["NOVA_DEVICE"]

    tercih = _tercih_edilen_cihaz()
    cihaz = "cpu"
    try:
        import torch

        if tercih in ("auto", "mps", "metal", "gpu") and torch.backends.mps.is_available():
            gpu = hardware.get_gpu_info()
            logger.info(f"[GPU] ⚡ Apple Metal (MPS) etkin: {gpu['name']} | Paylaşımlı bellek: {gpu['vram_str']}")
            cihaz = "mps"
        else:
            if tercih in ("auto", "mps") and not torch.backends.mps.is_built():
                logger.warning("[GPU] Bu PyTorch derlemesi MPS desteği içermiyor; CPU kullanılacak.")
            _cpu_hazirla(torch)
    except ImportError:
        logger.warning("[GPU] PyTorch kurulu değil! ./install.sh çalıştırın.")
    except Exception as e:
        logger.warning(f"[GPU] Algılama hatası, CPU kullanılacak: {e}")

    os.environ["NOVA_DEVICE"] = cihaz
    return cihaz


def vram_durumu() -> dict:
    gpu = hardware.get_gpu_info()
    if gpu["is_gpu"]:
        return {"gpu": gpu["name"], "mod": f"{gpu['backend']} ({gpu['vram_str']})",
                "toplam_mb": gpu["vram_mb"] or "Dinamik"}
    return {"gpu": "Yok (CPU modu)", "toplam_mb": 0}


KURULUM_REHBERI = """
  NOVA — PYTORCH KURULUMU (macOS)
  ───────────────────────────────
  Apple Silicon (M1 ve sonrası) : pip install torch   (Metal / MPS desteği dahil)

  Otomatik kurulum için:  ./install.sh
  Doğrulama:              ./nova.sh doctor
"""


if __name__ == "__main__":
    import platform
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    print("\n🔍 Nova GPU Algılama Testi\n" + "=" * 50)
    print(f"Seçilen cihaz : {gpu_hazirla().upper()}")
    for k, v in vram_durumu().items():
        print(f"  {k:<12}: {v}")
    print("-" * 50)
    print(hardware.get_system_summary())
    try:
        import torch
        print(f"PyTorch       : {torch.__version__} | MPS: {torch.backends.mps.is_available()}"
              f" (derleme: {torch.backends.mps.is_built()})")
    except ImportError:
        print(KURULUM_REHBERI)
    print(f"Platform      : {platform.system()} {platform.machine()}")
