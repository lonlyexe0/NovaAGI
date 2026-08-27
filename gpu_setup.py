# ═══════════════════════════════════════════════════════════════════════════════
# gpu_setup.py  —  Nova AMD RX 6500 XT + Ryzen 5600X Optimizasyon Katmanı
# ═══════════════════════════════════════════════════════════════════════════════
#
# Bu dosya main.py veya nova_launcher.py tarafından EN BAŞTA import edilir.
# Mevcut hiçbir dosyayı değiştirmez — sadece ortam değişkenlerini ve
# PyTorch ayarlarını yapılandırır.
#
# Desteklenen arka uçlar (otomatik algılama sırası):
#   1. ROCm   — Linux  + AMD GPU (pip install torch --index-url rocm)
#   2. DirectML— Windows + AMD GPU (pip install torch-directml)
#   3. CPU     — Fallback (Ryzen 5600X optimizeli, 12 thread)
#
# RX 6500 XT — RDNA 2 (gfx1035) — 4 GB GDDR6
# Ryzen 5600X — 6 çekirdek / 12 thread
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys
import platform
import logging

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger("nova.gpu")


import hardware

# ══════════════════════════════════════════════════════════════════════════════
# CPU İŞ PARÇACIĞI VE DONANIM DİNAMİK YAPILANDIRMASI
# ══════════════════════════════════════════════════════════════════════════════

_opt_threads = str(hardware.get_optimal_cpu_threads())

os.environ["OMP_NUM_THREADS"]        = _opt_threads
os.environ["MKL_NUM_THREADS"]        = _opt_threads
os.environ["OPENBLAS_NUM_THREADS"]   = _opt_threads
os.environ["VECLIB_MAXIMUM_THREADS"] = _opt_threads
os.environ["NUMEXPR_NUM_THREADS"]    = _opt_threads

# Bellek ayırma optimizasyonu
os.environ["MALLOC_ARENA_MAX"]       = "4"
os.environ["PYTORCH_NO_CUDA_MEMORY_CACHING"] = "0"



# ══════════════════════════════════════════════════════════════════════════════
# AMD RX 6500 XT — ROCm / DirectML ALGILAMA
# ══════════════════════════════════════════════════════════════════════════════

def _rocm_kurulu_mu() -> bool:
    """ROCm kütüphanelerinin sistemde var olup olmadığını kontrol et."""
    rocm_yollar = [
        "/opt/rocm",
        "/opt/rocm-5.7.0",
        "/opt/rocm-6.0.0",
        "/opt/rocm-6.1.0",
        "/opt/rocm-6.2.0",
    ]
    return any(os.path.isdir(p) for p in rocm_yollar)


def _directml_kurulu_mu() -> bool:
    """torch-directml paketi kurulu mu kontrol et."""
    try:
        import torch_directml  # noqa
        return True
    except ImportError:
        return False


def gpu_hazirla() -> str:
    """
    GPU'yu algıla, yapılandır ve kullanılacak cihaz adını döndür.
    Döner: "cuda", "privateuseone" (DirectML) veya "cpu"
    """
    sistemios = platform.system()   # "Linux" veya "Windows"

    # ── 1. CUDA / ROCm (Linux / Windows NVIDIA veya ROCm) ──────────────────────
    try:
        import torch
        if torch.cuda.is_available():
            gpu_adi    = torch.cuda.get_device_name(0)
            gpu_bellek = torch.cuda.get_device_properties(0).total_memory // (1024**2)

            if hasattr(torch.backends, "cuda") and hasattr(torch.backends.cuda, "matmul"):
                torch.backends.cuda.matmul.allow_tf32 = True
            if hasattr(torch.backends, "cudnn"):
                torch.backends.cudnn.allow_tf32 = True

            os.environ["PYTORCH_CUDA_ALLOC_CONF"] = (
                "max_split_size_mb:512,"
                "garbage_collection_threshold:0.8"
            )

            logger.info(
                f"[GPU] 🔥 CUDA/ROCm etkin: {gpu_adi} | VRAM: {gpu_bellek} MB"
            )
            return "cuda"
    except Exception as e:
        logger.debug(f"[GPU] CUDA/ROCm kontrol hatası: {e}")

    # ── 2. DirectML (Windows - AMD / Intel / NVIDIA) ─────────────────────────
    if _directml_kurulu_mu():
        try:
            import torch_directml
            cihaz = torch_directml.device()
            dev_name = torch_directml.device_name(0)
            logger.info(
                f"[GPU] ⚡ DirectML etkin — Windows GPU modu | Cihaz: {dev_name}"
            )
            return "privateuseone"
        except Exception as e:
            logger.warning(f"[GPU] DirectML başlatma başarısız: {e}")

    # ── 3. CPU Fallback (Dinamik CPU optimize) ────────────────────────────────
    try:
        import torch
        cpu_threads = hardware.get_optimal_cpu_threads()
        torch.set_num_threads(cpu_threads)
        torch.set_num_interop_threads(max(1, min(4, cpu_threads // 2)))

        if hasattr(torch, "set_flush_denormal"):
            torch.set_flush_denormal(True)

        cpu_info = hardware.get_cpu_info()
        logger.info(
            f"[GPU] 💻 CPU modu — {cpu_info['full_name']} ({cpu_threads} thread) | "
            "GPU bulunamadı veya sürücü eksik"
        )
    except Exception:
        pass

    return "cpu"


# ══════════════════════════════════════════════════════════════════════════════
# BRAIN.PY CONFIG'İNİ YAMALA (import sırası önemli!)
# ══════════════════════════════════════════════════════════════════════════════

def brain_config_yamala():
    """
    brain.py'nin Config sınıfının device alanını GPU algılama sonucuyla güncelle.
    brain.py import EDİLMEDEN önce çağrılmalı.
    """
    cihaz = gpu_hazirla()

    # brain.py henüz import edilmediyse, import sonrası Config'i güncelle
    if "brain" in sys.modules:
        sys.modules["brain"].Config.device = cihaz
        logger.info(f"[GPU] Config.device güncellendi → {cihaz}")
    else:
        # brain.py ilk import'ta bu env'i okuyacak
        os.environ["NOVA_DEVICE"] = cihaz

    return cihaz


# ══════════════════════════════════════════════════════════════════════════════
# VRAM VE MODEL BOYUTU OPTİMİZASYONU
# ══════════════════════════════════════════════════════════════════════════════

VRAM_GUVENLI_BATCH  = 32    # Standart güvenli batch boyutu
VRAM_GUVENLI_SEQ    = 384   # Maksimum sequence length


def vram_durumu() -> dict:
    """GPU VRAM durumunu dinamik olarak döndür."""
    try:
        gpu_info = hardware.get_gpu_info()
        if gpu_info["is_gpu"]:
            return {
                "gpu": gpu_info["name"],
                "mod": f"{gpu_info['backend']} ({gpu_info.get('vram_str', 'Aktif')})",
                "toplam_mb": gpu_info["vram_mb"] if gpu_info["vram_mb"] > 0 else "Dinamik/Sistem",
            }
    except Exception:
        pass
    return {"gpu": "Yok (CPU modu)", "toplam_mb": 0}


# ══════════════════════════════════════════════════════════════════════════════
# KURULUM REHBERİ
# ══════════════════════════════════════════════════════════════════════════════

KURULUM_REHBERI = """
╔══════════════════════════════════════════════════════════════════════╗
║         NOVA GPU / PYTORCH KURULUM REHBERİ                           ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  🐧 LINUX (ROCm / CUDA — Önerilen):                                  ║
║     pip install torch torchvision torchaudio                         ║
║                                                                      ║
║  🪟 WINDOWS (NVIDIA CUDA / AMD DirectML):                            ║
║     pip install torch torchvision torchaudio                         ║
║     pip install torch-directml                                       ║
║                                                                      ║
║  🍎 MACOS (Apple Silicon MPS):                                       ║
║     pip install torch torchvision torchaudio                         ║
║                                                                      ║
║  ✅ Doğrulama:                                                       ║
║     python gpu_setup.py                                              ║
╚══════════════════════════════════════════════════════════════════════╝
"""


# ── Doğrudan çalıştırma: GPU test modu ───────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(message)s"
    )

    print("\n🔍 Nova GPU Algılama Testi")
    print("=" * 50)

    cihaz = gpu_hazirla()
    print(f"\n✅ Seçilen cihaz : {cihaz.upper()}")

    durum = vram_durumu()
    for k, v in durum.items():
        print(f"   {k:<15}: {v}")

    print(f"\n{'─'*50}")
    print(f"Platform        : {platform.system()} {platform.machine()}")
    print(f"Python          : {platform.python_version()}")

    try:
        import torch
        print(f"PyTorch         : {torch.__version__}")
        print(f"CUDA/ROCm var  : {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"GPU adı         : {torch.cuda.get_device_name(0)}")
    except ImportError:
        print("PyTorch         : Kurulu değil!")
        print(KURULUM_REHBERI)

    cpu_info = hardware.get_cpu_info()
    print(f"\nİşlemci: {cpu_info['full_name']} ({os.environ.get('OMP_NUM_THREADS', '?')} thread)")
    print("\n" + "=" * 50)

    print("\n" + "=" * 50)
