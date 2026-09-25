"use strict";

/* ── Dil ───────────────────────────────────────────────────────────────── */
const LANG = (navigator.language || "en").toLowerCase().startsWith("tr") ? "tr" : "en";
const T = {
  tr: {
    connecting: "Bağlanıyor…", online: "Motor bağlı", offline: "Bağlantı yok",
    placeholder: "Nova'ya yazın veya fotoğraf ekleyin…", you: "Sen", system: "Sistem",
    listen: "🔊 Dinle", stopAudio: "⏹ Durdur", stop: "Bitir",
    soundTitle: "Yanıtları sesli oku", liveTitle: "Canlı sesli sohbet", pcTitle: "Bilgisayar paneli",
    photoTitle: "Fotoğraf gönder", micTitle: "Sesle yaz",
    liveListening: "Dinliyorum…", liveThinking: "Yanıt hazırlanıyor…",
    refresh: "🔄 Yenile", live3s: "Canlı (3 sn)",
    actLock: "Kilitle", actMute: "Sessiz", actVolDown: "Ses −", actVolUp: "Ses +",
    actDesktop: "Masaüstü", actMonitor: "Sistem izleyici", briefing: "Günlük brifing al",
    tokenTitle: "Erişim anahtarı", tokenHelp: "Masaüstü uygulamasındaki (Ayarlar → Mobil & Web) veya terminaldeki anahtarlı adresi açın ya da anahtarı buraya yapıştırın.",
    connect: "Bağlan", photoRequest: "📷 Görsel analizi istendi", noSTT: "Tarayıcınız ses tanımayı desteklemiyor.",
    serverError: "⚠️ Sunucuya ulaşılamadı: ", welcome: "Merhaba! Telefonunuzdan Nova'ya bağlandınız. Soru sorabilir, 📷 fotoğraf gönderebilir veya 🖥️ bilgisayar panelini açabilirsiniz.",
    chips: [["☕ Brifing", "!brifing"], ["📊 İstatistik", "!istatistik"], ["⏰ Saat kaç?", "Saat kaç?"],
            ["🧠 Yapay zeka nedir?", "Yapay zeka nedir?"], ["⚛️ Kuantum", "!wiki Kuantum dolanıklığı"], ["❓ Yardım", "!yardim"]],
    liveHello: "Canlı sohbet açık, dinliyorum.",
  },
  en: {
    connecting: "Connecting…", online: "Engine online", offline: "Offline",
    placeholder: "Message Nova or attach a photo…", you: "You", system: "System",
    listen: "🔊 Listen", stopAudio: "⏹ Stop", stop: "End",
    soundTitle: "Read replies aloud", liveTitle: "Live voice chat", pcTitle: "Computer panel",
    photoTitle: "Send a photo", micTitle: "Dictate",
    liveListening: "Listening…", liveThinking: "Thinking…",
    refresh: "🔄 Refresh", live3s: "Live (3 s)",
    actLock: "Lock", actMute: "Mute", actVolDown: "Volume −", actVolUp: "Volume +",
    actDesktop: "Desktop", actMonitor: "System monitor", briefing: "Get daily briefing",
    tokenTitle: "Access key", tokenHelp: "Open the link with the key shown in the desktop app (Settings → Mobile & Web) or the terminal, or paste the key here.",
    connect: "Connect", photoRequest: "📷 Image analysis requested", noSTT: "Speech recognition is not supported by this browser.",
    serverError: "⚠️ Could not reach the server: ", welcome: "Hi! You're connected to Nova from your phone. Ask anything, send a 📷 photo or open the 🖥️ computer panel.",
    chips: [["☕ Briefing", "!briefing"], ["📊 Stats", "!stats"], ["⏰ What time is it?", "What time is it?"],
            ["🧠 What is AI?", "What is artificial intelligence?"], ["⚛️ Quantum", "!wiki Quantum entanglement"], ["❓ Help", "!help"]],
    liveHello: "Live voice chat is on. I'm listening.",
  },
}[LANG];

const $ = (id) => document.getElementById(id);
const chat = $("chat"), input = $("input"), player = $("player");

document.documentElement.lang = LANG;
document.querySelectorAll("[data-i18n]").forEach((el) => (el.textContent = T[el.dataset.i18n]));
document.querySelectorAll("[data-i18n-title]").forEach((el) => (el.title = T[el.dataset.i18nTitle]));
document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => (el.placeholder = T[el.dataset.i18nPlaceholder]));

const store = {
  get(k, d) { try { return localStorage.getItem(k) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* özel pencere */ } },
};

/* ── Erişim anahtarı ───────────────────────────────────────────────────── */
let token = new URLSearchParams(location.search).get("token") || store.get("nova_token", "");
if (location.search.includes("token=")) {
  store.set("nova_token", token);
  history.replaceState(null, "", location.pathname);
}

function askToken() {
  const dlg = $("token-dialog");
  if (dlg.open) return;
  $("token-input").value = token;
  dlg.showModal();
}
$("token-form").addEventListener("submit", () => {
  token = $("token-input").value.trim();
  store.set("nova_token", token);
  boot();
});

const withToken = (url) => url + (url.includes("?") ? "&" : "?") + "token=" + encodeURIComponent(token);

async function api(path, body) {
  const opts = { headers: { "X-Nova-Token": token } };
  if (body !== undefined) {
    opts.method = "POST";
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(path, opts);
  if (res.status === 401) { askToken(); throw new Error("401"); }
  return res;
}

/* ── Mesaj görüntüleme ─────────────────────────────────────────────────── */
function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function renderText(text) {
  return escapeHtml(text)
    .replace(/```(\w*)\n?([\s\S]*?)```/g, (_, __, code) => `<pre>${code}</pre>`)
    .replace(/`([^`\n]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
}
const now = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

function addMessage(role, text, { action = null, image = null, time = now() } = {}) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;
  const meta = document.createElement("div");
  meta.className = "meta";
  meta.innerHTML = `<span class="who">${role === "user" ? T.you : role === "nova" ? "Nova" : T.system}</span><span>${escapeHtml(time)}</span>`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  const body = document.createElement("div");
  if (image) {
    const img = document.createElement("img");
    img.className = "attach";
    img.src = image;
    bubble.appendChild(img);
  }
  bubble.appendChild(body);

  let speakBtn = null;
  if (role === "nova") {
    speakBtn = document.createElement("button");
    speakBtn.className = "speak";
    speakBtn.textContent = T.listen;
    speakBtn.onclick = () => playAudio(msg.text, speakBtn);
    meta.appendChild(speakBtn);
  }
  wrap.append(meta, bubble);
  chat.appendChild(wrap);

  const msg = {
    text: "",
    speakBtn,
    set(t) { this.text = t; body.innerHTML = renderText(t); scrollDown(); },
    streaming(on) { body.classList.toggle("cursor", on); },
    tag(label) {
      if (!label) return;
      const tag = document.createElement("div");
      tag.className = "tag";
      tag.textContent = "⚡ " + label;
      bubble.appendChild(tag);
    },
  };
  msg.set(text);
  msg.tag(action);
  return msg;
}

let typingEl = null;
function typing(on) {
  if (on && !typingEl) {
    typingEl = document.createElement("div");
    typingEl.className = "msg nova";
    typingEl.innerHTML = '<div class="bubble typing"><i></i><i></i><i></i></div>';
    chat.appendChild(typingEl);
    scrollDown();
  } else if (!on && typingEl) {
    typingEl.remove();
    typingEl = null;
  }
}
const scrollDown = () => requestAnimationFrame(() => (chat.scrollTop = chat.scrollHeight));

function toast(text) {
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = text;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 2600);
}

/* ── Ses çıkışı ────────────────────────────────────────────────────────── */
let autoSpeak = store.get("nova_sound", "true") !== "false";
let playingBtn = null;

function updateSoundBtn() {
  const b = $("btn-sound");
  b.textContent = autoSpeak ? "🔊" : "🔇";
  b.classList.toggle("muted", !autoSpeak);
  b.setAttribute("aria-pressed", String(autoSpeak));
}

function stopAudio() {
  player.pause();
  if (playingBtn) { playingBtn.textContent = T.listen; playingBtn.classList.remove("playing"); playingBtn = null; }
}

function playAudio(text, btn = null, onEnd = null) {
  if (btn && btn === playingBtn) { stopAudio(); return; }
  stopAudio();
  const clean = (text || "").replace(/```[\s\S]*?```/g, " ").replace(/[*#_`>]/g, " ").replace(/\s+/g, " ").trim();
  if (!clean) { onEnd?.(); return; }
  if (btn) { playingBtn = btn; btn.textContent = T.stopAudio; btn.classList.add("playing"); }
  const voice = /[çğıöşüÇĞİÖŞÜ]/.test(clean) || LANG === "tr" ? "tr" : "en-IE-EmilyNeural";
  player.src = withToken(`/api/tts?text=${encodeURIComponent(clean.slice(0, 450))}&voice=${voice}`);
  const done = () => { stopAudio(); onEnd?.(); };
  player.onended = done;
  player.onerror = done;
  player.play().catch(done);
}

/* ── Sohbet ────────────────────────────────────────────────────────────── */
let pendingImage = null;
let busy = false;

async function sendMessage(textArg) {
  const text = (textArg ?? input.value).trim();
  const image = pendingImage;
  if ((!text && !image) || busy) return;
  busy = true;
  $("btn-send").disabled = true;
  input.value = "";
  autoGrow();
  clearImage();
  addMessage("user", text || T.photoRequest, { image });
  typing(true);
  if (live) $("live-status").textContent = T.liveThinking;

  let msg = null, full = "", action = null;
  try {
    const res = await api("/api/chat", { message: text, image, stream: true });
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let nl;
      while ((nl = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, nl).trim();
        buf = buf.slice(nl + 1);
        if (!line) continue;
        const ev = JSON.parse(line);
        if (!msg) { typing(false); msg = addMessage("nova", ""); msg.streaming(true); }
        if (ev.done) { full = ev.reply ?? full; action = ev.action; }
        else if (ev.chunk) full += ev.chunk;
        msg.set(full);
      }
    }
    if (!msg) { typing(false); msg = addMessage("nova", full || "…"); }
    msg.streaming(false);
    msg.tag(action);
    if (autoSpeak || live) playAudio(full, msg.speakBtn, live ? startListening : null);
  } catch (e) {
    typing(false);
    if (e.message !== "401") addMessage("system", T.serverError + e.message);
  } finally {
    busy = false;
    $("btn-send").disabled = false;
  }
}

function autoGrow() {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 140) + "px";
}
input.addEventListener("input", autoGrow);
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); sendMessage(); }
});
$("form").addEventListener("submit", (e) => { e.preventDefault(); sendMessage(); });

$("chips").append(...T.chips.map(([label, cmd]) => {
  const b = document.createElement("button");
  b.className = "chip";
  b.textContent = label;
  b.onclick = () => sendMessage(cmd);
  return b;
}));

/* ── Fotoğraf ──────────────────────────────────────────────────────────── */
$("btn-cam").onclick = () => $("file").click();
$("file").onchange = (e) => {
  const f = e.target.files?.[0];
  if (!f) return;
  const reader = new FileReader();
  reader.onload = () => {
    // Büyük fotoğrafları küçült (mobil veri ve bellek için)
    const img = new Image();
    img.onload = () => {
      const scale = Math.min(1, 1600 / Math.max(img.width, img.height));
      const c = document.createElement("canvas");
      c.width = Math.round(img.width * scale);
      c.height = Math.round(img.height * scale);
      c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
      pendingImage = c.toDataURL("image/jpeg", 0.85);
      $("img-thumb").src = pendingImage;
      $("img-preview").hidden = false;
    };
    img.src = reader.result;
  };
  reader.readAsDataURL(f);
};
function clearImage() {
  pendingImage = null;
  $("file").value = "";
  $("img-preview").hidden = true;
}
$("btn-img-clear").onclick = clearImage;

/* ── Konuşma tanıma ───────────────────────────────────────────────────── */
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
let rec = null, recognizing = false, live = false;
let sttLang = store.get("nova_stt_lang", LANG === "tr" ? "tr-TR" : "en-US");

function updateSttBtn() { $("btn-stt-lang").textContent = sttLang.startsWith("tr") ? "TR" : "EN"; }
$("btn-stt-lang").onclick = () => {
  sttLang = sttLang.startsWith("tr") ? "en-US" : "tr-TR";
  store.set("nova_stt_lang", sttLang);
  updateSttBtn();
};
updateSttBtn();

if (SR) {
  rec = new SR();
  rec.interimResults = false;
  rec.continuous = false;
  rec.onresult = (e) => sendMessage(e.results[0][0].transcript);
  rec.onend = () => { recognizing = false; $("btn-mic").classList.remove("recording"); };
  rec.onerror = () => { recognizing = false; if (live) setTimeout(startListening, 1200); };
}

function startListening() {
  if (!rec || recognizing || busy) return;
  try {
    rec.lang = sttLang;
    rec.start();
    recognizing = true;
    $("btn-mic").classList.add("recording");
    if (live) $("live-status").textContent = T.liveListening;
  } catch { /* zaten dinliyor */ }
}

$("btn-mic").onclick = () => {
  if (!rec) return toast(T.noSTT);
  if (recognizing) rec.stop(); else startListening();
};

function setLive(on) {
  live = on && !!rec;
  if (on && !rec) toast(T.noSTT);
  $("live-banner").hidden = !live;
  $("btn-live").classList.toggle("active", live);
  if (live) playAudio(T.liveHello, null, startListening);
  else { rec?.abort(); stopAudio(); }
}
$("btn-live").onclick = () => setLive(!live);
$("btn-live-stop").onclick = () => setLive(false);

$("btn-sound").onclick = () => {
  autoSpeak = !autoSpeak;
  store.set("nova_sound", String(autoSpeak));
  updateSoundBtn();
  if (!autoSpeak) stopAudio();
};
updateSoundBtn();

/* ── Bilgisayar paneli ─────────────────────────────────────────────────── */
let screenTimer = null;
const refreshScreen = () => ($("screen-img").src = withToken(`/api/screen?t=${Date.now()}`));

$("btn-pc").onclick = () => { $("pc-dialog").showModal(); refreshScreen(); };
$("btn-pc-close").onclick = () => $("pc-dialog").close();
$("pc-dialog").addEventListener("close", () => {
  clearInterval(screenTimer);
  screenTimer = null;
  $("chk-auto").checked = false;
});
$("btn-screen-refresh").onclick = refreshScreen;
$("chk-auto").onchange = (e) => {
  clearInterval(screenTimer);
  screenTimer = e.target.checked ? setInterval(refreshScreen, 3000) : null;
};
document.querySelectorAll(".act[data-action]").forEach((b) => (b.onclick = async () => {
  try {
    const data = await (await api("/api/action", { action: b.dataset.action })).json();
    toast(data.message || "✓");
    setTimeout(refreshScreen, 600);
  } catch (e) { if (e.message !== "401") toast(T.serverError + e.message); }
}));
$("btn-brief").onclick = () => { $("pc-dialog").close(); sendMessage(LANG === "tr" ? "!brifing" : "!briefing"); };

/* ── Telemetri & açılış ────────────────────────────────────────────────── */
function setStatus(on) {
  $("status-dot").className = "dot " + (on ? "on" : "off");
  $("status-text").textContent = on ? T.online : T.offline;
}

async function poll() {
  try {
    const d = await (await api("/api/telemetry")).json();
    setStatus(true);
    const p = d.architecture?.params;
    if (p) $("stat-badge").textContent = `${(p / 1e6).toFixed(1)}M · ${d.device || ""}`.trim();
  } catch (e) {
    if (e.message !== "401") setStatus(false);
  }
}

let booted = false;
async function boot() {
  if (!token) return askToken();
  try {
    const d = await (await api("/api/history?limit=20")).json();
    if (!booted) {
      chat.innerHTML = "";
      const msgs = d.messages || [];
      if (!msgs.length) addMessage("nova", T.welcome);
      for (const m of msgs) {
        const role = m.rol === "kullanici" ? "user" : m.rol === "nova" ? "nova" : "system";
        addMessage(role, m.icerik, { time: (m.zaman || "").slice(11, 16) });
      }
      booted = true;
      setInterval(poll, 5000);
    }
    poll();
  } catch (e) {
    if (e.message !== "401") { setStatus(false); addMessage("system", T.serverError + e.message); }
  }
}

// iOS/Android ses kilidini ilk dokunuşta aç
document.addEventListener("pointerdown", () => {
  player.src = "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=";
  player.play().catch(() => {});
}, { once: true });

boot();
