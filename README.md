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
[![License](https://img.shields.io/badge/License-GPL--3.0-green?style=for-the-badge)](LICENSE)

```
███╗   ██╗ ██████╗ ██╗   ██╗ █████╗     █████╗  ██████╗ ██╗
████╗  ██║██╔═══██╗██║   ██║██╔══██╗   ██╔══██╗██╔════╝ ██║
██╔██╗ ██║██║   ██║██║   ██║███████║   ███████║██║  ███╗██║
██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██║   ██╔══██║██║   ██║██║
██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║   ██║  ██║╚██████╔╝██║
╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝
```

*Nova is an autonomous, self-expanding artificial general intelligence prototype featuring continuous background learning, dynamic network morphism, real-time live web grounding, and an ultra-modern native desktop experience.*

</div>

---

## 🚀 Key Flagship Features

### 🌟 1. Native C# .NET 9 WPF Desktop Interface
- **Ultra-Responsive GUI**: Built with high-performance C# WPF running on .NET 9.0 with asynchronous inter-process communication (IPC) to the PyTorch neural backend.
- **Bilingual On-The-Fly Localization**: Instant real-time UI switching between **English** and **Turkish** without restarting.
- **Hardware Telemetry HUD**: Real-time monitoring of VRAM usage, loss curves, training steps, and parameter growth count.

### 🧠 2. Dynamically Growing Neural Architecture (Network Morphism)
- **Zero-Loss Growth**: When training loss reaches a plateau, the neural network autonomously expands its layers, hidden embedding dimensions, and Feed-Forward (FF) neurons without forgetting past weights.
- **Checkpoint Persistence**: Neural model architecture and weights are saved atomically with Windows lock protection, perfectly preserving grown parameter counts across restarts.

### 🕸️ 3. Interactive Visual Knowledge & Memory Graph Explorer
- **2D Dynamic Cluster Graph**: Interactive force-directed visualization of episodic memories (user conversations) and semantic knowledge (Wikipedia nodes).
- **Live Background Auto-Refresh**: Automatically detects newly ingested concepts and renders them in real time without UI flicker.
- **Instant Search & Topic Downloader**: Download any Wikipedia article straight into the knowledge graph with one click.

### ⚡ 4. Hardware Adaptive Acceleration & Multi-GPU
- **Universal GPU Detection**: Tailored support for **AMD Radeon** (DirectML), **NVIDIA GeForce / RTX** (CUDA), **ROCm**, and multi-core CPU fallback.
- **Multi-GPU Parallelism**: Distributes training across multiple graphics cards automatically with `DataParallel`.

### 🌐 5. Real-Time Online Grounding & Autonomous Curiosity Engine
- **Instant Wikipedia & Web Search**: Factual questions (`"... is what?"`, `"tell me about ..."`, etc.) trigger real-time Wikipedia REST API lookups, citing verified facts and storing them into memory.
- **Autonomous Background Explorer**: Periodically discovers and learns new scientific, historical, and technological concepts while idle.
- **Bulk Dataset Ingestion**: Stream hundreds or thousands of official Wikipedia articles from the Hugging Face Hub directly into `nova.db`.

### 🎙️ 6. Speech & Voice Interface
- **Voice Dictation (STT)**: Speak directly to Nova using native microphone speech recognition.
- **Text-to-Speech (TTS)**: Integrated speech synthesizer for voice responses.

### 📦 7. Model Export & Publishing
- **Universal ONNX Format**: Export your trained neural weights to `.onnx` for deployment in browser or edge runtimes.
- **Portable ZIP Packages**: Create ready-to-share weight checkpoints.

---

## 🏛️ System Architecture

```
c:/NOVA/
├── NovaApp/                 ← C# .NET 9.0 WPF Native Desktop GUI
│   ├── MainWindow.xaml      ← Primary chat interface & hardware HUD
│   ├── MemoryGraphWindow    ← Interactive 2D Knowledge Graph Explorer
│   ├── SettingsWindow       ← Hardware, neural hyperparameter & data configuration
│   └── Services/            ← Low-latency asynchronous JSON-Lines IPC bridge
│
├── brain.py                 ← PyTorch Transformer + Network Morphism + Continuous Learning
├── memory.py                ← SQLite3 Dual Memory (Episodic Chats + Semantic Bilgi Ağacı)
├── body.py                  ← Natural Language Intent Parser + OS Tools + Math & Python Sandbox
├── yetenekler.py            ← Dynamic Live Wikipedia REST API & DuckDuckGo Web Engine
├── hugging_loader.py        ← Autonomous Curiosity Engine + HuggingFace Bulk Ingestion
├── hardware.py              ← Multi-GPU, DirectML, CPU thread & VRAM telemetry scanner
├── gpu_setup.py             ← Adaptive hardware environment optimizer
├── nova_bridge.py           ← IPC Server coordinating C# WPF and Python backends
│
├── baslat_cs_gui.bat        ← 1-Click Launch Script (Recommended)
├── install.bat              ← 1-Click Environment Setup Script
└── requirements.txt         ← Python dependencies
```

---

## ⚡ Quick Start & Installation

### Prerequisites
- **Operating System**: Windows 10 / 11 (64-bit) or Linux
- **Python**: Python 3.10 or higher
- **.NET SDK**: [.NET 9.0 SDK](https://dotnet.microsoft.com/download/dotnet/9.0) (for compiling the WPF app)

### 1. Installation
Run the automated installer script:
```powershell
.\install.bat
```
*Or install dependencies manually:*
```powershell
pip install -r requirements.txt
```

### 2. Launch the Application
Start the native desktop application with 1 click:
```powershell
.\baslat_cs_gui.bat
```
*Or via .NET CLI:*
```powershell
dotnet run --project NovaApp/NovaApp.csproj
```

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

## 🛠️ Hardware Requirements

| Tier | Specification | Supported Acceleration |
| :--- | :--- | :--- |
| **Minimum** | Dual-core CPU, 4 GB RAM | CPU (Multi-threaded BLAS) |
| **Recommended** | 6-Core CPU (e.g. Ryzen 5600X), 16 GB RAM, 4GB+ GPU | AMD Radeon (DirectML), NVIDIA GTX/RTX (CUDA) |
| **High Performance** | Multi-GPU setup, 32 GB RAM | PyTorch DataParallel across all detected GPUs |

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**. See the [LICENSE](LICENSE) file for details.
