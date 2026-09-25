from __future__ import annotations
# ═══════════════════════════════════════════════════════════════════════════════
# brain.py  —  Nova Sınırsız Büyüyen Dinamik Sinir Ağı
# ═══════════════════════════════════════════════════════════════════════════════
#
# Nova çıkmaza girdiğinde (loss platosu) kendi kendine büyür:
#   Seviye 1 → Feed-Forward nöron sayısını artır   (hızlı, ucuz)
#   Seviye 2 → Yeni Transformer bloğu ekle          (derin)
#   Seviye 3 → Embedding boyutunu genişlet          (en kapsamlı)
#   → 3 seviye bittikten sonra 1'e döner.
#
# NETWORK MORPHISM: Büyüme sırasında eski ağırlıklar korunur; yeni nöronlar ≈0
# ile başlar, çıktıyı bozmaz ve zamanla öğrenir.
#
# Performans:
#   • scaled_dot_product_attention (Flash / bellek-verimli dikkat çekirdekleri)
#   • KV-cache ile token üretimi (her token için tüm dizi yeniden hesaplanmaz)
#   • Vektörize tekrar cezası (Python döngüsü yok)
#   • Eğitim tüm kayıtlardan pencere örnekler; bir veri partisi birkaç adımda kullanılır
#
# Cihaz, batch, öğrenme hızı ve dosya yolları ayarlar.json'dan okunur.
# ═══════════════════════════════════════════════════════════════════════════════

import os, json, time, random, logging, threading
from collections import deque
from typing import Optional, List, Dict, Tuple, Any, Iterator

import ayarlar  # torch'tan önce: CPU thread ayarı
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingWarmRestarts

logger = logging.getLogger("nova.brain")

KVCache = List[Tuple[torch.Tensor, torch.Tensor]]
torch.set_num_threads(ayarlar.thread_sayisi())


# ═══════════════════════════════════════════════════════════════════════════════
# KONFİGÜRASYON (varsayılanlar; ayarlar.json değerleri önceliklidir)
# ═══════════════════════════════════════════════════════════════════════════════
class Config:
    # ── Başlangıç mimarisi (küçük başla, büyüsün) ─────────────────────────────
    vocab_size    : int   = 1024
    embed_dim     : int   = 128
    n_heads       : int   = 4
    n_layers      : int   = 2
    ff_dim        : int   = 512
    max_seq_len   : int   = int(ayarlar.AYAR["max_seq_len"])
    dropout       : float = 0.10

    # ── Büyüme limitleri (bellek koruması) ────────────────────────────────────
    max_embed_dim : int   = 2048
    max_n_layers  : int   = 48
    max_n_heads   : int   = 32
    max_ff_dim    : int   = 16384

    # ── Büyüme tetikleyici ────────────────────────────────────────────────────
    plato_pencere : int   = 60
    plato_esigi   : float = float(ayarlar.AYAR["buyume_esigi"])
    buyume_bekleme: int   = 120
    ff_buyume_kat : float = 1.5

    # ── Eğitim ────────────────────────────────────────────────────────────────
    lr            : float = float(ayarlar.AYAR["ogrenme_hizi"])
    weight_decay  : float = 0.01
    batch_size    : int   = int(ayarlar.AYAR["batch_size"])
    grad_clip     : float = 1.0
    warmup_steps  : int   = 100
    t_max         : int   = 2000
    burst_adim    : int   = 4        # aynı veri partisiyle yapılan adım sayısı

    # ── Operasyon ─────────────────────────────────────────────────────────────
    save_every    : int   = int(ayarlar.AYAR["kayit_araligi"])
    min_text_len  : int   = 20

    # ── Dosyalar ──────────────────────────────────────────────────────────────
    weights_path  : str   = ayarlar.yol("agirlik_dosyasi")
    vocab_path    : str   = ayarlar.yol("vocab_dosyasi")
    device        : str   = ayarlar.cihaz()


def _yeni_linear(n_in: int, n_out: int, ref: torch.Tensor) -> nn.Linear:
    """Referans ağırlıkla aynı cihaz/dtype üzerinde bias'sız Linear katman."""
    return nn.Linear(n_in, n_out, bias=False, device=ref.device, dtype=ref.dtype)


# ═══════════════════════════════════════════════════════════════════════════════
# DİNAMİK FF — büyüyebilen feed-forward bloğu
# ═══════════════════════════════════════════════════════════════════════════════
class DinamikFF(nn.Module):
    def __init__(self, embed_dim: int, ff_dim: int, dropout: float):
        super().__init__()
        self._embed, self._ff, self.dropout = embed_dim, ff_dim, dropout
        self.fc1  = nn.Linear(embed_dim, ff_dim, bias=False)
        self.fc2  = nn.Linear(ff_dim, embed_dim, bias=False)
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.drop(self.fc2(F.gelu(self.fc1(x))))

    @property
    def ff_dim(self) -> int:
        return self._ff

    @torch.no_grad()
    def ff_genislet(self, yeni_ff: int) -> bool:
        if yeni_ff <= self._ff:
            return False
        w1, w2, e, ff = self.fc1.weight, self.fc2.weight, self._embed, self._ff
        yeni1, yeni2 = _yeni_linear(e, yeni_ff, w1), _yeni_linear(yeni_ff, e, w2)
        yeni1.weight[:ff] = w1
        yeni1.weight[ff:].normal_(0.0, 0.001)
        yeni2.weight[:, :ff] = w2
        yeni2.weight[:, ff:].zero_()
        self.fc1, self.fc2, self._ff = yeni1, yeni2, yeni_ff
        return True

    @torch.no_grad()
    def embed_guncelle(self, yeni_e: int) -> bool:
        if yeni_e <= self._embed:
            return False
        w1, w2, e, ff = self.fc1.weight, self.fc2.weight, self._embed, self._ff
        yeni1, yeni2 = _yeni_linear(yeni_e, ff, w1), _yeni_linear(ff, yeni_e, w2)
        yeni1.weight[:, :e] = w1
        yeni1.weight[:, e:].normal_(0.0, 0.001)
        yeni2.weight[:e] = w2
        yeni2.weight[e:].zero_()
        self.fc1, self.fc2, self._embed = yeni1, yeni2, yeni_e
        return True


# ═══════════════════════════════════════════════════════════════════════════════
# DİNAMİK DİKKAT — SDPA tabanlı, KV-cache destekli self-attention
# ═══════════════════════════════════════════════════════════════════════════════
class DinamikDikkat(nn.Module):
    def __init__(self, embed_dim: int, n_heads: int, max_seq: int, dropout: float):
        super().__init__()
        assert embed_dim % n_heads == 0
        self._e, self._h, self._ms, self._dp = embed_dim, n_heads, max_seq, dropout
        self.qkv      = nn.Linear(embed_dim, 3 * embed_dim, bias=False)
        self.proj     = nn.Linear(embed_dim, embed_dim, bias=False)
        self.res_drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor,
                cache: Optional[Tuple[torch.Tensor, torch.Tensor]] = None
                ) -> Tuple[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]:
        B, T, C = x.shape
        hd = C // self._h
        q, k, v = self.qkv(x).split(C, dim=2)
        q = q.view(B, T, self._h, hd).transpose(1, 2)
        k = k.view(B, T, self._h, hd).transpose(1, 2)
        v = v.view(B, T, self._h, hd).transpose(1, 2)
        if cache is not None:
            k = torch.cat((cache[0], k), dim=2)
            v = torch.cat((cache[1], v), dim=2)
        # Önbellekli tek-token adımında sorgu tüm geçmişi görebilir → maske gerekmez.
        out = F.scaled_dot_product_attention(
            q, k, v, is_causal=cache is None,
            dropout_p=self._dp if self.training else 0.0,
        )
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        return self.res_drop(self.proj(out)), (k, v)

    @torch.no_grad()
    def embed_guncelle(self, yeni_e: int, yeni_h: int) -> bool:
        if yeni_e <= self._e:
            return False
        assert yeni_e % yeni_h == 0
        e, ye = self._e, yeni_e
        wq, wp = self.qkv.weight, self.proj.weight
        yqkv, yproj = _yeni_linear(ye, 3 * ye, wq), _yeni_linear(ye, ye, wp)
        yqkv.weight.normal_(0.0, 0.001)
        # Q, K ve V bloklarını ayrı ayrı yeni düzene taşı (split(C) sınırları korunur)
        for i in range(3):
            yqkv.weight[i * ye: i * ye + e, :e] = wq[i * e:(i + 1) * e]
        yproj.weight.zero_()
        yproj.weight[:e, :e] = wp
        self.qkv, self.proj = yqkv, yproj
        self._e, self._h = yeni_e, yeni_h
        return True


# ═══════════════════════════════════════════════════════════════════════════════
# DİNAMİK BLOK
# ═══════════════════════════════════════════════════════════════════════════════
class DinamikBlok(nn.Module):
    def __init__(self, embed_dim: int, n_heads: int, ff_dim: int, max_seq: int, dropout: float):
        super().__init__()
        self._e    = embed_dim
        self.norm1 = nn.LayerNorm(embed_dim)
        self.attn  = DinamikDikkat(embed_dim, n_heads, max_seq, dropout)
        self.norm2 = nn.LayerNorm(embed_dim)
        self.ff    = DinamikFF(embed_dim, ff_dim, dropout)

    def forward(self, x: torch.Tensor, cache=None):
        a, yeni_cache = self.attn(self.norm1(x), cache)
        x = x + a
        x = x + self.ff(self.norm2(x))
        return x, yeni_cache

    def ff_genislet(self, yeni_ff: int) -> bool:
        return self.ff.ff_genislet(yeni_ff)

    @torch.no_grad()
    def embed_guncelle(self, yeni_e: int, yeni_h: int) -> bool:
        if yeni_e <= self._e:
            return False
        e = self._e
        for attr in ("norm1", "norm2"):
            old = getattr(self, attr)
            yeni = nn.LayerNorm(yeni_e, device=old.weight.device, dtype=old.weight.dtype)
            yeni.weight[:e] = old.weight
            yeni.bias[:e] = old.bias
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
        self.cfg = cfg
        self._e, self._h, self._ff = cfg.embed_dim, cfg.n_heads, cfg.ff_dim

        self.tok_emb  = nn.Embedding(cfg.vocab_size, cfg.embed_dim)
        self.pos_emb  = nn.Embedding(cfg.max_seq_len, cfg.embed_dim)
        self.emb_drop = nn.Dropout(cfg.dropout)
        self.bloklar  = nn.ModuleList([
            DinamikBlok(cfg.embed_dim, cfg.n_heads, cfg.ff_dim, cfg.max_seq_len, cfg.dropout)
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
            if isinstance(m, (nn.Linear, nn.Embedding)):
                nn.init.normal_(m.weight, 0.0, 0.02)
            elif isinstance(m, nn.LayerNorm):
                nn.init.ones_(m.weight); nn.init.zeros_(m.bias)

    def _ileri(self, idx: torch.Tensor, cache: Optional[KVCache] = None, pos0: int = 0
               ) -> Tuple[torch.Tensor, KVCache]:
        T = idx.shape[1]
        pos = torch.arange(pos0, pos0 + T, device=idx.device, dtype=torch.long)
        x = self.emb_drop(self.tok_emb(idx) + self.pos_emb(pos))
        yeni: KVCache = []
        for i, blok in enumerate(self.bloklar):
            x, c = blok(x, cache[i] if cache is not None else None)
            yeni.append(c)
        return self.head(self.norm(x)), yeni

    def forward(self, idx: torch.Tensor, targets: Optional[torch.Tensor] = None
                ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        logits, _ = self._ileri(idx)
        loss = None
        if targets is not None:
            loss = F.cross_entropy(logits.view(-1, logits.size(-1)), targets.view(-1),
                                   ignore_index=-1, label_smoothing=0.05)
        return logits, loss

    # ── Örnekleme ─────────────────────────────────────────────────────────────
    @staticmethod
    def _ornekle(logits: torch.Tensor, gecmis: torch.Tensor, sicaklik: float,
                 top_k: int, top_p: float, rep_ceza: float) -> torch.Tensor:
        logits = logits.float()
        if rep_ceza != 1.0 and gecmis.numel():
            skor = torch.gather(logits, 1, gecmis)
            skor = torch.where(skor > 0, skor / rep_ceza, skor * rep_ceza)
            logits = logits.scatter(1, gecmis, skor)
        logits = logits / max(sicaklik, 1e-8)
        if top_k > 0:
            v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
            logits = logits.masked_fill(logits < v[:, [-1]], float("-inf"))
        if 0 < top_p < 1:
            sl, si = torch.sort(logits, descending=True)
            p = F.softmax(sl, dim=-1)
            sl = sl.masked_fill(torch.cumsum(p, dim=-1) - p > top_p, float("-inf"))
            logits = torch.full_like(logits, float("-inf")).scatter(1, si, sl)
        return torch.multinomial(F.softmax(logits, dim=-1), 1)

    @torch.no_grad()
    def uret_stream(self, idx: torch.Tensor, max_new: int = 150, sicaklik: float = 0.65,
                    top_k: int = 8, top_p: float = 0.88, rep_ceza: float = 1.25) -> Iterator[int]:
        """KV-cache ile token token üretim (her adımda yalnızca yeni token işlenir)."""
        onceki_mod = self.training
        self.eval()
        try:
            ms = self.cfg.max_seq_len
            gen = idx[:, -ms:]
            logits, cache = self._ileri(gen)
            for _ in range(max_new):
                nxt = self._ornekle(logits[:, -1, :], gen, sicaklik, top_k, top_p, rep_ceza)
                gen = torch.cat((gen, nxt), dim=1)
                yield int(nxt[0, 0])
                boy = cache[0][0].shape[2]
                if boy + 1 > ms:
                    # Pencere doldu: son ms token ile önbelleği yeniden kur
                    gen = gen[:, -ms:]
                    logits, cache = self._ileri(gen)
                else:
                    logits, cache = self._ileri(nxt, cache, pos0=boy)
        finally:
            self.train(onceki_mod)

    @torch.no_grad()
    def uret(self, idx: torch.Tensor, max_new: int = 150, **kw) -> torch.Tensor:
        toks = list(self.uret_stream(idx, max_new=max_new, **kw))
        if not toks:
            return idx
        return torch.cat((idx, torch.tensor([toks], dtype=idx.dtype, device=idx.device)), dim=1)

    # ══ BÜYÜME ════════════════════════════════════════════════════════════════
    def _aktif_cihaz(self) -> torch.device:
        try:
            return next(self.parameters()).device
        except StopIteration:
            return torch.device("cpu")

    def ff_genislet(self) -> Optional[str]:
        """Seviye 1: Tüm bloklarda FF nöron sayısını artır."""
        if self._ff >= self.cfg.max_ff_dim:
            return None
        yeni = min(int(self._ff * self.cfg.ff_buyume_kat), self.cfg.max_ff_dim)
        yeni = (max(yeni, self._ff + 64) // 64) * 64
        if yeni <= self._ff:
            return None
        for blok in self.bloklar:
            blok.ff_genislet(yeni)
        eski, self._ff = self._ff, yeni
        self._kayit_buyume("ff_genislet", eski_ff=eski, yeni_ff=yeni, blok_sayisi=len(self.bloklar))
        return f"FF nöron: {eski:,} → {yeni:,} (tüm {len(self.bloklar)} blokta)"

    def yeni_blok_ekle(self) -> Optional[str]:
        """Seviye 2: Ortaya neredeyse şeffaf yeni bir Transformer bloğu ekle."""
        if len(self.bloklar) >= self.cfg.max_n_layers:
            return None
        yeni_blok = DinamikBlok(self._e, self._h, self._ff, self.cfg.max_seq_len,
                                self.cfg.dropout).to(self._aktif_cihaz())
        with torch.no_grad():
            for p in yeni_blok.parameters():
                p.mul_(0.01)
        idx = len(self.bloklar) // 2
        bl = list(self.bloklar)
        bl.insert(idx, yeni_blok)
        self.bloklar = nn.ModuleList(bl)
        self._kayit_buyume("yeni_blok", blok_idx=idx, toplam_blok=len(self.bloklar))
        return f"Yeni blok eklendi [idx={idx}] → toplam {len(self.bloklar)} blok"

    @torch.no_grad()
    def embed_genislet(self) -> Optional[str]:
        """Seviye 3: Embedding boyutunu ve ilgili tüm katmanları genişlet."""
        if self._e >= self.cfg.max_embed_dim:
            return None
        yeni_e = min(self._e + 64, self.cfg.max_embed_dim)
        yeni_h = self._h
        while yeni_e % yeni_h != 0 and yeni_h > 1:
            yeni_h -= 1

        dev, e, V, PS = self._aktif_cihaz(), self._e, self.cfg.vocab_size, self.cfg.max_seq_len

        yp = nn.Embedding(PS, yeni_e, device=dev)
        yp.weight[:, :e] = self.pos_emb.weight
        yp.weight[:, e:].normal_(0.0, 0.001)
        self.pos_emb = yp

        yn = nn.LayerNorm(yeni_e, device=dev)
        yn.weight[:e] = self.norm.weight
        yn.bias[:e] = self.norm.bias
        self.norm = yn

        yh = nn.Linear(yeni_e, V, bias=False, device=dev)
        yh.weight[:, :e] = self.head.weight
        yh.weight[:, e:].zero_()
        self.head = yh
        self.tok_emb = nn.Embedding(V, yeni_e, device=dev)
        self.tok_emb.weight = self.head.weight   # weight tying

        for blok in self.bloklar:
            blok.embed_guncelle(yeni_e, yeni_h)

        eski_e, eski_h = self._e, self._h
        self._e, self._h = yeni_e, yeni_h
        self._kayit_buyume("embed_genislet", eski_embed=eski_e, yeni_embed=yeni_e,
                           eski_kafa=eski_h, yeni_kafa=yeni_h)
        return f"Embed: {eski_e} → {yeni_e} | Kafa: {eski_h} → {yeni_h}"

    def _kayit_buyume(self, tip: str, **kwargs):
        from datetime import datetime
        self._toplam_buyume += 1
        self.buyume_gecmisi.append({"no": self._toplam_buyume, "tip": tip,
                                    "parametre": self.param_sayisi(),
                                    "zaman": datetime.now().strftime("%H:%M:%S"), **kwargs})

    # ══ DURUM ════════════════════════════════════════════════════════════════
    def param_sayisi(self) -> int:
        return sum(p.numel() for p in self.parameters())   # paylaşılan ağırlık bir kez sayılır

    def mimari_ozet(self) -> str:
        return (f"Nova[embed={self._e}, kafa={self._h}, blok={len(self.bloklar)}, "
                f"ff={self._ff}, param={self.param_sayisi():,}, büyüme={self._toplam_buyume}x]")

    def buyume_tablosu(self) -> str:
        if not self.buyume_gecmisi:
            return "  Henüz büyüme gerçekleşmedi."
        satirlar = [f"  {'No':>3} {'Tip':<16} {'Parametre':>12} {'Saat':>8}", "  " + "─" * 44]
        satirlar += [f"  {b['no']:>3} {b['tip']:<16} {b['parametre']:>12,} {b['zaman']:>8}"
                     for b in self.buyume_gecmisi[-15:]]
        return "\n".join(satirlar)


# ═══════════════════════════════════════════════════════════════════════════════
# PLATO (TAKILMA) ALGILAYICI
# ═══════════════════════════════════════════════════════════════════════════════
class PlatoAlgilayici:
    def __init__(self, pencere: int, esik: float, bekleme: int):
        self.pencere, self.esik, self.bekleme = pencere, esik, bekleme
        self._son: deque = deque(maxlen=pencere)
        self._son_b = 0
        self._adim  = 0

    def guncelle(self, loss: float) -> bool:
        self._adim += 1
        if loss > 0:
            self._son.append(loss)
        if len(self._son) < self.pencere or (self._adim - self._son_b) < self.bekleme:
            return False
        yari = self.pencere // 2
        degerler = list(self._son)
        ilk, son = sum(degerler[:yari]) / yari, sum(degerler[yari:]) / (len(degerler) - yari)
        dusus = (ilk - son) / max(ilk, 1e-8)
        if dusus < self.esik:
            logger.info(f"[Plato] Takıldı! Düşüş={dusus*100:.2f}% < Eşik={self.esik*100:.2f}%")
            return True
        return False

    def sifirla(self):
        self._son_b = self._adim
        self._son.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# BEYİN YÖNETİCİSİ
# ═══════════════════════════════════════════════════════════════════════════════
class BeynYoneticisi:
    def __init__(self, hafiza):
        self.hafiza = hafiza
        self.cfg    = Config()
        self.device = torch.device(self.cfg.device)
        self._lock  = threading.RLock()
        self.adim   = 0
        self._son_loss_toplami = 0.0
        self._son_loss_sayisi  = 0
        self.is_training       = False
        self._egitim_thread: Optional[threading.Thread] = None
        self._buyume_seviyesi  = 0   # döngü: 0→ff, 1→blok, 2→embed

        self.char2id: Dict[str, int] = {}
        self.id2char: Dict[int, str] = {}
        self._vocab_yukle_veya_olustur()

        self.model = DinamikNovaLM(self.cfg).to(self.device)
        self.optimizer, self.scheduler = self._optimizer_olustur()
        self.plato = PlatoAlgilayici(self.cfg.plato_pencere, self.cfg.plato_esigi, self.cfg.buyume_bekleme)

        self.yukle()
        logger.info(f"[Beyin] {self.model.mimari_ozet()} | Cihaz: {self.device}")

    # ── Optimizer ─────────────────────────────────────────────────────────────
    def _optimizer_olustur(self):
        params = [p for p in self.model.parameters() if p.requires_grad]
        groups = [
            {"params": [p for p in params if p.dim() >= 2], "weight_decay": self.cfg.weight_decay},
            {"params": [p for p in params if p.dim() < 2],  "weight_decay": 0.0},
        ]
        opt = AdamW(groups, lr=self.cfg.lr, betas=(0.9, 0.95), eps=1e-8,
                    fused=True if self.device.type == "cuda" else None)
        sch = CosineAnnealingWarmRestarts(opt, T_0=self.cfg.t_max, T_mult=2, eta_min=5e-6)
        return opt, sch

    # ── Vocab ─────────────────────────────────────────────────────────────────
    def _vocab_yukle_veya_olustur(self):
        if os.path.exists(self.cfg.vocab_path):
            with open(self.cfg.vocab_path, "r", encoding="utf-8") as f:
                d = json.load(f)
            self.char2id = d["char2id"]
            self.id2char = {int(k): v for k, v in d["id2char"].items()}
            return
        temel = (" \n\t\r"
                 "abcçdefgğhıijklmnoöpqrsştuüvwxyz"
                 "ABCÇDEFGĞHIİJKLMNOÖPQRSŞTUÜVWXYZ"
                 "0123456789.,!?;:'\"-()[]{}@#$%&*+=/<>\\|`~^_")
        for tok in ["<PAD>", "<UNK>", "<BOS>", "<EOS>", "<SEP>", *temel]:
            if tok not in self.char2id and len(self.char2id) < self.cfg.vocab_size:
                i = len(self.char2id); self.char2id[tok] = i; self.id2char[i] = tok
        self._vocab_kaydet()

    def _vocab_guncelle(self, metin: str) -> bool:
        yeni = set(metin).difference(self.char2id)
        if not yeni:
            return False
        with self._lock:
            degisti = False
            for ch in sorted(yeni):
                if ch in self.char2id:
                    continue
                if len(self.char2id) >= self.cfg.vocab_size - 1:
                    break
                i = len(self.char2id); self.char2id[ch] = i; self.id2char[i] = ch
                degisti = True
            if degisti:
                self._vocab_kaydet()
            return degisti

    def _vocab_kaydet(self):
        tmp = self.cfg.vocab_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"char2id": self.char2id, "id2char": self.id2char}, f, ensure_ascii=False)
        os.replace(tmp, self.cfg.vocab_path)

    def encode(self, metin: str) -> List[int]:
        unk = self.char2id.get("<UNK>", 1)
        return [self.char2id.get(ch, unk) for ch in metin]

    def decode(self, ids: List[int]) -> str:
        return "".join(self.id2char.get(i, "") for i in ids)

    # ── Büyüme ────────────────────────────────────────────────────────────────
    def buyut(self) -> str:
        """Takılmada çağrılır; 3 seviyeyi sırayla dener."""
        with self._lock:
            for _ in range(3):
                sev = self._buyume_seviyesi % 3
                self._buyume_seviyesi += 1
                mesaj = (self.model.ff_genislet() if sev == 0 else
                         self.model.yeni_blok_ekle() if sev == 1 else
                         self.model.embed_genislet())
                if mesaj is not None:
                    self.optimizer, self.scheduler = self._optimizer_olustur()
                    self.plato.sifirla()
                    logger.info(f"🧠 NOVA BÜYÜDÜ! [{self.model._toplam_buyume}. büyüme] "
                                f"{mesaj} → {self.model.mimari_ozet()}")
                    return mesaj
            return "Tüm boyutlar maksimuma ulaştı"

    # ── Üretim ────────────────────────────────────────────────────────────────
    def uret_stream(self, tohum: str, uzunluk: int = 250, sicaklik: float = 0.85,
                    top_k: int = 50, top_p: float = 0.92, rep_ceza: float = 1.3) -> Iterator[str]:
        """Karakter karakter üretim (KV-cache ile)."""
        eos_id = self.char2id.get("<EOS>", 3)
        with self._lock:
            self._vocab_guncelle(tohum)
            ids = (self.encode(tohum) or [self.char2id.get("<BOS>", 0)])[-self.cfg.max_seq_len:]
            idx = torch.tensor([ids], dtype=torch.long, device=self.device)
            for tok in self.model.uret_stream(idx, max_new=uzunluk, sicaklik=sicaklik,
                                              top_k=top_k, top_p=top_p, rep_ceza=rep_ceza):
                if tok == eos_id:
                    break
                ch = self.id2char.get(tok, "")
                if ch:
                    yield ch

    def uret(self, tohum: str, uzunluk: int = 250, sicaklik: float = 0.85,
             top_k: int = 50, top_p: float = 0.92, rep_ceza: float = 1.3, **_) -> str:
        return "".join(self.uret_stream(tohum, uzunluk, sicaklik, top_k, top_p, rep_ceza))

    # ── Eğitim ────────────────────────────────────────────────────────────────
    def _parcalari_hazirla(self, metinler: List[str]) -> Tuple[List[List[int]], List[List[int]]]:
        """Her metinden rastgele pencereler çıkarır (yalnızca ilk metin değil, hepsi öğrenilir)."""
        seq = self.cfg.max_seq_len
        gecerli = [m for m in metinler if len(m) >= self.cfg.min_text_len]
        if not gecerli:
            return [], []
        metin_basi = max(1, -(-self.cfg.batch_size * 2 // len(gecerli)))
        bx: List[List[int]] = []
        by: List[List[int]] = []
        for m in gecerli:
            self._vocab_guncelle(m)
            ids = self.encode(m)
            if len(ids) < 2:
                continue
            son_bas = max(0, len(ids) - seq - 1)
            baslar = {0} if son_bas == 0 else set(random.sample(range(son_bas + 1), min(metin_basi, son_bas + 1)))
            for s in baslar:
                ch = ids[s:s + seq + 1]
                pad = seq + 1 - len(ch)
                bx.append(ch[:-1] + [0] * pad)
                by.append(ch[1:] + [-1] * pad)
        return bx, by

    def _adim(self, bx: List[List[int]], by: List[List[int]]) -> float:
        if len(bx) < 2:
            return 0.0
        sel = random.sample(range(len(bx)), min(self.cfg.batch_size, len(bx)))
        with self._lock:
            xt = torch.tensor([bx[i] for i in sel], dtype=torch.long, device=self.device)
            yt = torch.tensor([by[i] for i in sel], dtype=torch.long, device=self.device)
            self.model.train()
            self.optimizer.zero_grad(set_to_none=True)
            if self.adim < self.cfg.warmup_steps:
                for g in self.optimizer.param_groups:
                    g["lr"] = self.cfg.lr * (self.adim + 1) / self.cfg.warmup_steps
            _, loss = self.model(xt, yt)
            if loss is None or not torch.isfinite(loss):
                return 0.0
            loss.backward()
            nn.utils.clip_grad_norm_(self.model.parameters(), self.cfg.grad_clip)
            self.optimizer.step()
            self.scheduler.step()
            self.adim += 1
            lv = loss.item()
            self._son_loss_toplami += lv
            self._son_loss_sayisi  += 1

            if self.plato.guncelle(lv):
                self.buyut()

            if self.adim % self.cfg.save_every == 0:
                ort = self._son_loss_toplami / max(self._son_loss_sayisi, 1)
                logger.info(f"[Beyin] Adım {self.adim:>5} | Loss: {ort:.4f} | "
                            f"LR: {self.optimizer.param_groups[0]['lr']:.2e} | {self.model.mimari_ozet()}")
                self._son_loss_toplami, self._son_loss_sayisi = 0.0, 0
                self.kaydet()
            return lv

    def egitim_adimi(self, metinler: List[str]) -> float:
        return self._adim(*self._parcalari_hazirla(metinler))

    # ── Sürekli Eğitim ────────────────────────────────────────────────────────
    def surekli_egitim_baslat(self) -> threading.Thread:
        if self.is_training and self._egitim_thread and self._egitim_thread.is_alive():
            return self._egitim_thread
        self.is_training = True

        def _dongu():
            logger.info("[Eğitim] Sürekli eğitim başladı.")
            while self.is_training:
                try:
                    kayitlar = self.hafiza.egitilmemis_bilgi_getir(limit=20)
                    metinler = ([r["icerik"] for r in kayitlar] if kayitlar else
                                [a["icerik"] for a in self.hafiza.son_anilar_getir(limit=20)])
                    bx, by = self._parcalari_hazirla(metinler)
                    if len(bx) < 2:
                        time.sleep(2)
                        continue
                    for _ in range(self.cfg.burst_adim):   # metni bir kez hazırla, birkaç adımda kullan
                        if not self.is_training:
                            break
                        self._adim(bx, by)
                    if kayitlar:
                        self.hafiza.bilgileri_isle([r["id"] for r in kayitlar])
                except Exception as e:
                    logger.error(f"[Eğitim] {e}", exc_info=True)
                    time.sleep(1)

        self._egitim_thread = threading.Thread(target=_dongu, daemon=True, name="NovaEgitim")
        self._egitim_thread.start()
        return self._egitim_thread

    def egitimi_durdur(self):
        self.is_training = False

    def son_loss(self) -> float:
        if self._son_loss_sayisi == 0:
            return float("inf")
        return self._son_loss_toplami / self._son_loss_sayisi

    # ── Checkpoint ────────────────────────────────────────────────────────────
    def kaydet(self):
        """Ağırlıkları atomik kaydeder (yazma yarıda kesilirse eski dosya bozulmaz)."""
        with self._lock:
            try:
                m = self.model
                tmp = self.cfg.weights_path + ".tmp"
                torch.save({
                    "model_state": m.state_dict(), "opt_state": self.optimizer.state_dict(),
                    "sch_state": self.scheduler.state_dict(), "adim": self.adim,
                    "char2id": self.char2id, "id2char": self.id2char,
                    "embed_dim": m._e, "n_heads": m._h, "n_layers": len(m.bloklar), "ff_dim": m._ff,
                    "buyume_gecmisi": m.buyume_gecmisi, "toplam_buyume": m._toplam_buyume,
                    "buyume_seviyesi": self._buyume_seviyesi,
                }, tmp)
                os.replace(tmp, self.cfg.weights_path)
                logger.info(f"[Beyin] Kaydedildi ({m.param_sayisi():,} param)")
            except Exception as e:
                logger.error(f"[Beyin] Kaydetme hatası: {e}")

    def yukle(self):
        if not os.path.isfile(self.cfg.weights_path):
            logger.info("[Beyin] Sıfırdan başlıyor.")
            return
        try:
            ck = torch.load(self.cfg.weights_path, map_location="cpu", weights_only=False)
            if "embed_dim" in ck:
                self.cfg.embed_dim = ck["embed_dim"]
                self.cfg.n_heads   = ck["n_heads"]
                self.cfg.ff_dim    = ck["ff_dim"]
                self.cfg.n_layers  = ck.get("n_layers", self.cfg.n_layers)
            if "char2id" in ck:
                self.char2id = ck["char2id"]
                self.id2char = {int(k): v for k, v in ck["id2char"].items()}
            model = DinamikNovaLM(self.cfg)
            model.load_state_dict(ck["model_state"], strict=False)   # eski 'mask' tamponları yok sayılır
            model.tok_emb.weight = model.head.weight
            model.buyume_gecmisi = ck.get("buyume_gecmisi", [])
            model._toplam_buyume = ck.get("toplam_buyume", 0)
            self.model = model.to(self.device)
            self.optimizer, self.scheduler = self._optimizer_olustur()
            try:
                self.optimizer.load_state_dict(ck["opt_state"])
            except Exception:
                pass
            self.adim = ck.get("adim", 0)
            self._buyume_seviyesi = ck.get("buyume_seviyesi", 0)
            logger.info(f"[Beyin] Yüklendi: {self.model.mimari_ozet()}")
        except Exception as e:
            logger.warning(f"[Beyin] Yükleme başarısız ({e}), sıfırdan.")
            self.model = DinamikNovaLM(self.cfg).to(self.device)
            self.optimizer, self.scheduler = self._optimizer_olustur()
