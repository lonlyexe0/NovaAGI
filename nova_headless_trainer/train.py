# -*- coding: utf-8 -*-
"""
train.py - Nova Bağımsız Headless Eğitim Motoru
Arayüzsüz, yüksek performanslı sinir ağı eğitimi, Network Morphism ve SQLite nova.db entegrasyonu.

Kullanım:
  python train.py --db nova.db --weights nova_weights.pth --batch_size 32
  python train.py --continuous (Veritabanına yeni veri geldikçe sürekli eğit)
"""
import os
import sys
import time
import json
import random
import logging
import argparse
import threading
from typing import List, Optional

import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingWarmRestarts

from config import TrainerConfig, varsayilan_cihaz
from model import DinamikNovaLM, PlatoAlgilayici, DirectMLAdamW
from tokenizer import NovaTokenizer
from db_manager import TrainerDBManager

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("nova.trainer")


class WebStreamer(threading.Thread):
    """
    Model eğitilirken arka planda internetten (Wikipedia) canlı ve sürekli
    olarak yeni bilgiler çeker ve anında nova.db'ye (islendi=0 olarak) ekler.
    Böylece model hiç durmadan yeni şeyler öğrenir.
    """
    def __init__(self, db: TrainerDBManager, lang: str = "tr", interval: float = 2.0):
        super().__init__(daemon=True, name="NovaWebStreamer")
        self.db = db
        self.lang = lang
        self.interval = interval
        self.running = True
        self.toplam_indirilen = 0
        self.tohumlar = [
            "Yapay zekâ", "Kuantum bilgisayarı", "Derin öğrenme", "Bilişsel bilim",
            "Nörobilim", "Büyük dil modeli", "Karadelik", "Evrenin genişlemesi",
            "Genetik mühendisliği", "Sibernetik", "Robotik", "Evrimsel biyoloji",
            "Astronomi", "Fizik", "Matematik", "Felsefe", "Bilgisayar bilimi",
            "Tarih", "Psikoloji", "Moleküler biyoloji", "Nanoteknoloji"
        ] if lang == "tr" else [
            "Artificial intelligence", "Quantum computing", "Deep learning", "Cognitive science",
            "Neuroscience", "Large language model", "Black hole", "Expansion of the universe",
            "Genetic engineering", "Cybernetics", "Robotics", "Evolutionary biology",
            "Astronomy", "Physics", "Mathematics", "Philosophy", "Computer science"
        ]

    def run(self):
        import urllib.request
        import urllib.parse
        logger.info(f"🌐 [Canlı İnternet Motoru] Aktif! Dil: {self.lang.upper()} | Sürekli yeni bilgi indiriliyor...")
        
        while self.running:
            try:
                if random.random() < 0.6:
                    url = f"https://{self.lang}.wikipedia.org/api/rest_v1/page/random/summary"
                else:
                    konu = random.choice(self.tohumlar)
                    encoded = urllib.parse.quote(konu.strip().replace(" ", "_"))
                    url = f"https://{self.lang}.wikipedia.org/api/rest_v1/page/summary/{encoded}"

                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "NovaAGI/3.5 (Autonomous Stream Learning Engine)"}
                )
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    baslik = data.get("title", "")
                    icerik = data.get("extract", "")
                    sayfa_url = data.get("content_urls", {}).get("desktop", {}).get("page", url)

                    if icerik and len(icerik) >= 60:
                        self.db.bulk_insert_knowledge([(sayfa_url, baslik, icerik)])
                        self.toplam_indirilen += 1
                        logger.info(f"🌐 [İnternetten İndirildi] '{baslik}' ({len(icerik)} harf) ➔ nova.db'ye eklendi (Toplam İndirilen: {self.toplam_indirilen})")
            except Exception:
                pass
            time.sleep(self.interval)

    def durdur(self):
        self.running = False


class HeadlessTrainer:
    def __init__(self, args):
        self.cfg = TrainerConfig()
        
        # Argümanlarla konfigürasyonu güncelle
        if args.batch_size: self.cfg.batch_size = args.batch_size
        if args.lr:         self.cfg.lr = args.lr
        if args.save_every: self.cfg.save_every = args.save_every
        if args.device:     self.cfg.device = args.device

        self.db_path      = os.path.abspath(args.db)
        self.weights_path = os.path.abspath(args.weights)
        self.vocab_path   = os.path.abspath(args.vocab)
        self.continuous   = args.continuous
        self.max_steps    = args.max_steps
        self.web_stream   = getattr(args, "web_stream", False)
        self.lang         = getattr(args, "lang", "tr")
        self.web_interval = getattr(args, "web_interval", 2.0)

        # Cihaz belirleme
        dev_str = self.cfg.device or varsayilan_cihaz()
        if str(dev_str).lower() in ("privateuseone", "directml"):
            try:
                import torch_directml
                self.device = torch_directml.device()
            except Exception:
                self.device = torch.device(dev_str)
        else:
            self.device = torch.device(dev_str)

        logger.info(f"⚡ Donanım Cihazı: {self.device}")

        # Veritabanı ve Tokenizer
        self.db = TrainerDBManager(self.db_path)
        self.tokenizer = NovaTokenizer(self.vocab_path, max_vocab_size=self.cfg.vocab_size)

        # Model ve Hiperparametreler
        self.model = DinamikNovaLM(self.cfg).to(self.device)
        self.adim = 0
        self._buyume_seviyesi = 0
        self._son_loss_toplami = 0.0
        self._son_loss_sayisi = 0

        # Plato Algılayıcı
        self.plato = PlatoAlgilayici(
            pencere=self.cfg.plato_pencere,
            esik=self.cfg.plato_esigi,
            bekleme=self.cfg.buyume_bekleme
        )

        # Ağırlıkları Yükle (Varsa)
        self._agirliklari_yukle()

        if getattr(args, "steps", None) is not None:
            self.hedef_adim = self.adim + args.steps
        elif getattr(args, "max_steps", None) is not None:
            self.hedef_adim = args.max_steps
        else:
            self.hedef_adim = None

        # Optimizer ve Scheduler
        self.optimizer, self.scheduler = self._optimizer_olustur()

        logger.info(f"🧠 Model Hazır: {self.model.mimari_ozet()}")
        db_stats = self.db.get_stats()
        logger.info(f"📊 Veritabanı: {db_stats['egitilmemis_bilgi']:,} eğitilmemiş / {db_stats['toplam_bilgi']:,} toplam kayıt ({self.db_path})")

    def _optimizer_olustur(self):
        decay = [p for n, p in self.model.named_parameters() if p.requires_grad and p.dim() >= 2]
        no_decay = [p for n, p in self.model.named_parameters() if p.requires_grad and p.dim() < 2]
        param_groups = [
            {"params": decay, "weight_decay": self.cfg.weight_decay},
            {"params": no_decay, "weight_decay": 0.0},
        ]
        if "privateuseone" in str(self.device).lower():
            opt = DirectMLAdamW(param_groups, lr=self.cfg.lr, betas=(0.9, 0.95), eps=1e-8)
        else:
            opt = AdamW(param_groups, lr=self.cfg.lr, betas=(0.9, 0.95), eps=1e-8)

        sch = CosineAnnealingWarmRestarts(opt, T_0=self.cfg.t_max, T_mult=2, eta_min=5e-6)
        return opt, sch

    def buyut(self) -> str:
        """Network Morphism: Takılma tespit edildiğinde modeli genişletir."""
        denenen = 0
        while denenen < 3:
            sev = self._buyume_seviyesi % 3
            if sev == 0:
                mesaj = self.model.ff_genislet()
            elif sev == 1:
                mesaj = self.model.yeni_blok_ekle()
            else:
                mesaj = self.model.embed_genislet()

            self._buyume_seviyesi += 1
            denenen += 1

            if mesaj is not None:
                self.optimizer, self.scheduler = self._optimizer_olustur()
                self.plato.sifirla()
                banner = (
                    f"\n{'═'*65}\n"
                    f"  🌟 NOVA NETWORK MORPHISM TETİKLENDİ! [{self.model._toplam_buyume}. Büyüme]\n"
                    f"  {mesaj}\n"
                    f"  Yeni Mimari: {self.model.mimari_ozet()}\n"
                    f"{'═'*65}\n"
                )
                logger.info(banner)
                self.kaydet()
                return mesaj
        return "Maksimum sınırlara ulaşıldı."

    def adim_egit(self, metinler: List[str]) -> float:
        """Metin listesini tokenleştirip bir adım gradient descent uygular."""
        seq = self.cfg.max_seq_len
        bx: List[List[int]] = []
        by: List[List[int]] = []

        for m in metinler:
            if len(m) < self.cfg.min_text_len:
                continue
            if self.tokenizer.guncelle(m):
                self.tokenizer.kaydet()

            ids = self.tokenizer.encode(m)
            if len(ids) < 2:
                continue

            for s in range(0, len(ids) - 1, seq // 2):
                ch = ids[s:s + seq + 1]
                if len(ch) < 2:
                    continue
                x = ch[:-1] + [0] * max(0, seq - len(ch) + 1)
                y = ch[1:]  + [-1] * max(0, seq - len(ch) + 1)
                bx.append(x[:seq])
                by.append(y[:seq])
                if len(bx) >= self.cfg.batch_size * 2:
                    break
            if len(bx) >= self.cfg.batch_size * 2:
                break

        if len(bx) < 2:
            return 0.0

        target_batch = min(self.cfg.batch_size, len(bx))
        sel = random.sample(range(len(bx)), target_batch)
        xt = torch.tensor([bx[i] for i in sel], dtype=torch.long, device=self.device)
        yt = torch.tensor([by[i] for i in sel], dtype=torch.long, device=self.device)

        self.model.train()
        self.optimizer.zero_grad(set_to_none=True)

        if self.adim < self.cfg.warmup_steps:
            for g in self.optimizer.param_groups:
                g["lr"] = self.cfg.lr * (self.adim + 1) / self.cfg.warmup_steps

        use_cuda = "cuda" in str(self.device).lower()
        use_bf16 = use_cuda and torch.cuda.is_bf16_supported()
        amp_dtype = torch.bfloat16 if use_bf16 else torch.float16

        with torch.autocast(device_type="cuda" if use_cuda else "cpu", dtype=amp_dtype, enabled=use_cuda):
            _, loss = self.model(xt, yt)

        if loss is None or torch.isnan(loss):
            return 0.0

        loss.backward()
        nn.utils.clip_grad_norm_(self.model.parameters(), self.cfg.grad_clip)
        self.optimizer.step()
        self.scheduler.step()
        self.adim += 1

        lv = loss.item()
        self._son_loss_toplami += lv
        self._son_loss_sayisi += 1

        # Plato kontrolü & Otomatik büyüme
        if self.plato.guncelle(lv):
            self.buyut()

        # Periyodik Loglama & Checkpoint
        if self.adim % self.cfg.save_every == 0:
            ort = self._son_loss_toplami / max(self._son_loss_sayisi, 1)
            lr = self.optimizer.param_groups[0]["lr"]
            logger.info(f"🎯 Adım {self.adim:>6} | Loss: {ort:.4f} | LR: {lr:.2e} | {self.model.mimari_ozet()}")
            self._son_loss_toplami = 0.0
            self._son_loss_sayisi = 0
            self.kaydet()

        return lv

    def kaydet(self):
        """Model ağırlıklarını ve durumunu atomik olarak kaydeder."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.weights_path)), exist_ok=True)
            state = {
                "model_state":     self.model.state_dict(),
                "opt_state":       self.optimizer.state_dict(),
                "sch_state":       self.scheduler.state_dict(),
                "adim":            self.adim,
                "char2id":         self.tokenizer.char2id,
                "id2char":         self.tokenizer.id2char,
                "embed_dim":       self.model._e,
                "n_heads":         self.model._h,
                "n_layers":        len(self.model.bloklar),
                "ff_dim":          self.model._ff,
                "buyume_gecmisi":  self.model.buyume_gecmisi,
                "toplam_buyume":   self.model._toplam_buyume,
                "buyume_seviyesi": self._buyume_seviyesi,
            }
            tmp = self.weights_path + ".tmp"
            torch.save(state, tmp)
            if os.path.exists(tmp) and os.path.getsize(tmp) > 1000:
                import shutil
                shutil.copyfile(tmp, self.weights_path)
                try: os.remove(tmp)
                except Exception: pass
            self.tokenizer.kaydet(self.vocab_path)
        except Exception as e:
            logger.error(f"❌ Kaydetme hatası: {e}")

    def _agirliklari_yukle(self):
        """Mevcut ağırlıkları kontrol eder ve mimariyi restore eder."""
        if not os.path.exists(self.weights_path) or os.path.getsize(self.weights_path) == 0:
            logger.info("🌱 Yeni model başlatılıyor (önceden eğitilmiş ağırlık bulunamadı).")
            return
        try:
            logger.info(f"📥 Ağırlıklar yükleniyor: {self.weights_path}")
            ck = torch.load(self.weights_path, map_location="cpu", weights_only=False)

            if "embed_dim" in ck:
                self.cfg.embed_dim = ck["embed_dim"]
                self.cfg.n_heads   = ck["n_heads"]
                self.cfg.ff_dim    = ck["ff_dim"]
                self.cfg.n_layers  = ck.get("n_layers", self.cfg.n_layers)
                self.model = DinamikNovaLM(self.cfg).to(self.device)

            if "char2id" in ck:
                self.tokenizer.char2id = ck["char2id"]
                self.tokenizer.id2char = {int(k) if isinstance(k, str) else k: v for k, v in ck["id2char"].items()}

            self.model.load_state_dict(ck["model_state"])
            self.model.tok_emb.weight = self.model.head.weight
            self.model.to(self.device)

            self.adim = ck.get("adim", 0)
            self._buyume_seviyesi = ck.get("buyume_seviyesi", 0)
            self.model.buyume_gecmisi = ck.get("buyume_gecmisi", [])
            self.model._toplam_buyume = ck.get("toplam_buyume", 0)
            logger.info(f"✅ Başarıyla yüklendi! Mevcut adım: {self.adim:,} | {self.model.mimari_ozet()}")
        except Exception as e:
            logger.warning(f"⚠️ Yükleme başarısız ({e}), sıfırdan başlanıyor.")

    def calistir(self):
        """Ana eğitim döngüsü."""
        logger.info("🚀 Eğitim döngüsü başlatıldı.")
        burst_limit = 4

        streamer = None
        if self.web_stream:
            streamer = WebStreamer(self.db, lang=self.lang, interval=self.web_interval)
            streamer.start()

        try:
            while True:
                # 1. Bilgi ağacından eğitilmemiş kayıtları çek
                kayitlar = self.db.get_unprocessed_knowledge(limit=40)
                if kayitlar:
                    metinler = [r["icerik"] for r in kayitlar]
                    ids = [r["id"] for r in kayitlar]

                    for _ in range(burst_limit):
                        self.adim_egit(metinler)
                        if self.hedef_adim and self.adim >= self.hedef_adim:
                            self.db.mark_knowledge_processed(ids)
                            logger.info(f"🏁 Hedef adım sayısına ulaşıldı: {self.adim}")
                            self.kaydet()
                            return

                    # Eğitilen kayıtları işaretle
                    self.db.mark_knowledge_processed(ids)
                    time.sleep(0.01)

                else:
                    # Eğitilmemiş bilgi kalmadıysa anılara bak veya sürekli modda bekle
                    anilar = self.db.get_memories(limit=40)
                    metinler = [a["icerik"] for a in anilar if len(a["icerik"]) >= self.cfg.min_text_len]

                    if metinler:
                        for _ in range(burst_limit):
                            self.adim_egit(metinler)
                            if self.hedef_adim and self.adim >= self.hedef_adim:
                                logger.info(f"🏁 Hedef adım sayısına ulaşıldı: {self.adim}")
                                self.kaydet()
                                return
                        time.sleep(0.05)
                    else:
                        if self.continuous or self.web_stream:
                            time.sleep(1.0)
                        else:
                            logger.info("🎉 Tebrikler! Veritabanındaki tüm kayıtlar eğitildi (islendi=1).")
                            self.kaydet()
                            break
        finally:
            if streamer:
                streamer.durdur()


def main():
    parser = argparse.ArgumentParser(description="Nova Headless Eğitim Motoru")
    parser.add_argument("--db", type=str, default="nova.db", help="SQLite veritabanı yolu")
    parser.add_argument("--weights", type=str, default="nova_weights.pth", help="Ağırlık dosya yolu")
    parser.add_argument("--vocab", type=str, default="nova_vocab.json", help="Sözlük dosya yolu")
    parser.add_argument("--batch_size", type=int, default=32, help="Mini-batch boyutu")
    parser.add_argument("--lr", type=float, default=3e-4, help="Öğrenme oranı")
    parser.add_argument("--device", type=str, default=None, help="Cihaz (cuda, privateuseone, cpu)")
    parser.add_argument("--save_every", type=int, default=50, help="Kaç adımda bir kaydedilsin")
    parser.add_argument("--steps", type=int, default=None, help="Kaç adım eğitilsin (örn: 50)")
    parser.add_argument("--max_steps", type=int, default=None, help="Maksimum adım sayısı (örn: 500)")
    parser.add_argument("--continuous", action="store_true", help="DB'ye yeni veri geldikçe durmadan devam et")
    parser.add_argument("--web_stream", action="store_true", help="Eğitim sürerken internetten sürekli yeni bilgi indir ve eğit")
    parser.add_argument("--lang", type=str, default="tr", choices=["tr", "en"], help="İnternet arama dili")
    parser.add_argument("--web_interval", type=float, default=2.0, help="Web indirme aralığı (saniye)")

    args = parser.parse_args()
    trainer = HeadlessTrainer(args)
    trainer.calistir()


if __name__ == "__main__":
    main()
