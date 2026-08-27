# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:/NOVA/nova_launcher.py'],
    pathex=['C:/NOVA'],
    binaries=[],
    datas=[('nova_vocab.json', '.'), ('nova_weights.pth', '.'), ('yetenekler.py', '.'), ('config_manager.py', '.'), ('hf_auth.py', '.'), ('gpu_setup.py', '.'), ('hardware.py', '.'), ('memory.py', '.'), ('brain.py', '.'), ('body.py', '.'), ('gui.py', '.'), ('hybrid_engine.py', '.'), ('nova.db', '.'), ('nova_icon.ico', '.'), ('nova_icon.png', '.'), ('nova_icon.svg', '.')],
    hiddenimports=['torch', 'torchvision', 'torchaudio', 'torch_directml', 'pyttsx3', 'pyttsx3.drivers', 'pyttsx3.drivers.sapi5', 'speech_recognition', 'comtypes', 'comtypes.client', 'comtypes.gen', 'PIL', 'PIL.Image', 'cv2', 'pyautogui', 'pyperclip', 'datasets', 'huggingface_hub', 'pyarrow', 'sqlite3', 'tkinter', 'requests', 'config_manager', 'hf_auth', 'gpu_setup', 'hardware', 'memory', 'brain', 'body', 'gui', 'hybrid_engine'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NovaAGI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:/NOVA/nova_icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NovaAGI',
)
