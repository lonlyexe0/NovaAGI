<div align="right">
  <strong>Languages:</strong> <b>English</b> | <a href="README.tr.md">Türkçe</a>
</div>

<div align="center">

<img src="assets/nova_icon.png" width="96" alt="Nova AGI">

# Nova AGI — Linux Edition

*A self-growing neural network with memory, voice, screen awareness and a native desktop app.*

[![Platform](https://img.shields.io/badge/Platform-Linux-blue?style=for-the-badge&logo=linux&logoColor=white)](#quick-start)
[![Python](https://img.shields.io/badge/Python-3.10%2B-yellow?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-CUDA%20%7C%20ROCm%20%7C%20XPU%20%7C%20CPU-red?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![UI](https://img.shields.io/badge/UI-Avalonia%20.NET%209-purple?style=for-the-badge&logo=dotnet)](https://avaloniaui.net/)
[![License](https://img.shields.io/badge/License-GPL--3.0-green?style=for-the-badge)](LICENSE)

<img src="docs/screenshot.png" width="880" alt="Nova AGI desktop app">

</div>

> [!NOTE]
> **Project status: archived.** *"The AI can be trained; I just don't have enough resources."*
> Nova is a working prototype — the architecture, growth, memory and interfaces all run — but training a
> useful language model from scratch needs far more compute than a desktop PC. Expect gibberish from an
> untrained model; tool answers (Wikipedia, calculator, time, screen analysis…) work immediately.

This branch is the **Linux port of the `windows-part` branch**: every Windows-only piece
(WPF, DirectML, `winreg`, `winsound`, GDI, Windows OCR, `.bat` scripts, Inno Setup) has been replaced
with a native Linux equivalent, and the code has been optimized along the way.

## Quick start

```bash
git clone -b claude-verison https://github.com/lonlyexe0/NovaAGI.git
cd NovaAGI
./install.sh          # system packages, Python venv, the right PyTorch build, desktop app, menu entry
./nova.sh             # launch
```

`install.sh` detects your GPU and installs the matching PyTorch build. Override it with
`--gpu=cuda|rocm|xpu|cpu`. Useful flags: `--no-system` (no sudo), `--no-desktop`, `--with-dotnet`
(installs the .NET SDK into `~/.dotnet` so the modern UI can be built), `-y`.

| Command | What it does |
|---|---|
| `./nova.sh` | Avalonia desktop app (falls back to the Tk UI if .NET is missing) |
| `./nova.sh term` | Terminal chat (`main.py`) |
| `./nova.sh launcher` | Advanced terminal launcher with Hugging Face streaming |
| `./nova.sh web` | Web/phone server, prints the access link |
| `./nova.sh tunnel` | Exposes the web server through a Cloudflare tunnel |
| `./nova.sh doctor` | GPU, tool and Python package check |
| `./nova.sh build` | Rebuild the desktop app |
| `./uninstall.sh` | Remove the menu entry, builds and (optionally) data |

## What changed from the Windows version

**Platform**
- **Desktop UI:** WPF → **Avalonia 11** (.NET 9). Redesigned dark theme, streaming chat, telemetry
  cards, loss chart and a force-directed memory graph with zoom/pan — drawn in a single render pass
  instead of thousands of UI elements.
- **GPU:** DirectML → **CUDA, ROCm (AMD) and XPU (Intel Arc)**. Consumer Radeon cards that ROCm does not
  officially list (e.g. RX 6500 XT / RX 7600) get `HSA_OVERRIDE_GFX_VERSION` set automatically.
- **Hardware detection:** registry → `/proc`, `/sys/class/drm`, `nvidia-smi`, `lspci`; cached, so
  telemetry polling is cheap.
- **Audio:** winsound/MCI → PipeWire, PulseAudio, ALSA, ffplay or mpv. Offline TTS fallback:
  **espeak-ng** (SAPI is gone).
- **Screen and OCR:** GDI/Windows OCR → `mss` (X11), Pillow, `grim`, `gnome-screenshot`, `spectacle`
  and **Tesseract**.
- **System actions:** `user32` key events → `loginctl`, `wpctl`/`pactl`/`amixer`, `wmctrl`/`xdotool`, and
  the system monitor of your desktop.
- **Scripts and packaging:** `.bat`/Inno Setup → `install.sh`, `nova.sh`, a `.desktop` entry and
  `packaging/build_release.sh`.
- **Data** lives in `~/.local/share/nova-agi` (XDG); set `NOVA_DATA_DIR` to override.

**Speed**
- Generation uses a **KV-cache** and vectorized sampling instead of re-running the whole context and
  looping in Python for every token.
- Attention runs on **`scaled_dot_product_attention`**, which picks Flash or memory-efficient kernels.
  CUDA uses the fused AdamW.
- Training samples windows from **every** queued record. Before, only the first document was learned
  and all 40 were marked as done.
- SQLite: an index on source URLs so imports no longer get slower as the database grows, RAG
  pre-filtering inside SQL, batched updates and a single-query stats call. The memory graph payload is
  truncated to avoid multi-MB JSON every refresh.

**Fixes**
- Embedding growth no longer scrambles the Q/K/V weights (network morphism is now actually
  function-preserving for Q/K/V).
- The desktop bridge's stdout is **protocol-only**. Stray `print()`s used to corrupt the JSON stream.
- The engine saves and exits when the UI closes. It used to spin forever on a closed stdin.
- Slow actions (screen watch, export, listening) run on a worker pool instead of blocking the bridge.
- Concurrent writes from the UI are serialized.
- Settings are merged instead of overwritten, and the device setting actually applies.
- The calculator uses a safe AST evaluator instead of `eval`, and `!python` no longer hijacks
  `sys.stdout`.
- The web server requires an **access key**. Before, anyone on the Wi-Fi could run code or view your
  screen. The server also serves static files from `web/`, streams replies (NDJSON) and caps request
  sizes.
- The celebrity voice-clone samples and XTTS scripts were removed. Nova now uses standard neural voices
  (`en-IE-EmilyNeural`, `tr-TR-EmelNeural`).

## Phone and web access

Turn it on in **Settings → Mobile & Web** (or run `./nova.sh web`). The app shows a link like
`http://192.168.1.20:8080/?token=…`. Open it on a device on the same Wi-Fi and use **Add to Home Screen**
for an app-like experience. The token is stored on the device after the first visit. For access over
the internet, run `./nova.sh tunnel` and append `?token=…` to the `trycloudflare.com` URL.

## Chat commands

`!help` lists everything. Highlights: `!stats`, `!train stop|start`, `!wiki <topic>`, `!search <q>`,
`!calc 2^10+sqrt(144)`, `!python <code>`, `!read <file>`, `!watch` (screen analysis), `!briefing`,
`!memories 5`, `!save`, `!grow`, `!hf <token>`, `!lang en|tr`.

## Desktop capability matrix

| Feature | X11 | Wayland |
|---|---|---|
| Chat, voice, memory, training, web | ✅ | ✅ |
| Screen watch / screenshot | ✅ `mss` | ✅ `grim` (wlroots), `gnome-screenshot`, `spectacle` |
| Mouse and keyboard control (`pyautogui`) | ✅ | XWayland windows only |
| Active window title, "show desktop" | ✅ `xdotool` / `wmctrl` | — |

## Project layout

```
nova_engine.py      core engine: chat pipeline, ! commands, telemetry, settings
nova_bridge.py      JSON-lines IPC for the desktop app (stdout = protocol only)
brain.py            self-growing transformer (KV-cache, SDPA, network morphism)
memory.py           SQLite episodic + semantic memory, RAG, graph data
body.py             agent body: web crawler, voice, vision, skills
linux_desktop.py    audio / screenshot / system actions on Linux
hardware.py         CPU/GPU/RAM detection and training profile
gpu_setup.py        CUDA · ROCm · XPU · CPU setup (run before importing torch)
web_server.py       REST API + web app (web/)
NovaApp/            Avalonia desktop app (C#)
main.py · nova_launcher.py · gui.py   terminal REPL, launcher, Tk fallback UI
nova_headless_trainer/                cloud/Colab trainer
```

## Troubleshooting

- **AMD GPU not used:** run `./nova.sh doctor`. You need the ROCm PyTorch build (`./install.sh --gpu=rocm`)
  and your user must be in the `render` and `video` groups.
- **No microphone input:** `pyaudio` needs `portaudio19-dev` (Debian/Ubuntu) or `portaudio-devel` (Fedora).
- **No voice output:** install `espeak-ng` (offline) or check your internet connection (edge-tts).
- **Desktop app does not start:** `./install.sh --with-dotnet` builds it. `./nova.sh tk` always works.

## License

GPL-3.0 — see [LICENSE](LICENSE).
