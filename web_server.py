from __future__ import annotations

import asyncio
import base64
import io
import importlib
import json
import logging
import os
import re
import socket
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger("nova.web")


def get_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(0.2)
            sock.connect(("10.254.254.254", 1))
            return sock.getsockname()[0]
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


def clean_tts_text(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"`[^`]*`|https?://\S+|www\.\S+", " ", text)
    return re.sub(r"\s+", " ", re.sub(r"[*#_~\[\]()>]", " ", text)).strip()[:450]


def tts_audio(text: str, voice: str = "") -> tuple[Optional[bytes], str]:
    text = clean_tts_text(text)
    if not text:
        return None, ""
    is_tr = voice.startswith("tr") or bool(re.search(r"[çğıöşüÇĞİÖŞÜ]", text))
    selected = "tr-TR-EmelNeural" if is_tr else "en-IE-EmilyNeural"

    try:
        edge_tts = importlib.import_module("edge_tts")

        async def render() -> bytes:
            communicate = edge_tts.Communicate(text, selected)
            chunks = []
            async for chunk in communicate.stream():
                if chunk.get("type") == "audio":
                    chunks.append(chunk["data"])
            return b"".join(chunks)

        return asyncio.run(render()), "audio/mpeg"
    except Exception as exc:
        logger.debug("edge-tts kullanılamadı: %s", exc)

    try:
        import pyttsx3
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as output:
            path = output.name
        engine = pyttsx3.init()
        engine.setProperty("rate", 175)
        engine.save_to_file(text, path)
        engine.runAndWait()
        with open(path, "rb") as audio_file:
            data = audio_file.read()
        os.unlink(path)
        return data, "audio/wav"
    except Exception as exc:
        logger.debug("pyttsx3 web fallback kullanılamadı: %s", exc)
        return None, ""


HTML = r'''<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>Nova AGI - Mobil & Web</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--bg:#090d16;--surface:#101626;--glass:#101626d1;--line:#ffffff14;--glow:#00e5b34d;--cyan:#00e5b3;--purple:#c084fc;--text:#f1f5f9;--sub:#94a3b8;--user:linear-gradient(135deg,#1e293b,#0f172a);--nova:#0f172ac2}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}body{font-family:'Plus Jakarta Sans',sans-serif;color:var(--text);background:var(--bg);background-image:radial-gradient(circle at 15% 10%,#00e5b312 0,transparent 40%),radial-gradient(circle at 85% 90%,#c084fc14 0,transparent 40%);height:100dvh;display:flex;flex-direction:column;overflow:hidden}button,input{font:inherit}
header{background:var(--glass);backdrop-filter:blur(16px);border-bottom:1px solid var(--line);padding:12px 18px;display:flex;align-items:center;justify-content:space-between;z-index:3}.brand{display:flex;align-items:center;gap:10px}.brand-icon{width:34px;height:34px;border-radius:10px;background:linear-gradient(135deg,var(--cyan),var(--purple));display:grid;place-items:center;font-weight:800;color:#050b14;box-shadow:0 0 16px #00e5b366}.brand h1{font-size:15px;letter-spacing:.5px}.brand p{font-size:10.5px;color:var(--cyan);font-weight:600}.dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--cyan);box-shadow:0 0 8px var(--cyan);animation:pulse 2s infinite}@keyframes pulse{50%{opacity:.45;transform:scale(.85)}}
.header-actions{display:flex;align-items:center;gap:8px}.hud-btn,.hud-badge,.chip,.icon-btn,.send-btn,.speak-btn{border:1px solid var(--line);color:var(--text);background:#ffffff0f;cursor:pointer;transition:.2s}.hud-btn{border-radius:20px;padding:5px 12px;font-size:11px}.hud-btn:hover,.hud-btn.active{border-color:var(--cyan);background:#00e5b326}.hud-badge{border-radius:20px;padding:5px 12px;color:var(--sub);font:11px 'JetBrains Mono',monospace}.hud-badge b{color:var(--cyan)}
#chat-container{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:14px;scroll-behavior:smooth}.msg-wrapper{display:flex;flex-direction:column;max-width:85%;animation:in .25s ease-out}.msg-wrapper.user{align-self:flex-end}.msg-wrapper.nova{align-self:flex-start}@keyframes in{from{opacity:0;transform:translateY(8px)}}.msg-header{font-size:10.5px;color:var(--sub);margin-bottom:4px;padding:0 4px;display:flex;align-items:center;gap:6px}.msg-actions{margin-left:auto}.msg-bubble{padding:12px 16px;border-radius:16px;font-size:13.5px;line-height:1.55;word-break:break-word;white-space:pre-wrap;box-shadow:0 4px 20px #00000040}.user .msg-bubble{background:var(--user);border:1px solid #ffffff1a;border-bottom-right-radius:4px}.nova .msg-bubble{background:var(--nova);border:1px solid var(--line);border-left:3px solid var(--cyan);border-bottom-left-radius:4px;backdrop-filter:blur(12px)}.speak-btn{border-radius:12px;padding:3px 8px;color:var(--cyan);font-size:10.5px}.speak-btn:hover{background:#00e5b333;border-color:var(--cyan)}
.chips-bar{padding:6px 14px;display:flex;gap:8px;overflow-x:auto;scrollbar-width:none}.chips-bar::-webkit-scrollbar{display:none}.chip{border-radius:14px;padding:5px 12px;font-size:11px;color:var(--sub);white-space:nowrap}.chip:hover{background:#00e5b326;border-color:var(--cyan);color:var(--text)}
.input-wrap{background:var(--glass);backdrop-filter:blur(16px);border-top:1px solid var(--line);padding:10px 14px calc(10px + env(safe-area-inset-bottom,0px))}.input-bar{display:flex;align-items:center;gap:8px;background:#00000059;border:1px solid var(--line);border-radius:24px;padding:4px 6px 4px 14px}.input-bar:focus-within{border-color:var(--cyan);box-shadow:0 0 16px #00e5b333}.input-bar input{flex:1;background:transparent;border:0;outline:0;color:var(--text);font-size:14px}.input-bar input::placeholder{color:#94a3b899}.icon-btn,.send-btn{width:36px;height:36px;border-radius:50%;display:grid;place-items:center;background:transparent;color:var(--sub)}.icon-btn:hover{color:var(--text);background:#ffffff14}.send-btn{background:linear-gradient(135deg,var(--cyan),#00bfa5);color:#050b14;font-weight:700}.send-btn:hover{box-shadow:0 0 12px #00e5b380}
.modal{position:fixed;inset:0;background:#04070ed9;backdrop-filter:blur(14px);z-index:8;display:grid;place-items:center;padding:16px}.modal-card{background:var(--surface);border:1px solid var(--glow);border-radius:20px;width:min(520px,100%);padding:18px;box-shadow:0 10px 40px #000000b3}.modal-head{display:flex;justify-content:space-between;margin-bottom:14px}.modal-head h2{font-size:14px;color:var(--cyan)}.close{background:0;border:0;color:var(--sub);cursor:pointer;font-size:18px}.screen{width:100%;display:block;min-height:180px;object-fit:contain;background:#000;border:1px solid var(--line);border-radius:12px}.screen-actions{display:flex;gap:8px;margin-top:10px}.pc-action{flex:1;padding:9px;border-radius:12px;background:#ffffff0d;border:1px solid var(--line);color:var(--text);cursor:pointer;font-size:12px}.pc-action:hover{border-color:var(--cyan);background:#00e5b326}
@media(max-width:700px){.hud-btn span:last-child,.hud-badge{display:none}.msg-wrapper{max-width:92%}.chips-bar{padding-inline:10px}.input-wrap{padding-inline:10px}}
</style></head><body>
<audio id="player" preload="auto"></audio>
<div id="pc-modal" class="modal" hidden><div class="modal-card"><div class="modal-head"><h2>🖥️ Bilgisayar Ekranı</h2><button class="close" onclick="closePc()">✕</button></div><img id="pc-screen" class="screen" src="/api/screen" alt="PC ekranı"><div class="screen-actions"><button class="pc-action" onclick="refreshScreen()">🔄 Yenile</button><button class="pc-action" onclick="closePc()">Kapat</button></div></div></div>
<header><div class="brand"><div class="brand-icon">N</div><div><h1>NOVA AGI</h1><p><span class="dot"></span> Bilgisayar Motoru Bağlı</p></div></div><div class="header-actions"><button id="sound" class="hud-btn active" onclick="toggleSound()">🔊 <span>Friday Sesi</span></button><button class="hud-btn" onclick="toggleVoice()">🎙️ <span>Canlı</span></button><button class="hud-btn" onclick="openPc()">🖥️ <span>PC Masası</span></button><div class="hud-badge">⚡ <b id="params">—</b></div></div></header>
<div id="chat-container"><div class="msg-wrapper nova"><div class="msg-header">🌟 Nova AGI • Sistem <div class="msg-actions"><button class="speak-btn" onclick="speak(this,'Merhaba patron. Nova AGI web arayüzü hazır.')">🔊 Dinle</button></div></div><div class="msg-bubble">Merhaba patron. Bilgisayarınızdaki Nova AGI motoruna bağlandınız. Buradan sohbet edebilir, yanıtları dinleyebilir ve PC ekranını izleyebilirsiniz.</div></div></div>
<div class="chips-bar"><button class="chip" data-q="!istatistik">📊 İstatistik</button><button class="chip" data-q="!anilar 5">🗂 Anılar</button><button class="chip" data-q="!yetenekler">🧠 Yetenekler</button><button class="chip" data-q="!kaydet">💾 Kaydet</button><button class="chip" onclick="openPc()">🖥️ PC Ekranı</button><button class="chip" data-q="Merhaba Nova, nasılsın?">👋 Merhaba</button></div>
<div class="input-wrap"><div class="input-bar"><input id="input" placeholder="Nova'ya yazın, soru sorun veya komut girin..." autocomplete="off"><button id="mic" class="icon-btn" title="Mikrofon">🎙️</button><button id="send" class="send-btn" title="Gönder">➤</button></div></div>
<script>
const input=document.querySelector('#input'),chat=document.querySelector('#chat-container'),player=document.querySelector('#player');let autoSpeak=true;
function add(role,text){const wrap=document.createElement('div');wrap.className='msg-wrapper '+role;const head=document.createElement('div');head.className='msg-header';head.textContent=role==='user'?'👤 Sen':'🌟 Nova AGI';if(role==='nova'){const actions=document.createElement('div');actions.className='msg-actions';const b=document.createElement('button');b.className='speak-btn';b.textContent='🔊 Dinle';b.onclick=()=>speak(b,text);actions.append(b);head.append(actions)}const bubble=document.createElement('div');bubble.className='msg-bubble';bubble.textContent=text;wrap.append(head,bubble);chat.append(wrap);chat.scrollTop=chat.scrollHeight;if(role==='nova'&&autoSpeak)speak(null,text)}
async function speak(button,text){try{const r=await fetch('/api/tts?text='+encodeURIComponent(text));if(!r.ok)throw Error();player.src=URL.createObjectURL(await r.blob());await player.play()}catch(e){speechSynthesis.speak(new SpeechSynthesisUtterance(text))}}
async function send(){const text=input.value.trim();if(!text)return;input.value='';add('user',text);try{const d=await(await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text})})).json();add('nova',d.reply||d.error||'Yanıt alınamadı.')}catch(e){add('nova','Sunucu hatası: '+e.message)}}
document.querySelector('#send').onclick=send;input.onkeydown=e=>{if(e.key==='Enter')send()};document.querySelectorAll('[data-q]').forEach(b=>b.onclick=()=>{input.value=b.dataset.q;send()});function toggleSound(){autoSpeak=!autoSpeak;document.querySelector('#sound').classList.toggle('active',autoSpeak)}
const Speech=window.SpeechRecognition||window.webkitSpeechRecognition;if(Speech){const rec=new Speech();rec.lang='tr-TR';rec.onresult=e=>{input.value=e.results[0][0].transcript;send()};window.toggleVoice=()=>rec.start()}else window.toggleVoice=()=>alert('Bu tarayıcı mikrofon desteklemiyor.');
function openPc(){document.querySelector('#pc-modal').hidden=false;refreshScreen()}function closePc(){document.querySelector('#pc-modal').hidden=true}function refreshScreen(){document.querySelector('#pc-screen').src='/api/screen?t='+Date.now()}
async function telemetry(){try{const d=await(await fetch('/api/telemetry')).json();document.querySelector('#params').textContent=((d.params||0)/1e6).toFixed(1)+'M Param'}catch(e){}}telemetry();setInterval(telemetry,5000);
</script></body></html>'''


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class NovaHandler(BaseHTTPRequestHandler):
    server_ref = None

    def log_message(self, *_args):
        return

    def _json(self, code: int, data: dict):
        raw = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _audio(self, data: bytes, content_type: str):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        ref = NovaHandler.server_ref
        if parsed.path in ("/", "/index.html"):
            raw = HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        elif parsed.path == "/api/status":
            self._json(200, {"online": True, "version": "linux-web", "local_ip": get_local_ip()})
        elif parsed.path == "/api/telemetry":
            self._json(200, ref.telemetry() if ref else {})
        elif parsed.path == "/api/history":
            limit = int(parse_qs(parsed.query).get("limit", [20])[0])
            messages = ref.hafiza.son_anilar_getir(limit=limit) if ref else []
            self._json(200, {"messages": messages})
        elif parsed.path == "/api/tts":
            query = parse_qs(parsed.query)
            audio, content_type = tts_audio(query.get("text", [""])[0], query.get("voice", [""])[0])
            self._audio(audio, content_type) if audio else self._json(503, {"error": "TTS kullanılamıyor"})
        elif parsed.path == "/api/screen":
            try:
                from PIL import ImageGrab
                image = ImageGrab.grab()
                buf = io.BytesIO(); image.save(buf, "JPEG", quality=75)
                self._audio(buf.getvalue(), "image/jpeg")
            except Exception as exc:
                self._json(503, {"error": str(exc)})
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        length = min(int(self.headers.get("Content-Length", 0)), 2_000_000)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            self._json(400, {"error": "Geçersiz JSON"}); return
        ref = NovaHandler.server_ref
        if parsed.path == "/api/chat" and ref:
            message = str(payload.get("message", "")).strip()
            self._json(200, {"reply": ref.reply(message) if message else "Mesaj boş."})
        elif parsed.path == "/api/tts":
            audio, content_type = tts_audio(str(payload.get("text", "")), str(payload.get("voice", "")))
            self._audio(audio, content_type) if audio else self._json(503, {"error": "TTS kullanılamıyor"})
        else:
            self._json(404, {"error": "Endpoint bulunamadı"})


class NovaWebServer:
    def __init__(self, hafiza, beyin, beden, port: int = 8080):
        self.hafiza, self.beyin, self.beden = hafiza, beyin, beden
        self.port = port
        self.server = None
        self.thread = None
        self.is_running = False

    def reply(self, message: str) -> str:
        try:
            if message.startswith("!"):
                parts = message[1:].split(maxsplit=1)
                command = parts[0].lower() if parts else ""
                argument = parts[1].strip() if len(parts) > 1 else ""
                if command == "istatistik":
                    status = self.telemetry()
                    return (f"Adım: {status['step']:,}\n"
                            f"Parametre: {status['params']:,}\n"
                            f"Anı: {status['memories']:,}\n"
                            f"Bilgi: {status['knowledge']:,}")
                if command == "anilar":
                    limit = int(argument) if argument.isdigit() else 5
                    return "\n".join(
                        f"{item['rol']}: {item['icerik']}"
                        for item in self.hafiza.son_anilar_getir(limit=limit)
                    ) or "Anı bulunamadı."
                if command == "yetenekler":
                    return "\n".join(self.beden.yetenek_listele())
                if command == "kaydet":
                    self.beyin.kaydet()
                    return "Model kaydedildi."
                if command == "konuş" or command == "konus":
                    return self.beden.ses.konuş(argument) if argument else "Kullanım: !konuş <metin>"
                if command == "gorevler":
                    tasks = self.hafiza.tum_gorevler()
                    return "\n".join(f"[{task['id']}] {task['durum']}: {task['tanim']}" for task in tasks) or "Görev kuyruğu boş."
                if command == "rag":
                    return self.hafiza.rag_sorgula(argument, k=3) if argument else "Kullanım: !rag <sorgu>"
                if command == "tara" and argument.startswith(("http://", "https://")):
                    content = self.beden.url_tara(argument)
                    if content:
                        self.hafiza.bilgi_kaydet(argument, argument, content)
                        return f"Tarandı ve kaydedildi: {len(content):,} karakter."
                    return "URL taranamadı."
                if command:
                    return f"Bilinmeyen komut: !{command}"
            context = self.hafiza.rag_sorgula(message, k=3, max_karakter=350)
            history = self.hafiza.son_anilar_getir(limit=4)
            prompt = "\n".join([f"[Bağlam: {context}]" if context else "", *[f"{a['rol']}: {a['icerik']}" for a in history], f"Kullanıcı: {message}\nNova:"])
            self.hafiza.ani_kaydet("kullanici", message)
            reply = self.beyin.uret(prompt, uzunluk=220, sicaklik=0.85, top_k=50, top_p=0.92)
            reply = re.split(r"\n(?:Nova|Kullanıcı):", reply, maxsplit=1)[0].strip() or "Yanıt üretilemedi."
            self.hafiza.ani_kaydet("nova", reply)
            return reply
        except Exception as exc:
            logger.exception("Web sohbet hatası")
            return f"Nova hatası: {exc}"

    def telemetry(self) -> dict:
        stat = self.hafiza.istatistik()
        model = self.beyin.model
        return {"step": self.beyin.adim, "loss": self.beyin.son_loss(), "params": model.param_sayisi(), "memories": stat.get("ani_sayisi", 0), "knowledge": stat.get("bilgi_sayisi", 0), "tts": True}

    def start(self, host: str = "0.0.0.0", port: Optional[int] = None) -> bool:
        if self.is_running:
            return True
        if port is not None:
            self.port = port
        try:
            NovaHandler.server_ref = self
            self.server = ThreadedHTTPServer((host, self.port), NovaHandler)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="NovaWeb")
            self.thread.start()
            self.is_running = True
            logger.info("[Web] http://127.0.0.1:%s | ağ: http://%s:%s", self.port, get_local_ip(), self.port)
            return True
        except OSError as exc:
            logger.error("[Web] Sunucu başlatılamadı: %s", exc)
            return False

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        self.is_running = False


if __name__ == "__main__":
    print("Nova web sunucusunu başlatmak için nova_launcher.py --web kullanın.")
