# -*- coding: utf-8 -*-
"""
model.py - Nova Sınırsız Büyüyen Dinamik Transformer Mimarisi (Network Morphism)
Saf PyTorch uygulaması. Arayüz ve bağımlılık içermez.
"""
from __future__ import annotations
import math
import logging
from collections import deque
from typing import Optional, List, Dict, Tuple, Any

import torch
import torch.nn as nn
import torch.nn.functional as F
from config import TrainerConfig

logger = logging.getLogger("nova.trainer.model")


# ═══════════════════════════════════════════════════════════════════════════════
# DİNAMİK FF — Büyüyebilen Feed-Forward Bloğu
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
# DİNAMİK DİKKAT — Kafa ve Boyut Genişletilebilir Self-Attention
# ═══════════════════════════════════════════════════════════════════════════════
class DinamikDikkat(nn.Module):
    def __init__(self, embed_dim: int, n_heads: int, max_seq: int, dropout: float):
        super().__init__()
        assert embed_dim % n_heads == 0, f"embed_dim ({embed_dim}) % n_heads ({n_heads}) != 0"
        self._e  = embed_dim
        self._h  = n_heads
        self._ms = max_seq
        self._dp = dropout
        self.qkv       = nn.Linear(embed_dim, 3 * embed_dim, bias=False)
        self.proj      = nn.Linear(embed_dim, embed_dim,     bias=False)
        self.attn_drop = nn.Dropout(dropout)
        self.res_drop  = nn.Dropout(dropout)
        mask = torch.tril(torch.ones(max_seq, max_seq, dtype=torch.bool))
        self.register_buffer("mask", mask.view(1, 1, max_seq, max_seq))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, C = x.shape
        hd = C // self._h
        q, k, v = self.qkv(x).split(C, dim=2)
        q = q.view(B, T, self._h, hd).transpose(1, 2)
        k = k.view(B, T, self._h, hd).transpose(1, 2)
        v = v.view(B, T, self._h, hd).transpose(1, 2)

        # FlashAttention-2 / SDPA hızlandırıcısı (A100 ve modern GPU'lar için 3x hız ve %70 VRAM tasarrufu)
        if hasattr(F, "scaled_dot_product_attention"):
            out = F.scaled_dot_product_attention(
                q, k, v,
                is_causal=True,
                dropout_p=self._dp if self.training else 0.0
            )
        else:
            att = (q @ k.transpose(-2, -1)) * (hd ** -0.5)
            att = att.masked_fill(~self.mask[:, :, :T, :T], float("-inf"))
            att = self.attn_drop(F.softmax(att, dim=-1))
            out = att @ v

        out = out.transpose(1, 2).contiguous().view(B, T, C)
        return self.res_drop(self.proj(out))

    def embed_guncelle(self, yeni_e: int, yeni_h: int) -> bool:
        if yeni_e <= self._e:
            return False
        assert yeni_e % yeni_h == 0
        fark, std = yeni_e - self._e, 0.001
        ye = yeni_e
        yqkv  = nn.Linear(ye, 3 * ye, bias=False)
        yproj = nn.Linear(ye, ye,     bias=False)
        with torch.no_grad():
            yqkv.weight[:3*self._e, :self._e] = self.qkv.weight
            yqkv.weight[:3*self._e, self._e:] = torch.randn(3*self._e, fark) * std
            yqkv.weight[3*self._e:, :]        = torch.randn(3*fark, ye) * std
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
# DİNAMİK NOVA LM — Sınırsız Büyüyen Ana Model (Network Morphism)
# ═══════════════════════════════════════════════════════════════════════════════
class DinamikNovaLM(nn.Module):
    def __init__(self, cfg: TrainerConfig):
        super().__init__()
        self.cfg    = cfg
        self._e     = cfg.embed_dim
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

        self.buyume_gecmisi: List[Dict[str, Any]] = []
        self._toplam_buyume = 0

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0.0, 0.02)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.Embedding):
                nn.init.normal_(m.weight, 0.0, 0.02)
            elif isinstance(m, nn.LayerNorm):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

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
        yeni = max(yeni, self._ff + 64)
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
        """Seviye 2: Ortaya yeni bir Transformer bloğu ekle (Şeffaf ağırlıklarla)."""
        if len(self.bloklar) >= self.cfg.max_n_layers:
            return None
        dev = self._aktif_cihaz()
        yeni_blok = DinamikBlok(self._e, self._h, self._ff,
                                 self.cfg.max_seq_len, self.cfg.dropout).to(dev)
        with torch.no_grad():
            for p in yeni_blok.parameters():
                p.data *= 0.01
        idx = len(self.bloklar) // 2
        bl  = list(self.bloklar)
        bl.insert(idx, yeni_blok)
        self.bloklar = nn.ModuleList(bl)
        self.to(dev)
        self._kayit_buyume("yeni_blok", blok_idx=idx,
                            toplam_blok=len(self.bloklar))
        return f"Yeni blok eklendi [idx={idx}] → toplam {len(self.bloklar)} blok"

    def embed_genislet(self) -> Optional[str]:
        """Seviye 3: Embedding boyutunu ve tüm ilgili projeksiyonları genişlet."""
        if self._e >= self.cfg.max_embed_dim:
            return None
        yeni_e = min(self._e + 64, self.cfg.max_embed_dim)
        yeni_h = self._h
        while yeni_e % yeni_h != 0 and yeni_h > 1:
            yeni_h -= 1
        if yeni_e % yeni_h != 0:
            return None

        dev = self._aktif_cihaz()
        fark, std = yeni_e - self._e, 0.001
        V  = self.cfg.vocab_size
        PS = self.cfg.max_seq_len

        yt = nn.Embedding(V, yeni_e).to(dev)
        yp = nn.Embedding(PS, yeni_e).to(dev)
        with torch.no_grad():
            yt.weight[:, :self._e] = self.tok_emb.weight.detach()
            yt.weight[:, self._e:] = torch.randn(V,  fark, device=dev) * std
            yp.weight[:, :self._e] = self.pos_emb.weight.detach()
            yp.weight[:, self._e:] = torch.randn(PS, fark, device=dev) * std
        self.tok_emb, self.pos_emb = yt, yp

        yn = nn.LayerNorm(yeni_e).to(dev)
        with torch.no_grad():
            yn.weight[:self._e] = self.norm.weight
            yn.weight[self._e:] = torch.ones(fark, device=dev)
            yn.bias[:self._e]   = self.norm.bias
            yn.bias[self._e:]   = torch.zeros(fark, device=dev)
        self.norm = yn

        yh = nn.Linear(yeni_e, V, bias=False).to(dev)
        with torch.no_grad():
            yh.weight[:, :self._e] = self.head.weight.detach()
            yh.weight[:, self._e:] = torch.zeros(V, fark, device=dev)
        self.head = yh

        self.tok_emb.weight = self.head.weight

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
        import datetime
        self.buyume_gecmisi.append({
            "no": self._toplam_buyume,
            "tip": tip,
            "parametre": self.param_sayisi(),
            "zaman": datetime.datetime.now().strftime("%H:%M:%S"),
            **kwargs
        })

    def param_sayisi(self) -> int:
        return sum(p.numel() for p in set(self.parameters()))

    def mimari_ozet(self) -> str:
        return (
            f"NovaModel[embed={self._e}, kafa={self._h}, "
            f"blok={len(self.bloklar)}, ff={self._ff}, "
            f"param={self.param_sayisi():,}, "
            f"büyüme={self._toplam_buyume}x]"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PLATO ALGILAYICI
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
            logger.info(f"[Plato] Durağanlık tespit edildi! Düşüş={dusus*100:.2f}% < Eşik={self.esik*100:.1f}%")
            return True
        return False

    def sifirla(self):
        self._son_b = self._adim
        self._son.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# DIRECTML GPU OPTIMIZED ADAMW (AMD UYUMLU)
# ═══════════════════════════════════════════════════════════════════════════════
class DirectMLAdamW(torch.optim.Optimizer):
    """DirectML / GPU için optimize edilmiş saf GPU AdamW."""
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
