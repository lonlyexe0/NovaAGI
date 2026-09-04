from __future__ import annotations
# ═══════════════════════════════════════════════════════════════════════════════
# brain.py  —  Nova Sınırsız Büyüyen Dinamik Sinir Ağı  [Python 3.10]
# ═══════════════════════════════════════════════════════════════════════════════
#
# Normal yapay zeka: embed=512, 8 kafa → sonsuza dek sabit.
# Nova: Çıkmaza girdiğinde kendi kendine yeni node / katman / boyut ekler.
#
# BÜYÜME HİYERARŞİSİ (takıldığında sırayla dener):
#   Seviye 1 → Feed-Forward nöron sayısını artır   (hızlı, ucuz)
#   Seviye 2 → Yeni Transformer bloğu ekle          (derin, güçlü)
#   Seviye 3 → Embedding boyutunu genişlet          (en kapsamlı)
#   → 3 seviye bittikten sonra 1'e döner, sonsuz döngü
#
# NETWORK MORPHISM: Büyüme sırasında eski ağırlıklar KORUNUR.
#   Yeni nöronlar ≈0 ile başlar → çıktıyı bozmaz → zamanla öğrenir.
#
# Parametre tavanı YOK. İzin verilen max'lar sadece bellek koruması içindir
# ve config'den artırılabilir.
#
# Başlangıç:   ~3M parametre
# Büyüyebilir: pratik olarak sınırsız (RAM / disk ile sınırlı)
# ═══════════════════════════════════════════════════════════════════════════════

import os, json, math, time, logging, threading
from collections import deque
from typing import Optional, List, Dict, Tuple, Any

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingWarmRestarts

logger = logging.getLogger("nova.brain")

os.environ.setdefault("OMP_NUM_THREADS", "4")
try:
    torch.set_num_threads(min(4, os.cpu_count() or 4))
except Exception:
    pass
# DirectML desteği için güvenli import (privateuseone arka ucu)

try:
    import torch_directml
    _DIRECTML_MEVCUT = True
except Exception:
    _DIRECTML_MEVCUT = False

def varsayilan_cihaz() -> str:
    if "NOVA_DEVICE" in os.environ:
        return os.environ["NOVA_DEVICE"]
    if torch.cuda.is_available():
        return "cuda"
    if _DIRECTML_MEVCUT:
        return "privateuseone"
    return "cpu"


# ═══════════════════════════════════════════════════════════════════════════════
# KONFİGÜRASYON
# ═══════════════════════════════════════════════════════════════════════════════
class Config:
    # ── Başlangıç mimarisi (küçük başla, büyüsün) ─────────────────────────────
    vocab_size    : int   = 1024
    embed_dim     : int   = 128      # Çok küçük başla
    n_heads       : int   = 4
    n_layers      : int   = 2
    ff_dim        : int   = 512
    max_seq_len   : int   = 256
    dropout       : float = 0.10

    # ── Büyüme limitleri (bellek koruması — artırılabilir) ────────────────────
    max_embed_dim : int   = 2048     # ~GPT-2 Small boyutu
    max_n_layers  : int   = 48       # ~GPT-3 Small boyutu
    max_n_heads   : int   = 32
    max_ff_dim    : int   = 16384    # ~GPT-3 ölçeği

    # ── Büyüme tetikleyici ────────────────────────────────────────────────────
    plato_pencere : int   = 60       # Son N adıma bak
    plato_esigi   : float = 0.003    # Loss bu kadar düşmüyorsa takıldı
    buyume_bekleme: int   = 120      # Büyümeden sonra N adım bekle

    # ── FF büyüme parametresi ─────────────────────────────────────────────────
    ff_buyume_kat : float = 1.5      # FF'yi bu kadar genişlet

    # ── Eğitim ────────────────────────────────────────────────────────────────
    lr            : float = 3e-4
    weight_decay  : float = 0.01
    batch_size    : int   = 32
    grad_clip     : float = 1.0

    warmup_steps  : int   = 100
    t_max         : int   = 2000

    # ── Operasyon ─────────────────────────────────────────────────────────────
    save_every    : int   = 50
    min_text_len  : int   = 20

    # ── Dosyalar ──────────────────────────────────────────────────────────────
    from config_manager import get_data_path
    weights_path  : str   = get_data_path("nova_weights.pth")
    vocab_path    : str   = get_data_path("nova_vocab.json")
    config_path   : str   = get_data_path(".nova_config.json")
    device        : str   = varsayilan_cihaz()



# ═══════════════════════════════════════════════════════════════════════════════
# DİNAMİK FF — büyüyebilen feed-forward bloğu
# ═══════════════════════════════════════════════════════════════════════════════
class DinamikFF(nn.Module):
    def __init__(self, embed_dim: int, ff_dim: int, dropout: float):
        super().__init__()
        self._embed  = embed_dim
        self._ff     = ff_dim
        self.dropout = dropout
        self.fc1  = nn.Linear(embed_dim, ff_dim,    bias=False)
        self.fc2  = nn.Linear(ff_dim,    embed_dim, bias=False)
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.drop(self.fc2(F.gelu(self.fc1(x))))

    @property
    def ff_dim(self) -> int:
        return self._ff

    def ff_genislet(self, yeni_ff: int) -> bool:
        if yeni_ff <= self._ff:
            return False
        fark, std = yeni_ff - self._ff, 0.001
        e = self._embed

        yeni1 = nn.Linear(e, yeni_ff, bias=False)
        yeni2 = nn.Linear(yeni_ff, e, bias=False)
        with torch.no_grad():
            yeni1.weight[:self._ff]       = self.fc1.weight
            yeni1.weight[self._ff:]       = torch.randn(fark, e) * std
            yeni2.weight[:, :self._ff]    = self.fc2.weight
            yeni2.weight[:, self._ff:]    = torch.zeros(e, fark)
        self.fc1, self.fc2, self._ff = yeni1, yeni2, yeni_ff
        return True

    def embed_guncelle(self, yeni_e: int) -> bool:
        if yeni_e <= self._embed:
            return False
        fark, std = yeni_e - self._embed, 0.001
        yeni1 = nn.Linear(yeni_e, self._ff, bias=False)
        yeni2 = nn.Linear(self._ff, yeni_e, bias=False)
        with torch.no_grad():
            yeni1.weight[:, :self._embed]  = self.fc1.weight
            yeni1.weight[:, self._embed:]  = torch.randn(self._ff, fark) * std
            yeni2.weight[:self._embed, :]  = self.fc2.weight
            yeni2.weight[self._embed:, :]  = torch.zeros(fark, self._ff)
        self.fc1, self.fc2, self._embed = yeni1, yeni2, yeni_e
        return True


# ═══════════════════════════════════════════════════════════════════════════════
# DİNAMİK DİKKAT — kafa eklenebilen self-attention
# ═══════════════════════════════════════════════════════════════════════════════
class DinamikDikkat(nn.Module):
    def __init__(self, embed_dim: int, n_heads: int, max_seq: int, dropout: float):
        super().__init__()
        assert embed_dim % n_heads == 0
        self._e  = embed_dim
        self._h  = n_heads
        self._ms = max_seq
        self._dp = dropout
        self.qkv       = nn.Linear(embed_dim, 3*embed_dim, bias=False)
        self.proj      = nn.Linear(embed_dim, embed_dim,   bias=False)
        self.attn_drop = nn.Dropout(dropout)
        self.res_drop  = nn.Dropout(dropout)
        mask = torch.tril(torch.ones(max_seq, max_seq, dtype=torch.bool))
        self.register_buffer("mask", mask.view(1,1,max_seq,max_seq))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, C = x.shape
        hd = C // self._h
        q, k, v = self.qkv(x).split(C, dim=2)
        q = q.view(B, T, self._h, hd).transpose(1, 2)
        k = k.view(B, T, self._h, hd).transpose(1, 2)
        v = v.view(B, T, self._h, hd).transpose(1, 2)
        att = (q @ k.transpose(-2,-1)) * (hd**-0.5)
        att = att.masked_fill(~self.mask[:,:,:T,:T], float("-inf"))
        att = self.attn_drop(F.softmax(att, dim=-1))
        out = (att @ v).transpose(1,2).contiguous().view(B, T, C)
        return self.res_drop(self.proj(out))

    def embed_guncelle(self, yeni_e: int, yeni_h: int) -> bool:
        if yeni_e <= self._e:
            return False
        assert yeni_e % yeni_h == 0
        fark, std = yeni_e - self._e, 0.001
        ye = yeni_e
        yqkv = nn.Linear(ye, 3*ye, bias=False)
        yproj= nn.Linear(ye, ye,   bias=False)
        with torch.no_grad():
            yqkv.weight[:3*self._e, :self._e] = self.qkv.weight
            yqkv.weight[:3*self._e, self._e:] = torch.randn(3*self._e, fark)*std
            yqkv.weight[3*self._e:, :]        = torch.randn(3*fark, ye)*std
            yproj.weight[:self._e, :self._e]  = self.proj.weight
            yproj.weight[:self._e, self._e:]  = torch.zeros(self._e, fark)
            yproj.weight[self._e:, :]         = torch.zeros(fark, ye)
        self.qkv, self.proj = yqkv, yproj
        self._e, self._h = yeni_e, yeni_h
        return True


# ═══════════════════════════════════════════════════════════════════════════════
# DİNAMİK BLOK
# ═══════════════════════════════════════════════════════════════════════════════
class DinamikBlok(nn.Module):
    def __init__(self, embed_dim: int, n_heads: int,
                 ff_dim: int, max_seq: int, dropout: float):
        super().__init__()
        self._e    = embed_dim
        self.norm1 = nn.LayerNorm(embed_dim)
        self.attn  = DinamikDikkat(embed_dim, n_heads, max_seq, dropout)
        self.norm2 = nn.LayerNorm(embed_dim)
        self.ff    = DinamikFF(embed_dim, ff_dim, dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.norm1(x))
        x = x + self.ff(self.norm2(x))
        return x

    def ff_genislet(self, yeni_ff: int) -> bool:
        return self.ff.ff_genislet(yeni_ff)

    def embed_guncelle(self, yeni_e: int, yeni_h: int) -> bool:
        if yeni_e <= self._e:
            return False
        fark, std = yeni_e - self._e, 0.001
        for attr in ("norm1", "norm2"):
            old = getattr(self, attr)
            yeni = nn.LayerNorm(yeni_e)
            with torch.no_grad():
                yeni.weight[:self._e] = old.weight
                yeni.weight[self._e:] = torch.ones(fark)
                yeni.bias[:self._e]   = old.bias
                yeni.bias[self._e:]   = torch.zeros(fark)
            setattr(self, attr, yeni)
        self.attn.embed_guncelle(yeni_e, yeni_h)
        self.ff.embed_guncelle(yeni_e)
        self._e = yeni_e
        return True


# ═══════════════════════════════════════════════════════════════════════════════
# DİNAMİK NOVA LM — sınırsız büyüyen ana model
# ═══════════════════════════════════════════════════════════════════════════════
class DinamikNovaLM(nn.Module):
    def __init__(self, cfg: Config):
        super().__init__()
        self.cfg    = cfg
        self._e     = cfg.embed_dim   # mevcut embed boyutu
        self._h     = cfg.n_heads
        self._ff    = cfg.ff_dim

        self.tok_emb  = nn.Embedding(cfg.vocab_size, cfg.embed_dim)
        self.pos_emb  = nn.Embedding(cfg.max_seq_len, cfg.embed_dim)
        self.emb_drop = nn.Dropout(cfg.dropout)
        self.bloklar  = nn.ModuleList([
            DinamikBlok(cfg.embed_dim, cfg.n_heads,
                        cfg.ff_dim, cfg.max_seq_len, cfg.dropout)
            for _ in range(cfg.n_layers)
        ])
        self.norm = nn.LayerNorm(cfg.embed_dim)
        self.head = nn.Linear(cfg.embed_dim, cfg.vocab_size, bias=False)
        self.tok_emb.weight = self.head.weight   # weight tying

        # Büyüme istatistikleri
        self.buyume_gecmisi: List[Dict[str, Any]] = []
        self._toplam_buyume = 0

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0.0, 0.02)
                if m.bias is not None: nn.init.zeros_(m.bias)
            elif isinstance(m, nn.Embedding):
                nn.init.normal_(m.weight, 0.0, 0.02)
            elif isinstance(m, nn.LayerNorm):
                nn.init.ones_(m.weight); nn.init.zeros_(m.bias)

    def forward(self, idx: torch.Tensor,
                targets: Optional[torch.Tensor] = None
                ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        B, T = idx.shape
        pos  = torch.arange(T, device=idx.device, dtype=torch.long)
        x    = self.emb_drop(self.tok_emb(idx) + self.pos_emb(pos))
        for blok in self.bloklar:
            x = blok(x)
        x      = self.norm(x)
        logits = self.head(x)
        loss   = None
        if targets is not None:
            loss = F.cross_entropy(logits.view(-1, self.cfg.vocab_size),
                                   targets.view(-1), ignore_index=-1,
                                   label_smoothing=0.05)
        return logits, loss

    @torch.no_grad()
    def uret(self, idx: torch.Tensor, max_new: int = 250,
             sicaklik: float = 0.85, top_k: int = 50,
             top_p: float = 0.92, rep_ceza: float = 1.3) -> torch.Tensor:
        self.eval()
        gen = idx.clone()
        for _ in range(max_new):
            cond = gen[:, -self.cfg.max_seq_len:]
            logits, _ = self(cond)
            # DirectML / Multi-GPU uyumlu güvenli CPU örnekleme
            next_logits = logits[:, -1, :].clone().to(torch.float32).cpu()
            for b in range(gen.shape[0]):
                for t in set(gen[b].tolist()):
                    if t < next_logits.shape[-1]:
                        next_logits[b, t] /= rep_ceza
            next_logits /= max(sicaklik, 1e-8)
            if top_k > 0:
                v, _ = torch.topk(next_logits, min(top_k, next_logits.size(-1)))
                next_logits[next_logits < v[:, [-1]]] = float("-inf")
            if 0 < top_p < 1:
                sl, si = torch.sort(next_logits, descending=True)
                cum = torch.cumsum(F.softmax(sl, dim=-1), dim=-1)
                sl[cum - F.softmax(sl, dim=-1) > top_p] = float("-inf")
                next_logits = torch.zeros_like(next_logits).scatter_(1, si, sl)
            probs = F.softmax(next_logits, dim=-1)
            next_token = torch.multinomial(probs, 1).to(idx.device)
            gen = torch.cat([gen, next_token], dim=1)
        self.train()
        return gen


    # ══ BÜYÜME METODLARİ ═════════════════════════════════════════════════════

    def _aktif_cihaz(self) -> torch.device:
        try:
            return next(self.parameters()).device
        except Exception:
            return torch.device("cpu")

    def ff_genislet(self) -> Optional[str]:
        """Seviye 1: Tüm bloklarda FF nöron sayısını artır."""
        if self._ff >= self.cfg.max_ff_dim:
            return None
        yeni = min(int(self._ff * self.cfg.ff_buyume_kat), self.cfg.max_ff_dim)
        yeni = max(yeni, self._ff + 64)  # en az 64 nöron ekle
        yeni = (yeni // 64) * 64
        if yeni <= self._ff:
            return None
        dev = self._aktif_cihaz()
        for blok in self.bloklar:
            blok.ff_genislet(yeni)
        self.to(dev)
        eski, self._ff = self._ff, yeni
        self._kayit_buyume("ff_genislet", eski_ff=eski, yeni_ff=yeni,
                            blok_sayisi=len(self.bloklar))
        return f"FF nöron: {eski:,} → {yeni:,} (tüm {len(self.bloklar)} blokta)"

    def yeni_blok_ekle(self) -> Optional[str]:
        """Seviye 2: Ortaya yeni bir Transformer bloğu ekle."""
        if len(self.bloklar) >= self.cfg.max_n_layers:
            return None
        dev = self._aktif_cihaz()
        yeni_blok = DinamikBlok(self._e, self._h, self._ff,
                                 self.cfg.max_seq_len, self.cfg.dropout).to(dev)
        # Network morphism: yeni blok başta neredeyse şeffaf davranır
        with torch.no_grad():
            for p in yeni_blok.parameters():
                p.data *= 0.01
        idx = len(self.bloklar) // 2  # Ortaya ekle
        bl  = list(self.bloklar)
        bl.insert(idx, yeni_blok)
        self.bloklar = nn.ModuleList(bl)
        self.to(dev)
        self._kayit_buyume("yeni_blok", blok_idx=idx,
                            toplam_blok=len(self.bloklar))
        return f"Yeni blok eklendi [idx={idx}] → toplam {len(self.bloklar)} blok"

    def embed_genislet(self) -> Optional[str]:
        """Seviye 3: Embedding boyutunu ve tüm ilgili katmanları genişlet."""
        if self._e >= self.cfg.max_embed_dim:
            return None
        yeni_e = min(self._e + 64, self.cfg.max_embed_dim)
        # n_heads ile bölünebilirlik
        yeni_h = self._h
        while yeni_e % yeni_h != 0 and yeni_h > 1:
            yeni_h -= 1
        if yeni_e % yeni_h != 0:
            return None

        dev = self._aktif_cihaz()
        fark, std = yeni_e - self._e, 0.001
        V  = self.cfg.vocab_size
        PS = self.cfg.max_seq_len

        # tok_emb ve pos_emb
        yt = nn.Embedding(V, yeni_e).to(dev)
        yp = nn.Embedding(PS, yeni_e).to(dev)
        with torch.no_grad():
            yt.weight[:, :self._e] = self.tok_emb.weight.detach()
            yt.weight[:, self._e:] = torch.randn(V,  fark, device=dev) * std
            yp.weight[:, :self._e] = self.pos_emb.weight.detach()
            yp.weight[:, self._e:] = torch.randn(PS, fark, device=dev) * std
        self.tok_emb, self.pos_emb = yt, yp

        # Final norm
        yn = nn.LayerNorm(yeni_e).to(dev)
        with torch.no_grad():
            yn.weight[:self._e] = self.norm.weight
            yn.weight[self._e:] = torch.ones(fark, device=dev)
            yn.bias[:self._e]   = self.norm.bias
            yn.bias[self._e:]   = torch.zeros(fark, device=dev)
        self.norm = yn

        # Output head
        yh = nn.Linear(yeni_e, V, bias=False).to(dev)
        with torch.no_grad():
            yh.weight[:, :self._e] = self.head.weight.detach()
            yh.weight[:, self._e:] = torch.zeros(V, fark, device=dev)
        self.head = yh

        # Weight tying yeniden bağla
        self.tok_emb.weight = self.head.weight

        # Tüm blokları güncelle
        for blok in self.bloklar:
            blok.embed_guncelle(yeni_e, yeni_h)

        self.to(dev)
        eski_e, eski_h = self._e, self._h
        self._e, self._h = yeni_e, yeni_h
        self._kayit_buyume("embed_genislet",
                            eski_embed=eski_e, yeni_embed=yeni_e,
                            eski_kafa=eski_h,  yeni_kafa=yeni_h)
        return f"Embed: {eski_e} → {yeni_e} | Kafa: {eski_h} → {yeni_h}"


    def _kayit_buyume(self, tip: str, **kwargs):
        self._toplam_buyume += 1
        self.buyume_gecmisi.append({
            "no": self._toplam_buyume,
            "tip": tip,
            "parametre": self.param_sayisi(),
            "zaman": __import__("datetime").datetime.now().strftime("%H:%M:%S"),
            **kwargs
        })

    # ══ DURUM ════════════════════════════════════════════════════════════════

    def param_sayisi(self) -> int:
        return sum(p.numel() for p in set(self.parameters()))


    def mimari_ozet(self) -> str:
        return (
            f"Nova[embed={self._e}, kafa={self._h}, "
            f"blok={len(self.bloklar)}, ff={self._ff}, "
            f"param={self.param_sayisi():,}, "
            f"büyüme={self._toplam_buyume}x]"
        )

    def buyume_tablosu(self) -> str:
        """İstatistik için büyüme geçmişini tablo olarak döndür."""
        if not self.buyume_gecmisi:
            return "  Henüz büyüme gerçekleşmedi."
        satirlar = [
            f"  {'No':>3} {'Tip':<16} {'Parametre':>12} {'Saat':>8}"
        ]
        satirlar.append("  " + "─" * 44)
        for b in self.buyume_gecmisi[-15:]:  # Son 15
            satirlar.append(
                f"  {b['no']:>3} {b['tip']:<16} {b['parametre']:>12,} {b['zaman']:>8}"
            )
        return "\n".join(satirlar)


# ═══════════════════════════════════════════════════════════════════════════════
# PLATO (TAKILMA) ALGILAYICI
# ═══════════════════════════════════════════════════════════════════════════════
class PlatoAlgilayici:
    def __init__(self, pencere: int, esik: float, bekleme: int):
        self.pencere  = pencere
        self.esik     = esik
        self.bekleme  = bekleme
        self._son     = deque(maxlen=pencere)
        self._son_b   = 0
        self._adim    = 0

    def guncelle(self, loss: float) -> bool:
        self._adim += 1
        if loss > 0:
            self._son.append(loss)
        if len(self._son) < self.pencere:
            return False
        if (self._adim - self._son_b) < self.bekleme:
            return False
        yari = self.pencere // 2
        ilk  = sum(list(self._son)[:yari]) / yari
        son  = sum(list(self._son)[yari:]) / yari
        dusus = (ilk - son) / max(ilk, 1e-8)
        if dusus < self.esik:
            logger.info(f"[Plato] Takıldı! Düşüş={dusus*100:.2f}% < Eşik={self.esik*100:.0f}%")
            return True
        return False

    def sifirla(self):
        self._son_b = self._adim
        self._son.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# DIRECTML GPU OPTIMIZED ADAMW (ZERO CPU FALLBACK)
# ═══════════════════════════════════════════════════════════════════════════════
class DirectMLAdamW(torch.optim.Optimizer):
    """AMD DirectML için özel optimize edilmiş, sıfır CPU-fallback saf GPU AdamW optimizer."""
    def __init__(self, params, lr=1e-3, betas=(0.9, 0.95), eps=1e-8, weight_decay=1e-2):
        defaults = dict(lr=lr, betas=betas, eps=eps, weight_decay=weight_decay)
        super().__init__(params, defaults)

    @torch.no_grad()
    def step(self, closure=None):
        loss = None
        if closure is not None:
            with torch.enable_grad():
                loss = closure()

        for group in self.param_groups:
            beta1, beta2 = group["betas"]
            eps = group["eps"]
            lr = group["lr"]
            wd = group["weight_decay"]

            for p in group["params"]:
                if p.grad is None:
                    continue
                grad = p.grad
                if grad.is_sparse:
                    raise RuntimeError("DirectMLAdamW sparse gradyanları desteklemez.")

                state = self.state[p]
                if len(state) == 0:
                    state["step"] = 0
                    state["exp_avg"] = torch.zeros_like(p)
                    state["exp_avg_sq"] = torch.zeros_like(p)

                exp_avg, exp_avg_sq = state["exp_avg"], state["exp_avg_sq"]
                state["step"] += 1
                step = state["step"]

                if wd != 0:
                    p.mul_(1.0 - lr * wd)

                exp_avg.mul_(beta1).add_(grad, alpha=1.0 - beta1)
                exp_avg_sq.mul_(beta2).addcmul_(grad, grad, value=1.0 - beta2)

                bias_correction1 = 1.0 - (beta1 ** step)
                bias_correction2 = 1.0 - (beta2 ** step)
                step_size = lr / bias_correction1
                denom = (exp_avg_sq.sqrt() / math.sqrt(bias_correction2)).add_(eps)

                p.addcdiv_(exp_avg, denom, value=-step_size)

        return loss


# ═══════════════════════════════════════════════════════════════════════════════
# BEYİN YÖNETİCİSİ
# ═══════════════════════════════════════════════════════════════════════════════
class BeynYoneticisi:
    def __init__(self, hafiza):
        self.hafiza = hafiza
        self.cfg    = Config()
        dev_str = self.cfg.device or varsayilan_cihaz()
        if str(dev_str).lower() in ("privateuseone", "directml", "privateuseone:0"):
            try:
                import torch_directml
                self.device = torch_directml.device()
            except Exception:
                self.device = torch.device(dev_str)
        else:
            self.device = torch.device(dev_str)
        self._lock  = threading.RLock()
        self.adim   = 0
        self._son_loss_toplami = 0.0
        self._son_loss_sayisi  = 0
        self.is_training       = False
        self._buyume_seviyesi  = 0  # döngü: 0→ff, 1→blok, 2→embed, tekrar

        # Donanım Profili ve Dinamik Hız/Kapasite Ayarı
        import hardware
        self.profile = hardware.get_hardware_profile()
        self.cfg.batch_size = self.profile.get("batch_size", 32)
        self.cfg.ff_buyume_kat = self.profile.get("ff_growth_factor", 1.35)
        self._burst_steps = self.profile.get("burst_steps", 4)
        self._pacing_sleep = self.profile.get("pacing_sleep", 0.01)
        logger.info(f"[Donanım Profili] {self.profile.get('tier_name')} | Batch: {self.cfg.batch_size} | Burst: {self._burst_steps}x")

        # Multi-GPU hazırlığı
        self.gpu_count = 1
        if torch.cuda.is_available():
            self.gpu_count = max(1, torch.cuda.device_count())
        self.is_multi_gpu = (self.gpu_count > 1 and str(self.device).startswith("cuda"))

        # Vocab
        self.char2id: Dict[str, int] = {}
        self.id2char: Dict[int, str] = {}
        self._vocab_yukle_veya_olustur()


        # Model
        self.raw_model = DinamikNovaLM(self.cfg).to(self.device)
        if self.is_multi_gpu:
            self.model = nn.DataParallel(self.raw_model)
            logger.info(f"[Beyin] 🔥 Multi-GPU DataParallel aktif ({self.gpu_count}x CUDA GPU)")
        else:
            self.model = self.raw_model

        self.optimizer, self.scheduler = self._optimizer_olustur()

        # Plato algılayıcı
        self.plato = PlatoAlgilayici(
            pencere=self.cfg.plato_pencere,
            esik=self.cfg.plato_esigi,
            bekleme=self.cfg.buyume_bekleme
        )

        self.yukle()
        logger.info(f"[Beyin] {self.raw_model.mimari_ozet()}")

    # ── Optimizer ─────────────────────────────────────────────────────────────
    def _optimizer_olustur(self):
        target = self.raw_model if hasattr(self, "raw_model") else self.model
        decay    = [p for n,p in target.named_parameters()
                    if p.requires_grad and p.dim() >= 2]
        no_decay = [p for n,p in target.named_parameters()
                    if p.requires_grad and p.dim() < 2]
        param_groups = [
            {"params": decay,    "weight_decay": self.cfg.weight_decay},
            {"params": no_decay, "weight_decay": 0.0},
        ]
        if "privateuseone" in str(self.device) or "dml" in str(self.device).lower():
            opt = DirectMLAdamW(param_groups, lr=self.cfg.lr, betas=(0.9, 0.95), eps=1e-8)
        else:
            opt = AdamW(param_groups, lr=self.cfg.lr, betas=(0.9, 0.95), eps=1e-8)

        sch = CosineAnnealingWarmRestarts(opt, T_0=self.cfg.t_max, T_mult=2, eta_min=5e-6)
        return opt, sch



    # ── Vocab ─────────────────────────────────────────────────────────────────
    def _vocab_yukle_veya_olustur(self):
        target_path = self.cfg.vocab_path
        if not os.path.exists(target_path):
            bundled = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nova_vocab.json")
            if os.path.exists(bundled):
                target_path = bundled

        if os.path.exists(target_path):
            with open(target_path, "r", encoding="utf-8") as f:
                d = json.load(f)
            self.char2id = d["char2id"]
            self.id2char = {int(k): v for k,v in d["id2char"].items()}
            return
        temel = (" \n\t\r"
                 "abcçdefgğhıijklmnoöpqrsştuüvwxyz"
                 "ABCÇDEFGĞHIİJKLMNOÖPQRSŞTUÜVWXYZ"
                 "0123456789.,!?;:'\"-()[]{}@#$%&*+=/<>\\|`~^_")
        for tok in ["<PAD>","<UNK>","<BOS>","<EOS>","<SEP>"]:
            i = len(self.char2id); self.char2id[tok] = i; self.id2char[i] = tok
        for ch in temel:
            if ch not in self.char2id and len(self.char2id) < self.cfg.vocab_size:
                i = len(self.char2id); self.char2id[ch] = i; self.id2char[i] = ch
        self._vocab_kaydet()

    def _vocab_guncelle(self, metin: str) -> bool:
        degisti = False
        for ch in metin:
            if ch not in self.char2id and len(self.char2id) < self.cfg.vocab_size-1:
                i = len(self.char2id); self.char2id[ch] = i; self.id2char[i] = ch
                degisti = True
        if degisti: self._vocab_kaydet()
        return degisti

    def _vocab_kaydet(self):
        with open(self.cfg.vocab_path, "w", encoding="utf-8") as f:
            json.dump({"char2id": self.char2id, "id2char": self.id2char},
                      f, ensure_ascii=False, indent=2)

    def encode(self, metin: str) -> List[int]:
        unk = self.char2id.get("<UNK>", 1)
        return [self.char2id.get(ch, unk) for ch in metin]

    def decode(self, ids: List[int]) -> str:
        return "".join(self.id2char.get(i,"") for i in ids)

    # ── Büyüme ────────────────────────────────────────────────────────────────
    def buyut(self) -> str:
        """Takılmayı algıladığında çağrılır. 3 seviyeyi sırayla dener."""
        with self._lock:
            denenen = 0
            while denenen < 3:
                sev = self._buyume_seviyesi % 3
                if sev == 0:   mesaj = self.raw_model.ff_genislet()
                elif sev == 1: mesaj = self.raw_model.yeni_blok_ekle()
                else:          mesaj = self.raw_model.embed_genislet()

                self._buyume_seviyesi += 1
                denenen += 1

                if mesaj is not None:
                    if self.is_multi_gpu:
                        self.model = nn.DataParallel(self.raw_model)
                    # Optimizer yeniden oluştur (yeni tensörler var)
                    self.optimizer, self.scheduler = self._optimizer_olustur()
                    self.plato.sifirla()
                    bildirim = (
                        f"\n{'═'*60}\n"
                        f"  🧠 NOVA BÜYÜDÜ! [{self.raw_model._toplam_buyume}. büyüme]\n"
                        f"  {mesaj}\n"
                        f"  Yeni: {self.raw_model.mimari_ozet()}\n"
                        f"{'═'*60}"
                    )
                    logger.info(bildirim)
                    print(bildirim)
                    return mesaj

            return "Tüm boyutlar maksimuma ulaştı"

    # ── Üretim ────────────────────────────────────────────────────────────────
    def uret(self, tohum: str, uzunluk: int = 250, sicaklik: float = 0.85,
             top_k: int = 50, top_p: float = 0.92, rep_ceza: float = 1.3, **kwargs) -> str:
        with self._lock:
            self._vocab_guncelle(tohum)
            ids = self.encode(tohum) or [self.char2id.get("<BOS>", 0)]
            ids = ids[-self.cfg.max_seq_len:]
            idx = torch.tensor([ids], dtype=torch.long, device=self.device)
            out = self.raw_model.uret(idx, max_new=uzunluk,
                                      sicaklik=sicaklik, top_k=top_k, top_p=top_p,
                                      rep_ceza=rep_ceza)
            return self.decode(out[0, len(ids):].tolist())


    # ── Eğitim ────────────────────────────────────────────────────────────────
    def egitim_adimi(self, metinler: List[str]) -> float:
        import random
        seq = self.cfg.max_seq_len
        bx: List[List[int]] = []
        by: List[List[int]] = []

        for m in metinler:
            if len(m) < self.cfg.min_text_len: continue
            self._vocab_guncelle(m)
            ids = self.encode(m)
            if len(ids) < 2: continue
            for s in range(0, len(ids)-1, seq//2):
                ch = ids[s:s+seq+1]
                if len(ch) < 2: continue
                x = ch[:-1] + [0]*max(0, seq-len(ch)+1)
                y = ch[1:]  + [-1]*max(0, seq-len(ch)+1)
                bx.append(x[:seq]); by.append(y[:seq])
                if len(bx) >= self.cfg.batch_size*2: break
            if len(bx) >= self.cfg.batch_size*2: break

        if len(bx) < 2: return 0.0

        try:
            target_batch = min(self.cfg.batch_size, len(bx))
            sel = random.sample(range(len(bx)), target_batch)
            xt = torch.tensor([bx[i] for i in sel], dtype=torch.long, device=self.device)
            yt = torch.tensor([by[i] for i in sel], dtype=torch.long, device=self.device)

            with self._lock:
                self.model.train()
                self.optimizer.zero_grad(set_to_none=True)
                if self.adim < self.cfg.warmup_steps:
                    for g in self.optimizer.param_groups:
                        g["lr"] = self.cfg.lr * (self.adim+1) / self.cfg.warmup_steps
                _, loss = self.model(xt, yt)
                if loss is None or torch.isnan(loss): return 0.0
                loss.backward()
                nn.utils.clip_grad_norm_(self.model.parameters(), self.cfg.grad_clip)
                self.optimizer.step()
                self.scheduler.step()
                self.adim += 1
                lv = loss.item()
                self._son_loss_toplami += lv
                self._son_loss_sayisi  += 1

                # Plato kontrolü → otomatik büyüme
                if self.plato.guncelle(lv):
                    self.buyut()

                if self.adim % self.cfg.save_every == 0:
                    ort = self._son_loss_toplami / max(self._son_loss_sayisi, 1)
                    lr  = self.optimizer.param_groups[0]["lr"]
                    raw = getattr(self, "raw_model", self.model)
                    logger.info(f"[Beyin] Adım {self.adim:>5} | Loss: {ort:.4f} | "
                                f"LR: {lr:.2e} | {raw.mimari_ozet() if hasattr(raw, 'mimari_ozet') else ''}")
                    self._son_loss_toplami = 0.0
                    self._son_loss_sayisi  = 0
                    self.kaydet()
                return lv
        except RuntimeError as re_err:
            if "memory" in str(re_err).lower() or "allocate" in str(re_err).lower():
                self.cfg.batch_size = max(4, self.cfg.batch_size // 2)
                import gc
                gc.collect()
                return 0.0
            raise



    # ── Sürekli Eğitim ────────────────────────────────────────────────────────
    def surekli_egitim_baslat(self) -> threading.Thread:
        if getattr(self, "is_training", False):
            logger.info("[Eğitim] Sürekli eğitim zaten aktif durumda.")
            return getattr(self, "_egitim_thread_ref", threading.current_thread())

        self.is_training = True

        def _dongu():
            logger.info("[Eğitim] Sürekli eğitim başladı.")
            burst = getattr(self, "_burst_steps", 4)
            pacing = getattr(self, "_pacing_sleep", 0.01)
            while getattr(self, "is_training", False):
                try:
                    kayitlar = self.hafiza.egitilmemis_bilgi_getir(limit=40)
                    if kayitlar:
                        texts = [r["icerik"] for r in kayitlar]
                        for _ in range(burst):
                            if not getattr(self, "is_training", False):
                                break
                            self.egitim_adimi(texts)
                        for r in kayitlar: self.hafiza.bilgiyi_isle(r["id"])
                        time.sleep(pacing)
                    else:
                        anilar = self.hafiza.son_anilar_getir(limit=40)
                        metinler = [a["icerik"] for a in anilar
                                    if len(a["icerik"]) >= self.cfg.min_text_len]
                        if metinler:
                            for _ in range(burst):
                                if not getattr(self, "is_training", False):
                                    break
                                self.egitim_adimi(metinler)
                            time.sleep(pacing)
                        else:
                            time.sleep(1.0)
                except Exception as e:
                    logger.error(f"[Eğitim] {e}", exc_info=True)
                    time.sleep(1)
            logger.info("[Eğitim] Sürekli eğitim döngüsü durduruldu.")

        t = threading.Thread(target=_dongu, daemon=True, name="NovaEgitim")
        self._egitim_thread_ref = t
        t.start()
        return t




    def egitimi_durdur(self):
        logger.info("[Eğitim] Sürekli eğitim durduruluyor...")
        self.is_training = False

    def son_loss(self) -> float:
        if self._son_loss_sayisi == 0: return float("inf")
        return self._son_loss_toplami / self._son_loss_sayisi

    # ── Checkpoint ────────────────────────────────────────────────────
    def kaydet(self):
        try:
            target = self.raw_model if hasattr(self, "raw_model") else self.model
            state = {
                "model_state":    target.state_dict(),
                "opt_state":      self.optimizer.state_dict(),
                "sch_state":      self.scheduler.state_dict(),
                "adim":           self.adim,
                "char2id":        self.char2id,
                "id2char":        self.id2char,
                "embed_dim":      target._e,
                "n_heads":        target._h,
                "n_layers":       len(target.bloklar),
                "ff_dim":         target._ff,
                "buyume_gecmisi": target.buyume_gecmisi,
                "toplam_buyume":  target._toplam_buyume,
                "buyume_seviyesi": getattr(self, "_buyume_seviyesi", 0),
            }
            target_path = self.cfg.weights_path
            tmp_path = target_path + ".tmp"
            torch.save(state, tmp_path)
            if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 1000:
                import shutil
                shutil.copyfile(tmp_path, target_path)
                try: os.remove(tmp_path)
                except Exception: pass
            logger.info(f"[Beyin] Kaydedildi ({target.param_sayisi():,} param)")
        except Exception as e:
            logger.error(f"[Beyin] Kaydetme hatası: {e}")

    def yukle(self):
        target_weights = self.cfg.weights_path
        if not os.path.exists(target_weights) or os.path.getsize(target_weights) == 0:
            bundled = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nova_weights.pth")
            if os.path.exists(bundled) and os.path.getsize(bundled) > 0:
                target_weights = bundled

        if not os.path.exists(target_weights) or os.path.getsize(target_weights) == 0:
            logger.info("[Beyin] Sıfırdan başlıyor."); return
        try:
            ck = torch.load(target_weights,
                            map_location="cpu", weights_only=False)
            # Mimariyi geri yükle
            if "embed_dim" in ck:
                self.cfg.embed_dim = ck["embed_dim"]
                self.cfg.n_heads   = ck["n_heads"]
                self.cfg.ff_dim    = ck["ff_dim"]
                self.cfg.n_layers  = ck.get("n_layers", self.cfg.n_layers)
                self.raw_model = DinamikNovaLM(self.cfg).to(self.device)
            if "char2id" in ck:
                self.char2id = ck["char2id"]
                self.id2char = {int(k) if isinstance(k,str) else k: v
                                for k,v in ck["id2char"].items()}
            self.raw_model.load_state_dict(ck["model_state"])
            self.raw_model.tok_emb.weight = self.raw_model.head.weight
            self.raw_model.to(self.device)
            if self.is_multi_gpu:
                self.model = nn.DataParallel(self.raw_model)
            else:
                self.model = self.raw_model


            self.optimizer, self.scheduler = self._optimizer_olustur()
            try: self.optimizer.load_state_dict(ck["opt_state"])
            except Exception: pass
            self.adim = ck.get("adim", 0)
            self._buyume_seviyesi = ck.get("buyume_seviyesi", 0)
            self.raw_model.buyume_gecmisi = ck.get("buyume_gecmisi", [])
            self.raw_model._toplam_buyume = ck.get("toplam_buyume", 0)
            logger.info(f"[Beyin] Yüklendi: {self.raw_model.mimari_ozet()}")
        except Exception as e:
            logger.warning(f"[Beyin] Yükleme başarısız ({e}), sıfırdan.")
            self.raw_model = DinamikNovaLM(self.cfg).to(self.device)
            if self.is_multi_gpu:
                self.model = nn.DataParallel(self.raw_model)
            else:
                self.model = self.raw_model
            self.optimizer, self.scheduler = self._optimizer_olustur()


    def onnx_disa_aktar(self, cikis_yolu: Optional[str] = None) -> str:
        """Eğitilmiş Nova sinir ağını evrensel ONNX formatına dönüştürür."""
        if not cikis_yolu:
            cikis_yolu = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nova_model.onnx")
        dir_name = os.path.dirname(os.path.abspath(cikis_yolu))
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with self._lock:
            target = self.raw_model.cpu()
            target.eval()
            dummy_input = torch.zeros((1, 32), dtype=torch.long, device="cpu")
            torch.onnx.export(
                target,
                dummy_input,
                cikis_yolu,
                input_names=["input_ids"],
                output_names=["logits"],
                dynamic_axes={
                    "input_ids": {0: "batch_size", 1: "seq_len"},
                    "logits": {0: "batch_size", 1: "seq_len"}
                },
                opset_version=14
            )
            target.to(self.device)
            return cikis_yolu

    def agirlik_paketi_olustur(self, cikis_zip: Optional[str] = None) -> str:
        """Ağırlıklar, kelime haznesi ve yapılandırma dosyasını içeren taşınabilir ZIP paketi üretir."""
        import zipfile
        if not cikis_zip:
            cikis_zip = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nova_model_paketi.zip")
        dir_name = os.path.dirname(os.path.abspath(cikis_zip))
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        self.kaydet()
        with zipfile.ZipFile(cikis_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            if os.path.exists(self.cfg.weights_path):
                zf.write(self.cfg.weights_path, "nova_weights.pth")
            if os.path.exists(self.cfg.vocab_path):
                zf.write(self.cfg.vocab_path, "nova_vocab.json")
            if os.path.exists(self.cfg.config_path):
                zf.write(self.cfg.config_path, ".nova_config.json")
        return cikis_zip



