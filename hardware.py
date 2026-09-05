import os
import platform
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, Optional


def get_optimal_cpu_threads() -> int:
    """Use a safe CPU thread count for local machine constraints."""
    try:
        count = os.cpu_count() or 1
    except Exception:
        count = 1
    if count <= 0:
        return 1
    return max(1, min(count, 12))


def get_cpu_info() -> Dict[str, Any]:
    """Return low-cost CPU metadata used by the GUI."""
    raw_name = ""
    threads = os.cpu_count() or 1

    if sys.platform.startswith("linux"):
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if "model name" in line or "Hardware" in line:
                        raw_name = line.split(":", 1)[1].strip()
                        break
        except Exception:
            pass
    elif sys.platform == "darwin":
        try:
            out = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True, errors="ignore")
            if out:
                raw_name = out.strip()
        except Exception:
            pass
    elif sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            val, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            winreg.CloseKey(key)
            raw_name = val.strip()
        except Exception:
            pass

    if not raw_name:
        proc = platform.processor() or platform.machine() or "Generic CPU"
        raw_name = proc

    full_name = " ".join(raw_name.split())
    short_name = full_name
    short_name = short_name.replace("(R)", "").replace("(TM)", "")
    short_name = " ".join(short_name.split())
    match = re.search(r"(Ryzen\s+\d+\s+\w+|Ryzen\s+\w+|Core\s+i\d-\w+|i\d-\w+|M[1-4](?:\s*(?:Pro|Max|Ultra))?)", short_name, re.I)
    if match:
        short_name = match.group(0).strip()
    if len(short_name) > 24:
        short_name = short_name[:22].strip()

    return {"full_name": full_name, "short_name": short_name, "threads": threads}


def get_gpu_info() -> Dict[str, Any]:
    """Return a simple GPU summary for the GUI and launcher."""
    info = {"name": "CPU only", "vendor": "cpu", "available": False}

    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            info = {"name": name, "vendor": "nvidia", "available": True}
            return info
    except Exception:
        pass

    gpus = []
    for cmd in (["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], ["lspci"]):
        try:
            out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, shell=False)
            if out:
                gpus.extend([line.strip() for line in out.splitlines() if line.strip()])
        except Exception:
            pass

    for line in gpus:
        if line:
            info = {"name": line, "vendor": "gpu", "available": True}
            break
    return info


def get_system_summary(lang: str = "en") -> str:
    """Build the status text shown in the right panel."""
    import platform
    cpu = get_cpu_info()
    gpu = get_gpu_info()
    lang_label = "English" if lang == "en" else "Türkçe"
    return (
        f"OS: {platform.system()} {platform.release()}\n"
        f"Python: {platform.python_version()}\n"
        f"CPU: {cpu['short_name']} ({cpu['threads']}T)\n"
        f"GPU: {gpu['name']}"
    )


def get_all_gpus() -> list[Dict[str, Any]]:
    return [get_gpu_info()]
