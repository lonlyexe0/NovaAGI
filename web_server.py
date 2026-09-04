# ═══════════════════════════════════════════════════════════════════════════════
# web_server.py  —  Nova AGI Mobil & Web Yerel Sunucusu (REST API + Web App)
# ═══════════════════════════════════════════════════════════════════════════════
#
# Bilgisayarınızdaki Nova AGI yapay zekasına aynı Wi-Fi ağındaki telefonlardan,
# tabletlerden veya harici tarayıcılardan anında erişim sağlayan hafif web sunucusu.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys
import re
import json
import socket
import logging
import threading
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Optional, Dict, Any

import config_manager

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


# ── Mobil Web TTS Ses Sentezi ve Önbellek ─────────────────────────────────────
_tts_cache: Dict[str, bytes] = {}

def clean_tts_text(text: str) -> str:
    """TTS için metindeki kod bloklarını, linkleri ve markdown işaretlerini temizler."""
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`[^`]*`', '', text)
    text = re.sub(r'http\S+|www\.\S+', '', text)
    text = re.sub(r'[*#_~\[\]\(\)>]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:450]


def get_tts_audio_bytes(text: str, lang: Optional[str] = None) -> Optional[bytes]:
    """
    Telefonlar ve web tarayıcısı için ultra-hızlı Neural MP3 ses dosyası üretir.
    Türkçe için tr-TR-EmelNeural, İngilizce için en-IE-EmilyNeural (F.R.I.D.A.Y. stili).
    """
    clean = clean_tts_text(text)
    if not clean:
        return None

    if not lang:
        lang = "tr" if bool(re.search(r'[çğıöşüÇĞİÖŞÜ]', clean)) else (config_manager.get_language() or "tr")

    cache_key = f"{lang}:{clean}"
    if cache_key in _tts_cache:
        return _tts_cache[cache_key]

    voice = "en-IE-EmilyNeural" if lang == "en" else "tr-TR-EmelNeural"
    try:
        import edge_tts
        import asyncio

        async def _run():
            comm = edge_tts.Communicate(clean, voice)
            chunks = []
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    chunks.append(chunk["data"])
            return b"".join(chunks)

        audio_bytes = asyncio.run(_run())
        if audio_bytes:
            if len(_tts_cache) > 80:
                _tts_cache.clear()
            _tts_cache[cache_key] = audio_bytes
            return audio_bytes
    except Exception as e:
        logger.debug(f"[WebTTS] Audio üretilemedi: {e}")
    return None


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

        .header-actions {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .hud-btn {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid var(--border-glass);
            border-radius: 20px;
            padding: 5px 12px;
            font-size: 11px;
            font-family: inherit;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
            transition: all 0.2s;
            outline: none;
        }

        .hud-btn:hover, .hud-btn:active {
            background: rgba(0, 229, 179, 0.18);
            border-color: var(--accent-cyan);
            color: #ffffff;
        }

        .hud-btn.active {
            border-color: var(--accent-cyan);
            background: rgba(0, 229, 179, 0.15);
            box-shadow: 0 0 10px rgba(0, 229, 179, 0.25);
        }

        .hud-btn.muted {
            opacity: 0.6;
            border-color: rgba(255, 255, 255, 0.1);
        }

        .btn-msg-speak {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid var(--border-glass);
            color: var(--accent-cyan);
            border-radius: 12px;
            padding: 3px 9px;
            font-size: 11px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            margin-left: auto;
            transition: all 0.2s;
            outline: none;
        }

        .btn-msg-speak:hover, .btn-msg-speak:active {
            background: rgba(0, 229, 179, 0.2);
            border-color: var(--accent-cyan);
        }

        .btn-msg-speak.playing {
            background: rgba(239, 68, 68, 0.25);
            border-color: #ef4444;
            color: #fca5a5;
            animation: pulse-red 1.2s infinite;
        }

        @keyframes pulse-red {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.75; transform: scale(0.96); }
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
        <div class="header-actions">
            <button class="hud-btn active" id="btn-speaker-toggle" onclick="toggleAutoSpeak()" title="Sesli Okuma: Açık / Kapalı">
                <span id="speaker-icon">🔊</span> <span id="speaker-text">Ses Açık</span>
            </button>
            <div class="hud-badge" id="hud-stats">
                <span>⚡ GPU</span> <span id="stat-params">—</span>
            </div>
        </div>
    </header>

    <!-- Chat Messages -->
    <div id="chat-container">
        <div class="msg-wrapper nova">
            <div class="msg-header">
                <span>🌟 Nova AGI • Sistem</span>
                <button class="btn-msg-speak" onclick="speakMessage(this, 'Merhaba! Telefonunuzdan bilgisayarınızdaki Nova AGI motoruna bağlandınız. Buradan canlı sohbet edebilir, Wikipedia araştırması yaptırabilir veya komut gönderebilirsiniz.')">🔊 Dinle</button>
            </div>
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
        <div class="chip" onclick="readRecentHistory()">🔊 Geçmişi Oku</div>
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

        // Ses Yönetimi (TTS)
        let autoSpeak = localStorage.getItem('nova_auto_speak') !== 'false';
        let currentAudio = null;
        let currentBtn = null;

        function updateSpeakerUI() {
            const btn = document.getElementById('btn-speaker-toggle');
            const icon = document.getElementById('speaker-icon');
            const text = document.getElementById('speaker-text');
            if (!btn) return;
            if (autoSpeak) {
                btn.className = 'hud-btn active';
                icon.innerText = '🔊';
                text.innerText = 'Ses Açık';
            } else {
                btn.className = 'hud-btn muted';
                icon.innerText = '🔇';
                text.innerText = 'Ses Kapalı';
            }
        }
        updateSpeakerUI();

        function toggleAutoSpeak() {
            autoSpeak = !autoSpeak;
            localStorage.setItem('nova_auto_speak', autoSpeak ? 'true' : 'false');
            updateSpeakerUI();
            if (!autoSpeak) {
                stopSpeech();
            } else {
                speakText('Sesli okuma açıldı.');
            }
        }

        function stopSpeech() {
            if (currentAudio) {
                currentAudio.pause();
                currentAudio.currentTime = 0;
                currentAudio = null;
            }
            if ('speechSynthesis' in window) {
                window.speechSynthesis.cancel();
            }
            if (currentBtn) {
                currentBtn.innerHTML = '🔊 Dinle';
                currentBtn.classList.remove('playing');
                currentBtn = null;
            }
        }

        function speakMessage(btn, text) {
            if (btn && btn.classList.contains('playing')) {
                stopSpeech();
                return;
            }
            speakText(text, btn);
        }

        function speakText(text, btnElement = null) {
            stopSpeech();
            if (!text) return;

            const clean = text.replace(/```[\s\S]*?```/g, ' ')
                              .replace(/`[^`]*`/g, ' ')
                              .replace(/http\S+|www\.\S+/g, '')
                              .replace(/[*#_~\[\]\(\)>]/g, ' ')
                              .replace(/\s+/g, ' ').trim();
            if (!clean) return;

            if (btnElement) {
                currentBtn = btnElement;
                btnElement.innerHTML = '⏹️ Durdur';
                btnElement.classList.add('playing');
            }

            // 1. Sunucu Taraflı Neural Edge-TTS Endpoint'i
            const url = '/api/tts?text=' + encodeURIComponent(clean.substring(0, 450));
            const audio = new Audio(url);
            currentAudio = audio;

            audio.onended = () => {
                if (currentBtn) {
                    currentBtn.innerHTML = '🔊 Dinle';
                    currentBtn.classList.remove('playing');
                    currentBtn = null;
                }
                currentAudio = null;
            };

            audio.onerror = () => {
                // Sunucu TTS yanıt vermezse tarayıcının yerel ses sentezine (SpeechSynthesis) geç
                fallbackSpeech(clean, btnElement);
            };

            const playPromise = audio.play();
            if (playPromise !== undefined) {
                playPromise.catch(() => {
                    // Otomatik oynatma kısıtlaması (iOS/Android) -> yerel senteze geç
                    fallbackSpeech(clean, btnElement);
                });
            }
        }

        function fallbackSpeech(text, btnElement) {
            if (!('speechSynthesis' in window)) {
                if (btnElement) {
                    btnElement.innerHTML = '🔊 Dinle';
                    btnElement.classList.remove('playing');
                    currentBtn = null;
                }
                return;
            }

            window.speechSynthesis.cancel();
            const utter = new SpeechSynthesisUtterance(text);
            const isTr = /[çğıöşüÇĞİÖŞÜ]/.test(text) || (document.documentElement.lang === 'tr');
            utter.lang = isTr ? 'tr-TR' : 'en-US';
            utter.rate = 1.05;

            utter.onend = () => {
                if (btnElement) {
                    btnElement.innerHTML = '🔊 Dinle';
                    btnElement.classList.remove('playing');
                    currentBtn = null;
                }
            };

            utter.onerror = () => {
                if (btnElement) {
                    btnElement.innerHTML = '🔊 Dinle';
                    btnElement.classList.remove('playing');
                    currentBtn = null;
                }
            };

            window.speechSynthesis.speak(utter);
        }

        async function readRecentHistory() {
            try {
                const res = await fetch('/api/history?limit=6');
                if (res.ok) {
                    const data = await res.json();
                    if (data.messages && data.messages.length > 0) {
                        const items = data.messages.slice(-4);
                        const parts = [];
                        items.forEach(m => {
                            const who = (m.rol === 'kullanici' || m.rol === 'user') ? 'Sen' : 'Nova';
                            parts.push(who + ': ' + m.icerik);
                        });
                        const full = parts.join('. ');
                        speakText(full);
                        appendMessage('nova', '🔊 Sohbet geçmişi sesli okunuyor:\n\n' + parts.join('\n'));
                        return;
                    }
                }
            } catch(e) {}
            sendQuick('!oku 2');
        }

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
                    const msgObj = appendMessage('nova', data.reply, data.action);
                    if (autoSpeak && msgObj.speakBtn) {
                        speakMessage(msgObj.speakBtn, data.reply);
                    }
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
            
            const titleSpan = document.createElement('span');
            titleSpan.innerText = (role === 'user' ? '👤 Sen • ' : '🌟 Nova • ') + time;
            header.appendChild(titleSpan);

            let speakBtn = null;
            if (role === 'nova') {
                speakBtn = document.createElement('button');
                speakBtn.className = 'btn-msg-speak';
                speakBtn.innerHTML = '🔊 Dinle';
                speakBtn.title = 'Sesli oku';
                speakBtn.onclick = () => speakMessage(speakBtn, text);
                header.appendChild(speakBtn);
            }
            
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

            return { wrap, bubble, speakBtn };
        }

        function sendQuick(txt) {
            userInput.value = txt;
            sendMessage();
        }

        userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        // Web Speech STT (Mikrofon)
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

        # 2. Mobil / Web TTS Ses Akışı (/api/tts)
        if url == '/api/tts':
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            text = query.get("text", [""])[0].strip()
            lang = query.get("lang", [""])[0].strip() or None

            audio = get_tts_audio_bytes(text, lang=lang)
            if audio:
                self.send_response(200)
                self.send_header('Content-Type', 'audio/mpeg')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'public, max-age=3600')
                self.send_header('Content-Length', str(len(audio)))
                self.end_headers()
                self.wfile.write(audio)
            else:
                self._send_json(500, {"error": "TTS audio üretilemedi"})
            return

        # 3. Geçmiş Mesajlar (/api/history)
        if url == '/api/history':
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            limit = int(query.get("limit", [20])[0])
            if NovaHttpHandler.server_bridge:
                anilar = NovaHttpHandler.server_bridge.hafiza.son_anilar_getir(limit=limit)
                self._send_json(200, {"status": "ok", "messages": anilar})
            else:
                self._send_json(200, {"status": "ok", "messages": []})
            return

        # 4. Telemetri & Donanım Durumu
        if url == '/api/telemetry':
            if NovaHttpHandler.server_bridge:
                data = NovaHttpHandler.server_bridge._telemetri_paketi()
                self._send_json(200, data)
            else:
                self._send_json(200, {"status": "running", "engine": "Nova AGI v3.5"})
            return

        # 5. Basit Durum Kontrolü
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
                    res = bridge._sohbet_uret(message)
                    reply = res.get("reply", "")
                    tool_used = res.get("tool_used", False)
                    source = res.get("source")
                    action_label = f"Kaynak: {source}" if source else ("Akıllı Araç" if tool_used else None)
                    self._send_json(200, {
                        "reply": reply,
                        "action": action_label,
                        "status": "ok"
                    })
                except Exception as e:
                    self._send_json(500, {"error": str(e), "reply": f"Hata: {e}"})
            else:
                try:
                    from memory import HafizaYoneticisi
                    from brain import BeynYoneticisi
                    from body import AjanBeden
                    hafiza = HafizaYoneticisi()
                    beyin = BeynYoneticisi(hafiza)
                    beden = AjanBeden(hafiza, beyin)
                    reply = beden.akilli_arac_isleyici(message) or beyin.uret(message, uzunluk=120)
                    self._send_json(200, {"reply": reply, "status": "standalone"})
                except Exception as e:
                    self._send_json(200, {"reply": f"Echo: {message}", "status": "fallback"})
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
                    info = yetenekler.wiki_ara(topic)
                    if info and "hata" not in info.lower():
                        NovaHttpHandler.server_bridge.hafiza.bilgi_kaydet(topic, info)
                        self._send_json(200, {"success": True, "topic": topic, "summary": info[:200]})
                        return
                except Exception as e:
                    self._send_json(500, {"error": str(e)})
                    return
            self._send_json(400, {"success": False, "message": "Konu bulunamadı"})
            return

        # 3. Mobil / Web TTS POST Endpoint'i (/api/tts)
        if url == '/api/tts':
            content_length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(content_length).decode('utf-8')
            try:
                payload = json.loads(raw_body)
                text = payload.get("text", "").strip()
                lang = payload.get("lang", "") or None
            except Exception:
                self._send_json(400, {"error": "Geçersiz JSON formatı"})
                return

            audio = get_tts_audio_bytes(text, lang=lang)
            if audio:
                self.send_response(200)
                self.send_header('Content-Type', 'audio/mpeg')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'public, max-age=3600')
                self.send_header('Content-Length', str(len(audio)))
                self.end_headers()
                self.wfile.write(audio)
            else:
                self._send_json(500, {"error": "TTS audio üretilemedi"})
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
