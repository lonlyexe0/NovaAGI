<div align="right">
  <strong>Diller:</strong> 
  <a href="README.md">English</a> | <b>Türkçe</b>
</div>

# NOVA — Otonom Öğrenen AGI Prototipi

```
███╗   ██╗ ██████╗ ██╗   ██╗ █████╗
████╗  ██║██╔═══██╗██║   ██║██╔══██╗
██╔██╗ ██║██║   ██║██║   ██║███████║
██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██╗
██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║
╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝
```

## Proje Vizyonu

Nova sadece bir chatbot değildir. İki ana bileşenden oluşan **yaşayan bir organizmadır**:

1. **Üretken Beyin** — PyTorch Mini-GPT Transformer (~15M parametre)
2. **Otonom Beden** — Web Crawler + Self-Coding + Hot-Reload Yetenek Sistemi

---

## Mimari

```
nova/
├── main.py          ← Bilinç Döngüsü (2 Thread orkestratörü)
├── brain.py         ← Mini-GPT Transformer + Sürekli Eğitim
├── memory.py        ← SQLite3 Hafıza + RAG Altyapısı
├── body.py          ← Crawler + Self-Coding + Araç Motoru
├── yetenekler.py    ← Hot-reload ile büyüyen yetenek havuzu
├── requirements.txt
└── README.md
```

### Otomatik Oluşturulan Dosyalar
```
nova.db              ← SQLite veritabanı
nova_weights.pth     ← Model checkpoint (otomatik kaydedilir)
nova_vocab.json      ← Karakter sözlüğü (dinamik büyür)
nova.log             ← Sistem logları
```

---

## ⚡ Hızlı Başlangıç (Önerilen Tek Komutla Kurulum)

> [!IMPORTANT]
> **Linux kullanıcıları için tek komutla tüm sistemi kurup başlatmanın en kolay yolu:**
> ```bash
> chmod +x install.sh
> ./install.sh
> ```
> **`install.sh` scripti neler yapar?**
> 1. Sistem paketlerini (`tk`, `espeak-ng`, `python-pip` vb.) otomatik tespit edip kurar.
> 2. Tüm Python bağımlılıklarını eksiksiz yükler.
> 3. **Nova AGI'yi masaüstü uygulaması olarak kaydeder** (Masaüstü kısayolu & Başlat menüsü ikonu ekler).
> 4. Nova'yı doğrudan başlatır.

---

## Manuel Kurulum

```bash
# 1. Sanal ortam oluştur (önerilir)
python -m venv nova_env
source nova_env/bin/activate        # Linux/macOS
# nova_env\Scripts\activate         # Windows

# 2. Bağımlılıkları yükle
pip install -r requirements.txt

# 3. CUDA ile PyTorch (GPU varsa):
# pip install torch --index-url https://download.pytorch.org/whl/cu118
```

---

## Çalıştırma Alternatifleri

```bash
# 🚀 Tek Tıkla / Script ile Başlatma (Önerilen)
./install.sh
# veya
./run_nova.sh

# Arayüzlü Başlatıcı (GUI Launcher)
python nova_launcher.py

# Terminal REPL Başlatma
python main.py

# Debug modu (ayrıntılı loglar)
python main.py --debug

# Mobil/web arayüzü
python nova_launcher.py --web
# Özel port
python nova_launcher.py --web --web-port 8080

# Web taraması olmadan (sadece konuşma + eğitim)
python main.py --no-crawl

# Özel veritabanı yolu
python main.py --db /path/to/nova.db
```

---

## Model Mimarisi

| Parametre | Değer |
|-----------|-------|
| Mimari | Decoder-only Causal Transformer (GPT tarzı) |
| Toplam parametre | ~15 Milyon |
| Gömme boyutu | 384 |
| Dikkat kafası | 6 |
| Transformer katmanı | 6 |
| Feed-forward boyutu | 1536 |
| Bağlam penceresi | 256 token |
| Tokenizasyon | Karakter düzeyinde (dinamik vocab) |
| Örnekleme | Top-k (k=50) + Nucleus Top-p (p=0.92) + Tekrar Cezası |

### Özel Özellikler
- **Pre-Norm**: LayerNorm sublayer öncesinde → daha stabil eğitim
- **Weight Tying**: Embedding ↔ Output katmanı paylaşımı → az parametre, iyi genelleme
- **Label Smoothing**: 0.05 → overfitting önleme
- **AdamW + CosineAnnealingWarmRestarts**: LR yerel minimumdan kaçar

---

## Veritabanı Şeması

```sql
-- Epizodik hafıza
CREATE TABLE anilar (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    rol         TEXT NOT NULL CHECK(rol IN ('kullanici','nova','sistem')),
    icerik      TEXT NOT NULL,
    zaman       TEXT DEFAULT (datetime('now','localtime')),
    onem_skoru  REAL DEFAULT 0.5
);

-- Semantik hafıza (internetten öğrenilen)
CREATE TABLE bilgi_agaci (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    kaynak_url  TEXT,
    konu        TEXT,
    icerik      TEXT NOT NULL,
    islendi     INTEGER DEFAULT 0,   -- 0=ham, 1=eğitimde kullanıldı
    zaman       TEXT DEFAULT (datetime('now','localtime'))
);

-- Görev kuyruğu
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

## Komut Rehberi

| Komut | Açıklama |
|-------|----------|
| `!yardim` | Tüm komutları listele |
| `!istatistik` | DB, model ve eğitim durumu |
| `!tara <url>` | URL'yi tara ve öğren |
| `!yetenekler` | Mevcut yetenekleri listele |
| `!cagir hesapla(2**10)` | Yetenek çağır |
| `!kod isim\|def isim():...` | Yeni yetenek yaz & yükle |
| `!gorev TARA: <url>` | Görevi kuyruğa ekle |
| `!anilar 10` | Son 10 anıyı göster |
| `!rag <sorgu>` | Hafızadan bağlam sorgula |
| `!komut ls -la` | Shell komutu çalıştır |
| `!kaydet` | Model checkpoint'i zorla kaydet |
| `!cikis` | Güvenli kapanış |

---

## Self-Coding Örneği

Nova terminalde:
```
Sen » !kod hava_durumu|def hava_durumu(sehir: str) -> str:
    import requests
    r = requests.get(f"https://wttr.in/{sehir}?format=3")
    return r.text if r.ok else "Alınamadı"

Nova » ✓ 'hava_durumu' yeteneği sisteme eklendi.

Sen » !cagir hava_durumu(Istanbul)
Nova » Istanbul: ⛅️  +18°C
```

---

## Sürekli Öğrenme Döngüsü

```
┌─────────────────────────────────────────────────────────────┐
│  Thread 1 (Bilinçaltı, 90s aralıkla)                        │
│                                                             │
│  Wikipedia/Web  ──►  bilgi_agaci  ──►  egitim_adimi()       │
│                           ↑                                 │
│  Görev Kuyruğu  ──►  gorevi_coz()                           │
└─────────────────────────────────────────────────────────────┘
           ↕ (paylaşılan SQLite WAL modunda)
┌─────────────────────────────────────────────────────────────┐
│  Thread 2 (Bilinç, terminal REPL)                           │
│                                                             │
│  Kullanıcı  ──►  RAG  ──►  brain.uret()  ──►  Cevap        │
│                                    │                        │
│                          [EYLEM:...]  ──►  body.gorevi_coz  │
└─────────────────────────────────────────────────────────────┘

  Thread 3 (Daemon, brain.surekli_egitim_baslat())
  ─ Her 15 saniyede bir eğitilmemiş verileri çek ve eğit
```

---

## Modül Test Komutları

```bash
# Her modülü ayrı ayrı test et
python memory.py       # SQLite + RAG test
python brain.py        # Model + eğitim test (5 adım)
python body.py         # Crawler + self-coding test
python main.py         # Tam sistem
```

---

## Geliştirme Yol Haritası

- [ ] Embedding tabanlı vektör RAG (FAISS)
- [ ] Çok GPU desteği (DataParallel)
- [ ] LoRA fine-tuning adaptörü
- [ ] REST API arayüzü (FastAPI)
- [ ] Görsel hafıza (image embedding)
- [ ] Çoklu ajan iletişimi

---

## Lisans

Bu proje GNU Genel Kamu Lisansı v3.0 (GPL-3.0) ile lisanslanmıştır - detaylar için [LICENSE](LICENSE) dosyasına bakabilirsiniz.

---

*Nova, her konuşmayla, her web sayfasıyla, her yazdığı kodla büyümeye devam eder.*
