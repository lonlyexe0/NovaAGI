# 🧠 Nova Headless Trainer & Spark Pipeline

Bu klasör, **NOVA AGI** sinir ağı mimarisinin kullanıcı arayüzü (C# WPF), ses sistemleri (TTS/STT), IPC köprüleri ve masaüstü bağımlılıklarından **tamamen arındırılmış** saf eğitim ve büyük veri hazırlama modülüdür.

Bu sistem bağımsız bir sunucuda, kümede (cluster) veya yerel terminalde çalıştırılabilir. **Eğitim tamamlandıktan sonra güncellenmiş `nova.db` ve `nova_weights.pth` dosyaları ana NOVA uygulamasına geri aktarılabilir.**

---

## 🏛️ Dosya Yapısı

```
nova_headless_trainer/
├── config.py               ← Model hiperparametreleri ve cihaz (GPU/DirectML/CPU) yapılandırması
├── model.py                ← Dinamik Transformer mimarisi ve sıfır kayıpla büyüme (Network Morphism)
├── tokenizer.py            ← Dinamik karakter sözlüğü ve token dönüştürücü
├── db_manager.py           ← SQLite nova.db okuma, toplu veri yazma ve durum takip yöneticisi
├── train.py                ← Saf PyTorch yüksek performanslı terminal eğitim motoru
├── spark_data_pipeline.py  ← Apache Spark ile dağıtık veri temizleme, filtreleme ve DB'ye yazma
├── sync_manager.py         ← Ana NOVA ile DB ve ağırlık senkronizasyon/yedekleme aracı
├── requirements.txt        ← Gerekli minimum Python kütüphaneleri
└── README.md               ← Kullanım kılavuzu (bu dosya)
```

---

## 🚀 4 Adımda İş Akışı (Spark ETL → Headless Eğitim → DB Geri Alma)

### Adım 1: Mevcut Veritabanını ve Ağırlıkları Çekin (PULL)
Eğer ana NOVA projesindeki mevcut konuşma ve hafıza veritabanını kullanmak istiyorsanız:

```bash
python sync_manager.py --pull
```
*(Bu komut `c:\NOVA` altındaki `nova.db`, `nova_weights.pth` ve `nova_vocab.json` dosyalarını bu klasöre güvenle kopyalar).*

---

### Adım 2: Apache Spark ile Büyük Veriyi Hazırlayın (ETL)
Apache Spark [Quick Start](https://spark.apache.org/docs/latest/quick-start.html) mimarisiyle metinleri temizleyin, filtreleyin ve `nova.db` içindeki `bilgi_agaci` tablosuna (`islendi=0` olarak) aktarın:

**Örnek 1: Ham Metin Dosyaları ile:**
```bash
python spark_data_pipeline.py --input "veriler/*.txt" --format text --db nova.db --topic "Genel Bilim"
```

**Örnek 2: Parquet / JSON / CSV Datasetleri ile:**
```bash
python spark_data_pipeline.py --input "wikipedia_dataset.parquet" --format parquet --db nova.db --topic "Wikipedia"
```

**Örnek 3: Hızlı Demo Testi (Spark sözdizimini doğrulamak için):**
```bash
python spark_data_pipeline.py --demo
```

---

### Adım 3: Headless Antrenörü Başlatın (Eğitim)
Veritabanındaki eğitilmemiş verileri GPU/DirectML/CPU ile eğitin:

```bash
# Otomatik en iyi donanım (CUDA / DirectML / CPU) ile eğitim
python train.py --db nova.db --batch_size 32

# Sürekli mod (Spark veya dış kaynaklardan DB'ye yeni veri geldikçe durmadan eğitsin)
python train.py --db nova.db --continuous

# Belirli bir adım sayısına kadar eğit
python train.py --db nova.db --max_steps 500
```

> 💡 **Network Morphism**: Eğitim sırasında model plato (takılma) algılarsa, otomatik olarak Feed-Forward nöronlarını genişletir, yeni bloklar ekler ve embedding boyutunu sıfır kayıpla büyütür.

---

### Adım 4: Eğitilen DB'yi ve Ağırlıkları Ana Sisteme Geri Alın (PUSH)
Eğitim tamamlandıktan sonra, eğitilmiş veritabanını ve ağırlıkları ana NOVA sistemine geri aktarın:

```bash
python sync_manager.py --push
```

*Not: `sync_manager.py`, ana sistemdeki eski dosyaların otomatik olarak `.bak` uzantılı zaman damgalı yedeğini alır.*

Durumu ve iki sistem arasındaki veri sayılarını istediğiniz an görmek için:
```bash
python sync_manager.py --status
```
