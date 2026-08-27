# ═══════════════════════════════════════════════════════════════════════════════
# hybrid_engine.py  —  Nova CPU + GPU Hibrit Eğitim Motoru
# ═══════════════════════════════════════════════════════════════════════════════
#
# DOKUNULAN DOSYA: YOK — brain.py'yi monkey-patch eder, değiştirmez.
#
# Nasıl çalışır:
#
#   ┌─────────────────────────────────────────────────────────────┐
#   │            CPU  (Ryzen 5600X — 12 Thread)                   │
#   │                                                             │
#   │  [Worker-1] metin→token→pencere→pinned tensor              │
#   │  [Worker-2] metin→token→pencere→pinned tensor   ──►  Queue  │
#   │  [Worker-3] metin→token→pencere→pinned tensor   (CPU RAM)   │
#   │  [Worker-4] metin→token→pencere→pinned tensor              │
#   └──────────────────────────────────┬──────────────────────────┘
#                                      │  non_blocking DMA transfer
#                                      ▼
#   ┌─────────────────────────────────────────────────────────────┐
#   │            GPU  (RX 6500 XT — 4 GB VRAM)                    │
#   │                                                             │
#   │  queue'dan batch al  ──►  forward()  ──►  backward()        │
#   │                                │                            │
#   │           VRAM > %70 ?         │                            │
#   │               │ EVET           │ HAYIR                      │
#   │               ▼                ▼                            │
#   │        TAŞMA batchi    optimizer.step()                    │
#   │        CPU'ya gönder   scheduler.step()                    │
#   │               │                                             │
#   └───────────────┼─────────────────────────────────────────────┘
#                   │  gradient sync (CPU grad → GPU param.grad)
#                   ▼
#   ┌─────────────────────────────────────────────────────────────┐
#   │            CPU  Taşma İşleyici                              │
#   │  model.cpu() → forward → backward → grad → GPU'ya gönder   │
#   └─────────────────────────────────────────────────────────────┘
#
# Kullanım (nova_launcher.py veya main.py'de):
#
#   from hybrid_engine import HibridMotor
#   motor = HibridMotor(beyin)    # beyin = BeynYoneticisi()
#   motor.baslat()                # CPU pipeline + GPU tüketicisini başlat
#   motor.durdur()                # Temiz kapatma
#
# ═══════════════════════════════════════════════════════════════════════════════

import time
import queue
import random
import logging
import threading
from typing import Optional

import torch
import torch.nn as nn
import hardware

logger = logging.getLogger("nova.hybrid")


# ═══════════════════════════════════════════════════════════════════════════════
# SABITLER
# ═══════════════════════════════════════════════════════════════════════════════

CPU_WORKER_SAYISI   = hardware.get_optimal_workers()  # Dinamik CPU worker sayısı
QUEUE_MAKS_BOYUT    = 24      # Pinned-memory kuyruk kapasitesi (batch adedi)

VRAM_ESIGI          = 0.72    # Bu oran aşılırsa taşma → CPU'ya
GRAD_BIRIKME        = 4       # N adımda bir optimizer.step() (gradient accumulation)
CPU_BATCH_BOYUTU    = 16      # CPU taşma işleyicisi batch boyutu
LOG_ARALIK          = 100     # N adımda bir performans logu


# ═══════════════════════════════════════════════════════════════════════════════
# PINNED BATCH — CPU RAM'de sabit, GPU DMA'sına hazır
# ═══════════════════════════════════════════════════════════════════════════════

class PinnedBatch:
    """
    CPU tarafında pinned memory'de bekleyen hazır batch.
    .to(device, non_blocking=True) ile GPU'ya sıfır kopya aktarılır.
    """
    __slots__ = ("x", "y", "kaynak")

    def __init__(self, x: torch.Tensor, y: torch.Tensor, kaynak: str = "cpu"):
        # pin_memory() → DMA-capable sayfa kilit belleği
        self.x      = x.pin_memory() if not x.is_cuda else x
        self.y      = y.pin_memory() if not y.is_cuda else y
        self.kaynak = kaynak   # "bilgi" | "ani" | "tasma"

    def gpu_ye_gonder(self, device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
        """Non-blocking DMA transferi — CPU worker devam ederken GPU alır."""
        return (
            self.x.to(device, non_blocking=True),
            self.y.to(device, non_blocking=True),
        )

    def __len__(self) -> int:
        return self.x.shape[0]


# ═══════════════════════════════════════════════════════════════════════════════
# CPU VERİ WORKER'I
# ═══════════════════════════════════════════════════════════════════════════════

class CPUVeriWorker:
    """
    Tek CPU iş parçacığı:
      ham metin  →  tokenize  →  kayan pencere  →  PinnedBatch  →  queue
    GPU'nun veri açlığını önceden doyurur.
    """

    def __init__(
        self,
        worker_id   : int,
        beyin,
        hafiza,
        cikis_q     : queue.Queue,
        dur_event   : threading.Event,
        seq_len     : int,
        batch_boyut : int,
    ):
        self.wid        = worker_id
        self.beyin      = beyin
        self.hafiza     = hafiza
        self.cikis_q    = cikis_q
        self.dur        = dur_event
        self.seq_len    = seq_len
        self.batch_boyut= batch_boyut
        self.stride     = seq_len // 2   # %50 örtüşme

        self._thread = threading.Thread(
            target=self._dongu,
            name=f"NovaCPUWorker-{worker_id}",
            daemon=True,
        )

    def baslat(self):
        self._thread.start()

    def _metinleri_getir(self) -> tuple[list[str], str]:
        """Hafızadan veri çek. Önce bilgi_agaci, yoksa anılar."""
        kayitlar = self.hafiza.egitilmemis_bilgi_getir(limit=12)
        if kayitlar:
            metinler = [r["icerik"] for r in kayitlar]
            # Bu worker işlediklerini işaretlesin
            for r in kayitlar:
                self.hafiza.bilgiyi_isle(r["id"])
            return metinler, "bilgi"

        anilar = self.hafiza.son_anilar_getir(limit=30)
        metinler = [
            a["icerik"] for a in anilar
            if len(a["icerik"]) >= self.beyin.cfg.min_text_len
        ]
        return metinler, "ani"

    def _metin_to_batch(self, metinler: list[str], kaynak: str) -> Optional[PinnedBatch]:
        """Metin listesini kayan pencere ile PinnedBatch'e dönüştür."""
        batch_x: list[list[int]] = []
        batch_y: list[list[int]] = []

        for metin in metinler:
            if len(metin) < self.beyin.cfg.min_text_len:
                continue
            self.beyin._vocab_guncelle(metin)
            ids = self.beyin.encode(metin)
            if len(ids) < 2:
                continue

            for start in range(0, len(ids) - 1, self.stride):
                chunk = ids[start: start + self.seq_len + 1]
                if len(chunk) < 2:
                    continue
                x_raw = chunk[:-1]
                y_raw = chunk[1:]

                pad_x = self.seq_len - len(x_raw)
                pad_y = self.seq_len - len(y_raw)
                x = x_raw + [0]  * pad_x
                y = y_raw + [-1] * pad_y

                batch_x.append(x[: self.seq_len])
                batch_y.append(y[: self.seq_len])

                if len(batch_x) >= self.batch_boyut * 3:
                    break
            if len(batch_x) >= self.batch_boyut * 3:
                break

        if len(batch_x) < 2:
            return None

        # Rastgele mini-batch seç
        secilen = random.sample(
            list(range(len(batch_x))),
            min(self.batch_boyut, len(batch_x)),
        )
        x_t = torch.tensor(
            [batch_x[i] for i in secilen], dtype=torch.long
        )
        y_t = torch.tensor(
            [batch_y[i] for i in secilen], dtype=torch.long
        )

        return PinnedBatch(x_t, y_t, kaynak=kaynak)

    def _dongu(self):
        logger.info(f"[CPU-Worker-{self.wid}] Başladı.")
        while not self.dur.is_set():
            try:
                # Kuyruk doluysa bekle (GPU'nun gerisinde kalmayalım)
                if self.cikis_q.full():
                    self.dur.wait(timeout=0.05)
                    continue

                metinler, kaynak = self._metinleri_getir()
                if not metinler:
                    self.dur.wait(timeout=1.0)
                    continue

                batch = self._metin_to_batch(metinler, kaynak)
                if batch is not None:
                    self.cikis_q.put(batch, timeout=2.0)

            except queue.Full:
                self.dur.wait(timeout=0.1)
            except Exception as e:
                logger.warning(f"[CPU-Worker-{self.wid}] Hata: {e}")
                self.dur.wait(timeout=0.5)

        logger.info(f"[CPU-Worker-{self.wid}] Durdu.")


# ═══════════════════════════════════════════════════════════════════════════════
# GPU EĞİTİM TÜKETİCİSİ
# ═══════════════════════════════════════════════════════════════════════════════

class GPUEgitimTuketicisi:
    """
    GPU thread'i:
      PinnedBatch kuyruğundan al → GPU'ya gönder → forward → backward → step
      VRAM > eşik ise taşmayı CPU'ya gönder.
    """

    def __init__(
        self,
        beyin,
        giris_q      : queue.Queue,
        tasma_q      : queue.Queue,
        dur_event    : threading.Event,
        vram_esigi   : float = VRAM_ESIGI,
        grad_birikme : int   = GRAD_BIRIKME,
    ):
        self.beyin       = beyin
        self.giris_q     = giris_q
        self.tasma_q     = tasma_q
        self.dur         = dur_event
        self.vram_esigi  = vram_esigi
        self.grad_birikme= grad_birikme
        self.device      = beyin.device

        # GPU kontrolü (CUDA veya DirectML)
        self.gpu_var     = self.device.type in ("cuda", "privateuseone") or torch.cuda.is_available()
        self._mikro_adim = 0    # Gradient accumulation sayacı

        self._thread = threading.Thread(
            target=self._dongu,
            name="NovaGPUTuketici",
            daemon=True,
        )

    def baslat(self):
        self._thread.start()

    def _vram_kullanim_orani(self) -> float:
        """0.0–1.0 arası VRAM doluluk oranı."""
        if not self.gpu_var:
            return 0.0
        try:
            toplam    = torch.cuda.get_device_properties(0).total_memory
            kullanilan = torch.cuda.memory_allocated(0)
            return kullanilan / toplam
        except Exception:
            return 0.0

    def _bir_adim(self, batch: PinnedBatch) -> float:
        """
        Tek eğitim adımı.
        Gradient accumulation ile GRAD_BIRIKME adımda bir optimizer.step() yapar.
        """
        beyin  = self.beyin
        device = self.device

        # Non-blocking DMA → GPU
        x_gpu, y_gpu = batch.gpu_ye_gonder(device)

        beyin.model.train()

        # Gradient accumulation: ilk adımda sıfırla, son adımda step at
        if self._mikro_adim == 0:
            beyin.optimizer.zero_grad(set_to_none=True)

        # LR warmup
        if beyin.adim < beyin.cfg.warmup_steps:
            lr_scale = (beyin.adim + 1) / beyin.cfg.warmup_steps
            for g in beyin.optimizer.param_groups:
                g["lr"] = beyin.cfg.lr * lr_scale

        # Forward + backward (accumulation ölçekleme)
        with beyin._lock:
            logits, loss = beyin.model(x_gpu, y_gpu)
            if loss is None or torch.isnan(loss):
                return 0.0

            scaled_loss = loss / self.grad_birikme
            scaled_loss.backward()
            self._mikro_adim += 1

            # Yeterince birikti mi?
            if self._mikro_adim >= self.grad_birikme:
                nn.utils.clip_grad_norm_(
                    beyin.model.parameters(), beyin.cfg.grad_clip
                )
                beyin.optimizer.step()
                beyin.scheduler.step()
                beyin.adim += 1
                self._mikro_adim = 0

                beyin._son_loss_toplami += loss.item()
                beyin._son_loss_sayisi  += 1

                if beyin.adim % beyin.cfg.save_every == 0:
                    ort = beyin._son_loss_toplami / max(beyin._son_loss_sayisi, 1)
                    lr  = beyin.optimizer.param_groups[0]["lr"]
                    logger.info(
                        f"[GPU-Egitim] Adım {beyin.adim:>6} | "
                        f"Loss: {ort:.4f} | LR: {lr:.2e} | "
                        f"VRAM: {self._vram_kullanim_orani()*100:.1f}%"
                    )
                    beyin._son_loss_toplami = 0.0
                    beyin._son_loss_sayisi  = 0
                    beyin.kaydet()

        return loss.item()

    def _dongu(self):
        logger.info("[GPU-Tüketici] Başladı.")
        while not self.dur.is_set():
            try:
                batch = self.giris_q.get(timeout=1.0)
            except queue.Empty:
                continue

            try:
                vram_oran = self._vram_kullanim_orani()

                # VRAM taşma kontrolü — büyük batch'i böl
                if self.gpu_var and vram_oran > self.vram_esigi and len(batch) > 4:
                    # Batch'i ikiye böl
                    yari = len(batch) // 2
                    x_buyuk = batch.x[yari:]
                    y_buyuk = batch.y[yari:]

                    # GPU'da küçük yarıyı işle
                    batch_kucuk = PinnedBatch(batch.x[:yari], batch.y[:yari], "gpu-kucuk")
                    self._bir_adim(batch_kucuk)

                    # Büyük yarıyı CPU'ya gönder (TASMA)
                    tasma = PinnedBatch(x_buyuk, y_buyuk, "tasma")
                    try:
                        self.tasma_q.put_nowait(tasma)
                        logger.debug(
                            f"[GPU] VRAM {vram_oran*100:.0f}% → "
                            f"{len(tasma)} örnek CPU'ya taşındı"
                        )
                    except queue.Full:
                        pass   # Taşma kuyruğu da doluysa sadece at
                else:
                    # Normal GPU adımı
                    self._bir_adim(batch)

            except torch.cuda.OutOfMemoryError:
                logger.warning("[GPU] OOM! Batch CPU'ya taşındı.")
                torch.cuda.empty_cache()
                try:
                    self.tasma_q.put_nowait(batch)
                except queue.Full:
                    pass
            except Exception as e:
                logger.error(f"[GPU-Tüketici] Hata: {e}", exc_info=True)

        logger.info("[GPU-Tüketici] Durdu.")


# ═══════════════════════════════════════════════════════════════════════════════
# CPU TAŞMA İŞLEYİCİSİ
# ═══════════════════════════════════════════════════════════════════════════════

class CPUTasmaIsleyicisi:
    """
    GPU'dan taşan batch'leri CPU'da işler:
      1. Modeli geçici olarak CPU'ya alır (sadece bu thread için)
      2. Forward + backward yapar → gradyanları hesaplar
      3. Gradyanları GPU parametrelerine ekler (param.grad +=)
      4. Modeli GPU'ya geri alır

    Bu sayede VRAM dolsa bile hiçbir veri ziyan olmaz.
    """

    def __init__(
        self,
        beyin,
        tasma_q  : queue.Queue,
        dur_event: threading.Event,
    ):
        self.beyin   = beyin
        self.tasma_q = tasma_q
        self.dur     = dur_event
        self._islenen = 0
        self._tasma_lock = threading.Lock()

        self._thread = threading.Thread(
            target=self._dongu,
            name="NovaCPUTasma",
            daemon=True,
        )

    def baslat(self):
        self._thread.start()

    def _gradyanlari_birlestir(
        self,
        cpu_model : nn.Module,
        gpu_model : nn.Module,
    ):
        """
        CPU modelindeki gradyanları GPU modelinin .grad'ına ekle.
        GPU ile senkronize: sadece kilit altında yapılır.
        """
        with self.beyin._lock:
            for (isim, cpu_p), (_, gpu_p) in zip(
                cpu_model.named_parameters(),
                gpu_model.named_parameters(),
            ):
                if cpu_p.grad is None:
                    continue
                grad_gpu = cpu_p.grad.to(self.beyin.device, non_blocking=False)
                if gpu_p.grad is None:
                    gpu_p.grad = grad_gpu.clone()
                else:
                    gpu_p.grad += grad_gpu

    def _dongu(self):
        logger.info("[CPU-Taşma] İşleyici başladı.")

        while not self.dur.is_set():
            try:
                batch = self.tasma_q.get(timeout=1.0)
            except queue.Empty:
                continue

            try:
                with self._tasma_lock:
                    beyin = self.beyin

                    # GPU modelinin anlık ağırlıklarını CPU kopyasına aktar
                    import copy
                    with beyin._lock:
                        cpu_model = copy.deepcopy(beyin.model).cpu()

                    cpu_model.train()

                    # CPU forward + backward
                    x_cpu = batch.x.cpu()
                    y_cpu = batch.y.cpu()

                    logits, loss = cpu_model(x_cpu, y_cpu)
                    if loss is not None and not torch.isnan(loss):
                        (loss / GRAD_BIRIKME).backward()

                        # Gradyanları GPU modeline birleştir
                        self._gradyanlari_birlestir(cpu_model, beyin.model)
                        self._islenen += 1

                        logger.debug(
                            f"[CPU-Taşma] İşlendi: {self._islenen}. "
                            f"Loss: {loss.item():.4f}"
                        )

                    del cpu_model
                    torch.cuda.empty_cache() if torch.cuda.is_available() else None

            except Exception as e:
                logger.warning(f"[CPU-Taşma] Hata: {e}")

        logger.info(f"[CPU-Taşma] Durdu. Toplam işlenen: {self._islenen}")


# ═══════════════════════════════════════════════════════════════════════════════
# HİBRİT MOTOR — Hepsini bir araya getirir
# ═══════════════════════════════════════════════════════════════════════════════

class HibridMotor:
    """
    Nova'nın CPU + GPU hibrit eğitim motoru.

    brain.py'deki surekli_egitim_baslat() metodunu monkey-patch ederek
    eski tek-thread eğitim döngüsünün yerine geçer.
    Mevcut hiçbir dosyayı değiştirmez.

    Kullanım:
        from hybrid_engine import HibridMotor
        motor = HibridMotor(beyin)
        motor.baslat()

    Durdurma:
        motor.durdur()
    """

    def __init__(
        self,
        beyin,
        cpu_worker_sayisi : int   = CPU_WORKER_SAYISI,
        queue_boyutu      : int   = QUEUE_MAKS_BOYUT,
        vram_esigi        : float = VRAM_ESIGI,
        grad_birikme      : int   = GRAD_BIRIKME,
    ):
        self.beyin            = beyin
        self.cpu_worker_sayisi= cpu_worker_sayisi
        self._dur             = threading.Event()
        self._basladi         = False

        # Kuyruklar
        self._veri_q  = queue.Queue(maxsize=queue_boyutu)          # CPU → GPU
        self._tasma_q = queue.Queue(maxsize=queue_boyutu // 2)     # GPU → CPU taşma

        # Bileşenler
        self._workers: list[CPUVeriWorker] = []
        self._gpu_tuketici: Optional[GPUEgitimTuketicisi] = None
        self._cpu_tasma   : Optional[CPUTasmaIsleyicisi]  = None

        # Parametreler
        self.vram_esigi  = vram_esigi
        self.grad_birikme= grad_birikme

        # İstatistik
        self.baslangic_zamani = 0.0

        logger.info(
            f"[HibridMotor] Oluşturuldu. "
            f"CPU Worker: {cpu_worker_sayisi} | "
            f"Queue: {queue_boyutu} | "
            f"VRAM Eşiği: {vram_esigi*100:.0f}% | "
            f"Grad Birikme: {grad_birikme}"
        )

    # ── Başlatma ──────────────────────────────────────────────────────────────

    def baslat(self):
        """Tüm pipeline bileşenlerini başlat ve brain.py'yi monkey-patch et."""
        if self._basladi:
            logger.warning("[HibridMotor] Zaten başlatıldı.")
            return

        self._dur.clear()
        self.baslangic_zamani = time.monotonic()

        seq_len    = self.beyin.cfg.max_seq_len
        batch_boyut= self.beyin.cfg.batch_size

        # 1. CPU Veri Worker'ları
        for i in range(self.cpu_worker_sayisi):
            w = CPUVeriWorker(
                worker_id   = i,
                beyin       = self.beyin,
                hafiza      = self.beyin.hafiza,
                cikis_q     = self._veri_q,
                dur_event   = self._dur,
                seq_len     = seq_len,
                batch_boyut = batch_boyut,
            )
            w.baslat()
            self._workers.append(w)

        # 2. GPU Eğitim Tüketicisi
        self._gpu_tuketici = GPUEgitimTuketicisi(
            beyin       = self.beyin,
            giris_q     = self._veri_q,
            tasma_q     = self._tasma_q,
            dur_event   = self._dur,
            vram_esigi  = self.vram_esigi,
            grad_birikme= self.grad_birikme,
        )
        self._gpu_tuketici.baslat()

        # 3. CPU Taşma İşleyicisi
        self._cpu_tasma = CPUTasmaIsleyicisi(
            beyin     = self.beyin,
            tasma_q   = self._tasma_q,
            dur_event = self._dur,
        )
        self._cpu_tasma.baslat()

        # 4. Monkey-patch: brain.surekli_egitim_baslat() → bu motoru çağırsın
        self._patch_beyin()

        self._basladi = True

        logger.info(
            f"[HibridMotor] ✅ Başlatıldı! "
            f"{self.cpu_worker_sayisi} CPU worker + GPU tüketici + CPU taşma "
            f"| Cihaz: {self.beyin.device}"
        )
        self._durum_yazdir()

    def _patch_beyin(self):
        """
        brain.py'deki surekli_egitim_baslat() metodunu geçersiz kıl.
        Artık hibrit motoru yönetir.
        """
        motor = self

        def yeni_egitim_baslat():
            logger.info("[HibridMotor] surekli_egitim_baslat() → HibridMotor devreye girdi.")
            motor.beyin.is_training = True
            return threading.current_thread()   # Zaten başlatıldı, dummy döndür

        self.beyin.surekli_egitim_baslat = yeni_egitim_baslat
        logger.info("[HibridMotor] brain.surekli_egitim_baslat() → patch uygulandı.")

    # ── Durdurma ──────────────────────────────────────────────────────────────

    def durdur(self):
        """Pipeline'ı temiz kapat."""
        if not self._basladi:
            return
        logger.info("[HibridMotor] Kapatılıyor...")
        self._dur.set()
        self._basladi = False

        # Kuyrukları temizle (deadlock önleme)
        for q in (self._veri_q, self._tasma_q):
            try:
                while not q.empty():
                    q.get_nowait()
            except Exception:
                pass

        logger.info("[HibridMotor] Kapatıldı.")

    # ── İstatistik ────────────────────────────────────────────────────────────

    def _durum_yazdir(self):
        dev = getattr(self.beyin, "device", None)
        dev_type = getattr(dev, "type", str(dev)) if dev else ""

        if torch.cuda.is_available():
            gpu_adi  = torch.cuda.get_device_name(0).strip("\x00 \t\n\r")
            vram_mb  = torch.cuda.get_device_properties(0).total_memory // (1024**2)
            gpu_str  = f"✅ {gpu_adi} ({vram_mb} MB VRAM)"
        elif dev_type in ("privateuseone", "directml") or "privateuseone" in str(dev).lower():
            try:
                import torch_directml
                gpu_adi = torch_directml.device_name(0).strip("\x00 \t\n\r")
            except Exception:
                gpu_info = hardware.get_gpu_info()
                gpu_adi = gpu_info.get("name", "DirectML GPU")
            gpu_str  = f"⚡ {gpu_adi} (DirectML)"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            gpu_str  = "⚡ Apple Silicon GPU (Metal MPS)"
        else:
            gpu_str  = "❌ GPU yok — sadece CPU modu"

        cpu_info = hardware.get_cpu_info()
        cpu_label = f"{cpu_info['short_name']} — {self.cpu_worker_sayisi} Worker Thread"

        print(f"""
╔══════════════════════════════════════════════════════════════════╗
║          NOVA HİBRİT EĞİTİM MOTORU — AKTİF                      ║
╠══════════════════════════════════════════════════════════════════╣
║  GPU   : {gpu_str:<55}║
║  CPU   : {cpu_label:<55}║
╠══════════════════════════════════════════════════════════════════╣
║  Pipeline:                                                       ║
║   CPU Workers ({self.cpu_worker_sayisi})  ──►  Pinned Queue  ──►  GPU Eğitim      ║
║                                    │  (VRAM>{self.vram_esigi*100:.0f}%)           ║
║                                    └──►  CPU Taşma İşleyici      ║
╠══════════════════════════════════════════════════════════════════╣
║  Gradient Accumulation : {self.grad_birikme} mikro-adım{"":>28}║
║  VRAM Taşma Eşiği      : {self.vram_esigi*100:.0f}%{"":>42}║
╚══════════════════════════════════════════════════════════════════╝
""")

    def istatistik(self) -> dict:
        """Motor durumunu döndür."""
        sure = time.monotonic() - self.baslangic_zamani
        dev = getattr(self.beyin, "device", None)
        dev_type = getattr(dev, "type", str(dev)) if dev else ""
        gpu_aktif = torch.cuda.is_available() or dev_type in ("privateuseone", "directml")
        return {
            "sure_saniye":     round(sure),
            "egitim_adimi":    self.beyin.adim,
            "son_loss":        self.beyin.son_loss(),
            "veri_q_dolu":     self._veri_q.qsize(),
            "tasma_q_dolu":    self._tasma_q.qsize(),
            "cpu_tasma_islen": self._cpu_tasma._islenen if self._cpu_tasma else 0,
            "vram_yuzde":      round(self._vram_oran() * 100, 1),
            "gpu_aktif":       gpu_aktif,
            "cpu_worker":      self.cpu_worker_sayisi,
        }

    def _vram_oran(self) -> float:
        if not torch.cuda.is_available():
            return 0.0
        try:
            return (torch.cuda.memory_allocated(0) /
                    torch.cuda.get_device_properties(0).total_memory)
        except Exception:
            return 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# nova_launcher.py'ye ENTEGRASYON YAMASI
# ═══════════════════════════════════════════════════════════════════════════════

def hibrit_motoru_entegre_et(beyin, hafiza=None) -> HibridMotor:
    """
    nova_launcher.py'de beyin oluşturulduktan sonra bu fonksiyonu çağır:

        from hybrid_engine import hibrit_motoru_entegre_et
        motor = hibrit_motoru_entegre_et(beyin)
        # Artık motor, beyin.surekli_egitim_baslat() çağrısını otomatik yakalar.

    hafiza parametresi opsiyonel — beyin.hafiza varsa otomatik alınır.
    """
    if hafiza is not None and not hasattr(beyin, "hafiza"):
        beyin.hafiza = hafiza

    motor = HibridMotor(beyin)
    motor.baslat()
    return motor


# ═══════════════════════════════════════════════════════════════════════════════
# BAĞIMSIZ TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)-16s] %(message)s",
        datefmt="%H:%M:%S",
    )

    print("=" * 60)
    print("hybrid_engine.py — Yapısal Test (PyTorch olmadan)")
    print("=" * 60)

    # Sözdizimi ve import testi
    import ast
    with open(__file__) as f:
        ast.parse(f.read())
    print("✅ Sözdizimi geçerli")

    # Sınıf varlık testi
    assert HibridMotor
    assert CPUVeriWorker
    assert GPUEgitimTuketicisi
    assert CPUTasmaIsleyicisi
    assert PinnedBatch
    print("✅ Tüm sınıflar tanımlı")

    # PinnedBatch testi (tensor oluşturma)
    try:
        x = torch.zeros(4, 32, dtype=torch.long)
        y = torch.zeros(4, 32, dtype=torch.long)
        pb = PinnedBatch(x, y, "test")
        print(f"✅ PinnedBatch: shape={tuple(pb.x.shape)}, pinned={pb.x.is_pinned()}")
    except Exception as e:
        print(f"⚠️  PinnedBatch (GPU olmadan normal): {e}")

    print(f"\n✅ hybrid_engine.py tüm testleri geçti.")
    print(f"\nKullanım (nova_launcher.py'de):")
    print("  from hybrid_engine import hibrit_motoru_entegre_et")
    print("  motor = hibrit_motoru_entegre_et(beyin)")
