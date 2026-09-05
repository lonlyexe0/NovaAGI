<div align="right">
  <strong>Languages:</strong> 
  <b>English</b> | <a href="README.tr.md">Türkçe</a>
</div>

<div align="center">

# 🌟 NOVA AGI v3.5
### *Autonomous Growing Neural Intelligence & Consciousness Architecture*

[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-blue?style=for-the-badge&logo=windows)](https://github.com/lonlyexe0/NovaAGI)
[![Runtime](https://img.shields.io/badge/.NET-9.0%20WPF-purple?style=for-the-badge&logo=dotnet)](https://dotnet.microsoft.com/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-yellow?style=for-the-badge&logo=python)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-DirectML%20%7C%20CUDA-red?style=for-the-badge&logo=pytorch)](https://pytorch.org/)
[![FlashAttention](https://img.shields.io/badge/FlashAttention-2%20Enabled-orange?style=for-the-badge)](https://pytorch.org/)
[![Voice Engine](https://img.shields.io/badge/Voice-F.R.I.D.A.Y.%20Neural%20TTS-brightgreen?style=for-the-badge)](https://github.com/rany2/edge-tts)
[![License](https://img.shields.io/badge/License-GPL--3.0-green?style=for-the-badge)](LICENSE)

```
███╗   ██╗ ██████╗ ██╗   ██╗ █████╗     █████╗  ██████╗ ██╗
████╗  ██║██╔═══██╗██║   ██║██╔══██╗   ██╔══██╗██╔════╝ ██║
██╔██╗ ██║██║   ██║██║   ██║███████║   ███████║██║  ███╗██║
██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██║   ██╔══██║██║   ██║██║
██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║   ██║  ██║╚██████╔╝██║
╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝
```

*Nova is an autonomous, self-expanding artificial general intelligence system featuring dynamic network morphism, F.R.I.D.A.Y. neural voice interaction, ChatGPT-style real-time typewriter streaming, continuous background training, and an ultra-modern native desktop experience.*

</div>

---

## 🚀 Key Flagship Features

### 🌟 1. Native C# .NET 9.0 WPF Desktop Interface & Live Streaming
- **Real-Time Typewriter Streaming**: Instantaneous character/token streaming straight from the neural network to the WPF chat bubbles (`chat_chunk`). No frozen screens or waiting for full paragraphs; words appear in real-time just like ChatGPT.
- **Ultra-Responsive GUI**: Built with .NET 9.0 and C# WPF using asynchronous inter-process communication (IPC) to the PyTorch neural backend.
- **Bilingual On-The-Fly Localization**: Instant real-time UI switching between **English** and **Turkish** without restarting.
- **Hardware Telemetry HUD**: Real-time monitoring of VRAM usage, loss curves, training steps, and parameter growth count.

### 🎙️ 2. F.R.I.D.A.Y. Neural Voice Engine (Speech & Audio)
- **Neural Text-to-Speech (TTS)**: Integrated high-fidelity Microsoft Edge Neural TTS voice modeled after Marvel's F.R.I.D.A.Y. (Irish Neural / Turkish Emel Neural) with zero-latency speech queuing and Windows SAPI offline fallback.
- **Voice Dictation (STT)**: Direct hands-free voice input via microphone using dynamic energy-threshold speech recognition.
- **Voice Commands**: Say `"Read history"` or `"Geçmişi oku"` to have Nova read your recent conversation history aloud.
- **One-Click Audio Toggles**: Dedicated microphone (record) and speaker (mute/unmute) controls embedded directly in the chat bar.

### 🧠 3. Dynamically Growing Neural Architecture (Network Morphism)
- **Zero-Loss Growth**: When training loss plateaus, the neural network autonomously expands its layers, hidden embedding dimensions, and Feed-Forward (FF) neurons without forgetting previously learned weights.
- **From 400M to 1.4B+ Parameters**: Dynamically scales from a compact 32-layer model to an ultra-large multi-billion class architecture.
- **Checkpoint Persistence**: Neural model architecture and weights are saved atomically with Windows lock protection, perfectly preserving grown parameter counts across restarts.

### ⚡ 4. Cloud & Headless Cluster Trainer (`nova_headless_trainer`)
- **FlashAttention-2 & BFloat16**: Accelerated with `F.scaled_dot_product_attention` (saving 70% VRAM and providing 3x speedup) and mixed-precision BFloat16/FP16 for NVIDIA A100/H100 and RTX Tensor Cores.
- **Autonomous Big Data Ingestion**: Pre-loaded with over 600,000 records including official Wikipedia articles, CodeAlpaca programming datasets, Python instructions, and Turkish daily dialogues.
- **Multi-GPU Parallelism**: Automatically distributes training across multiple GPUs using PyTorch `DataParallel`.
- **AMD DirectML & CPU Optimization**: Custom `DirectMLAdamW` zero-CPU fallback optimizer for AMD Radeon graphics cards.

### 🕸️ 5. Interactive Visual Knowledge & Memory Graph Explorer
- **2D Dynamic Cluster Graph**: Interactive force-directed visualization of episodic memories (user conversations) and semantic knowledge (Wikipedia nodes).
- **Live Background Auto-Refresh**: Automatically detects newly ingested concepts and renders them in real time without UI flicker.
- **Instant Search & Topic Downloader**: Download any Wikipedia article straight into the knowledge graph with one click.

### 🌐 6. Web Server & Cloudflare Remote Access
- **Mobile & Web UI**: Built-in responsive web dashboard running on port 8080/9090 (`baslat_web.bat`).
- **Cloudflare Tunnel**: Instant secure public URL generation (`baslat_tunnel.bat`) to chat with Nova securely from your phone or tablet away from home.

---

## 🎙️ How to Use the Voice Engine

Nova comes with a complete neural voice pipeline out of the box:

### 1. Speaking to Nova (Voice Input / Microphone)
1. In the modern desktop GUI (`NovaAGI.exe`), click the **Microphone (🎤)** icon located next to the message input box.
2. The mic button will glow active. Speak clearly into your microphone.
3. Nova will automatically transcribe your speech using noise-filtering speech recognition and send it to the neural engine.

### 2. Hearing Nova Speak (Neural TTS)
1. Click the **Speaker (🔊)** icon next to the send button to toggle voice output on/off.
2. When enabled, Nova speaks responses aloud using high-definition neural voices:
   * **Turkish Mode**: High-clarity `tr-TR-EmelNeural`
   * **English Mode**: F.R.I.D.A.Y. Irish Neural `en-IE-EmilyNeural`
3. If an internet connection is unavailable, it automatically falls back to offline Windows SAPI voices without crashing.

### 3. Voice Commands
You can speak or type:
* `"Geçmişi oku"` / `"Read history"`: Nova will summarize and read aloud recent conversation memories.

---

## 🏛️ System Architecture

```
c:/NOVA/
├── NovaApp/                 ← C# .NET 9.0 WPF Native Desktop GUI
│   ├── MainWindow.xaml      ← Primary chat interface, live typewriter streaming & HUD
│   ├── MemoryGraphWindow    ← Interactive 2D Knowledge Graph Explorer
│   ├── SettingsWindow       ← Hardware, neural hyperparameter & data configuration
│   └── Services/            ← Low-latency asynchronous JSON-Lines IPC bridge
│
├── brain.py                 ← PyTorch Transformer + Network Morphism + uret_stream generator
├── memory.py                ← SQLite3 Dual Memory (Episodic Chats + Semantic Bilgi Ağacı)
├── body.py                  ← F.R.I.D.A.Y. Neural Voice Engine + Intent Parser + Python Sandbox
├── yetenekler.py            ← Dynamic Live Wikipedia REST API & DuckDuckGo Web Engine
├── web_server.py            ← Asynchronous HTTP & Mobile Web Dashboard
├── hardware.py              ← Multi-GPU, DirectML, CPU thread & VRAM telemetry scanner
├── gpu_setup.py             ← Adaptive hardware environment optimizer
├── nova_bridge.py           ← IPC Server coordinating C# WPF and Python backends
│
├── nova_headless_trainer/   ← Standalone Cloud / Cluster Training System
│   ├── train.py             ← FlashAttention-2 + BFloat16 Headless Training Loop
│   ├── model.py             ← Scalable DinamikNovaLM architecture
│   ├── db_manager.py        ← Priority dialogue & knowledge data loader
│   └── sync_manager.py      ← Cloud & local weights/database synchronization
│
├── baslat_cs_gui.bat        ← 1-Click Launch Desktop GUI (.NET 9 Release)
├── baslat_web.bat           ← 1-Click Launch Web & Mobile Server
├── baslat_tunnel.bat        ← 1-Click Launch Cloudflare Mobile Tunnel
├── install.bat              ← Automated Python & dependency installer
└── requirements.txt         ← Core Python dependencies
```

---

## ⚡ Quick Start & Installation

### Prerequisites
- **Operating System**: Windows 10 / 11 (64-bit) or Linux
- **Python**: Python 3.10 or higher
- **.NET SDK**: [.NET 9.0 SDK](https://dotnet.microsoft.com/download/dotnet/9.0) (for building the native GUI)
- **Audio (Optional for Voice)**: Microphone and working speaker/headset

### 1. Automated Installation
Run the installer script:
```powershell
.\install.bat
```
*Or install dependencies manually:*
```powershell
pip install -r requirements.txt
pip install edge-tts speechrecognition pyaudio
```

### 2. Launch Nova Desktop GUI
Start the desktop application with 1 click:
```powershell
.\baslat_cs_gui.bat
```

### 3. Launch Web & Mobile Interface (Optional)
```powershell
.\baslat_web.bat
```
Access via your browser at `http://localhost:8080` (or over your local Wi-Fi via your PC's IP address).

---

## ☁️ Cloud & Headless Training (Google Colab / Clusters)

If you wish to train Nova on cloud GPUs (such as NVIDIA A100 / H100):

```bash
cd nova_headless_trainer
python train.py --db nova.db --weights nova_weights.pth --batch_size 32 --continuous
```

- **Speed**: FlashAttention-2 and BFloat16 enabled automatically.
- **Model Scalability**: Models automatically expand using Network Morphism as they learn.
- **Sync Back to PC**: Once training is complete, copy `nova_weights.pth` and `nova.db` into `c:\NOVA` to immediately run the updated brain locally.

---

## 💬 In-App Commands & Shortcuts

You can type direct commands in the chat interface or use the quick action chips:

| Command | Description |
| :--- | :--- |
| `!istatistik` / `!stats` | Displays live neural network parameters, memory node count, and training steps. |
| `!wiki <topic>` | Searches Wikipedia live and stores the full article in the knowledge base. |
| `!ara <query>` | Queries DuckDuckGo / web search and summarizes findings. |
| `!hesapla <math>` | Computes mathematical equations (e.g. `2^10 + sqrt(144)`). |
| `!python <code>` | Executes Python code safely in the sandbox. |
| `!anilar [N]` | Retrieves the last `N` episodic conversation memories. |
| `!kaydet` / `!save` | Forces an immediate atomic checkpoint save of model weights. |
| `!buyut` / `!grow` | Triggers immediate neural network growth and layer expansion. |
| `!lang <tr/en>` | Switches active language between Turkish and English. |

---

## 🛠️ Hardware Compatibility

| Tier | Hardware | Acceleration Engine |
| :--- | :--- | :--- |
| **Budget / Laptop** | Quad-core CPU, 8 GB RAM | Multi-threaded CPU BLAS |
| **Standard Desktop** | Ryzen 5 5600X / Intel i5, 16 GB RAM, 4GB+ GPU | AMD Radeon (DirectML), NVIDIA GTX/RTX (CUDA) |
| **Workstation / Cloud** | NVIDIA A100 / H100 / Multi-RTX, 32GB+ RAM | FlashAttention-2 + BFloat16 Tensor Cores + PyTorch DataParallel |

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**. See the [LICENSE](LICENSE) file for details.
