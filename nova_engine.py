# ═══════════════════════════════════════════════════════════════════════════════
# nova_engine.py  —  Nova AGI Çekirdek Motoru
# ═══════════════════════════════════════════════════════════════════════════════
#
# Masaüstü köprüsü (nova_bridge.py) ve tek başına web sunucusu (web_server.py)
# tarafından paylaşılan motor: sohbet akışı, ! komutları, telemetri, ayarlar.
# gpu_setup.gpu_hazirla() bu modül import edilmeden önce çağrılmış olmalıdır.
# ═══════════════════════════════════════════════════════════════════════════════

import re
import time
import logging
import threading
from contextlib import closing
from typing import Dict, Any, Optional, Callable

import hardware
import config_manager
import yetenekler
from web_server import NovaWebServer, get_local_ip
from memory import HafizaYoneticisi
from brain import BeynYoneticisi
from body import AjanBeden

logger = logging.getLogger("nova.engine")

VERSION = "4.0-linux"


class NovaMotoru:
    """Hafıza + Beyin + Beden + Web sunucusu + Merak motorunu yöneten çekirdek."""

    def __init__(self, start_web: bool = True, web_zorla: bool = False):
        self.hafiza = HafizaYoneticisi()
        self.beyin = BeynYoneticisi(self.hafiza)
        self.beden = AjanBeden(self.hafiza, self.beyin)
        self._calisiyor = True

        if config_manager.is_continuous_training_enabled():
            self.beyin.surekli_egitim_baslat()
        else:
            logger.info("[Bridge] Sürekli eğitim ayarlardan kapalı.")

        self.web_sunucu: Optional[NovaWebServer] = None
        if start_web:
            port = int(config_manager.get_setting("web_server_port"))
            self.web_sunucu = NovaWebServer(bridge_instance=self, port=port)
            if web_zorla or config_manager.get_setting("web_server_enabled"):
                self.web_sunucu.start(port=port)

        try:
            from hugging_loader import OtonomMerakMotoru
            self.merak_motoru = OtonomMerakMotoru(self.hafiza)
            threading.Thread(target=self._merak_dongusu, daemon=True, name="NovaMerak").start()
        except Exception as e:
            logger.debug(f"[Bridge] Merak motoru başlatılamadı: {e}")
            self.merak_motoru = None

    # ── Arka Plan ─────────────────────────────────────────────────────────────
    def _merak_dongusu(self):
        """Periyodik olarak özerk Wikipedia araştırması yapar."""
        while self._calisiyor:
            cfg = config_manager.get_all_settings()
            try:
                if cfg.get("curiosity_enabled") and self.merak_motoru:
                    lang = cfg.get("language") or "tr"
                    if cfg.get("curiosity_topics"):
                        self.merak_motoru.tohum_ekle(cfg["curiosity_topics"], lang)
                    res = self.merak_motoru.merak_adimi(lang=lang)
                    if res:
                        logger.info(res)
            except Exception as e:
                logger.debug(f"[Merak] {e}")
            time.sleep(max(int(cfg.get("curiosity_interval") or 20), 5))

    # ── Telemetri ─────────────────────────────────────────────────────────────
    _ip_onbellek = ("127.0.0.1", 0.0)

    def _yerel_ip(self) -> str:
        ip, t = NovaMotoru._ip_onbellek
        if time.monotonic() - t > 30:
            ip = get_local_ip()
            NovaMotoru._ip_onbellek = (ip, time.monotonic())
        return ip

    def _model_vram_mb(self, raw_model) -> int:
        dev = self.beyin.device
        if dev.type == "cpu":
            return 0
        try:
            import torch
            if dev.type == "cuda":
                return int(torch.cuda.memory_allocated() // 1024 ** 2)
            if dev.type == "xpu":
                return int(torch.xpu.memory_allocated() // 1024 ** 2)
        except Exception:
            pass
        return 0

    def _telemetri_paketi(self) -> Dict[str, Any]:
        """Model, hafıza ve donanım telemetrisi."""
        try:
            stat = self.hafiza.istatistik()
            raw = self.beyin.raw_model
            loss = self.beyin.son_loss()
            lang = config_manager.get_language() or "en"
            gpus = hardware.get_all_gpus()
            vram = self._model_vram_mb(raw)
            for g in gpus:
                if g.get("is_gpu") and not g.get("vram_allocated_mb"):
                    g["vram_allocated_mb"] = vram

            ws = self.web_sunucu
            port = ws.port if ws else int(config_manager.get_setting("web_server_port"))
            ip = self._yerel_ip()
            return {
                "type": "telemetry",
                "step": self.beyin.adim,
                "loss": round(loss, 4) if loss not in (float("inf"),) and loss >= 0 else 0.0,
                "learning_rate": self.beyin.ogrenme_hizi(),
                "vocab_size": len(self.beyin.char2id),
                "episodic_nodes": stat["ani_sayisi"],
                "semantic_nodes": stat["bilgi_sayisi"],
                "pending_tasks": stat["gorev_bekleyen"],
                "untrained": stat["egitilmemis"],
                "is_training": self.beyin.is_training,
                "device": str(self.beyin.device),
                "hardware_tier": self.beyin.profile.get("tier_name", ""),
                "architecture": {
                    "embed_dim": raw._e, "n_heads": raw._h, "n_layers": len(raw.bloklar),
                    "ff_dim": raw._ff, "params": raw.param_sayisi(), "growth_count": raw._toplam_buyume,
                },
                "hardware": {
                    "cpu": hardware.get_cpu_info(),
                    "gpus": gpus,
                    "gpu_summary": {k: v for k, v in hardware.get_gpu_info().items() if k != "devices"},
                    "ram": hardware.get_ram_info(),
                    "system_summary": hardware.get_system_summary(lang=lang),
                },
                "web_server": {
                    "is_running": bool(ws and ws.is_running), "port": port,
                    "local_ip": ip, "url": f"http://{ip}:{port}",
                },
            }
        except Exception as e:
            logger.debug(f"[Bridge] Telemetri hatası: {e}", exc_info=True)
            return {"type": "telemetry_error", "message": str(e)}

    # ── Sohbet ────────────────────────────────────────────────────────────────
    _SORU_KELIMELERI = ("nedir", "kimdir", "nasıl", "nerede", "bilgi", "anlat", "açıkla",
                        "what is", "who is", "how", "explain")
    _TEMIZLE_RE = re.compile(r"(nedir\??|kimdir\??|nerededir\??|hakkında|bilgi\s+ver|anlat|açıkla|"
                             r"what is|who is|tell me about|how to|explain)", re.IGNORECASE)

    def _gecmisi_oku(self, adet: int) -> int:
        anilar = self.hafiza.son_anilar_getir(limit=adet)
        metin = ". ".join(f"{'Kullanıcı' if a['rol'] == 'kullanici' else 'Nova'}: {a['icerik']}"
                          for a in anilar)
        if metin:
            self.beden.ses.konuş(metin)
        return len(anilar)

    def _sohbet_uret(self, girdi: str, chunk_cb: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """Mesajı işler: komutlar → araçlar → RAG/Wikipedia → sinir ağı üretimi."""
        girdi = girdi.strip()
        if not girdi:
            return {"type": "chat_reply", "reply": "", "role": "nova"}

        lang = config_manager.get_language() or "tr"
        gl = girdi.lower()

        def bitir(cevap: str, rol: str = "nova", kaydet: bool = True, **ek) -> Dict[str, Any]:
            if kaydet:
                self.hafiza.ani_kaydet("kullanici", girdi)
                self.hafiza.ani_kaydet("nova", cevap)
            if chunk_cb:
                chunk_cb(cevap)
            return {"type": "chat_reply", "reply": cevap, "role": rol, **ek}

        # 1. ! komutları
        if girdi.startswith("!"):
            cmd = girdi.split()[0].lower()
            if cmd not in ("!istatistik", "!stats"):
                arac = self.beden.akilli_arac_isleyici(girdi)
                if arac:
                    return bitir(arac, tool_used=True)
            return bitir(self._komut_isle(girdi), rol="system", kaydet=False)

        # 2. Saf matematik (örn: 145 * 24 + 10)
        mat = girdi.replace("x", "*").replace("^", "**")
        if re.fullmatch(r"[\d\s+\-*/().%]+", mat) and any(op in mat for op in "+-*/%"):
            sonuc = yetenekler.hesapla(mat)
            if yetenekler.basarili_mi(sonuc):
                return bitir(f"🧮 `{girdi}` = **{sonuc}**", tool_used=True, action="Hesaplama")

        # 3. Sesli geçmiş okuma
        if any(w in gl for w in ("geçmişi oku", "sohbeti oku", "sohbet geçmişini oku", "read history", "read the history")):
            self._gecmisi_oku(6)
            return bitir("Son konuşmaları sesli okuyorum." if lang == "tr" else "Reading recent conversation aloud.")

        # 4. Araç niyetleri (saat, ekran, hesap, arama...)
        arac = self.beden.akilli_arac_isleyici(girdi)
        if arac:
            return bitir(arac, tool_used=True)

        # 5. RAG + Wikipedia bağlamı
        self.hafiza.ani_kaydet("kullanici", girdi)
        baglam, kaynak = "", None
        if girdi.endswith("?") or any(w in gl for w in self._SORU_KELIMELERI):
            try:
                baglam = self.hafiza.rag_sorgula(girdi, k=2, max_karakter=350)
            except Exception:
                baglam = ""
            if len(baglam.strip()) < 30:
                sorgu = self._TEMIZLE_RE.sub("", girdi).strip(" ?!.")
                if len(sorgu) > 2 and sorgu.lower() not in ("sen", "ben", "o", "biz", "bu", "şu", "you", "me"):
                    wiki = yetenekler.wiki_ara(sorgu, lang=lang)
                    if yetenekler.basarili_mi(wiki) and len(wiki) > 50:
                        baglam, kaynak = wiki[:400], "Wikipedia"
                        self.beden._bilgi_sakla(sorgu, wiki)

        # 6. Prompt
        gecmis = "".join(
            f"{'Kullanıcı' if a['rol'] == 'kullanici' else 'Nova'}: {a['icerik']}\n"
            for a in self.hafiza.son_anilar_getir(limit=5)[:-1][-4:]
        )
        parcalar = ([f"[Bilgi: {baglam.strip()[:300]}]"] if baglam else []) + \
                   ([gecmis.strip()] if gecmis.strip() else []) + [f"Kullanıcı: {girdi}\nNova:"]
        tohum = "\n".join(parcalar)

        # 7. Sinir ağı üretimi (akış)
        cevap = ""
        durdurucular = ("Kullanıcı:", "Nova:", "[Bilgi:", "<EOS>", "<BOS>")
        try:
            with closing(self.beyin.uret_stream(tohum, uzunluk=140, sicaklik=0.70, top_k=8,
                                                top_p=0.88, rep_ceza=1.25)) as akis:
                for ch in akis:
                    cevap += ch
                    kes = min((cevap.find(t) for t in durdurucular if t in cevap), default=-1)
                    if kes >= 0:
                        cevap = cevap[:kes]
                        break
                    if chunk_cb:
                        chunk_cb(ch)
        except Exception as e:
            logger.warning(f"[Bridge] Sinir ağı üretim hatası: {e}")

        cevap = cevap.strip()
        if len(cevap) < 6:
            cevap = baglam.strip() if baglam else (
                f"Girdinizi aldım: \"{girdi}\". Nova öğrenmeye ve büyümeye devam ediyor." if lang == "tr"
                else f"Acknowledged: \"{girdi}\". Nova is still learning and growing.")
            if chunk_cb:
                chunk_cb(cevap)

        self.hafiza.ani_kaydet("nova", cevap)
        return {"type": "chat_reply", "reply": cevap, "role": "nova", "source": kaynak,
                "action": f"Kaynak: {kaynak}" if kaynak else None}

    # ── ! Komutları ───────────────────────────────────────────────────────────
    def _komut_isle(self, girdi: str) -> str:
        parcalar = girdi[1:].split(maxsplit=1)
        cmd = parcalar[0].lower() if parcalar else ""
        arg = parcalar[1].strip() if len(parcalar) > 1 else ""
        en = config_manager.is_english()

        if cmd in ("istatistik", "stats"):
            s = self.hafiza.istatistik()
            raw = self.beyin.raw_model
            return (
                f"🧠 NOVA AGI — {'NETWORK & MEMORY' if en else 'SİNİR AĞI VE HAFIZA'}\n"
                f" ├─ {'Nodes' if en else 'Düğüm'}: {s['bilgi_sayisi'] + s['ani_sayisi']:,} "
                f"({'semantic' if en else 'semantik'} {s['bilgi_sayisi']:,} · {'episodic' if en else 'epizodik'} {s['ani_sayisi']:,})\n"
                f" ├─ {'Training queue' if en else 'Eğitim kuyruğu'}: {s['egitilmemis']:,}\n"
                f" ├─ {'Model' if en else 'Model'}: {raw.mimari_ozet()}\n"
                f" ├─ {'Device' if en else 'Cihaz'}: {self.beyin.device}\n"
                f" └─ {'Step' if en else 'Adım'}: {self.beyin.adim:,}"
            )
        if cmd in ("anilar", "anılar", "memories"):
            n = int(arg) if arg.isdigit() else 5
            return "\n".join([f"📜 {'Last' if en else 'Son'} {n}:"] +
                             [f"[{a['zaman']}] {a['rol']}: {a['icerik'][:70]}" for a in self.hafiza.son_anilar_getir(limit=n)])
        if cmd in ("oku", "read", "gecmis_oku", "geçmiş_oku"):
            n = self._gecmisi_oku((int(arg) if arg.isdigit() else 3) * 2)
            return f"🔊 {n} {'messages read aloud.' if en else 'mesaj sesli okunuyor.'}" if n else \
                ("No history to read." if en else "Okunacak geçmiş yok.")
        if cmd in ("izle", "ekran", "gozlem", "gözlem", "watch"):
            return self.beden.gozlemci.goruntule_ve_incele(arg or girdi)
        if cmd in ("kaydet", "save"):
            self.beyin.kaydet()
            return "✓ Model saved." if en else "✓ Model ve ağırlıklar kaydedildi."
        if cmd in ("buyut", "büyüt", "grow"):
            return f"✓ {'Growth' if en else 'Büyüme'}: {self.beyin.buyut()}"
        if cmd == "hf":
            from hf_auth import hf_durum_metni, hf_token_kaydet_ve_giris, hf_token_sil
            if not arg:
                return hf_durum_metni()
            if arg.lower() in ("sil", "logout"):
                hf_token_sil()
                return "Hugging Face token removed." if en else "Hugging Face token'ı silindi."
            return hf_token_kaydet_ve_giris(arg)[1]
        if cmd in ("lang", "dil"):
            if arg.lower() in ("en", "eng", "english"):
                config_manager.set_language("en")
                return "✓ Language set to English."
            if arg.lower() in ("tr", "tur", "türkçe", "turkce"):
                config_manager.set_language("tr")
                return "✓ Dil Türkçe olarak ayarlandı."
            return f"🌐 {'Active language' if en else 'Aktif dil'}: {'English (en)' if en else 'Türkçe (tr)'}"
        if cmd in ("egitim", "eğitim", "train"):
            sub = arg.lower()
            if sub in ("durdur", "stop", "pause", "kapat", "off"):
                self.beyin.egitimi_durdur()
                config_manager.set_continuous_training(False)
                return "⏸️ Training paused." if en else "⏸️ Sürekli eğitim durduruldu."
            if sub in ("baslat", "başlat", "start", "resume", "ac", "aç", "on"):
                self.beyin.surekli_egitim_baslat()
                config_manager.set_continuous_training(True)
                return "▶️ Training resumed." if en else "▶️ Sürekli eğitim başlatıldı."
            aktif = self.beyin.is_training
            return (f"ℹ️ Training: {'active 🔥' if aktif else 'paused ⏸️'}  (!train stop | !train start)" if en else
                    f"ℹ️ Sürekli eğitim: {'aktif 🔥' if aktif else 'durduruldu ⏸️'}  (!egitim durdur | !egitim baslat)")
        if cmd in ("yardim", "yardım", "help"):
            if en:
                return ("📖 Commands:\n"
                        "  !stats            — model & memory metrics\n"
                        "  !train [stop|start] — continuous training\n"
                        "  !wiki <topic>     — live Wikipedia lookup\n"
                        "  !search <query>   — web search\n"
                        "  !calc <expr>      — calculator (2^10 + sqrt(144))\n"
                        "  !python <code>    — run a short Python snippet\n"
                        "  !read <file>      — read a local text file\n"
                        "  !watch            — observe the screen\n"
                        "  !memories [N]     — recent memories\n"
                        "  !save · !grow · !hf · !lang en|tr · !briefing")
            return ("📖 Komutlar:\n"
                    "  !istatistik           — model ve hafıza metrikleri\n"
                    "  !egitim [durdur|baslat] — sürekli eğitim\n"
                    "  !wiki <konu>          — canlı Wikipedia araştırması\n"
                    "  !ara <sorgu>          — web araması\n"
                    "  !hesapla <ifade>      — hesap makinesi (2^10 + sqrt(144))\n"
                    "  !python <kod>         — kısa Python kodu çalıştır\n"
                    "  !oku <dosya>          — yerel metin dosyasını oku\n"
                    "  !izle                 — ekranı gözlemle\n"
                    "  !anilar [N]           — son anılar\n"
                    "  !kaydet · !buyut · !hf · !lang en|tr · !brifing")
        return f"Unknown command: !{cmd}. Try !help" if en else f"Bilinmeyen komut: !{cmd}. !yardim yazabilirsiniz."

    # ── Ayarlar ───────────────────────────────────────────────────────────────
    def _ayarlari_uygula(self, yeni: Dict[str, Any]) -> Dict[str, Any]:
        eski = config_manager.get_all_settings()
        yeni = {k: v for k, v in yeni.items() if k in config_manager.DEFAULTS or k == "weights_file"}
        if "language" in yeni:
            yeni["language"] = config_manager._normalize_lang(str(yeni["language"] or "en"))
        config_manager.update_settings(yeni)
        b = self.beyin

        try:
            if "learning_rate" in yeni:
                b.cfg.lr = float(yeni["learning_rate"])
                for pg in b.optimizer.param_groups:
                    pg["lr"] = b.cfg.lr
            if "batch_size" in yeni:
                b.cfg.batch_size = max(1, int(yeni["batch_size"]))
            if "growth_threshold" in yeni:
                b.plato.esik = float(yeni["growth_threshold"])
        except (TypeError, ValueError) as e:
            logger.warning(f"[Bridge] Geçersiz hiperparametre: {e}")

        if yeni.get("hf_token") and yeni["hf_token"] != eski.get("hf_token"):
            from hf_auth import hf_token_kaydet_ve_giris
            hf_token_kaydet_ve_giris(yeni["hf_token"])

        if self.web_sunucu and ("web_server_enabled" in yeni or "web_server_port" in yeni):
            acik = bool(config_manager.get_setting("web_server_enabled"))
            port = int(config_manager.get_setting("web_server_port"))
            if acik and (not self.web_sunucu.is_running or self.web_sunucu.port != port):
                self.web_sunucu.stop()
                self.web_sunucu.start(port=port)
            elif not acik and self.web_sunucu.is_running:
                self.web_sunucu.stop()

        if "continuous_training_enabled" in yeni:
            if yeni["continuous_training_enabled"] and not b.is_training:
                b.surekli_egitim_baslat()
            elif not yeni["continuous_training_enabled"] and b.is_training:
                b.egitimi_durdur()

        yeniden_baslat = any(yeni.get(k) != eski.get(k) for k in ("device", "multi_gpu_enabled") if k in yeni)
        return {"restart_required": yeniden_baslat, "settings": config_manager.get_all_settings()}

    def kapat(self):
        if not self._calisiyor:
            return
        self._calisiyor = False
        self.beyin.egitimi_durdur()
        if self.web_sunucu:
            self.web_sunucu.stop()
        self.beyin.kaydet()
        logger.info("[Motor] Nova motoru kapatıldı.")
