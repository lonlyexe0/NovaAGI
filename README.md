<div align="right"><b>English</b> · <a href="README.tr.md">Türkçe</a></div>

<div align="center">

<img src="assets/nova_icon.svg" width="88" alt="Nova">

# Nova

**A small language model that grows itself when it gets stuck, remembers, and learns from the web.**

![Python](https://img.shields.io/badge/python-3.10+-3776AB?logo=python&logoColor=white)
![PyTorch](https://img.shields.io/badge/pytorch-2.2+-EE4C2C?logo=pytorch&logoColor=white)
![License](https://img.shields.io/badge/license-GPL--3.0-2ea44f)

</div>

> [!NOTE]
> **Archived.** *"The AI can be trained; I just don't have enough resources."*
> The architecture, growth, memory and learning loop all work. Training a model that actually talks
> from scratch needs far more compute than a home PC, so an untrained Nova produces gibberish.

## How it works

| | |
|---|---|
| 🧠 **Brain** (`brain.py`) | A Transformer that starts small. When the loss plateaus it grows: first the feed-forward neurons, then a new block, then the embedding size. Old weights are preserved (network morphism). |
| 💾 **Memory** (`memory.py`) | SQLite: conversations (episodic), learned text (semantic) and a task queue. Keyword-based retrieval (RAG). |
| 🌐 **Body** (`body.py`) | Explores Wikipedia out of curiosity, writes its own Python skills, and can optionally use the screen, voice and camera. |
| 🔁 **Loop** (`main.py`) | Crawls and trains in the background while it chats with you in the foreground. |

## Setup

```bash
git clone https://github.com/lonlyexe0/NovaAGI.git
cd NovaAGI
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cpu   # or the GPU build
pip install -r requirements.txt
python main.py
```

Other entry points: `python nova_launcher.py --term` (launcher with Hugging Face Wikipedia streaming)
and `python nova_launcher.py --gui` (Tk window).

## Settings — `ayarlar.json`

Nova is not tied to any operating system; everything is configured by hand. Edit the file and restart.

| Key | Default | Meaning |
|---|---|---|
| `cihaz` | `auto` | `auto`, `cpu`, `cuda` (NVIDIA / AMD ROCm) or `mps` (Apple). `auto` picks a GPU if there is one. |
| `cpu_thread` | `0` | CPU cores to use. `0` means all of them. |
| `batch_size` | `16` | Samples per training step. Lower it if you run out of memory. |
| `ogrenme_hizi` | `0.0003` | Learning rate. |
| `max_seq_len` | `256` | Characters the model sees at once. |
| `kayit_araligi` | `50` | Save the weights every N training steps. |
| `buyume_esigi` | `0.003` | The model grows when the loss improves by less than this ratio. |
| `agirlik_dosyasi` · `vocab_dosyasi` · `veritabani` | `nova_weights.pth` … | File paths (relative to the project folder). |

## Commands

`!yardim` lists everything. The most used ones:

```
!istatistik        model and memory status       !tara <url>       read a page and learn it
!anilar [N]        recent conversations          !yetenekler       skills written so far
!rag <query>       search memory                 !kod name|code    write a new skill
!gorev <task>      queue a task                  !kaydet · !cikis
```

## Performance

The brain and memory were rewritten. The behavior is the same, with less work:

- **~3.4× faster generation:** a KV-cache means the whole context is no longer recomputed for every new
  character (200 characters: 1.04 s → 0.31 s on CPU). The gap widens as the model grows.
- **Faster attention:** `scaled_dot_product_attention` picks the Flash or memory-efficient kernel for
  your hardware. The repetition penalty is now one tensor operation instead of a Python loop.
- **More efficient training:** only the first of 20 queued records used to be learned. Now every record
  is sampled, and each prepared batch of data is reused for several steps.
- **Correct growth:** fixed the Q/K/V weights being scrambled when the embedding grows.
- **Safe saves:** weights and vocab are written to a temporary file and swapped in one step, so an
  interrupted write can no longer corrupt them.
- **Memory:** an index on source URLs (imports no longer slow down as the database grows), SQL-side
  pre-filtering for search, batched updates and a single-query stats call.

## Files

```
main.py          terminal chat + background loop
nova_launcher.py advanced launcher with Hugging Face streaming (--term / --gui)
brain.py         the growing Transformer
memory.py        SQLite memory and RAG
body.py          crawler, skills, voice / vision / computer control
yetenekler.py    functions Nova writes for itself (hot-reloaded)
ayarlar.json     all settings
```

Platform-specific editions live on separate branches:
[`windows-part`](https://github.com/lonlyexe0/NovaAGI/tree/windows-part) (WPF UI, DirectML) and
[`claude-verison`](https://github.com/lonlyexe0/NovaAGI/tree/claude-verison) (Linux, Avalonia UI,
web/phone access).

## License

[GPL-3.0](LICENSE)
