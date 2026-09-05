# ═══════════════════════════════════════════════════════════════════════════════
# nova_bridge.py  —  Nova AGI C# WPF GUI Köprüsü ve IPC Servisi
# ═══════════════════════════════════════════════════════════════════════════════
#
# C# .NET 9 WPF Arayüzü ile Nova Motoru (Memory, Brain, Body, Hardware)
# arasında yüksek performanslı çift yönlü JSON Lines (stdin/stdout) protokolü.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys
import json
import time
import queue
import signal
import threading
import logging
from typing import Dict, Any, Optional

# UTF-8 Konsol yapılandırması
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
        if hasattr(sys.stdin, "reconfigure"):
            sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass

# GPU ve Donanım Hazırlığı
try:
    import gpu_setup
    gpu_setup.gpu_hazirla()
except Exception:
    pass

import hardware
import config_manager
import yetenekler
import re
from web_server import NovaWebServer, get_local_ip
from memory import HafizaYoneticisi
from brain import BeynYoneticisi
from body import AjanBeden


# Sessiz loglama (köprü stdout'u kirletmemeli, sadece UTF-8 stderr)
try:
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger("nova.bridge")


class NovaBridgeServer:
    def __init__(self):
        self.hafiza = HafizaYoneticisi()
        self.beyin = BeynYoneticisi(self.hafiza)
        self.beden = AjanBeden(self.hafiza, self.beyin)
        self._calisiyor = True
        self._lock = threading.Lock()

        # Sürekli arka plan eğitimi başlat (ayar kontrolü ile)
        if config_manager.is_continuous_training_enabled():
            self._egitim_thread = self.beyin.surekli_egitim_baslat()
        else:
            self._egitim_thread = None
            logger.info("[Bridge] Sürekli arka plan eğitimi ayarlardan dolayı kapalı (başlatılmadı).")

        # Web & Mobil Sunucusu
        try:
            w_port = int(config_manager.get_setting("web_server_port", 8080))
            self.web_sunucu = NovaWebServer(bridge_instance=self, port=w_port)
            if config_manager.get_setting("web_server_enabled", False):
                self.web_sunucu.start(port=w_port)
        except Exception as e:
            logger.warning(f"[Bridge] Web sunucusu başlatılamadı: {e}")
            self.web_sunucu = None

        # Otonom Merak Motoru (Arka plan Wikipedia araştırmacısı)
        try:
            from hugging_loader import OtonomMerakMotoru
            self.merak_motoru = OtonomMerakMotoru(self.hafiza)
            self._merak_thread = threading.Thread(target=self._merak_dongusu, daemon=True, name="NovaMerak")
            self._merak_thread.start()
        except Exception:
            self.merak_motoru = None


    def _merak_dongusu(self):
        """Arka planda periyodik olarak özerk Wikipedia araştırması yapar."""
        while self._calisiyor:
            interval = 15
            try:
                cfg = config_manager._config_oku()
                if cfg.get("curiosity_enabled", True) and self.merak_motoru:
                    lang = cfg.get("language", "tr")
                    custom_seeds = cfg.get("curiosity_topics", "")
                    if custom_seeds and hasattr(self.merak_motoru, "tohum_ekle"):
                        self.merak_motoru.tohum_ekle(custom_seeds, lang)
                    res = self.merak_motoru.merak_adimi(lang=lang)
                    if res:
                        logger.info(f"[Merak] {res}")
                interval = int(cfg.get("curiosity_interval", 15))
            except Exception:
                pass
            time.sleep(max(interval, 5))



    def _cevap_yaz(self, obj: Dict[str, Any]):
        """JSON satırı olarak stdout'a yazar ve flush eder (thread-safe)."""
        try:
            line = json.dumps(obj, ensure_ascii=False)
            with self._lock:
                sys.stdout.write(line + "\n")
                sys.stdout.flush()
        except Exception as e:
            sys.stderr.write(f"Bridge write error: {e}\n")

    def _telemetri_paketi(self) -> Dict[str, Any]:
        """Anlık model, bellek ve çoklu GPU donanım telemetrisini üretir."""
        try:
            stat = self.hafiza.istatistik()
            raw_model = getattr(self.beyin, "raw_model", self.beyin.model)
            loss = self.beyin.son_loss()
            if loss == float("inf") or loss < 0:
                loss = 0.0

            lr = 3e-4
            try:
                lr = self.beyin.optimizer.param_groups[0]["lr"]
            except Exception:
                pass

            lang = config_manager.get_language() or "en"
            gpus = hardware.get_all_gpus()
            gpu_summary = hardware.get_gpu_info()
            cpu_info = hardware.get_cpu_info()
            ram_info = hardware.get_ram_info()
            sys_sum = hardware.get_system_summary(lang=lang)
            prof = hardware.get_hardware_profile()

            # Accurate VRAM calculation (CUDA, DirectML, Model tensors + AdamW + buffers)
            model_vram_mb = 0
            if "cpu" not in str(self.beyin.device).lower():
                try:
                    import torch
                    if torch.cuda.is_available() and "cuda" in str(self.beyin.device).lower():
                        model_vram_mb = int(torch.cuda.memory_allocated() // (1024**2))
                    else:
                        param_b = sum(p.numel() * p.element_size() for p in raw_model.parameters())
                        opt_b = sum(p.numel() * 8 for p in raw_model.parameters())
                        act_b = self.beyin.cfg.batch_size * self.beyin.cfg.max_seq_len * getattr(raw_model, '_e', 128) * len(getattr(raw_model, 'bloklar', [])) * 8
                        runtime_overhead = 160 * 1024 * 1024  # DirectML D3D12 pipeline
                        model_vram_mb = max(int((param_b + opt_b + act_b + runtime_overhead) // (1024**2)), 180)
                except Exception:
                    pass

            for g in gpus:
                if g.get("is_gpu") and g.get("vram_allocated_mb", 0) == 0:
                    g["vram_allocated_mb"] = model_vram_mb

            return {
                "type": "telemetry",

                "step": self.beyin.adim,
                "loss": round(loss, 4),
                "learning_rate": lr,
                "vocab_size": len(self.beyin.char2id),
                "episodic_nodes": stat.get("ani_sayisi", 0),
                "semantic_nodes": stat.get("bilgi_sayisi", 0),
                "pending_tasks": stat.get("gorev_bekleyen", 0),
                "is_training": self.beyin.is_training,
                "hardware_tier": prof.get("tier_name", ""),
                "architecture": {
                    "embed_dim": getattr(raw_model, "_e", 128),
                    "n_heads": getattr(raw_model, "_h", 4),
                    "n_layers": len(getattr(raw_model, "bloklar", [])),
                    "ff_dim": getattr(raw_model, "_ff", 512),
                    "params": raw_model.param_sayisi() if hasattr(raw_model, "param_sayisi") else 0,
                    "growth_count": getattr(raw_model, "_toplam_buyume", 0),
                },
                "hardware": {
                    "cpu": cpu_info,
                    "gpus": gpus,
                    "gpu_summary": gpu_summary,
                    "ram": ram_info,
                    "system_summary": sys_sum,
                },
                "web_server": {
                    "is_running": getattr(self.web_sunucu, "is_running", False) if self.web_sunucu else False,
                    "port": getattr(self.web_sunucu, "port", 8080) if self.web_sunucu else 8080,
                    "local_ip": get_local_ip(),
                    "url": f"http://{get_local_ip()}:{getattr(self.web_sunucu, 'port', 8080)}" if self.web_sunucu else f"http://{get_local_ip()}:8080"
                }
            }
        except Exception as e:
            return {"type": "telemetry_error", "message": str(e)}


    def _sohbet_uret(self, girdi: str, chunk_cb: Optional[Any] = None) -> Dict[str, Any]:
        """Kullanıcı mesajını işler, araç niyetlerini kontrol eder ve yanıt üretir."""
        girdi = girdi.strip()
        if not girdi:
            return {"type": "chat_reply", "reply": "", "role": "nova"}

        # 1. Komut mu?
        if girdi.startswith("!"):
            # Akıllı araç kontrolü (!hesapla, !wiki, !ara, !oku, !python, !zaman)
            arac_res = self.beden.akilli_arac_isleyici(girdi)
            if arac_res:
                self.hafiza.ani_kaydet("kullanici", girdi)
                self.hafiza.ani_kaydet("nova", arac_res)
                if chunk_cb:
                    chunk_cb(arac_res)
                return {"type": "chat_reply", "reply": arac_res, "role": "nova", "tool_used": True}

            cevap = self._komut_isle(girdi)
            if chunk_cb:
                chunk_cb(cevap)
            return {"type": "chat_reply", "reply": cevap, "role": "system"}

        # 2. Doğal Dil Akıllı Araç / Niyet Tespiti (hesaplama, nedir, kimdir, saat vb.)
        arac_res = self.beden.akilli_arac_isleyici(girdi)
        if arac_res:
            self.hafiza.ani_kaydet("kullanici", girdi)
            self.hafiza.ani_kaydet("nova", arac_res)
            if chunk_cb:
                chunk_cb(arac_res)
            return {"type": "chat_reply", "reply": arac_res, "role": "nova", "tool_used": True}

        # 2.1 Geçmiş mesajları sesli okuma niyeti
        girdi_lower = girdi.lower()
        if any(w in girdi_lower for w in ["geçmişi oku", "geçmiş mesajları oku", "sohbeti oku", "sohbet geçmişini oku", "read history", "read the history", "read past messages"]):
            anilar = self.hafiza.son_anilar_getir(limit=6)
            metinler = []
            for a in anilar:
                kim = "Kullanıcı" if a.get('rol') in ('kullanici', 'user') else "Nova"
                metinler.append(f"{kim}: {a.get('icerik', '')}")
            okunacak = ". ".join(metinler)
            if okunacak:
                self.beden.ses.konuş(okunacak)
            lang_now = config_manager.get_language() or "tr"
            cevap = "Sohbet geçmişindeki son konuşmaları sesli olarak okuyorum." if lang_now == "tr" else "Reading recent conversation history aloud for you."
            self.hafiza.ani_kaydet("kullanici", girdi)
            self.hafiza.ani_kaydet("nova", cevap)
            if chunk_cb:
                chunk_cb(cevap)
            return {"type": "chat_reply", "reply": cevap, "role": "nova"}

        # 3. Hafıza, RAG ve Canlı İnternet / Wikipedia Zenginleştirme
        self.hafiza.ani_kaydet("kullanici", girdi)
        baglam = self.hafiza.rag_sorgula(girdi, k=3, max_karakter=300)
        lang = config_manager.get_language() or "tr"

        # Eğer yerel hafızada bilgi yoksa, internetten canlı araştır ve hafızayı besle
        if not baglam or len(baglam.strip()) < 20:
            try:
                # Soru kalıplarını temizleyip anahtar kelimeleri çıkar
                temiz_sorgu = re.sub(r"(nedir\??|kimdir\??|nerededir\??|hakkında|bilgi\s+ver|anlat|açıkla|what is|who is|tell me about|how to)", "", girdi, flags=re.IGNORECASE).strip()
                if len(temiz_sorgu) > 2:
                    wiki_res = yetenekler.wiki_ara(temiz_sorgu, lang=lang)
                    if "hata" not in wiki_res.lower() and len(wiki_res) > 50:
                        baglam = wiki_res[:300]
                        self.hafiza.bilgi_kaydet(temiz_sorgu, wiki_res[:2000], lang)
                        # Kullanıcıya doğrudan kaynaklı bilgiyi sun
                        self.hafiza.ani_kaydet("nova", wiki_res)
                        if chunk_cb:
                            chunk_cb(wiki_res)
                        return {"type": "chat_reply", "reply": wiki_res, "role": "nova", "source": "Wikipedia"}
            except Exception as e:
                logger.debug(f"[Canlı Araştırma] Hata: {e}")

        son_anilar = self.hafiza.son_anilar_getir(limit=6)
        gecmis = ""
        for ani in son_anilar[-4:]:
            pref = "Kullanıcı" if ani["rol"] == "kullanici" else "Nova"
            gecmis += f"{pref}: {ani['icerik']}\n"

        parcalar = []
        if baglam:
            parcalar.append(f"[Bağlam: {baglam[:250]}]")
        if gecmis:
            parcalar.append(gecmis.strip())
        parcalar.append(f"Kullanıcı: {girdi}\nNova:")
        tohum = "\n".join(parcalar)

        cevap_ham = ""
        stop_tags = ["Nova:", "Kullanıcı:", "[Bağlam:", "<EOS>"]
        for ch in self.beyin.uret_stream(tohum, uzunluk=140, sicaklik=0.85, top_k=50, top_p=0.92):
            cevap_ham += ch
            dur = False
            for tag in stop_tags:
                if tag in cevap_ham:
                    dur = True
                    break
            if dur:
                break
            if chunk_cb:
                chunk_cb(ch)

        for tag in stop_tags:
            idx = cevap_ham.find(tag)
            if idx != -1:
                cevap_ham = cevap_ham[:idx]

        default_fallback = "I understand. As I learn more from Wikipedia and your conversations, my answers will become richer." if lang == "en" else "Anlıyorum. Wikipedia ve sohbetlerimizden öğrendikçe yanıtlarım daha da zenginleşecektir."
        cevap = re.sub(r"\n{3,}", "\n\n", cevap_ham).strip() or default_fallback

        self.hafiza.ani_kaydet("nova", cevap)
        return {"type": "chat_reply", "reply": cevap, "role": "nova"}

    def _komut_isle(self, girdi: str) -> str:
        """! komutlarını doğrudan işler."""
        parcalar = girdi[1:].split(maxsplit=1)
        cmd = parcalar[0].lower() if parcalar else ""
        arg = parcalar[1].strip() if len(parcalar) > 1 else ""

        if cmd == "istatistik":
            s = self.hafiza.istatistik()
            sem = s.get("bilgi_sayisi", 0)
            epi = s.get("ani_sayisi", 0)
            raw = getattr(self.beyin, "raw_model", self.beyin.model)
            params = f"{raw.param_sayisi():,}" if hasattr(raw, "param_sayisi") else "—"
            return (
                f"🧠 NOVA AGI — SİNİR AĞI VE DÜĞÜM DURUMU\n"
                f" ├─ Toplam Düğüm: {sem + epi:,} Node (Semantik: {sem:,}, Epizodik: {epi:,})\n"
                f" ├─ Bekleyen Kuyruk: {s.get('egitilmemis', 0):,} Veri\n"
                f" ├─ Sinir Ağı Boyutu: {params} Parametre ({raw.mimari_ozet() if hasattr(raw, 'mimari_ozet') else ''})\n"
                f" └─ Eğitim Adımı: {self.beyin.adim:,}"
            )
        elif cmd in ("anilar", "anılar"):
            n = int(arg) if arg.isdigit() else 5
            anilar = self.hafiza.son_anilar_getir(limit=n)
            satirlar = [f"📜 Son {n} Anı:"]
            for a in anilar:
                satirlar.append(f"[{a['zaman']}] {a['rol']}: {a['icerik'][:70]}")
            return "\n".join(satirlar)
        elif cmd in ("oku", "read", "gecmis_oku", "geçmiş_oku"):
            n = int(arg) if arg.isdigit() else 3
            anilar = self.hafiza.son_anilar_getir(limit=n * 2)
            metinler = []
            for a in anilar:
                kim = "Kullanıcı" if a.get('rol') in ('kullanici', 'user') else "Nova"
                metinler.append(f"{kim}: {a.get('icerik', '')}")
            okunacak = ". ".join(metinler)
            if okunacak:
                self.beden.ses.konuş(okunacak)
                return f"🔊 Son {len(anilar)} sohbet mesajı sesli okunuyor."
            return "Okunacak geçmiş mesaj bulunamadı."
        elif cmd in ("izle", "ekran", "gozlem", "gözlem", "watch"):
            return self.beden.gozlemci.goruntule_ve_incele(arg or girdi)
        elif cmd == "kaydet":
            self.beyin.kaydet()
            return "✓ Model ve ağırlıklar başarıyla kaydedildi."
        elif cmd == "buyut":
            msg = self.beyin.buyut()
            return f"✓ Büyüme tetiklendi: {msg}"
        elif cmd == "hf":
            from hf_auth import hf_durum_metni, hf_token_kaydet_ve_giris, hf_token_sil
            if not arg: return hf_durum_metni()
            elif arg.lower() in ("sil", "logout"):
                hf_token_sil()
                return "Hugging Face token'ı silindi."
            else:
                ok, msg = hf_token_kaydet_ve_giris(arg)
                return msg
        elif cmd in ("lang", "dil"):
            if not arg:
                l = config_manager.get_language() or "en"
                return f"🌐 Aktif Dil: {'English (en)' if l=='en' else 'Türkçe (tr)'}"
            elif arg.lower() in ("en", "eng"):
                config_manager.set_language("en")
                return "✓ Dil İngilizce (en) olarak ayarlandı."
            elif arg.lower() in ("tr", "tur"):
                config_manager.set_language("tr")
                return "✓ Dil Türkçe (tr) olarak ayarlandı."
        elif cmd in ("egitim", "eğitim", "train"):
            sub = arg.lower().strip()
            if sub in ("durdur", "stop", "pause", "kapat", "off"):
                self.beyin.egitimi_durdur()
                config_manager.set_continuous_training(False)
                return "⏸️ Sürekli arka plan eğitimi durduruldu. (CPU/GPU eğitimi kapalı)"
            elif sub in ("baslat", "başlat", "start", "resume", "ac", "aç", "on"):
                self.beyin.surekli_egitim_baslat()
                config_manager.set_continuous_training(True)
                return "▶️ Sürekli arka plan eğitimi başlatıldı. (Model öğrenmeye devam ediyor)"
            else:
                durum = "Aktif (Öğreniyor 🔥)" if getattr(self.beyin, "is_training", False) else "Durduruldu (Beklemede ⏸️)"
                return f"ℹ️ Sürekli Arka Plan Eğitimi: {durum}\nKullanım:\n  !egitim durdur  — Eğitimi duraklatır\n  !egitim baslat   — Eğitimi devam ettirir"
        elif cmd == "yardim":
            return (
                "📖 Komutlar & Yetenekler:\n"
                "  !istatistik    — Model ve hafıza metrikleri\n"
                "  !egitim [durum|durdur|baslat] — Sürekli eğitimi yönet\n"
                "  !wiki [konu]   — Wikipedia'da canlı araştır\n"
                "  !ara [sorgu]   — Web ve bilgi araması\n"
                "  !hesapla [mat] — Matematik hesabı (örn: 2^10 + sqrt(144))\n"
                "  !python [kod]  — Python kodunu güvenli çalıştır\n"
                "  !oku [dosya]   — Yerel metin/kod dosyasını oku\n"
                "  !anilar [N]    — Son anıları listele\n"
                "  !kaydet / !buyut / !hf / !lang"
            )
        return f"Bilinmeyen komut: !{cmd}. !yardim yazabilirsiniz."

    def calistir(self):
        """Ana döngü: stdin'den gelen komutları okur ve işler."""
        self._cevap_yaz({"type": "ready", "version": "3.5", "message": "Nova Engine Ready"})

        while self._calisiyor:
            try:
                satir = sys.stdin.readline()
                if not satir:
                    time.sleep(0.02)
                    continue

                satir = satir.strip()
                if not satir:
                    continue

                req = json.loads(satir)
                action = req.get("action", "")
                req_id = req.get("id", None)

                if action == "ping":
                    self._cevap_yaz({"type": "pong", "id": req_id, "time": time.time()})
                elif action == "telemetry":
                    tel = self._telemetri_paketi()
                    tel["id"] = req_id
                    self._cevap_yaz(tel)
                elif action == "chat":
                    prompt = req.get("prompt", "")
                    def _chat_worker(p, r_id):
                        def on_chunk(c):
                            self._cevap_yaz({
                                "type": "chat_chunk",
                                "chunk": c,
                                "role": "nova",
                                "id": r_id,
                                "done": False
                            })
                        res = self._sohbet_uret(p, chunk_cb=on_chunk)
                        res["id"] = r_id
                        self._cevap_yaz({
                            "type": "chat_chunk",
                            "chunk": "",
                            "role": res.get("role", "nova"),
                            "id": r_id,
                            "done": True,
                            "reply": res.get("reply", "")
                        })
                        self._cevap_yaz(res)
                    threading.Thread(target=_chat_worker, args=(prompt, req_id), daemon=True).start()
                elif action == "speak":
                    text = req.get("text", "")
                    if text:
                        self.beden.ses.konuş(text)
                    self._cevap_yaz({"type": "speak_reply", "id": req_id, "status": "ok"})
                elif action == "listen":
                    timeout = int(req.get("timeout", 6))
                    lang = req.get("language", None)
                    def _listen_worker(t_out, l_ang, r_id):
                        recognized = self.beden.ses.dinle(zaman_asimi=t_out, dil=l_ang)
                        self._cevap_yaz({
                            "type": "listen_reply",
                            "id": r_id,
                            "text": recognized or "",
                            "status": "ok" if recognized else "empty"
                        })
                    threading.Thread(target=_listen_worker, args=(timeout, lang, req_id), daemon=True).start()
                elif action == "get_history":
                    limit = int(req.get("limit", 40))
                    anilar = self.hafiza.son_anilar_getir(limit=limit)
                    self._cevap_yaz({"type": "history_reply", "id": req_id, "messages": anilar})
                elif action == "read_history":
                    count = int(req.get("count", 3))
                    anilar = self.hafiza.son_anilar_getir(limit=count * 2)
                    metinler = []
                    for a in anilar:
                        kim = "Kullanıcı" if a.get('rol') in ('kullanici', 'user') else "Nova"
                        metinler.append(f"{kim}: {a.get('icerik', '')}")
                    okunacak = ". ".join(metinler)
                    if okunacak:
                        self.beden.ses.konuş(okunacak)
                    self._cevap_yaz({"type": "read_history_reply", "id": req_id, "status": "ok", "count": len(anilar)})
                elif action == "observe_screen":
                    prompt = req.get("prompt", "")
                    speak = req.get("speak", True)
                    res_text = self.beden.gozlemci.goruntule_ve_incele(prompt, seslendir=speak)
                    self._cevap_yaz({"type": "observation_reply", "id": req_id, "text": res_text, "status": "ok"})
                elif action == "command":
                    cmd = req.get("command", "")
                    res_str = self._komut_isle(cmd)
                    self._cevap_yaz({"type": "command_reply", "id": req_id, "reply": res_str})
                elif action == "get_settings":
                    cfg = config_manager._config_oku()
                    self._cevap_yaz({"type": "settings", "id": req_id, "settings": cfg})
                elif action == "save_settings":
                    new_cfg = req.get("settings", {})
                    config_manager._config_yaz(new_cfg)
                    if "language" in new_cfg:
                        config_manager.set_language(new_cfg["language"])
                    # Canlı Parametre Güncellemesi (Canlı Model Hiperparametreleri)
                    if "learning_rate" in new_cfg:
                        try:
                            lr_val = float(new_cfg["learning_rate"])
                            for pg in self.beyin.optimizer.param_groups:
                                pg["lr"] = lr_val
                        except Exception: pass
                    if "batch_size" in new_cfg:
                        try:
                            self.beyin.cfg.batch_size = int(new_cfg["batch_size"])
                        except Exception: pass
                    if "growth_threshold" in new_cfg:
                        try:
                            self.beyin.plato.esik = float(new_cfg["growth_threshold"])
                        except Exception: pass
                    if "hf_token" in new_cfg and new_cfg["hf_token"]:
                        try:
                            from hf_auth import hf_token_kaydet_ve_giris
                            hf_token_kaydet_ve_giris(new_cfg["hf_token"])
                        except Exception: pass
                    # Canlı Web Sunucusu Kontrolü
                    if "web_server_enabled" in new_cfg or "web_server_port" in new_cfg:
                        try:
                            w_en = bool(new_cfg.get("web_server_enabled", False))
                            w_pt = int(new_cfg.get("web_server_port", 8080))
                            if self.web_sunucu:
                                if w_en:
                                    if not self.web_sunucu.is_running or self.web_sunucu.port != w_pt:
                                        self.web_sunucu.stop()
                                        self.web_sunucu.start(port=w_pt)
                                else:
                                    if self.web_sunucu.is_running:
                                        self.web_sunucu.stop()
                        except Exception as e:
                            logger.error(f"[Bridge] Web sunucusu ayar hatası: {e}")

                    # Canlı Sürekli Eğitim Kontrolü
                    if "continuous_training_enabled" in new_cfg:
                        try:
                            c_train = bool(new_cfg.get("continuous_training_enabled", True))
                            if c_train:
                                if not getattr(self.beyin, "is_training", False):
                                    self._egitim_thread = self.beyin.surekli_egitim_baslat()
                                    logger.info("[Bridge] Sürekli eğitim ayarlardan ETKİNLEŞTİRİLDİ.")
                            else:
                                if getattr(self.beyin, "is_training", False):
                                    self.beyin.egitimi_durdur()
                                    logger.info("[Bridge] Sürekli eğitim ayarlardan DURDURULDU.")
                        except Exception as e:
                            logger.error(f"[Bridge] Sürekli eğitim ayar hatası: {e}")

                    self._cevap_yaz({"type": "save_settings_reply", "id": req_id, "status": "ok", "settings": new_cfg})

                elif action == "pause_training":
                    self.beyin.egitimi_durdur()
                    config_manager.set_continuous_training(False)
                    logger.info("[Bridge] pause_training eylemi ile eğitim durduruldu.")
                    self._cevap_yaz({"type": "training_status_reply", "id": req_id, "status": "ok", "is_training": False})
                elif action == "resume_training":
                    self._egitim_thread = self.beyin.surekli_egitim_baslat()
                    config_manager.set_continuous_training(True)
                    logger.info("[Bridge] resume_training eylemi ile eğitim başlatıldı.")
                    self._cevap_yaz({"type": "training_status_reply", "id": req_id, "status": "ok", "is_training": True})

                elif action == "graph":
                    limit_ani = int(req.get("limit_ani", 100))
                    limit_bilgi = int(req.get("limit_bilgi", 250))
                    g_data = self.hafiza.graf_verisi_getir(limit_ani=limit_ani, limit_bilgi=limit_bilgi)
                    self._cevap_yaz({"type": "graph_data", "id": req_id, "data": g_data})
                elif action == "fetch_wiki_topic":
                    topic = req.get("topic", "").strip()
                    lang = req.get("lang", config_manager.get_language() or "tr")
                    if topic:
                        res = yetenekler.wiki_ara(topic, lang=lang)
                        if res and "hata" not in res.lower() and len(res) > 40:
                            self.hafiza.bilgi_kaydet(topic, res, lang)
                            self._cevap_yaz({"type": "fetch_wiki_reply", "id": req_id, "status": "ok", "topic": topic, "summary": res[:300]})
                        else:
                            self._cevap_yaz({"type": "fetch_wiki_reply", "id": req_id, "status": "error", "message": f"Wikipedia'da '{topic}' bulunamadı."})
                    else:
                        self._cevap_yaz({"type": "fetch_wiki_reply", "id": req_id, "status": "error", "message": "Konu belirtilmedi."})
                elif action == "bulk_wiki_ingest":
                    limit_count = int(req.get("limit", 200))
                    lang = req.get("lang", config_manager.get_language() or "tr")
                    def _ingest_worker():
                        try:
                            from hugging_loader import veri_enjekte_et
                            veri_enjekte_et(limit=limit_count)
                        except Exception as e:
                            logger.error(f"[Bulk Ingest] {e}")
                    t = threading.Thread(target=_ingest_worker, daemon=True, name="WikiBulkIngest")
                    t.start()
                    self._cevap_yaz({"type": "bulk_wiki_reply", "id": req_id, "status": "started", "limit": limit_count, "lang": lang})

                elif action == "export_onnx":
                    out_path = self.beyin.onnx_disa_aktar()
                    self._cevap_yaz({"type": "export_reply", "id": req_id, "status": "ok", "path": out_path, "format": "ONNX"})
                elif action == "export_package":
                    out_path = self.beyin.agirlik_paketi_olustur()
                    self._cevap_yaz({"type": "export_reply", "id": req_id, "status": "ok", "path": out_path, "format": "ZIP"})
                elif action == "grow_brain":
                    msg = self.beyin.buyut()
                    self._cevap_yaz({"type": "grow_reply", "id": req_id, "message": msg})
                elif action == "save_checkpoint":
                    self.beyin.kaydet()
                    self._cevap_yaz({"type": "save_reply", "id": req_id, "status": "ok"})

                elif action in ("exit", "quit"):
                    self._calisiyor = False
                    self._cevap_yaz({"type": "exit_ack", "id": req_id})
                    break
                else:
                    self._cevap_yaz({"type": "error", "id": req_id, "message": f"Unknown action: {action}"})


            except json.JSONDecodeError:
                pass
            except Exception as e:
                self._cevap_yaz({"type": "error", "message": str(e)})


        # Güvenli kapat
        try:
            if hasattr(self, "web_sunucu") and self.web_sunucu:
                self.web_sunucu.stop()
        except Exception:
            pass

        try:
            self.beyin.kaydet()
        except Exception:
            pass



if __name__ == "__main__":
    server = NovaBridgeServer()
    server.calistir()
