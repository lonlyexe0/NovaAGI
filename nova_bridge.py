# ═══════════════════════════════════════════════════════════════════════════════
# nova_bridge.py  —  Nova AGI Masaüstü Arayüz Köprüsü (JSON Lines IPC)
# ═══════════════════════════════════════════════════════════════════════════════
#
# Avalonia masaüstü uygulaması (NovaApp) ile Nova motoru (Hafıza, Beyin, Beden,
# Donanım) arasında stdin/stdout üzerinden satır başına bir JSON protokolü.
#
#   İstek : {"id": 7, "action": "chat", "prompt": "..."}
#   Yanıt : {"id": 7, "type": "chat_chunk" | "chat_reply" | ..., ...}
#
# stdout yalnızca protokol içindir: modüllerin print() çıktıları stderr'e
# yönlendirilir, böylece JSON akışı asla bozulmaz. stdin kapanınca (arayüz
# kapandığında) motor ağırlıkları kaydedip çıkar.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys
import json
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

# Protokol kanalını ayır: gerçek stdout'u sakla, geri kalan her şey stderr'e gitsin.
_PROTOKOL = sys.stdout
sys.stdout = sys.stderr

logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                    format="%(asctime)s [%(name)s] %(message)s", datefmt="%H:%M:%S")
for _lib in ("urllib3", "requests", "httpx", "datasets", "huggingface_hub"):
    logging.getLogger(_lib).setLevel(logging.WARNING)
logger = logging.getLogger("nova.bridge")

import gpu_setup
gpu_setup.gpu_hazirla()

import config_manager
import yetenekler
from nova_engine import NovaMotoru, VERSION


class NovaBridgeServer(NovaMotoru):
    """NovaMotoru + JSON Lines protokolü."""

    def __init__(self, start_web: bool = True):
        super().__init__(start_web=start_web)
        self._yaz_lock = threading.Lock()
        self._havuz = ThreadPoolExecutor(max_workers=4, thread_name_prefix="NovaIstek")

    def _cevap_yaz(self, obj: Dict[str, Any]):
        """JSON satırını protokol kanalına yazar (thread-safe)."""
        try:
            line = json.dumps(obj, ensure_ascii=False, default=str)
            with self._yaz_lock:
                _PROTOKOL.write(line + "\n")
                _PROTOKOL.flush()
        except (BrokenPipeError, ValueError):
            self._calisiyor = False
        except Exception as e:
            logger.error(f"Bridge yazma hatası: {e}")

    # ── İstek İşleyici ────────────────────────────────────────────────────────
    def _istek_isle(self, req: Dict[str, Any]):
        action, rid = req.get("action", ""), req.get("id")

        def yanit(tip: str, **veri):
            self._cevap_yaz({"type": tip, "id": rid, **veri})

        try:
            if action == "ping":
                yanit("pong", time=time.time())
            elif action == "telemetry":
                self._cevap_yaz({**self._telemetri_paketi(), "id": rid})
            elif action == "chat":
                on_chunk = lambda c: yanit("chat_chunk", chunk=c, role="nova", done=False)
                res = self._sohbet_uret(req.get("prompt", ""), chunk_cb=on_chunk)
                yanit("chat_chunk", chunk="", role=res.get("role", "nova"), done=True,
                      reply=res.get("reply", ""), action=res.get("action"))
            elif action == "command":
                yanit("command_reply", reply=self._komut_isle(req.get("command", "")))
            elif action == "speak":
                if req.get("text"):
                    self.beden.ses.konuş(req["text"])
                yanit("speak_reply", status="ok")
            elif action == "stop_speaking":
                self.beden.ses.sustur()
                yanit("speak_reply", status="ok")
            elif action == "listen":
                metin = self.beden.ses.dinle(zaman_asimi=int(req.get("timeout", 6)), dil=req.get("language"))
                yanit("listen_reply", text=metin, status="ok" if metin else "empty")
            elif action == "get_history":
                yanit("history_reply", messages=self.hafiza.son_anilar_getir(limit=int(req.get("limit", 40))))
            elif action == "read_history":
                yanit("read_history_reply", status="ok", count=self._gecmisi_oku(int(req.get("count", 3)) * 2))
            elif action == "observe_screen":
                metin = self.beden.gozlemci.goruntule_ve_incele(req.get("prompt", ""), seslendir=req.get("speak", True))
                yanit("observation_reply", text=metin, status="ok")
            elif action == "get_settings":
                yanit("settings", settings=config_manager.get_all_settings(),
                      web_token=config_manager.get_web_token())
            elif action == "save_settings":
                yanit("save_settings_reply", status="ok", **self._ayarlari_uygula(req.get("settings", {})))
            elif action in ("pause_training", "resume_training"):
                aktif = action == "resume_training"
                if aktif:
                    self.beyin.surekli_egitim_baslat()
                else:
                    self.beyin.egitimi_durdur()
                config_manager.set_continuous_training(aktif)
                yanit("training_status_reply", status="ok", is_training=aktif)
            elif action == "graph":
                yanit("graph_data", data=self.hafiza.graf_verisi_getir(
                    limit_ani=int(req.get("limit_ani", 100)), limit_bilgi=int(req.get("limit_bilgi", 250))))
            elif action == "fetch_wiki_topic":
                konu = (req.get("topic") or "").strip()
                lang = req.get("lang") or config_manager.get_language() or "tr"
                sonuc = yetenekler.wiki_ara(konu, lang=lang) if konu else ""
                if konu and yetenekler.basarili_mi(sonuc) and len(sonuc) > 40:
                    self.hafiza.bilgi_kaydet(url=f"https://{lang}.wikipedia.org/wiki/{konu.replace(' ', '_')}",
                                             konu=konu, icerik=sonuc)
                    yanit("fetch_wiki_reply", status="ok", topic=konu, summary=sonuc[:300])
                else:
                    yanit("fetch_wiki_reply", status="error",
                          message=f"'{konu}' bulunamadı." if konu else "Konu belirtilmedi.")
            elif action == "bulk_wiki_ingest":
                limit = int(req.get("limit", 200))
                from hugging_loader import veri_enjekte_et
                threading.Thread(target=veri_enjekte_et, kwargs={"limit": limit, "lang": req.get("lang")},
                                 daemon=True, name="WikiBulkIngest").start()
                yanit("bulk_wiki_reply", status="started", limit=limit)
            elif action == "export_onnx":
                yanit("export_reply", status="ok", path=self.beyin.onnx_disa_aktar(), format="ONNX")
            elif action == "export_package":
                yanit("export_reply", status="ok", path=self.beyin.agirlik_paketi_olustur(), format="ZIP")
            elif action == "grow_brain":
                yanit("grow_reply", message=self.beyin.buyut())
            elif action == "save_checkpoint":
                self.beyin.kaydet()
                yanit("save_reply", status="ok")
            elif action == "system_action":
                yanit("system_action_reply", message=yetenekler.sistem_eylemi(req.get("name", "")))
            else:
                yanit("error", message=f"Unknown action: {action}")
        except Exception as e:
            logger.error(f"[Bridge] '{action}' hatası: {e}", exc_info=True)
            yanit("error", message=str(e))

    def calistir(self):
        """Ana döngü: stdin'den JSON satırları okur; stdin kapanınca çıkar."""
        self._cevap_yaz({"type": "ready", "version": VERSION, "message": "Nova Engine Ready",
                         "device": str(self.beyin.device)})
        for satir in sys.stdin:
            satir = satir.strip()
            if not satir:
                continue
            try:
                req = json.loads(satir)
            except json.JSONDecodeError:
                continue
            if req.get("action") in ("exit", "quit"):
                self._cevap_yaz({"type": "exit_ack", "id": req.get("id")})
                break
            self._havuz.submit(self._istek_isle, req)
            if not self._calisiyor:
                break
        self.kapat()

    def kapat(self):
        self._havuz.shutdown(wait=False, cancel_futures=True)
        super().kapat()


if __name__ == "__main__":
    import signal

    server = NovaBridgeServer()
    signal.signal(signal.SIGTERM, lambda *_: (server.kapat(), os._exit(0)))
    try:
        server.calistir()
    except KeyboardInterrupt:
        server.kapat()
