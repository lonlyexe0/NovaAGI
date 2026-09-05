# ═══════════════════════════════════════════════════════════════════════════════
# hardware.py  —  Nova AGI Evrensel Donanım Algılama ve Optimizasyon Modülü
# ═══════════════════════════════════════════════════════════════════════════════
#
# Tüm işletim sistemleri (Windows, Linux, macOS) ve donanım üreticileri
# (AMD, Intel, NVIDIA, Apple Silicon) ile %100 uyumlu dinamik donanım tespiti.
# Sıfır harici bağımlılık — Yerel OS API'leri ve güvenli fallback mekanizmaları.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys
import platform
import subprocess
import re
from typing import Dict, Any, Tuple, Optional

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass



def get_cpu_info() -> Dict[str, Any]:
    """
    İşlemci modelini, çekirdek ve thread sayısını tespit eder.
    Windows (Registry), Linux (/proc/cpuinfo), macOS (sysctl) destekler.
    """
    raw_name = ""
    threads = os.cpu_count() or 1

    # 1. Windows Registry (En doğru işlemci adını verir)
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            )
            val, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            winreg.CloseKey(key)
            raw_name = " ".join(val.split())
        except Exception:
            pass

    # 2. Linux /proc/cpuinfo
    if not raw_name and sys.platform.startswith("linux"):
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if "model name" in line or "Hardware" in line:
                        raw_name = line.split(":", 1)[1].strip()
                        break
        except Exception:
            pass

    # 3. macOS sysctl
    if not raw_name and sys.platform == "darwin":
        try:
            out = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                text=True, errors="ignore"
            ).strip()
            if out:
                raw_name = out
        except Exception:
            pass

    # 4. Fallback
    if not raw_name:
        proc = platform.processor()
        if proc and not proc.startswith("Intel64") and not proc.startswith("AMD64"):
            raw_name = proc
        else:
            raw_name = platform.machine() or "Generic CPU"

    # Temizleme ve kısa etiket oluşturma
    full_name = " ".join(raw_name.split()).strip()

    # Kısa ad (örn: "Ryzen 5 5600X", "Core i7-13700K", "Apple M2")
    short_clean = full_name
    for r in ["(R)", "(TM)", "Processor", "Six-Core", "Eight-Core", "Quad-Core", "Dual-Core", "Core(TM)"]:
        short_clean = short_clean.replace(r, "")
    short_clean = " ".join(short_clean.split())

    m = re.search(
        r"(Ryzen\s+\d+\s+\w+|Ryzen\s+\w+|i\d-\w+|Core\s+i\d-\w+|M[1-4]\s*(?:Pro|Max|Ultra)?)",
        short_clean,
        re.I
    )
    if m:
        short_label = m.group(0).strip()
    else:
        # Çok uzunsa kısalt
        short_label = short_clean[:22].strip() if len(short_clean) > 22 else short_clean

    return {
        "full_name": full_name,
        "short_name": short_label or full_name,
        "threads": threads,
    }


def get_all_gpus() -> list[Dict[str, Any]]:
    """
    Sistemdeki TÜM aktif GPU ve grafik hızlandırıcılarını tespit eder ve liste döner.
    Çoklu GPU (Multi-GPU) konfigürasyonlarını eksiksiz destekler.
    """
    gpus: list[Dict[str, Any]] = []

    # 1. PyTorch CUDA (NVIDIA / ROCm Multi-GPU)
    try:
        import torch
        if torch.cuda.is_available() and torch.cuda.device_count() > 0:
            for i in range(torch.cuda.device_count()):
                name = torch.cuda.get_device_name(i).strip("\x00 \t\n\r")
                vram = torch.cuda.get_device_properties(i).total_memory // (1024**2)
                try:
                    alloc = torch.cuda.memory_allocated(i) // (1024**2)
                except Exception:
                    alloc = 0
                gpus.append({
                    "index": i,
                    "name": name,
                    "short_name": name.replace("NVIDIA GeForce ", "").replace("NVIDIA ", "").strip(),
                    "backend": "CUDA",
                    "vram_mb": vram,
                    "vram_allocated_mb": alloc,
                    "vram_str": f"{vram} MB",
                    "is_gpu": True,
                })
            if gpus:
                return gpus
    except Exception:
        pass

    # 2. PyTorch DirectML (Windows AMD / Intel / NVIDIA Multi-GPU)
    try:
        import torch_directml
        dev_count = getattr(torch_directml, "device_count", lambda: 1)()
        
        # Windows Registry'den DirectML adaptörlerinin gerçek VRAM miktarını çek
        vram_map = {}
        if sys.platform == "win32":
            try:
                import winreg
                base_k = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
                )
                for ki in range(16):
                    try:
                        sub = winreg.OpenKey(base_k, f"{ki:04d}")
                        d_name, _ = winreg.QueryValueEx(sub, "DriverDesc")
                        v_bytes = None
                        try:
                            v_bytes, _ = winreg.QueryValueEx(sub, "HardwareInformation.qwMemorySize")
                        except Exception:
                            try:
                                v_bytes, _ = winreg.QueryValueEx(sub, "HardwareInformation.MemorySize")
                            except Exception:
                                pass
                        winreg.CloseKey(sub)
                        if v_bytes and v_bytes > 0:
                            clean_k = re.sub(r"[^a-zA-Z0-9]", "", d_name.lower())
                            vram_map[clean_k] = int(v_bytes // (1024**2))
                    except Exception:
                        continue
                winreg.CloseKey(base_k)
            except Exception:
                pass

        for i in range(dev_count):
            try:
                name = torch_directml.device_name(i).strip("\x00 \t\n\r")
                clean_target = re.sub(r"[^a-zA-Z0-9]", "", name.lower())
                detected_vram = 0
                for vk, vv in vram_map.items():
                    if vk in clean_target or clean_target in vk:
                        detected_vram = vv
                        break
                if detected_vram == 0:
                    detected_vram = 4096  # DirectML harici GPU varsayılanı

                vram_gb = round(detected_vram / 1024)
                vram_str = f"{vram_gb} GB" if vram_gb >= 1 else f"{detected_vram} MB"

                gpus.append({

                    "index": i,
                    "name": name,
                    "short_name": name.replace("AMD Radeon ", "").replace("Intel(R) ", "").strip(),
                    "backend": "DirectML",
                    "vram_mb": detected_vram,
                    "vram_allocated_mb": 0,
                    "vram_str": f"{vram_str} (DirectML)",
                    "is_gpu": True,
                })
            except Exception:
                break
        if gpus:
            return gpus
    except Exception:
        pass


    # 3. Apple Silicon Metal (MPS)
    try:
        import torch
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            gpus.append({
                "index": 0,
                "name": "Apple Silicon (Metal MPS)",
                "short_name": "Apple MPS",
                "backend": "MPS",
                "vram_mb": 0,
                "vram_allocated_mb": 0,
                "vram_str": "Unified Memory",
                "is_gpu": True,
            })
            return gpus
    except Exception:
        pass

    # 4. OS Seviyesi GPU Tespiti (Windows Registry Multi-GPU)
    if sys.platform == "win32":
        try:
            import winreg
            base_key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
            )
            idx = 0
            for i in range(16):
                try:
                    subkey = winreg.OpenKey(base_key, f"{i:04d}")
                    driver_desc, _ = winreg.QueryValueEx(subkey, "DriverDesc")
                    winreg.CloseKey(subkey)
                    desc_clean = driver_desc.strip("\x00 \t\n\r")
                    if desc_clean and "basic display" not in desc_clean.lower() and "basic render" not in desc_clean.lower():
                        gpus.append({
                            "index": idx,
                            "name": f"{desc_clean} (Sistem)",
                            "short_name": desc_clean,
                            "backend": "Sistem",
                            "vram_mb": 0,
                            "vram_allocated_mb": 0,
                            "vram_str": "—",
                            "is_gpu": True,
                        })
                        idx += 1
                except Exception:
                    continue
            winreg.CloseKey(base_key)
            if gpus:
                return gpus
        except Exception:
            pass

    # Fallback: GPU yok
    return [{
        "index": 0,
        "name": "Yok (CPU modu)",
        "short_name": "CPU",
        "backend": "CPU",
        "vram_mb": 0,
        "vram_allocated_mb": 0,
        "vram_str": "—",
        "is_gpu": False,
    }]


def get_gpu_info() -> Dict[str, Any]:
    """
    Sistemdeki GPU durumunu özetler. Çoklu GPU durumunda toplu metrik üretir.
    """
    devices = get_all_gpus()
    active_gpus = [g for g in devices if g.get("is_gpu")]

    if not active_gpus:
        return {
            "name": "Yok (CPU modu)",
            "short_name": "CPU",
            "backend": "CPU",
            "count": 0,
            "is_multi_gpu": False,
            "vram_mb": 0,
            "vram_str": "—",
            "is_gpu": False,
            "devices": devices,
        }

    count = len(active_gpus)
    backend = active_gpus[0]["backend"]
    total_vram = sum(g.get("vram_mb", 0) for g in active_gpus)

    if count == 1:
        g = active_gpus[0]
        return {
            "name": g["name"],
            "short_name": g["short_name"],
            "backend": g["backend"],
            "count": 1,
            "is_multi_gpu": False,
            "vram_mb": g["vram_mb"],
            "vram_str": g["vram_str"],
            "is_gpu": True,
            "devices": active_gpus,
        }

    # Çoklu GPU (Multi-GPU)
    names = [g["short_name"] for g in active_gpus]
    if len(set(names)) == 1:
        # Aynı model GPU'lar (örn: 2x RTX 4090)
        multi_name = f"{count}x {names[0]}"
    else:
        multi_name = " + ".join(names[:3])

    vram_str = f"{total_vram} MB Toplam" if total_vram > 0 else f"{count} Aygıt"

    return {
        "name": multi_name,
        "short_name": multi_name,
        "backend": backend,
        "count": count,
        "is_multi_gpu": True,
        "vram_mb": total_vram,
        "vram_str": vram_str,
        "is_gpu": True,
        "devices": active_gpus,
    }



def get_ram_info() -> Dict[str, Any]:
    """
    Toplam ve kullanılabilir fiziksel bellek (RAM) miktarını döner.
    """
    total_gb = 0.0
    free_gb = 0.0

    if sys.platform == "win32":
        try:
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                total_gb = stat.ullTotalPhys / (1024**3)
                free_gb = stat.ullAvailPhys / (1024**3)
        except Exception:
            pass
    elif sys.platform.startswith("linux"):
        try:
            with open("/proc/meminfo", "r", encoding="utf-8", errors="ignore") as f:
                mem_total = 0
                mem_avail = 0
                for line in f:
                    if "MemTotal:" in line:
                        mem_total = int(line.split()[1])
                    elif "MemAvailable:" in line:
                        mem_avail = int(line.split()[1])
                if mem_total > 0:
                    total_gb = mem_total / (1024**2)
                    free_gb = mem_avail / (1024**2)
        except Exception:
            pass
    elif sys.platform == "darwin":
        try:
            out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip()
            total_gb = int(out) / (1024**3)
            free_gb = 0.0
        except Exception:
            pass

    return {
        "total_gb": round(total_gb, 1),
        "free_gb": round(free_gb, 1),
    }


def get_optimal_cpu_threads() -> int:
    """
    Mevcut makinenin çekirdek sayısına göre optimum iş parçacığı sayısını hesaplar.
    """
    total = os.cpu_count() or 4
    return max(1, total)


def get_optimal_workers() -> int:
    """
    Veri işleme / background workers için optimum thread sayısını hesaplar.
    """
    threads = os.cpu_count() or 4
    if threads <= 4:
        return max(1, threads - 1)
    elif threads <= 8:
        return 4
    elif threads <= 16:
        return 6
    else:
        return 8


def get_system_summary(lang: Optional[str] = None) -> str:
    """
    GUI ve loglar için dinamik, eksiksiz sistem özet metni üretir.
    """
    os_str = f"{platform.system()} {platform.release()}"
    py_str = platform.python_version()

    cpu = get_cpu_info()
    gpu = get_gpu_info()
    ram = get_ram_info()

    cpu_text = f"{cpu['short_name']} ({cpu['threads']}T)"
    
    if gpu["is_gpu"]:
        if gpu["backend"] == "CUDA":
            gpu_text = f"{gpu['name']} ({gpu['vram_str']})"
        elif gpu["backend"] == "DirectML":
            gpu_text = f"{gpu['name']} [DirectML]"
        elif gpu["backend"] == "MPS":
            gpu_text = f"{gpu['name']}"
        else:
            gpu_text = f"{gpu['name']}"
    else:
        gpu_text = gpu["name"]

    ram_str = f"{ram['total_gb']} GB" if ram["total_gb"] > 0 else "—"
    if ram["free_gb"] > 0:
        is_tr = (lang == "tr")
        free_label = "Boş" if is_tr else "Free"
        ram_str += f" ({ram['free_gb']} GB {free_label})"

    return (
        f"OS: {os_str}\n"
        f"Python: {py_str}\n"
        f"CPU: {cpu_text}\n"
        f"GPU: {gpu_text}\n"
        f"RAM: {ram_str}"
    )


def get_hardware_profile() -> Dict[str, Any]:
    """
    Kullanıcının GPU ve VRAM kapasitesine göre dinamik eğitim ve model profilini otomatik belirler.
    Güçlü sistemlerde (RTX 4090, 3090, Multi-GPU) maksimum hız ve paralel batch açar,
    Giriş seviyesi GPU veya CPU sistemlerde belleği taşmayacak şekilde optimize eder.
    """
    gpu_info = get_gpu_info()
    vram_mb = gpu_info.get("vram_mb", 0)
    is_multi = gpu_info.get("is_multi_gpu", False)
    is_gpu = gpu_info.get("is_gpu", False)
    gpu_count = gpu_info.get("count", 1)

    # 1. Tier 1: Enthusiast / Multi-GPU (16GB+ VRAM veya Multi-GPU, örn. RTX 4090, RTX 3090, A100)
    if is_multi or vram_mb >= 16384:
        return {
            "tier": "enthusiast",
            "tier_name": "Tier 1: Ultra / Multi-GPU Performans",
            "batch_size": 64 * max(1, gpu_count),
            "burst_steps": 8,
            "max_seq_len": 512,
            "ff_growth_factor": 1.75,
            "pacing_sleep": 0.001,
            "embed_dim": 256,
            "workers": min(8, os.cpu_count() or 4)
        }
    # 2. Tier 2: Mid-Range GPU (8GB - 16GB VRAM, örn. RTX 3060, 4060, RX 6700, RX 7600)
    elif is_gpu and vram_mb >= 8192:
        return {
            "tier": "mid_range",
            "tier_name": "Tier 2: Orta/Yüksek GPU Performans",
            "batch_size": 48,
            "burst_steps": 6,
            "max_seq_len": 256,
            "ff_growth_factor": 1.5,
            "pacing_sleep": 0.005,
            "embed_dim": 192,
            "workers": min(6, os.cpu_count() or 4)
        }
    # 3. Tier 3: Entry GPU (4GB - 8GB VRAM, örn. RX 6500 XT, GTX 1650, RTX 3050)
    elif is_gpu and vram_mb >= 3000:
        return {
            "tier": "entry_gpu",
            "tier_name": "Tier 3: Giriş Seviyesi GPU Hızlandırma",
            "batch_size": 32,
            "burst_steps": 4,
            "max_seq_len": 256,
            "ff_growth_factor": 1.35,
            "pacing_sleep": 0.01,
            "embed_dim": 128,
            "workers": min(4, os.cpu_count() or 4)
        }
    # 4. Tier 4: CPU Only veya Düşük VRAM (<4GB)
    else:
        return {
            "tier": "cpu_mode",
            "tier_name": "Tier 4: CPU / Entegre Grafik Modu",
            "batch_size": 16,
            "burst_steps": 2,
            "max_seq_len": 128,
            "ff_growth_factor": 1.25,
            "pacing_sleep": 0.05,
            "embed_dim": 128,
            "workers": min(2, os.cpu_count() or 2)
        }


if __name__ == "__main__":
    print("=" * 60)
    print("🔍 Nova AGI Donanım Tespiti")
    print("=" * 60)
    print(get_system_summary())
    print("=" * 60)
    print("Donanım Profili:", get_hardware_profile())
    print("=" * 60)

