# ═══════════════════════════════════════════════════════════════════════════════
# gpu_setup.py  —  Nova AGI Linux GPU / CPU Hazırlık Katmanı
# ═══════════════════════════════════════════════════════════════════════════════
#
# PyTorch import edilmeden ÖNCE çağrılmalıdır (ortam değişkenleri torch
# başlatılırken okunur). Desteklenen arka uçlar:
#   1. CUDA  — NVIDIA           (pip install torch)
#   2. ROCm  — AMD Radeon       (pip install torch --index-url .../rocm6.x)
#   3. XPU   — Intel Arc        (pip install torch --index-url .../xpu)
#   4. CPU   — Fallback
#
# Ayarlardaki "device" (auto / cuda / xpu / cpu) değeri tercih olarak kullanılır.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import glob
import logging

import hardware

logger = logging.getLogger("nova.gpu")

_threads = str(hardware.get_optimal_cpu_threads())
for _var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_var, _threads)
os.environ.setdefault("MALLOC_ARENA_MAX", "4")
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
os.environ.setdefault("PYTORCH_HIP_ALLOC_CONF", "expandable_segments:True")


def _rocm_gfx_override() -> None:
    """
    Resmi ROCm listesinde olmayan tüketici Radeon kartları (ör. RX 6500 XT = gfx1034,
    RX 7600 = gfx1102) için HSA_OVERRIDE_GFX_VERSION ayarlar. Kullanıcı zaten
    ayarladıysa dokunmaz.
    """
    if "HSA_OVERRIDE_GFX_VERSION" in os.environ:
        return
    for props in glob.glob("/sys/class/kfd/kfd/topology/nodes/*/properties"):
        try:
            with open(props, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("gfx_target_version"):
                        v = int(line.split()[1])
                        if 100301 <= v < 100400:      # RDNA2 (gfx1031-1036)
                            os.environ["HSA_OVERRIDE_GFX_VERSION"] = "10.3.0"
                        elif 110001 <= v < 110100:    # RDNA3 (gfx1101/1102/1103)
                            os.environ["HSA_OVERRIDE_GFX_VERSION"] = "11.0.0"
                        if "HSA_OVERRIDE_GFX_VERSION" in os.environ:
                            logger.info(f"[GPU] ROCm uyumluluk: HSA_OVERRIDE_GFX_VERSION="
                                        f"{os.environ['HSA_OVERRIDE_GFX_VERSION']} (gfx {v})")
                            return
        except (OSError, ValueError, IndexError):
            continue


_rocm_gfx_override()


def _tercih_edilen_cihaz() -> str:
    try:
        import config_manager
        return str(config_manager.get_setting("device", "auto")).lower()
    except Exception:
        return "auto"


def gpu_hazirla() -> str:
    """
    GPU'yu algılar ve yapılandırır. Sonucu NOVA_DEVICE ortam değişkenine yazar.
    Döner: "cuda", "xpu" veya "cpu".
    """
    if os.environ.get("NOVA_DEVICE"):
        return os.environ["NOVA_DEVICE"]

    tercih = _tercih_edilen_cihaz()
    cihaz = "cpu"
    try:
        import torch

        if tercih in ("auto", "cuda", "rocm") and torch.cuda.is_available():
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
            torch.backends.cudnn.benchmark = True
            props = torch.cuda.get_device_properties(0)
            backend = "ROCm" if getattr(torch.version, "hip", None) else "CUDA"
            logger.info(f"[GPU] 🔥 {backend} etkin: {props.name} | VRAM: {props.total_memory // 1024**2} MB")
            cihaz = "cuda"
        elif tercih in ("auto", "xpu") and getattr(torch, "xpu", None) is not None and torch.xpu.is_available():
            logger.info(f"[GPU] ⚡ Intel XPU etkin: {torch.xpu.get_device_name(0)}")
            cihaz = "xpu"
        else:
            n = hardware.get_optimal_cpu_threads()
            torch.set_num_threads(n)
            try:
                torch.set_num_interop_threads(max(1, min(4, n // 2)))
            except RuntimeError:
                pass  # interop thread sayısı yalnızca bir kez ayarlanabilir
            torch.set_flush_denormal(True)
            logger.info(f"[GPU] 💻 CPU modu — {hardware.get_cpu_info()['full_name']} ({n} thread)")
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
  NOVA — PYTORCH KURULUMU (Linux)
  ───────────────────────────────
  NVIDIA (CUDA) : pip install torch
  AMD (ROCm)    : pip install torch --index-url https://download.pytorch.org/whl/rocm6.2
  Intel (XPU)   : pip install torch --index-url https://download.pytorch.org/whl/xpu
  Sadece CPU    : pip install torch --index-url https://download.pytorch.org/whl/cpu

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
        print(f"PyTorch       : {torch.__version__} | CUDA/ROCm: {torch.cuda.is_available()}"
              f" | HIP: {getattr(torch.version, 'hip', None)}")
    except ImportError:
        print(KURULUM_REHBERI)
    print(f"Platform      : {platform.system()} {platform.machine()}")
