# ═══════════════════════════════════════════════════════════════════════════════
# build_exe.py  —  Nova AGI Windows Tek Tıkla Standalone EXE Derleyici
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys
import subprocess
import shutil
import winreg

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def build():
    print("=" * 65)
    print("Nova AGI — Windows Standalone EXE Derleyici Baslatiliyor")
    print("=" * 65)

    # 1. PyInstaller kurulu mu kontrol et
    try:
        import PyInstaller
        print(f"✓ PyInstaller bulundu: v{PyInstaller.__version__}")
    except ImportError:
        print("📦 PyInstaller kuruluyor...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 2. Gerekli gizli importlar ve veri dosyaları
    hidden_imports = [
        "torch",
        "torchvision",
        "torchaudio",
        "torch_directml",
        "pyttsx3",
        "pyttsx3.drivers",
        "pyttsx3.drivers.sapi5",
        "speech_recognition",
        "comtypes",
        "comtypes.client",
        "comtypes.gen",
        "PIL",
        "PIL.Image",
        "cv2",
        "pyautogui",
        "pyperclip",
        "datasets",
        "huggingface_hub",
        "pyarrow",
        "sqlite3",
        "tkinter",
        "requests",
        "config_manager",
        "hf_auth",
        "gpu_setup",
        "memory",
        "brain",
        "body",
        "gui",
        "hybrid_engine",
    ]

    # Ek veri dosyaları (data files)
    data_files = [
        ("nova_vocab.json", "."),
        ("nova_weights.pth", "."),
        ("yetenekler.py", "."),
        ("config_manager.py", "."),
        ("hf_auth.py", "."),
        ("gpu_setup.py", "."),
        ("memory.py", "."),
        ("brain.py", "."),
        ("body.py", "."),
        ("gui.py", "."),
        ("hybrid_engine.py", "."),
    ]
    if os.path.exists(os.path.join(ROOT_DIR, "nova.db")):
        data_files.append(("nova.db", "."))
    if os.path.exists(os.path.join(ROOT_DIR, "nova_icon.ico")):
        data_files.append(("nova_icon.ico", "."))
    if os.path.exists(os.path.join(ROOT_DIR, "nova_icon.png")):
        data_files.append(("nova_icon.png", "."))
    if os.path.exists(os.path.join(ROOT_DIR, "nova_icon.svg")):
        data_files.append(("nova_icon.svg", "."))

    # PyInstaller komut parametreleri
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--name=NovaAGI",
        "--onedir",             # PyTorch ve DirectML C uzantıları için onedir en hızlı ve kararlısıdır
        "--windowed",           # Konsolsuz arka plan (GUI modu) veya konsollu
        f"--paths={ROOT_DIR}",
        "--noconfirm",
        "--clean",
    ]

    icon_file = os.path.join(ROOT_DIR, "nova_icon.ico")
    if os.path.exists(icon_file):
        cmd.append("--icon=" + icon_file)

    for hi in hidden_imports:
        cmd.extend(["--hidden-import", hi])

    for src, dst in data_files:
        if os.path.exists(os.path.join(ROOT_DIR, src)):
            cmd.extend(["--add-data", f"{src};{dst}"])

    # Ana giriş noktası
    cmd.append(os.path.join(ROOT_DIR, "nova_launcher.py"))

    print("\n🔨 PyInstaller derlemesi çalıştırılıyor (Bu işlem birkaç dakika sürebilir)...")
    print("Komut:", " ".join(cmd))
    subprocess.check_call(cmd, cwd=ROOT_DIR)

    dist_dir = os.path.join(ROOT_DIR, "dist", "NovaAGI")
    print("\n" + "=" * 65)
    print("🎉 DERLEME BAŞARIYLA TAMAMLANDI!")
    print(f"📁 EXE ve Bağımsız Paket Konumu:\n   {dist_dir}")
    print(f"👉 Çalıştırılabilir Dosya:\n   {os.path.join(dist_dir, 'NovaAGI.exe')}")
    print("=" * 65)

    # Inno Setup ile installer oluştur
    iscc = _find_iscc()
    if iscc:
        iss_file = os.path.join(ROOT_DIR, "installer.iss")
        if os.path.exists(iss_file):
            os.makedirs(os.path.join(ROOT_DIR, "dist_installer"), exist_ok=True)
            # dist klasöründeki geçici veya açık log dosyalarını temizle
            for log_name in ("nova.log", "nova.log.1", "nova.tmp"):
                log_path = os.path.join(dist_dir, log_name)
                if os.path.exists(log_path):
                    try:
                        os.remove(log_path)
                    except Exception:
                        pass
            print("\n📦 Inno Setup ile kurulum paketi oluşturuluyor...")
            result = subprocess.run([iscc, iss_file], cwd=ROOT_DIR)
            if result.returncode == 0:
                setup_exe = os.path.join(ROOT_DIR, "dist_installer", "NovaAGI_v3_Setup.exe")
                print("\n" + "=" * 65)
                print("🎉 KURULUM EXE'Sİ OLUŞTURULDU!")
                print(f"📦 Kurulum Paketi:\n   {setup_exe}")
                print("=" * 65)
            else:
                print("⚠️  Inno Setup derleme başarısız oldu.")
        else:
            print("⚠️  installer.iss bulunamadı, kurulum paketi oluşturulamadı.")
    else:
        print("⚠️  Inno Setup (ISCC.exe) bulunamadı. Sadece dist\\NovaAGI klasörü oluşturuldu.")
        print("   Inno Setup'ı şu adresten indirebilirsiniz: https://jrsoftware.org/isdl.php")


def _find_iscc() -> str:
    """ISCC.exe'yi bilinen konumlarda ve registry'de arar."""
    # Bilinen yollar
    candidates = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Inno Setup 6\ISCC.exe"),
        os.path.expanduser(r"~\AppData\Local\Programs\Inno Setup 5\ISCC.exe"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path

    # Registry'den bul
    try:
        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for subkey in (
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
            ):
                try:
                    with winreg.OpenKey(root, subkey) as uk:
                        for i in range(winreg.QueryInfoKey(uk)[0]):
                            try:
                                sub = winreg.EnumKey(uk, i)
                                with winreg.OpenKey(uk, sub) as sk:
                                    try:
                                        name, _ = winreg.QueryValueEx(sk, "DisplayName")
                                        if "Inno Setup" in str(name):
                                            install_loc, _ = winreg.QueryValueEx(sk, "InstallLocation")
                                            iscc = os.path.join(install_loc, "ISCC.exe")
                                            if os.path.exists(iscc):
                                                return iscc
                                    except FileNotFoundError:
                                        pass
                            except OSError:
                                pass
                except OSError:
                    pass
    except Exception:
        pass

    # PATH'te ara
    iscc = shutil.which("ISCC")
    if iscc:
        return iscc

    return None


if __name__ == "__main__":
    build()
