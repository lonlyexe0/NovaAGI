# ═══════════════════════════════════════════════════════════════════════════════
# web_server.py  —  Nova AGI Mobil & Web Sunucusu (REST API + Web App)
# ═══════════════════════════════════════════════════════════════════════════════
#
# Aynı ağdaki telefon/tablet/tarayıcılardan Nova'ya erişim. Arayüz dosyaları
# web/ klasöründedir. Tüm /api/* uçları erişim anahtarı ister:
#   • Başlık : X-Nova-Token: <anahtar>
#   • veya   : ?token=<anahtar>  (resim/ses etiketleri için)
# Anahtar ayarlarda (web_access_token) tutulur; masaüstü uygulaması ve
# `./nova.sh web` komutu anahtarlı bağlantı adresini gösterir.
#
# Tek başına çalıştırma:  python web_server.py [--port 8080]
# ═══════════════════════════════════════════════════════════════════════════════

import io
import os
import re
import hmac
import json
import socket
import base64
import logging
import threading
import subprocess
from collections import OrderedDict
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any

import config_manager

logger = logging.getLogger("nova.web")

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
MAX_GOVDE = 16 * 1024 * 1024   # 16 MB (fotoğraf yüklemeleri için)
_ICERIK_TURU = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
                ".js": "application/javascript; charset=utf-8", ".svg": "image/svg+xml",
                ".png": "image/png", ".json": "application/manifest+json"}


def get_local_ip() -> str:
    """Yerel ağdaki (Wi-Fi / Ethernet) IP adresi."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.254.254.254", 1))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def erisim_adresi(port: Optional[int] = None, host: Optional[str] = None) -> str:
    port = port or int(config_manager.get_setting("web_server_port"))
    return f"http://{host or get_local_ip()}:{port}/?token={config_manager.get_web_token()}"


# ── TTS ───────────────────────────────────────────────────────────────────────
_tts_cache: "OrderedDict[str, bytes]" = OrderedDict()
_tts_lock = threading.Lock()


def clean_tts_text(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]*`", "", text)
    text = re.sub(r"http\S+|www\.\S+", "", text)
    text = re.sub(r"[*#_~\[\]()>|═─│├└]", " ", text)
    return re.sub(r"\s+", " ", text).strip()[:450]


def get_tts_audio_bytes(text: str, voice: Optional[str] = None) -> Optional[bytes]:
    """Telefon/tarayıcı için ses üretir: edge-tts (MP3) → espeak-ng (WAV)."""
    clean = clean_tts_text(text)
    if not clean:
        return None
    turkce = bool(re.search(r"[çğıöşüÇĞİÖŞÜ]", clean)) or (voice or "").startswith("tr")
    secilen = "tr-TR-EmelNeural" if turkce else (voice if voice and "Neural" in voice else "en-IE-EmilyNeural")
    anahtar = f"{secilen}:{clean}"
    with _tts_lock:
        if anahtar in _tts_cache:
            _tts_cache.move_to_end(anahtar)
            return _tts_cache[anahtar]

    ses: Optional[bytes] = None
    try:
        import asyncio
        import edge_tts

        async def _uret():
            parcalar = []
            async for c in edge_tts.Communicate(clean, secilen).stream():
                if c["type"] == "audio":
                    parcalar.append(c["data"])
            return b"".join(parcalar)

        ses = asyncio.run(_uret()) or None
    except Exception as e:
        logger.debug(f"[WebTTS] edge-tts başarısız: {e}")

    if ses is None:
        import linux_desktop
        prog = linux_desktop.ilk_bulunan("espeak-ng", "espeak")
        if prog:
            try:
                ses = subprocess.run([prog, "-v", "tr" if turkce else "en-us", "-s", "165", "--stdout", clean],
                                     capture_output=True, timeout=20).stdout or None
            except Exception as e:
                logger.debug(f"[WebTTS] espeak başarısız: {e}")

    if ses:
        with _tts_lock:
            _tts_cache[anahtar] = ses
            while len(_tts_cache) > 64:
                _tts_cache.popitem(last=False)
    return ses


# ═══════════════════════════════════════════════════════════════════════════════
# HTTP İSTEK İŞLEYİCİ
# ═══════════════════════════════════════════════════════════════════════════════
class NovaHttpHandler(BaseHTTPRequestHandler):
    server_bridge = None          # NovaMotoru örneği
    server_version = "NovaAGI/4.0"
    _statik: Dict[str, bytes] = {}

    def log_message(self, format, *args):
        pass

    # ── Yardımcılar ───────────────────────────────────────────────────────────
    def _gonder(self, kod: int, govde: bytes, tur: str, ek: Optional[Dict[str, str]] = None):
        try:
            self.send_response(kod)
            self.send_header("Content-Type", tur)
            self.send_header("Content-Length", str(len(govde)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            for k, v in (ek or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(govde)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, kod: int, veri: Dict[str, Any]):
        self._gonder(kod, json.dumps(veri, ensure_ascii=False, default=str).encode("utf-8"),
                     "application/json; charset=utf-8")

    def _sorgu(self) -> Dict[str, str]:
        return {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}

    def _yetkili(self) -> bool:
        verilen = self.headers.get("X-Nova-Token") or self._sorgu().get("token", "")
        return bool(verilen) and hmac.compare_digest(verilen, config_manager.get_web_token())

    def _govde_json(self) -> Optional[Dict[str, Any]]:
        try:
            uzunluk = int(self.headers.get("Content-Length", 0))
        except ValueError:
            uzunluk = 0
        if uzunluk <= 0 or uzunluk > MAX_GOVDE:
            self._json(413 if uzunluk > MAX_GOVDE else 400, {"error": "Geçersiz istek gövdesi"})
            return None
        try:
            veri = json.loads(self.rfile.read(uzunluk).decode("utf-8"))
            return veri if isinstance(veri, dict) else {}
        except (ValueError, UnicodeDecodeError):
            self._json(400, {"error": "Geçersiz JSON"})
            return None

    @classmethod
    def _statik_dosya(cls, ad: str) -> Optional[bytes]:
        if ad not in cls._statik:
            yol = os.path.realpath(os.path.join(WEB_DIR, ad))
            if not yol.startswith(os.path.realpath(WEB_DIR) + os.sep) or not os.path.isfile(yol):
                return None
            with open(yol, "rb") as f:
                cls._statik[ad] = f.read()
        return cls._statik[ad]

    # ── GET ───────────────────────────────────────────────────────────────────
    def do_GET(self):
        yol = urlparse(self.path).path
        if yol in ("/", "/index.html", "/app"):
            yol = "/index.html"
        if not yol.startswith("/api/"):
            veri = self._statik_dosya(yol.lstrip("/"))
            if veri is None:
                return self._json(404, {"error": "Bulunamadı"})
            return self._gonder(200, veri, _ICERIK_TURU.get(os.path.splitext(yol)[1], "application/octet-stream"))

        if yol == "/api/status":
            return self._json(200, {"online": True, "version": "4.0-linux", "auth": self._yetkili()})
        if not self._yetkili():
            return self._json(401, {"error": "Erişim anahtarı gerekli"})

        bridge = NovaHttpHandler.server_bridge
        q = self._sorgu()
        if yol == "/api/tts":
            ses = get_tts_audio_bytes(q.get("text", ""), voice=q.get("voice"))
            if not ses:
                return self._json(500, {"error": "TTS üretilemedi"})
            return self._gonder(200, ses, "audio/wav" if ses[:4] == b"RIFF" else "audio/mpeg")
        if yol == "/api/screen":
            import linux_desktop
            img = linux_desktop.ekran_goruntusu()
            if img is None:
                return self._json(500, {"error": "Ekran yakalanamadı"})
            img.thumbnail((1280, 1280))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=72, optimize=True)
            return self._gonder(200, buf.getvalue(), "image/jpeg")
        if yol == "/api/history":
            limit = max(1, min(200, int(q.get("limit", 30)) if q.get("limit", "").isdigit() else 30))
            return self._json(200, {"status": "ok",
                                    "messages": bridge.hafiza.son_anilar_getir(limit=limit) if bridge else []})
        if yol == "/api/telemetry":
            return self._json(200, bridge._telemetri_paketi() if bridge else {"status": "no-engine"})
        return self._json(404, {"error": "Bulunamadı"})

    # ── POST ──────────────────────────────────────────────────────────────────
    def do_POST(self):
        yol = urlparse(self.path).path
        if not self._yetkili():
            return self._json(401, {"error": "Erişim anahtarı gerekli"})
        veri = self._govde_json()
        if veri is None:
            return
        bridge = NovaHttpHandler.server_bridge

        if yol == "/api/chat":
            return self._chat(bridge, veri)
        if yol == "/api/tts":
            ses = get_tts_audio_bytes(str(veri.get("text", "")), voice=veri.get("voice"))
            if not ses:
                return self._json(500, {"error": "TTS üretilemedi"})
            return self._gonder(200, ses, "audio/wav" if ses[:4] == b"RIFF" else "audio/mpeg")
        if yol == "/api/action":
            import yetenekler
            return self._json(200, {"status": "ok", "message": yetenekler.sistem_eylemi(str(veri.get("action", "")))})
        if yol == "/api/wiki" and bridge:
            import yetenekler
            konu = str(veri.get("topic", "")).strip()
            bilgi = yetenekler.wiki_ara(konu) if konu else ""
            if yetenekler.basarili_mi(bilgi):
                bridge.hafiza.bilgi_kaydet(konu=konu, icerik=bilgi, url=f"nova://wiki/{konu.replace(' ', '_')}")
                return self._json(200, {"success": True, "topic": konu, "summary": bilgi[:200]})
            return self._json(404, {"success": False, "message": "Konu bulunamadı"})
        return self._json(404, {"error": "Uç nokta bulunamadı"})

    def _chat(self, bridge, veri: Dict[str, Any]):
        mesaj = str(veri.get("message", "")).strip()
        gorsel = veri.get("image")
        if not mesaj and not gorsel:
            return self._json(400, {"error": "Boş mesaj"})
        if bridge is None:
            return self._json(503, {"error": "Nova motoru çalışmıyor"})

        rapor = ""
        if gorsel:
            try:
                from PIL import Image
                b64 = gorsel.split(",", 1)[-1]
                img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
                rapor = bridge.beden.gozlemci.foto_analiz(img, istek=mesaj)
            except Exception as e:
                rapor = f"⚠️ Görsel işleme hatası: {e}"
            if not mesaj:
                return self._json(200, {"reply": rapor, "action": "📷 Görsel Analiz", "status": "ok"})

        if not veri.get("stream"):
            res = bridge._sohbet_uret(mesaj)
            yanit = f"{rapor}\n\n💬 {res.get('reply', '')}" if rapor else res.get("reply", "")
            return self._json(200, {"reply": yanit, "action": res.get("action"), "status": "ok"})

        # NDJSON akışı: her satır {"chunk": "..."}; son satır {"done": true, "reply": "..."}
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()

            def yaz(obj: Dict[str, Any]):
                self.wfile.write((json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"))
                self.wfile.flush()

            if rapor:
                yaz({"chunk": rapor + "\n\n💬 "})
            res = bridge._sohbet_uret(mesaj, chunk_cb=lambda c: yaz({"chunk": c}))
            yaz({"done": True, "reply": (rapor + "\n\n💬 " if rapor else "") + res.get("reply", ""),
                 "action": res.get("action")})
        except (BrokenPipeError, ConnectionResetError):
            pass
        self.close_connection = True


# ═══════════════════════════════════════════════════════════════════════════════
# SUNUCU YÖNETİCİSİ
# ═══════════════════════════════════════════════════════════════════════════════
class NovaWebServer:
    def __init__(self, bridge_instance=None, port: int = 8080):
        self.port = port
        self.bridge = bridge_instance
        self.server: Optional[ThreadingHTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.is_running = False

    def start(self, host: str = "0.0.0.0", port: Optional[int] = None) -> bool:
        if self.is_running:
            return True
        self.port = port or self.port
        NovaHttpHandler.server_bridge = self.bridge
        config_manager.get_web_token()
        try:
            self.server = ThreadingHTTPServer((host, self.port), NovaHttpHandler)
            self.server.daemon_threads = True
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="NovaWebHTTP")
            self.thread.start()
            self.is_running = True
            logger.info(f"[Web] 🌐 Nova web sunucusu: {erisim_adresi(self.port)}")
            return True
        except OSError as e:
            logger.error(f"[Web] Sunucu başlatılamadı ({host}:{self.port}): {e}")
            return False

    def stop(self):
        if not self.is_running or not self.server:
            return
        try:
            self.server.shutdown()
            self.server.server_close()
        finally:
            self.is_running = False
            logger.info("[Web] 🛑 Web sunucusu durduruldu.")


if __name__ == "__main__":
    import sys
    import time
    import signal
    import argparse

    ap = argparse.ArgumentParser(description="Nova AGI web sunucusu (motor ile birlikte)")
    ap.add_argument("--port", type=int, default=None)
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s", datefmt="%H:%M:%S")
    if args.port:
        config_manager.set_setting("web_server_port", args.port)

    import gpu_setup
    gpu_setup.gpu_hazirla()
    from nova_engine import NovaMotoru

    motor = NovaMotoru(start_web=True, web_zorla=True)
    port = motor.web_sunucu.port
    print(f"\n{'═' * 64}\n  🌐 NOVA AGI WEB SUNUCUSU AKTİF\n"
          f"  💻 Bu bilgisayar : {erisim_adresi(port, 'localhost')}\n"
          f"  📱 Telefon       : {erisim_adresi(port)}\n"
          f"  (Adres erişim anahtarı içerir; yalnızca güvendiğiniz cihazlarla paylaşın.)\n{'═' * 64}\n")

    dur = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: dur.set())
    signal.signal(signal.SIGTERM, lambda *_: dur.set())
    while not dur.wait(1):
        pass
    motor.kapat()
    sys.exit(0)
