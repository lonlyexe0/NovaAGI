# Nova AGI on Linux

Nova AGI is a local neural assistant with a Python/PyTorch core, SQLite memory, live telemetry, streaming chat, web access, and a cross-platform Avalonia desktop client.

This document covers the Linux build. The original Windows WPF client remains under `NovaApp/`; the Linux client lives under `NovaApp.Avalonia/`.

## What Works on Linux

- Avalonia desktop client with the Nova dark gradient theme
- Python bridge over JSON Lines
- Streaming chat responses
- Right-aligned user messages and left-aligned Nova messages
- Live training, model, memory, CPU, and GPU telemetry
- SQLite episodic and semantic memory
- CUDA, ROCm, or CPU fallback through PyTorch
- Local web dashboard on port `8080`
- Settings for language, training, device, batch size, learning rate, web server, and growth threshold
- Memory graph window and Wikipedia ingestion
- English and Turkish UI settings

Desktop automation is optional. On Linux Wayland sessions, screen-control libraries may not have permission to access the display; Nova continues running with that capability disabled.

## Requirements

- Linux x86_64
- Python 3.10 or newer
- .NET 8 SDK or newer
- 6 GB RAM minimum for the compact local model
- Optional: NVIDIA CUDA, AMD ROCm, microphone, and audio output

The launcher automatically detects a user-local .NET installation at `~/.dotnet`.

## Installation

Create a virtual environment and install the Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

For optional speech support, install the system audio packages required by your distribution, then install:

```bash
python -m pip install edge-tts SpeechRecognition pyttsx3
```

For microphone input, PyAudio may require PortAudio development headers. On Arch-based systems:

```bash
sudo pacman -S portaudio
python -m pip install pyaudio
```

Install the .NET SDK if it is not already available. The launcher can also use a user-local SDK at `~/.dotnet`.

## Start the Desktop Client

From the repository root:

```bash
chmod +x baslat_avalonia.sh
./baslat_avalonia.sh
```

The launcher builds and starts `NovaApp.Avalonia`, then starts the Python Nova bridge automatically.

The first launch may take longer because PyTorch initializes the model and Nova creates its SQLite database.

## Start the Web Client

Start the Python web server directly:

```bash
source .venv/bin/activate
python3 web_server.py
```

Open:

```text
http://localhost:8080
```

To connect from another device on the same network, use the local IP shown by Nova telemetry.

## Start the Terminal Client

```bash
source .venv/bin/activate
python3 nova_launcher.py --term
```

Useful options:

```bash
python3 nova_launcher.py --term --debug
python3 nova_launcher.py --term --no-crawl
```

## GPU Selection

Nova chooses the best available backend in this order:

1. CUDA or ROCm through `torch.cuda`
2. CPU fallback with optimized thread counts

Check the detected hardware with:

```bash
source .venv/bin/activate
python3 gpu_setup.py
```

DirectML is Windows-only and is not used by the Linux client.

## Configuration

Settings are stored in `.nova_config.json` when the project directory is writable. If it is not writable, Nova uses a user data directory.

The desktop Settings window can change:

- Language: English or Turkish
- Continuous background training
- CUDA/ROCm/CPU preference
- Multi-GPU preference
- CPU worker count
- Learning rate and batch size
- Automatic growth threshold
- Local web server and port

Changes are sent to the running Python bridge and persisted for the next launch.

## Troubleshooting

### `dotnet: command not found`

Install .NET 8 or add the user-local SDK to the current shell:

```bash
export PATH="$HOME/.dotnet:$PATH"
./baslat_avalonia.sh
```

The launcher already adds this path automatically when `$HOME/.dotnet/dotnet` exists.

### The window says the Nova engine could not connect

Run the bridge directly to inspect startup logs:

```bash
python3 nova_bridge.py
```

The bridge must emit a line containing:

```json
{"type": "ready", "version": "3.5"}
```

Press `Ctrl+C` to stop the direct test.

### Wayland display permission warning

A warning about `pyautogui` or X11 authorization affects optional screen automation only. Chat, memory, model inference, training, telemetry, and the web client can continue without it.

### Slow first response

The compact model is initialized during bridge startup. CPU-only systems may need more time for the first response. Disable continuous training from Settings if the system is resource constrained.

## Project Layout

```text
NovaAGI-windows-part/
├── NovaApp.Avalonia/       # Linux desktop client
├── NovaApp/                # Original Windows WPF client and shared C# models/bridge
├── nova_bridge.py          # Python-to-desktop JSON Lines server
├── brain.py                # PyTorch model and training loop
├── memory.py               # SQLite memory manager
├── body.py                 # Voice, vision, and optional desktop automation
├── web_server.py           # Local web dashboard
├── nova_headless_trainer/  # Headless training tools
├── requirements.txt        # Python dependencies
└── baslat_avalonia.sh      # Linux launcher
```

## Validation

The Linux client currently builds with:

```text
dotnet build NovaApp.Avalonia/NovaApp.Avalonia.csproj
Build succeeded.
0 Warning(s)
0 Error(s)
```

## License

Nova AGI is distributed under the GNU General Public License v3.0. See [LICENSE](LICENSE).
