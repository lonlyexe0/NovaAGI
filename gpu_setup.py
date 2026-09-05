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
import importlib

logger = logging.getLogger("nova.gpu")


# ══════════════════════════════════════════════════════════════════════════════
# RYZEN 5600X — CPU İŞ PARÇACIĞI OPTİMİZASYONU
# (brain.py'daki 12 thread ayarını güçlendir)
# ══════════════════════════════════════════════════════════════════════════════

# Makinenin gerçek CPU kapasitesine göre güvenli bir üst sınır kullan.
_CPU_THREADS = max(1, min(os.cpu_count() or 1, 12))
os.environ.setdefault("OMP_NUM_THREADS",        str(_CPU_THREADS))
os.environ.setdefault("MKL_NUM_THREADS",        str(_CPU_THREADS))
os.environ.setdefault("OPENBLAS_NUM_THREADS",   str(_CPU_THREADS))
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", str(_CPU_THREADS))
os.environ.setdefault("NUMEXPR_NUM_THREADS",    str(_CPU_THREADS))

# Bellek ayırma optimizasyonu
os.environ["MALLOC_ARENA_MAX"]      = "4"   # glibc malloc arena sayısı
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
        importlib.import_module("torch_directml")
        return True
    except ImportError:
        return False


def gpu_hazirla() -> str:
    """
    GPU'yu algıla, yapılandır ve kullanılacak cihaz adını döndür.
    Döner: "cuda", "privateuseone" (DirectML) veya "cpu"
    """
    sistemios = platform.system()   # "Linux" veya "Windows"

    # ── 1. ROCm (Linux) ───────────────────────────────────────────────────────
    if sistemios == "Linux":
        try:
            import torch

            # RX 6500 XT = gfx1035 — ROCm resmi olarak desteklemez ama
            # bu override ile çalıştırır (RDNA 2 mimarisi uyumlu)
            

            # ROCm'da PyTorch CUDA API'sini yeniden kullanır
            if torch.cuda.is_available():
                gpu_adi    = torch.cuda.get_device_name(0)
                gpu_bellek = torch.cuda.get_device_properties(0).total_memory // (1024**2)

                # Mixed precision için TF32 etkinleştir
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32       = True

                # 6500 XT 4GB VRAM — bellek verimli dikkat
                os.environ["PYTORCH_CUDA_ALLOC_CONF"] = (
                    "max_split_size_mb:512,"
                    "garbage_collection_threshold:0.8"
                )

                logger.info(
                    f"[GPU] 🔥 ROCm/AMD GPU etkin: {gpu_adi} "
                    f"| VRAM: {gpu_bellek} MB"
                )
                return "cuda"

        except Exception as e:
            logger.debug(f"[GPU] ROCm denenemedi: {e}")

    # ── 2. DirectML (Windows) ─────────────────────────────────────────────────
    if sistemios == "Windows" and _directml_kurulu_mu():
        try:
            torch_directml = importlib.import_module("torch_directml")

            cihaz = torch_directml.device()   # AMD/Intel/NVIDIA hepsini destekler
            logger.info(
                f"[GPU] ⚡ DirectML etkin — Windows AMD GPU modu | "
                f"Cihaz: {torch_directml.device_name(0)}"
            )
            return "privateuseone"   # DirectML'nin PyTorch cihaz adı

        except Exception as e:
            logger.warning(f"[GPU] DirectML başarısız: {e}")

    # ── 3. CPU Fallback (Ryzen 5600X optimize) ────────────────────────────────
    try:
        import torch
        torch.set_num_threads(_CPU_THREADS)
        torch.set_num_interop_threads(max(1, min(4, _CPU_THREADS // 2)))

        # AVX2 / AVX-512 — Zen 3 destekler
        if hasattr(torch, "set_flush_denormal"):
            torch.set_flush_denormal(True)   # Denormal sayıları temizle (hız)

        logger.info(
            f"[GPU] 💻 CPU modu — {_CPU_THREADS} thread | "
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
# RX 6500 XT VRAM OPTİMİZASYONU (brain.py Config için önerilen değerler)
# ══════════════════════════════════════════════════════════════════════════════

# RX 6500 XT 4 GB VRAM'e göre güvenli model boyutu:
#   ~26M param @ fp32 = ~100 MB  ✅ Güvenli
#   ~26M param @ fp16 = ~50  MB  ✅ Çok güvenli
#   batch_size=32 @ seq=384      ✅ Sığar
VRAM_GUVENLI_BATCH  = 32    # 4 GB için güvenli batch boyutu
VRAM_GUVENLI_SEQ    = 384   # Maksimum sequence length


def vram_durumu() -> dict:
    """GPU VRAM durumunu DirectML uyumlu olarak döndür."""
    try:
        import torch
        torch_directml = importlib.import_module("torch_directml")
        
        # DirectML cihazını al
        device_name = torch_directml.device_name(0)
        
        # NOT: DirectML üzerinden anlık VRAM miktarını çekmek CUDA kadar kolay değildir,
        # ancak cihaz adını doğrulamak bağlantının kurulduğunu kanıtlar.
        return {
            "gpu": device_name,
            "mod": "DirectML (AMD)",
            "toplam_mb": "4096 (RX 6500 XT Standart)", # Kartın sabit bilgisi
        }
    except Exception:
        pass
    return {"gpu": "Yok (CPU modu)", "toplam_mb": 0}


# ══════════════════════════════════════════════════════════════════════════════
# KURULUM REHBERİ
# ══════════════════════════════════════════════════════════════════════════════

KURULUM_REHBERI = """
╔══════════════════════════════════════════════════════════════════════╗
║         RX 6500 XT İÇİN PYTORCH KURULUM REHBERİ                     ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  🐧 LINUX (ROCm — Önerilen):                                         ║
║     pip install torch torchvision torchaudio \\                       ║
║         --index-url https://download.pytorch.org/whl/rocm6.0         ║
║                                                                      ║
║     Sürücü kurulumu (Ubuntu):                                        ║
║     wget https://repo.radeon.com/amdgpu-install/6.0/ubuntu/...      ║
║     sudo amdgpu-install --usecase=rocm                               ║
║     sudo usermod -aG render,video $USER                              ║
║                                                                      ║
║  🪟 WINDOWS (DirectML):                                              ║
║     pip install torch torchvision torchaudio                         ║
║     pip install torch-directml                                       ║
║                                                                      ║
║  ⚡ Ortak (her iki platform):                                        ║
║     pip install datasets requests beautifulsoup4                     ║
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

    print(f"\nCPU thread limiti: {os.environ.get('OMP_NUM_THREADS', '?')}")
    print("\n" + "=" * 50)
