<div align="right">
  <strong>Languages:</strong> 
  <b>English</b> | <a href="README.tr.md">Türkçe</a>
</div>

# NOVA — Autonomous Learning AGI Prototype

> [!IMPORTANT]
> ⚠️ **Note:** I couldn't manage to build the standalone EXE properly; feel free to experiment and try it yourself however you like!

```
███╗   ██╗ ██████╗ ██╗   ██╗ █████╗
████╗  ██║██╔═══██╗██║   ██║██╔══██╗
██╔██╗ ██║██║   ██║██║   ██║███████║
██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██║
██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║
╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝
```

## Project Vision

Nova is not just a chatbot. It is a **living organism** composed of two core components:

1. **Generative Brain** — PyTorch Mini-GPT Transformer (~15M parameters)
2. **Autonomous Body** — Web Crawler + Self-Coding + Hot-Reload Skill System

---

## Architecture

```
nova/
├── main.py          ← Consciousness Loop (2 Thread Orchestrator)
├── brain.py         ← Mini-GPT Transformer + Continuous Training
├── memory.py        ← SQLite3 Memory + RAG Infrastructure
├── body.py          ← Crawler + Self-Coding + Tool Engine
├── yetenekler.py    ← Dynamic Hot-reload Skill Pool
├── requirements.txt
└── README.md
```

### Auto-Generated Files
```
nova.db              ← SQLite database
nova_weights.pth     ← Model checkpoint (auto-saved)
nova_vocab.json      ← Character vocabulary (dynamically expands)
nova.log             ← System logs
```

---

## Installation

```bash
# 1. Create virtual environment (recommended)
python -m venv nova_env
source nova_env/bin/activate        # Linux/macOS
# nova_env\Scripts\activate         # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. PyTorch with CUDA (if GPU available):
# pip install torch --index-url https://download.pytorch.org/whl/cu118
```

---

## Running

```bash
# Terminal startup
python main.py

# GUI Launcher startup
python nova_launcher.py

# Python 3.10 Launcher startup
py -3.10 nova_launcher.py

# Debug mode (detailed logs)
python main.py --debug

# Without web crawling (chat + training only)
python main.py --no-crawl

# Custom database path
python main.py --db /path/to/nova.db
```

---

## Model Architecture

| Parameter | Value |
|-----------|-------|
| Architecture | Decoder-only Causal Transformer (GPT-style) |
| Total Parameters | ~15 Million |
| Embedding Size | 384 |
| Attention Heads | 6 |
| Transformer Layers | 6 |
| Feed-forward Size | 1536 |
| Context Window | 256 tokens |
| Tokenization | Character-level (dynamic vocabulary) |
| Sampling | Top-k (k=50) + Nucleus Top-p (p=0.92) + Repetition Penalty |

### Key Features
- **Pre-Norm**: LayerNorm prior to sublayers → stable training
- **Weight Tying**: Shared Embedding ↔ Output Layer → parameter efficiency & generalization
- **Label Smoothing**: 0.05 → prevents overfitting
- **AdamW + CosineAnnealingWarmRestarts**: Learning rate escapes local minima

---

## Database Schema

```sql
-- Episodic Memory
CREATE TABLE anilar (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    rol         TEXT NOT NULL CHECK(rol IN ('kullanici','nova','sistem')),
    icerik      TEXT NOT NULL,
    zaman       TEXT DEFAULT (datetime('now','localtime')),
    onem_skoru  REAL DEFAULT 0.5
);

-- Semantic Memory (learned from internet)
CREATE TABLE bilgi_agaci (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    kaynak_url  TEXT,
    konu        TEXT,
    icerik      TEXT NOT NULL,
    islendi     INTEGER DEFAULT 0,   -- 0=raw, 1=used in training
    zaman       TEXT DEFAULT (datetime('now','localtime'))
);

-- Task Queue
CREATE TABLE gorevler (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tanim       TEXT NOT NULL,
    durum       TEXT DEFAULT 'bekliyor',
    oncelik     INTEGER DEFAULT 5,
    olusturulma TEXT DEFAULT (datetime('now','localtime')),
    tamamlanma  TEXT
);
```

---

## Command Reference

| Command | Description |
|---------|-------------|
| `!yardim` | List all commands |
| `!istatistik` | Display DB, model, and training status |
| `!tara <url>` | Crawl URL and learn |
| `!yetenekler` | List available skills |
| `!cagir calculate(2**10)` | Execute a skill |
| `!kod name\|def name():...` | Write & load a new skill |
| `!gorev TARA: <url>` | Add a task to queue |
| `!anilar 10` | Show last 10 memory entries |
| `!rag <query>` | Query context from memory |
| `!komut ls -la` | Execute shell command |
| `!kaydet` | Force model checkpoint save |
| `!cikis` | Safe shutdown |

---

## Self-Coding Example

Nova terminal interaction:
```
You » !kod weather|def weather(city: str) -> str:
    import requests
    r = requests.get(f"https://wttr.in/{city}?format=3")
    return r.text if r.ok else "Failed"

Nova » ✓ Skill 'weather' added to the system.

You » !cagir weather(Istanbul)
Nova » Istanbul: ⛅️  +18°C
```

---

## Continuous Learning Loop

```
┌─────────────────────────────────────────────────────────────┐
│  Thread 1 (Subconscious, 90s interval)                     │
│                                                             │
│  Wikipedia/Web  ──►  knowledge_tree  ──►  train_step()      │
│                           ↑                                 │
│  Task Queue     ──►  solve_task()                           │
└─────────────────────────────────────────────────────────────┘
           ↕ (shared SQLite WAL mode)
┌─────────────────────────────────────────────────────────────┐
│  Thread 2 (Consciousness, terminal REPL)                    │
│                                                             │
│  User  ──►  RAG  ──►  brain.generate()  ──►  Response       │
│                                │                            │
│                      [ACTION:...]  ──►  body.solve_task     │
└─────────────────────────────────────────────────────────────┘

  Thread 3 (Daemon, brain.start_continuous_training())
  ─ Fetch untrained data every 15 seconds and train
```

---

## Module Test Commands

```bash
# Test each module individually
python memory.py       # SQLite + RAG test
python brain.py        # Model + training test (5 steps)
python body.py         # Crawler + self-coding test
python main.py         # Full system test
```

---

## Development Roadmap

- [ ] Embedding-based vector RAG (FAISS)
- [ ] Multi-GPU support (DataParallel)
- [ ] LoRA fine-tuning adapter
- [ ] REST API interface (FastAPI)
- [ ] Visual memory (image embedding)
- [ ] Multi-agent communication

---

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0) - see the [LICENSE](LICENSE) file for details.

---

*Nova continues to grow with every conversation, every webpage, and every line of code it writes.*
