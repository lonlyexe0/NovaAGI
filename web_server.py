# ═══════════════════════════════════════════════════════════════════════════════
# web_server.py  —  Nova AGI Mobil & Web Yerel Sunucusu (REST API + Web App)
# ═══════════════════════════════════════════════════════════════════════════════
#
# Bilgisayarınızdaki Nova AGI yapay zekasına aynı Wi-Fi ağındaki telefonlardan,
# tabletlerden veya harici tarayıcılardan anında erişim sağlayan hafif web sunucusu.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys
import json
import socket
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Optional, Dict, Any

logger = logging.getLogger("nova.web")

def get_local_ip() -> str:
    """Yerel ağdaki (Wi-Fi / Ethernet) IP adresini tespit eder."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(('10.254.254.254', 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


# ═══════════════════════════════════════════════════════════════════════════════
# MOBİL & MASAÜSTÜ WEB ARAYÜZÜ (HTML / CSS / JS)
# ═══════════════════════════════════════════════════════════════════════════════
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="theme-color" content="#0d1117">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <title>Nova AGI — Mobil & Web</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #090d16;
            --bg-surface: #101626;
            --bg-glass: rgba(16, 22, 38, 0.82);
            --border-glass: rgba(255, 255, 255, 0.08);
            --border-glow: rgba(0, 229, 179, 0.3);
            --accent-cyan: #00e5b3;
            --accent-purple: #c084fc;
            --accent-blue: #3b82f6;
            --text-main: #f1f5f9;
            --text-sub: #94a3b8;
            --msg-user-bg: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            --msg-nova-bg: rgba(15, 23, 42, 0.75);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-base);
            background-image: 
                radial-gradient(circle at 15% 10%, rgba(0, 229, 179, 0.07) 0%, transparent 40%),
                radial-gradient(circle at 85% 90%, rgba(192, 132, 252, 0.08) 0%, transparent 40%);
            color: var(--text-main);
            height: 100dvh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        /* ── Header ─────────────────────────────────────────── */
        header {
            background: var(--bg-glass);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border-bottom: 1px solid var(--border-glass);
            padding: 12px 18px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            z-index: 100;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .brand-icon {
            width: 34px;
            height: 34px;
            border-radius: 10px;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 16px;
            color: #050b14;
            box-shadow: 0 0 16px rgba(0, 229, 179, 0.4);
        }

        .brand-text h1 {
            font-size: 15px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }

        .brand-text p {
            font-size: 10.5px;
            color: var(--accent-cyan);
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .status-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background-color: var(--accent-cyan);
            box-shadow: 0 0 8px var(--accent-cyan);
            display: inline-block;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(0.85); }
        }

        .hud-badge {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-glass);
            border-radius: 20px;
            padding: 5px 12px;
            font-size: 11px;
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-sub);
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .hud-badge span {
            color: var(--accent-cyan);
            font-weight: 600;
        }

        /* ── Chat Container ─────────────────────────────────── */
        #chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 14px;
            scroll-behavior: smooth;
        }

        .msg-wrapper {
            display: flex;
            flex-direction: column;
            max-width: 85%;
            animation: fadeIn 0.25s ease-out;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .msg-wrapper.user {
            align-self: flex-end;
        }

        .msg-wrapper.nova {
            align-self: flex-start;
        }

        .msg-header {
            font-size: 10.5px;
            color: var(--text-sub);
            margin-bottom: 4px;
            padding: 0 4px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .msg-bubble {
            padding: 12px 16px;
            border-radius: 16px;
            font-size: 13.5px;
            line-height: 1.55;
            word-break: break-word;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        }

        .msg-wrapper.user .msg-bubble {
            background: var(--msg-user-bg);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #ffffff;
            border-bottom-right-radius: 4px;
        }

        .msg-wrapper.nova .msg-bubble {
            background: var(--msg-nova-bg);
            border: 1px solid var(--border-glass);
            border-left: 3px solid var(--accent-cyan);
            border-bottom-left-radius: 4px;
            backdrop-filter: blur(12px);
        }

        .action-tag {
            display: inline-block;
            margin-top: 6px;
            font-size: 10px;
            font-family: 'JetBrains Mono', monospace;
            background: rgba(0, 229, 179, 0.12);
            color: var(--accent-cyan);
            padding: 3px 8px;
            border-radius: 6px;
            border: 1px solid rgba(0, 229, 179, 0.25);
        }

        /* ── Chips / Quick Actions ──────────────────────────── */
        .chips-bar {
            padding: 6px 14px;
            display: flex;
            gap: 8px;
            overflow-x: auto;
            scrollbar-width: none;
        }

        .chips-bar::-webkit-scrollbar {
            display: none;
        }

        .chip {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border-glass);
            padding: 5px 12px;
            border-radius: 14px;
            font-size: 11px;
            color: var(--text-sub);
            white-space: nowrap;
            cursor: pointer;
            transition: all 0.2s;
        }

        .chip:hover, .chip:active {
            background: rgba(0, 229, 179, 0.15);
            border-color: var(--accent-cyan);
            color: var(--text-main);
        }

        /* ── Input Bar ──────────────────────────────────────── */
        .input-bar-container {
            background: var(--bg-glass);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border-top: 1px solid var(--border-glass);
            padding: 10px 14px calc(10px + env(safe-area-inset-bottom, 0px));
        }

        .input-bar {
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(0, 0, 0, 0.35);
            border: 1px solid var(--border-glass);
            border-radius: 24px;
            padding: 4px 6px 4px 14px;
            transition: border-color 0.2s, box-shadow 0.2s;
        }

        .input-bar:focus-within {
            border-color: var(--accent-cyan);
            box-shadow: 0 0 16px rgba(0, 229, 179, 0.2);
        }

        #user-input {
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            color: var(--text-main);
            font-size: 14px;
            font-family: inherit;
        }

        #user-input::placeholder {
            color: rgba(148, 163, 184, 0.6);
        }

        .btn-icon {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            border: none;
            background: transparent;
            color: var(--text-sub);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn-icon:hover {
            color: var(--text-main);
            background: rgba(255, 255, 255, 0.08);
        }

        .btn-send {
            background: linear-gradient(135deg, var(--accent-cyan), #00bfa5);
            color: #050b14;
            font-weight: bold;
        }

        .btn-send:hover {
            background: var(--accent-cyan);
            box-shadow: 0 0 12px rgba(0, 229, 179, 0.5);
        }

        /* ── Typings Indicator ──────────────────────────────── */
        .typing-indicator {
            display: none;
            align-self: flex-start;
            padding: 8px 14px;
            background: var(--msg-nova-bg);
            border: 1px solid var(--border-glass);
            border-radius: 14px;
            gap: 4px;
            margin-bottom: 8px;
        }

        .typing-dot {
            width: 6px;
            height: 6px;
            background: var(--accent-cyan);
            border-radius: 50%;
            animation: bounce 1.4s infinite ease-in-out both;
        }

        .typing-dot:nth-child(1) { animation-delay: -0.32s; }
        .typing-dot:nth-child(2) { animation-delay: -0.16s; }

        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
    </style>
</head>
<body>

    <!-- Header -->
    <header>
        <div class="brand">
            <div class="brand-icon">N</div>
            <div class="brand-text">
                <h1>NOVA AGI</h1>
                <p><span class="status-dot"></span> Bilgisayar Motoru Bağlı</p>
            </div>
        </div>
        <div class="hud-badge" id="hud-stats">
            <span>⚡ GPU</span> <span id="stat-params">—</span>
        </div>
    </header>

    <!-- Chat Messages -->
    <div id="chat-container">
        <div class="msg-wrapper nova">
            <div class="msg-header">🌟 Nova AGI • Sistem</div>
            <div class="msg-bubble">
                Merhaba! Telefonunuzdan bilgisayarınızdaki Nova AGI motoruna bağlandınız. Buradan canlı sohbet edebilir, Wikipedia araştırması yaptırabilir veya komut gönderebilirsiniz.
            </div>
        </div>
    </div>

    <!-- Typing indicator -->
    <div class="typing-indicator" id="typing-box" style="margin-left: 16px;">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    </div>

    <!-- Suggestions Bar -->
    <div class="chips-bar">
        <div class="chip" onclick="sendQuick('Merhaba Nova, nasılsın?')">👋 Merhaba</div>
        <div class="chip" onclick="sendQuick('!istatistik')">📊 İstatistik</div>
        <div class="chip" onclick="sendQuick('Kuantum dolanıklığı nedir?')">⚛️ Kuantum</div>
        <div class="chip" onclick="sendQuick('!wiki Yapay Zeka')">🧠 Yapay Zeka</div>
        <div class="chip" onclick="sendQuick('!hesapla 2^16')">🔢 Hesapla</div>
    </div>

    <!-- Input Bar -->
    <div class="input-bar-container">
        <div class="input-bar">
            <input type="text" id="user-input" placeholder="Nova'ya bir soru sorun veya komut yazın..." autocomplete="off">
            <button class="btn-icon" id="btn-mic" onclick="toggleVoice()" title="Sesle Yaz">🎙️</button>
            <button class="btn-icon btn-send" id="btn-send" onclick="sendMessage()">➤</button>
        </div>
    </div>

    <script>
        const chatBox = document.getElementById('chat-container');
        const userInput = document.getElementById('user-input');
        const typingBox = document.getElementById('typing-box');
        const statParams = document.getElementById('stat-params');

        // Telemetry Poller
        async function fetchTelemetry() {
            try {
                const res = await fetch('/api/telemetry');
                if (res.ok) {
                    const data = await res.json();
                    if (data.architecture && data.architecture.params) {
                        statParams.innerText = (data.architecture.params / 1000000).toFixed(1) + 'M Param';
                    }
                }
            } catch (e) {}
        }
        setInterval(fetchTelemetry, 5000);
        fetchTelemetry();

        // Send Message
        async function sendMessage() {
            const text = userInput.value.trim();
            if (!text) return;

            appendMessage('user', text);
            userInput.value = '';
            typingBox.style.display = 'flex';
            chatBox.scrollTop = chatBox.scrollHeight;

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text })
                });
                const data = await res.json();
                typingBox.style.display = 'none';

                if (data.reply) {
                    appendMessage('nova', data.reply, data.action);
                } else {
                    appendMessage('nova', 'Yanıt alınamadı.');
                }
            } catch (err) {
                typingBox.style.display = 'none';
                appendMessage('nova', '⚠️ Sunucuya bağlanırken hata oluştu: ' + err.message);
            }
        }

        function appendMessage(role, text, action = null) {
            const wrap = document.createElement('div');
            wrap.className = 'msg-wrapper ' + role;
            
            const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const header = document.createElement('div');
            header.className = 'msg-header';
            header.innerText = (role === 'user' ? '👤 Sen • ' : '🌟 Nova • ') + time;
            
            const bubble = document.createElement('div');
            bubble.className = 'msg-bubble';
            bubble.innerText = text;

            if (action) {
                const actTag = document.createElement('div');
                actTag.className = 'action-tag';
                actTag.innerText = '⚡ ' + action;
                bubble.appendChild(actTag);
            }

            wrap.appendChild(header);
            wrap.appendChild(bubble);
            chatBox.appendChild(wrap);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        function sendQuick(txt) {
            userInput.value = txt;
            sendMessage();
        }

        userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        // Web Speech STT
        let recognizing = false;
        let recognition = null;
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRec();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'tr-TR';

            recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                userInput.value = transcript;
                recognizing = false;
                document.getElementById('btn-mic').style.color = 'var(--text-sub)';
                sendMessage();
            };

            recognition.onerror = () => {
                recognizing = false;
                document.getElementById('btn-mic').style.color = 'var(--text-sub)';
            };

            recognition.onend = () => {
                recognizing = false;
                document.getElementById('btn-mic').style.color = 'var(--text-sub)';
            };
        }

        function toggleVoice() {
            if (!recognition) {
                alert('Tarayıcınız ses tanıma (STT) desteklemiyor.');
                return;
            }
            if (recognizing) {
                recognition.stop();
                recognizing = false;
                document.getElementById('btn-mic').style.color = 'var(--text-sub)';
            } else {
                recognition.start();
                recognizing = true;
                document.getElementById('btn-mic').style.color = 'var(--accent-cyan)';
            }
        }
    </script>
</body>
</html>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# HTTP İSTEK İŞLEYİCİSİ (REQUEST HANDLER)
# ═══════════════════════════════════════════════════════════════════════════════
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class NovaHttpHandler(BaseHTTPRequestHandler):
    server_bridge = None  # Reference to NovaBridgeServer or Bridge Instance

    def log_message(self, format, *args):
        # Mute standard noisy HTTP access logs
        pass

    def _send_json(self, status_code: int, data: Dict[str, Any]):
        try:
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        url = self.path.split('?')[0]
        
        # 1. Ana Web Arayüzü (HTML)
        if url in ('/', '/index.html', '/app'):
            try:
                body = HTML_TEMPLATE.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception:
                pass
            return

        # 2. Telemetri & Donanım Durumu
        if url == '/api/telemetry':
            if NovaHttpHandler.server_bridge:
                data = NovaHttpHandler.server_bridge._telemetri_paketi()
                self._send_json(200, data)
            else:
                self._send_json(200, {"status": "running", "engine": "Nova AGI v3.5"})
            return

        # 3. Basit Durum Kontrolü
        if url == '/api/status':
            self._send_json(200, {
                "online": True,
                "version": "3.5",
                "local_ip": get_local_ip()
            })
            return

        # 404 Bulunamadı
        self.send_error(404, "Sayfa Bulunamadı")

    def do_POST(self):
        url = self.path.split('?')[0]

        # 1. Sohbet Endpoint'i (/api/chat)
        if url == '/api/chat':
            content_length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(content_length).decode('utf-8')
            try:
                payload = json.loads(raw_body)
                message = payload.get("message", "").strip()
            except Exception:
                self._send_json(400, {"error": "Geçersiz JSON formatı"})
                return

            if not message:
                self._send_json(400, {"error": "Boş mesaj"})
                return

            if NovaHttpHandler.server_bridge:
                bridge = NovaHttpHandler.server_bridge
                try:
                    # Beden / Beyin üzerinden yanıt üret
                    cevap, eylem = bridge.beden.karar_ver(message)
                    bridge.hafiza.ani_kaydet("user", message)
                    bridge.hafiza.ani_kaydet("nova", cevap)

                    self._send_json(200, {
                        "reply": cevap,
                        "action": eylemler_ozeti(eylem) if eylem else None,
                        "status": "ok"
                    })
                except Exception as e:
                    self._send_json(500, {"error": str(e), "reply": f"Hata: {e}"})
            else:
                self._send_json(200, {"reply": f"Echo: {message}", "status": "standalone"})
            return

        # 2. Wikipedia Madde İndir (/api/wiki)
        if url == '/api/wiki':
            content_length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(content_length).decode('utf-8')
            try:
                payload = json.loads(raw_body)
                topic = payload.get("topic", "").strip()
            except Exception:
                self._send_json(400, {"error": "Geçersiz JSON formatı"})
                return

            if NovaHttpHandler.server_bridge:
                import yetenekler
                try:
                    info = yetenekler.wikipedia_ozet(topic)
                    if info:
                        NovaHttpHandler.server_bridge.hafiza.bilgi_kaydet(
                            url=f"https://tr.wikipedia.org/wiki/{topic}",
                            konu=topic,
                            icerik=info
                        )
                        self._send_json(200, {"success": True, "topic": topic, "summary": info[:200]})
                        return
                except Exception as e:
                    self._send_json(500, {"error": str(e)})
                    return
            self._send_json(400, {"success": False, "message": "Konu bulunamadı"})
            return

        self.send_error(404, "Endpoint Bulunamadı")


def eylemler_ozeti(eylem: Any) -> Optional[str]:
    if not eylem: return None
    if isinstance(eylem, str): return eylem
    if isinstance(eylem, dict):
        return f"{eylem.get('arac', '')}: {eylem.get('girdi', '')}"
    return str(eylem)


# ═══════════════════════════════════════════════════════════════════════════════
# SUNUCU YÖNETİCİSİ (WEB SERVER CONTROLLER)
# ═══════════════════════════════════════════════════════════════════════════════
class NovaWebServer:
    def __init__(self, bridge_instance=None, port: int = 8080):
        self.port = port
        self.bridge = bridge_instance
        self.server: Optional[ThreadedHTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.is_running = False

    def start(self, host: str = "0.0.0.0", port: Optional[int] = None) -> bool:
        if self.is_running:
            return True

        if port is not None:
            self.port = port

        NovaHttpHandler.server_bridge = self.bridge
        try:
            self.server = ThreadedHTTPServer((host, self.port), NovaHttpHandler)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="NovaWebHTTP")
            self.thread.start()
            self.is_running = True
            local_ip = get_local_ip()
            logger.info(f"[Web] 🌐 Nova Web Sunucusu Başlatıldı: http://localhost:{self.port} ve http://{local_ip}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"[Web] Web sunucusu başlatılamadı ({host}:{self.port}): {e}")
            self.is_running = False
            return False

    def stop(self):
        if not self.is_running or not self.server:
            return
        try:
            self.server.shutdown()
            self.server.server_close()
            self.is_running = False
            logger.info("[Web] 🛑 Nova Web Sunucusu durduruldu.")
        except Exception as e:
            logger.debug(f"[Web] Durdurma hatası: {e}")


if __name__ == "__main__":
    server = NovaWebServer(port=8080)
    server.start()
    ip = get_local_ip()
    print(f"\n{'═'*60}")
    print(f"  🌐 NOVA AGI MOBİL & WEB SUNUCUSU AKTİF!")
    print(f"  📍 Bilgisayardan: http://localhost:8080")
    print(f"  📱 Telefondan:    http://{ip}:8080")
    print(f"{'═'*60}\n")
    try:
        while True:
            time = __import__("time")
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
