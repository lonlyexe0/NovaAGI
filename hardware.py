# ═══════════════════════════════════════════════════════════════════════════════
# hardware.py  —  Nova AGI Donanım Algılama ve Profil Modülü (Linux)
# ═══════════════════════════════════════════════════════════════════════════════
#
# GPU algılama sırası:
#   1. PyTorch CUDA  (NVIDIA CUDA veya AMD ROCm/HIP)
#   2. PyTorch XPU   (Intel Arc / Data Center GPU)
#   3. nvidia-smi / rocm-smi / sysfs (/sys/class/drm) + lspci  (PyTorch GPU görmüyorsa)
#
# Statik donanım bilgisi bir kez toplanır ve önbelleklenir; telemetri çağrıları
# sadece anlık değerleri (RAM, ayrılmış VRAM) yeniden okur.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import re
import glob
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
                              errors="ignore").stdout
    except Exception:
        return ""


def _read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    except OSError:
        return ""


def _fmt_vram(mb: int) -> str:
    return f"{mb / 1024:.0f} GB" if mb >= 1024 else (f"{mb} MB" if mb else "—")


# ── CPU ───────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_cpu_info() -> Dict[str, Any]:
    """İşlemci adı ve thread sayısı (/proc/cpuinfo)."""
    raw = ""
    for line in _read("/proc/cpuinfo").splitlines():
        if line.startswith(("model name", "Hardware", "Model")):
            raw = line.split(":", 1)[1].strip()
            break
    if not raw:
        raw = platform.processor() or platform.machine() or "Generic CPU"

    full = " ".join(raw.split())
    clean = full
    for r in ("(R)", "(TM)", "Processor", "CPU", "with Radeon Graphics", "Six-Core",
              "Eight-Core", "Quad-Core", "Dual-Core", "Core(TM)"):
        clean = clean.replace(r, "")
    clean = re.sub(r"@.*$", "", " ".join(clean.split())).strip()

    m = re.search(r"(Ryzen\s+(?:Threadripper\s+)?\d+\s+\w+|Core\s+i\d-\w+|i\d-\w+|Core\s+Ultra\s+\d+\s+\w+|Xeon\s+\S+|EPYC\s+\S+)",
                  clean, re.I)
    short = m.group(0).strip() if m else clean[:24].strip()
    return {"full_name": full, "short_name": short or full, "threads": os.cpu_count() or 1}


# ── GPU ───────────────────────────────────────────────────────────────────────

def _torch_gpus() -> List[Dict[str, Any]]:
    try:
        import torch
    except Exception:
        return []

    gpus: List[Dict[str, Any]] = []
    try:
        if torch.cuda.is_available():
            backend = "ROCm" if getattr(torch.version, "hip", None) else "CUDA"
            for i in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(i)
                name = props.name.strip("\x00 \t\n\r")
                vram = props.total_memory // (1024 ** 2)
                gpus.append({
                    "index": i, "name": name,
                    "short_name": re.sub(r"^(NVIDIA\s+(GeForce\s+)?|AMD\s+Radeon\s+)", "", name).strip(),
                    "backend": backend, "vram_mb": vram, "vram_allocated_mb": 0,
                    "vram_str": _fmt_vram(vram), "is_gpu": True,
                })
            if gpus:
                return gpus
    except Exception:
        pass

    try:
        xpu = getattr(torch, "xpu", None)
        if xpu is not None and xpu.is_available():
            for i in range(xpu.device_count()):
                props = xpu.get_device_properties(i)
                vram = getattr(props, "total_memory", 0) // (1024 ** 2)
                name = str(getattr(props, "name", f"Intel XPU {i}"))
                gpus.append({
                    "index": i, "name": name, "short_name": name.replace("Intel(R) ", ""),
                    "backend": "XPU", "vram_mb": vram, "vram_allocated_mb": 0,
                    "vram_str": _fmt_vram(vram), "is_gpu": True,
                })
    except Exception:
        pass
    return gpus


def _lspci_names() -> Dict[str, str]:
    """PCI slot → cihaz adı (VGA / 3D / Display denetleyicileri)."""
    names: Dict[str, str] = {}
    for line in _run(["lspci", "-mm"]).splitlines():
        parts = re.findall(r'"([^"]*)"', line)
        if len(parts) >= 3 and re.search(r"VGA|3D|Display", parts[0]):
            slot = line.split()[0]
            vendor = parts[1].replace("Advanced Micro Devices, Inc. [AMD/ATI]", "AMD").replace(" Corporation", "")
            names[slot] = f"{vendor} {parts[2]}".strip()
    return names


def _os_gpus() -> List[Dict[str, Any]]:
    """PyTorch GPU görmediğinde işletim sistemi seviyesinde GPU listesi."""
    gpus: List[Dict[str, Any]] = []

    out = _run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"])
    for line in out.splitlines():
        try:
            name, mem = [p.strip() for p in line.split(",")[:2]]
            vram = int(float(mem))
        except ValueError:
            continue
        gpus.append({"index": len(gpus), "name": name, "short_name": name.replace("NVIDIA ", ""),
                     "backend": "Sistem", "vram_mb": vram, "vram_allocated_mb": 0,
                     "vram_str": _fmt_vram(vram), "is_gpu": True})
    if gpus:
        return gpus

    pci_names = _lspci_names()
    for card in sorted(glob.glob("/sys/class/drm/card[0-9]")):
        dev = os.path.join(card, "device")
        slot = os.path.basename(os.path.realpath(dev))  # 0000:03:00.0
        vendor = _read(os.path.join(dev, "vendor"))
        vram_raw = _read(os.path.join(dev, "mem_info_vram_total"))  # amdgpu
        vram = int(vram_raw) // (1024 ** 2) if vram_raw.isdigit() else 0
        name = pci_names.get(slot.split(":", 1)[-1], "")
        if not name:
            name = {"0x1002": "AMD GPU", "0x10de": "NVIDIA GPU", "0x8086": "Intel GPU"}.get(vendor, "GPU")
        gpus.append({"index": len(gpus), "name": name,
                     "short_name": re.sub(r"^(AMD|NVIDIA|Intel)\s+", "", name),
                     "backend": "Sistem", "vram_mb": vram, "vram_allocated_mb": 0,
                     "vram_str": _fmt_vram(vram), "is_gpu": True})
    return gpus


@lru_cache(maxsize=1)
def _static_gpus() -> tuple:
    gpus = _torch_gpus() or _os_gpus()
    return tuple(gpus) if gpus else (dict(_CPU_FALLBACK),)


def get_all_gpus() -> List[Dict[str, Any]]:
    """Tüm GPU'lar (statik bilgi önbellekten, ayrılmış VRAM canlı)."""
    gpus = [dict(g) for g in _static_gpus()]
    if gpus and gpus[0]["backend"] in ("CUDA", "ROCm", "XPU"):
        try:
            import torch
            mod = torch.xpu if gpus[0]["backend"] == "XPU" else torch.cuda
            for g in gpus:
                g["vram_allocated_mb"] = int(mod.memory_allocated(g["index"]) // (1024 ** 2))
        except Exception:
            pass
    return gpus


def get_gpu_info() -> Dict[str, Any]:
    """GPU özeti; çoklu GPU'da toplu metrik üretir."""
    devices = get_all_gpus()
    active = [g for g in devices if g.get("is_gpu")]
    if not active:
        return {"name": "Yok (CPU modu)", "short_name": "CPU", "backend": "CPU", "count": 0,
                "is_multi_gpu": False, "vram_mb": 0, "vram_str": "—", "is_gpu": False,
                "devices": devices}

    count = len(active)
    if count == 1:
        g = active[0]
        return {"name": g["name"], "short_name": g["short_name"], "backend": g["backend"],
                "count": 1, "is_multi_gpu": False, "vram_mb": g["vram_mb"],
                "vram_str": g["vram_str"], "is_gpu": True, "devices": active}

    names = [g["short_name"] for g in active]
    multi_name = f"{count}x {names[0]}" if len(set(names)) == 1 else " + ".join(names[:3])
    total = sum(g["vram_mb"] for g in active)
    return {"name": multi_name, "short_name": multi_name, "backend": active[0]["backend"],
            "count": count, "is_multi_gpu": True, "vram_mb": total,
            "vram_str": f"{_fmt_vram(total)} toplam" if total else f"{count} aygıt",
            "is_gpu": True, "devices": active}


# ── RAM / OS ──────────────────────────────────────────────────────────────────

def get_ram_info() -> Dict[str, Any]:
    """Toplam ve kullanılabilir RAM (/proc/meminfo)."""
    total = avail = 0
    for line in _read("/proc/meminfo").splitlines():
        if line.startswith("MemTotal:"):
            total = int(line.split()[1])
        elif line.startswith("MemAvailable:"):
            avail = int(line.split()[1])
    return {"total_gb": round(total / 1024 ** 2, 1), "free_gb": round(avail / 1024 ** 2, 1)}


@lru_cache(maxsize=1)
def get_os_name() -> str:
    for line in _read("/etc/os-release").splitlines():
        if line.startswith("PRETTY_NAME="):
            return line.split("=", 1)[1].strip('"')
    return f"{platform.system()} {platform.release()}"


def get_optimal_cpu_threads() -> int:
    return max(1, os.cpu_count() or 4)


def get_optimal_workers() -> int:
    t = os.cpu_count() or 4
    return max(1, t - 1) if t <= 4 else 4 if t <= 8 else 6 if t <= 16 else 8


def get_system_summary(lang: Optional[str] = None) -> str:
    """GUI ve loglar için sistem özeti."""
    cpu, gpu, ram = get_cpu_info(), get_gpu_info(), get_ram_info()
    gpu_text = gpu["name"]
    if gpu["is_gpu"]:
        gpu_text += f" [{gpu['backend']}]" + (f" ({gpu['vram_str']})" if gpu["vram_mb"] else "")
    ram_str = f"{ram['total_gb']} GB" if ram["total_gb"] else "—"
    if ram["free_gb"]:
        ram_str += f" ({ram['free_gb']} GB {'boş' if lang == 'tr' else 'free'})"
    return (f"OS: {get_os_name()} ({platform.release()})\n"
            f"Python: {platform.python_version()}\n"
            f"CPU: {cpu['short_name']} ({cpu['threads']}T)\n"
            f"GPU: {gpu_text}\n"
            f"RAM: {ram_str}")


@lru_cache(maxsize=1)
def get_hardware_profile() -> Dict[str, Any]:
    """GPU/VRAM kapasitesine göre eğitim profili (bir kez hesaplanır)."""
    gpu = get_gpu_info()
    vram, is_gpu, cores = gpu.get("vram_mb", 0), gpu.get("is_gpu", False), os.cpu_count() or 4

    if gpu.get("is_multi_gpu") or vram >= 16384:
        return {"tier": "enthusiast", "tier_name": "Tier 1: Ultra / Multi-GPU",
                "batch_size": 64 * max(1, gpu.get("count", 1)), "burst_steps": 8, "max_seq_len": 512,
                "ff_growth_factor": 1.75, "pacing_sleep": 0.001, "embed_dim": 256, "workers": min(8, cores)}
    if is_gpu and vram >= 8192:
        return {"tier": "mid_range", "tier_name": "Tier 2: Orta/Yüksek GPU",
                "batch_size": 48, "burst_steps": 6, "max_seq_len": 256,
                "ff_growth_factor": 1.5, "pacing_sleep": 0.005, "embed_dim": 192, "workers": min(6, cores)}
    if is_gpu and vram >= 3000:
        return {"tier": "entry_gpu", "tier_name": "Tier 3: Giriş Seviyesi GPU",
                "batch_size": 32, "burst_steps": 4, "max_seq_len": 256,
                "ff_growth_factor": 1.35, "pacing_sleep": 0.01, "embed_dim": 128, "workers": min(4, cores)}
    return {"tier": "cpu_mode", "tier_name": "Tier 4: CPU / Entegre Grafik",
            "batch_size": 16, "burst_steps": 2, "max_seq_len": 128,
            "ff_growth_factor": 1.25, "pacing_sleep": 0.05, "embed_dim": 128, "workers": min(2, cores)}


if __name__ == "__main__":
    print("=" * 60)
    print("🔍 Nova AGI Donanım Tespiti")
    print("=" * 60)
    print(get_system_summary())
    print("=" * 60)
    print("Profil:", get_hardware_profile())
