# ═══════════════════════════════════════════════════════════════════════════════
# hardware.py  —  Nova AGI Donanım Algılama ve Profil Modülü (macOS)
# ═══════════════════════════════════════════════════════════════════════════════
#
#   CPU : sysctl (machdep.cpu.brand_string, performans / verimlilik çekirdekleri)
#   GPU : Apple Silicon (ioreg AGXAccelerator) → PyTorch MPS (Metal)
#   RAM : psutil (yoksa sysctl hw.memsize)
#
# Apple Silicon'da bellek birleşiktir (unified memory): GPU'nun "VRAM"i, Metal'in
# önerdiği üst sınırdır (toplam RAM'in ~%65-75'i).
#
# Statik donanım bilgisi bir kez toplanır ve önbelleklenir; telemetri çağrıları
# sadece anlık değerleri (RAM, ayrılmış GPU belleği) yeniden okur.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import re
import shutil
import platform
import subprocess
from functools import lru_cache
from typing import Dict, Any, List, Optional

_CPU_FALLBACK = {
    "index": 0, "name": "Yok (CPU modu)", "short_name": "CPU", "backend": "CPU",
    "vram_mb": 0, "vram_allocated_mb": 0, "vram_str": "—", "is_gpu": False,
}


def _run(cmd: List[str], timeout: float = 3.0) -> str:
    """Komutu çalıştırır; yoksa / hata verirse boş string döner."""
    if not shutil.which(cmd[0]):
        return ""
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              errors="ignore").stdout.strip()
    except Exception:
        return ""


def _sysctl(ad: str) -> str:
    return _run(["sysctl", "-n", ad])


def _sysctl_int(ad: str) -> int:
    v = _sysctl(ad)
    return int(v) if v.isdigit() else 0


def _fmt_vram(mb: int) -> str:
    return f"{mb / 1024:.0f} GB" if mb >= 1024 else (f"{mb} MB" if mb else "—")


def apple_silicon() -> bool:
    return platform.system() == "Darwin" and platform.machine() == "arm64"


# ── CPU ───────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_cpu_info() -> Dict[str, Any]:
    """İşlemci adı, thread ve performans / verimlilik çekirdeği sayısı."""
    full = " ".join((_sysctl("machdep.cpu.brand_string") or platform.processor()
                     or platform.machine() or "Generic CPU").split())
    clean = re.sub(r"\(R\)|\(TM\)|CPU|Processor|@.*$", "", full)
    short = " ".join(clean.split())[:24] or full
    perf, eff = _sysctl_int("hw.perflevel0.physicalcpu"), _sysctl_int("hw.perflevel1.physicalcpu")
    return {"full_name": full, "short_name": short, "threads": os.cpu_count() or 1,
            "perf_cores": perf, "efficiency_cores": eff}


# ── GPU ───────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _apple_gpu() -> Dict[str, Any]:
    """Apple Silicon GPU adı ve çekirdek sayısı (ioreg; izin gerektirmez)."""
    out = _run(["ioreg", "-rc", "AGXAccelerator", "-d1"])
    model = re.search(r'"model"\s*=\s*"([^"]+)"', out)
    cores = re.search(r'"gpu-core-count"\s*=\s*(\d+)', out)
    return {"model": model.group(1) if model else get_cpu_info()["short_name"],
            "cores": int(cores.group(1)) if cores else 0}


def _mps_hazir() -> bool:
    try:
        import torch
        return bool(torch.backends.mps.is_available())
    except Exception:
        return False


def _gpu_bellek_mb() -> int:
    """Metal'in GPU için önerdiği bellek üst sınırı (birleşik bellek)."""
    try:
        import torch
        rec = torch.mps.recommended_max_memory()
        if rec:
            return int(rec // (1024 ** 2))
    except Exception:
        pass
    total = get_ram_info()["total_gb"] * 1024
    return int(total * (0.75 if total > 36 * 1024 else 0.66))


@lru_cache(maxsize=1)
def _static_gpus() -> tuple:
    if not apple_silicon():
        return (dict(_CPU_FALLBACK),)
    g = _apple_gpu()
    mps = _mps_hazir()
    vram = _gpu_bellek_mb()
    cekirdek = f" ({g['cores']}-core GPU)" if g["cores"] else " GPU"
    return ({
        "index": 0, "name": f"{g['model']}{cekirdek}", "short_name": g["model"],
        "backend": "MPS" if mps else "Metal", "vram_mb": vram, "vram_allocated_mb": 0,
        "vram_str": f"{_fmt_vram(vram)} paylaşımlı", "is_gpu": mps, "gpu_cores": g["cores"],
    },)


def get_all_gpus() -> List[Dict[str, Any]]:
    """Tüm GPU'lar (statik bilgi önbellekten, ayrılmış bellek canlı)."""
    gpus = [dict(g) for g in _static_gpus()]
    if gpus and gpus[0]["backend"] == "MPS":
        try:
            import torch
            gpus[0]["vram_allocated_mb"] = int(torch.mps.current_allocated_memory() // (1024 ** 2))
        except Exception:
            pass
    return gpus


def get_gpu_info() -> Dict[str, Any]:
    """GPU özeti (Apple Silicon'da tek, birleşik bellekli GPU)."""
    devices = get_all_gpus()
    active = [g for g in devices if g.get("is_gpu")]
    if not active:
        return {"name": "Yok (CPU modu)", "short_name": "CPU", "backend": "CPU", "count": 0,
                "is_multi_gpu": False, "vram_mb": 0, "vram_str": "—", "is_gpu": False,
                "devices": devices}
    g = active[0]
    return {"name": g["name"], "short_name": g["short_name"], "backend": g["backend"],
            "count": 1, "is_multi_gpu": False, "vram_mb": g["vram_mb"],
            "vram_str": g["vram_str"], "is_gpu": True, "devices": active}


# ── RAM / OS ──────────────────────────────────────────────────────────────────

def get_ram_info() -> Dict[str, Any]:
    """Toplam ve kullanılabilir RAM."""
    try:
        import psutil
        vm = psutil.virtual_memory()
        return {"total_gb": round(vm.total / 1024 ** 3, 1), "free_gb": round(vm.available / 1024 ** 3, 1)}
    except Exception:
        total = _sysctl_int("hw.memsize")
        return {"total_gb": round(total / 1024 ** 3, 1), "free_gb": 0}


@lru_cache(maxsize=1)
def get_os_name() -> str:
    ver = platform.mac_ver()[0] or _run(["sw_vers", "-productVersion"])
    return f"macOS {ver}" if ver else f"{platform.system()} {platform.release()}"


def get_optimal_cpu_threads() -> int:
    # Apple Silicon'da matris işlemleri performans çekirdeklerinde en hızlı;
    # verimlilik çekirdeklerine taşan thread'ler yavaşlatır.
    perf = get_cpu_info().get("perf_cores") or 0
    return max(1, perf or os.cpu_count() or 4)


def get_optimal_workers() -> int:
    t = os.cpu_count() or 4
    return max(1, t - 1) if t <= 4 else 4 if t <= 8 else 6 if t <= 16 else 8


def get_system_summary(lang: Optional[str] = None) -> str:
    """GUI ve loglar için sistem özeti."""
    cpu, gpu, ram = get_cpu_info(), get_gpu_info(), get_ram_info()
    gpu_text = gpu["name"]
    if gpu["is_gpu"]:
        gpu_text += f" [{gpu['backend']}]" + (f" ({gpu['vram_str']})" if gpu["vram_mb"] else "")
    cekirdek = (f"{cpu['perf_cores']}P+{cpu['efficiency_cores']}E" if cpu.get("perf_cores")
                else f"{cpu['threads']}T")
    ram_str = f"{ram['total_gb']} GB" if ram["total_gb"] else "—"
    if ram["free_gb"]:
        ram_str += f" ({ram['free_gb']} GB {'boş' if lang == 'tr' else 'free'})"
    return (f"OS: {get_os_name()} ({platform.machine()})\n"
            f"Python: {platform.python_version()}\n"
            f"CPU: {cpu['short_name']} ({cekirdek})\n"
            f"GPU: {gpu_text}\n"
            f"RAM: {ram_str}")


@lru_cache(maxsize=1)
def get_hardware_profile() -> Dict[str, Any]:
    """GPU belleği kapasitesine göre eğitim profili (bir kez hesaplanır)."""
    gpu = get_gpu_info()
    vram, is_gpu, cores = gpu.get("vram_mb", 0), gpu.get("is_gpu", False), os.cpu_count() or 4

    if is_gpu and vram >= 24576:      # M-serisi Pro/Max/Ultra, 36 GB+ RAM
        return {"tier": "enthusiast", "tier_name": "Tier 1: Apple Silicon Pro/Max",
                "batch_size": 64, "burst_steps": 8, "max_seq_len": 512,
                "ff_growth_factor": 1.75, "pacing_sleep": 0.001, "embed_dim": 256, "workers": min(8, cores)}
    if is_gpu and vram >= 8192:       # 16–24 GB RAM
        return {"tier": "mid_range", "tier_name": "Tier 2: Apple Silicon (16 GB+)",
                "batch_size": 48, "burst_steps": 6, "max_seq_len": 256,
                "ff_growth_factor": 1.5, "pacing_sleep": 0.005, "embed_dim": 192, "workers": min(6, cores)}
    if is_gpu and vram >= 3000:       # 8 GB RAM
        return {"tier": "entry_gpu", "tier_name": "Tier 3: Apple Silicon (8 GB)",
                "batch_size": 32, "burst_steps": 4, "max_seq_len": 256,
                "ff_growth_factor": 1.35, "pacing_sleep": 0.01, "embed_dim": 128, "workers": min(4, cores)}
    return {"tier": "cpu_mode", "tier_name": "Tier 4: CPU",
            "batch_size": 16, "burst_steps": 2, "max_seq_len": 128,
            "ff_growth_factor": 1.25, "pacing_sleep": 0.05, "embed_dim": 128, "workers": min(2, cores)}


if __name__ == "__main__":
    print("=" * 60)
    print("🔍 Nova AGI Donanım Tespiti")
    print("=" * 60)
    print(get_system_summary())
    print("=" * 60)
    print("Profil:", get_hardware_profile())
