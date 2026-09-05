# -*- coding: utf-8 -*-
"""
config.py - Nova Headless Trainer Konfigürasyonu
Arayüz ve masaüstü bağımlılıklarından arındırılmış bağımsız konfigürasyon.
"""
import os
import torch

try:
    import torch_directml
    _DIRECTML_MEVCUT = True
except Exception:
    _DIRECTML_MEVCUT = False

def varsayilan_cihaz() -> str:
    """Kullanılabilir en iyi donanım hızlandırma cihazını seçer."""
    if "NOVA_DEVICE" in os.environ:
        return os.environ["NOVA_DEVICE"]
    if torch.cuda.is_available():
        return "cuda"
    if _DIRECTML_MEVCUT:
        return "privateuseone"
    return "cpu"

class TrainerConfig:
    # ── Temel Model Mimarisi ──────────────────────────────────────────────────
    vocab_size    : int   = 1024
    embed_dim     : int   = 128
    n_heads       : int   = 4
    n_layers      : int   = 2
    ff_dim        : int   = 512
    max_seq_len   : int   = 256
    dropout       : float = 0.10

    # ── Büyüme (Network Morphism) Sınırları ────────────────────────────────────
    max_embed_dim : int   = 2048
    max_n_layers  : int   = 48
    max_n_heads   : int   = 32
    max_ff_dim    : int   = 16384
    ff_buyume_kat : float = 1.35

    # ── Plato & Büyüme Tetikleyicisi ──────────────────────────────────────────
    plato_pencere : int   = 60
    plato_esigi   : float = 0.003
    buyume_bekleme: int   = 120

    # ── Eğitim Hiperparametreleri ─────────────────────────────────────────────
    lr            : float = 3e-4
    weight_decay  : float = 0.01
    batch_size    : int   = 32
    grad_clip     : float = 1.0
    warmup_steps  : int   = 100
    t_max         : int   = 2000
    save_every    : int   = 50
    min_text_len  : int   = 20

    # ── Dosya Yolları (Varsayılan olarak yerel dizin) ──────────────────────────
    base_dir      : str   = os.path.dirname(os.path.abspath(__file__))
    db_path       : str   = os.getenv("NOVA_DB_PATH", os.path.join(base_dir, "nova.db"))
    weights_path  : str   = os.getenv("NOVA_WEIGHTS_PATH", os.path.join(base_dir, "nova_weights.pth"))
    vocab_path    : str   = os.getenv("NOVA_VOCAB_PATH", os.path.join(base_dir, "nova_vocab.json"))
    device        : str   = varsayilan_cihaz()
