<div align="right"><a href="README.md">English</a> · <b>Türkçe</b></div>

<div align="center">

<img src="assets/nova_icon.svg" width="88" alt="Nova">

# Nova

**Takıldığında kendi kendine büyüyen, hafızası olan ve internetten öğrenen küçük bir dil modeli.**

![Python](https://img.shields.io/badge/python-3.10+-3776AB?logo=python&logoColor=white)
![PyTorch](https://img.shields.io/badge/pytorch-2.2+-EE4C2C?logo=pytorch&logoColor=white)
![Lisans](https://img.shields.io/badge/lisans-GPL--3.0-2ea44f)

</div>

> [!NOTE]
> **Proje rafa kaldırıldı.** *"Yapay zeka eğitilebilir, sadece elimde yeterince kaynak yok."*
> Mimari, büyüme, hafıza ve öğrenme döngüsü çalışıyor. Ama sıfırdan anlamlı konuşan bir model
> eğitmek bir ev bilgisayarının çok ötesinde işlem gücü ister; eğitilmemiş model anlamsız metin üretir.

## Nasıl çalışır

| | |
|---|---|
| 🧠 **Beyin** (`brain.py`) | Küçük başlayan bir Transformer. Loss durduğunda sırayla FF nöronlarını, yeni bir bloğu ve embedding boyutunu büyütür. Eski ağırlıklar korunur (network morphism). |
| 💾 **Hafıza** (`memory.py`) | SQLite: konuşmalar (epizodik), öğrenilen metinler (semantik) ve görev kuyruğu. Anahtar kelimeyle bağlam getirir (RAG). |
| 🌐 **Beden** (`body.py`) | Wikipedia'yı merakla gezer, kendine Python yetenekleri yazar, isteğe bağlı olarak ekran, ses ve kamerayı kullanır. |
| 🔁 **Döngü** (`main.py`) | Arka planda sürekli tarar ve eğitir; önde seninle sohbet eder. |

## Kurulum

```bash
git clone https://github.com/lonlyexe0/NovaAGI.git
cd NovaAGI
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cpu   # veya GPU sürümü
pip install -r requirements.txt
python main.py
```

Başka yollar: `python nova_launcher.py --term` (Hugging Face Wikipedia akışlı başlatıcı),
`python nova_launcher.py --gui` (Tk penceresi).

## Ayarlar — `ayarlar.json`

Nova hiçbir işletim sistemine bağlı değildir; her şey elle ayarlanır. Dosyayı düzenleyip programı
yeniden başlatın.

| Anahtar | Varsayılan | Anlamı |
|---|---|---|
| `cihaz` | `auto` | `auto`, `cpu`, `cuda` (NVIDIA / AMD ROCm) veya `mps` (Apple). `auto`: varsa GPU. |
| `cpu_thread` | `0` | Kullanılacak işlemci çekirdeği sayısı. `0` = hepsi. |
| `batch_size` | `16` | Tek eğitim adımındaki örnek sayısı. Bellek yetmezse düşürün. |
| `ogrenme_hizi` | `0.0003` | Öğrenme hızı. |
| `max_seq_len` | `256` | Modelin bir seferde gördüğü karakter sayısı. |
| `kayit_araligi` | `50` | Kaç eğitim adımında bir ağırlıkların kaydedileceği. |
| `buyume_esigi` | `0.003` | Loss bu orandan az düşerse model büyür. |
| `agirlik_dosyasi` · `vocab_dosyasi` · `veritabani` | `nova_weights.pth` … | Dosya yolları (proje klasörüne göre). |

## Komutlar

`!yardim` hepsini listeler. En sık kullanılanlar:

```
!istatistik        model ve hafıza durumu        !tara <url>       sayfayı oku ve öğren
!anilar [N]        son konuşmalar                !yetenekler       yazılmış yetenekler
!rag <sorgu>       hafızada ara                  !kod isim|kod     yeni yetenek yaz
!gorev <tanım>     görev kuyruğuna ekle          !kaydet · !cikis
```

## Performans

Beyin ve hafıza yeniden yazıldı; davranış aynı, iş daha az:

- **~3.4× hızlı üretim:** KV-cache sayesinde her yeni karakterde tüm bağlam yeniden hesaplanmıyor
  (200 karakter: 1.04 sn → 0.31 sn, CPU). Model büyüdükçe fark artar.
- **Hızlı dikkat katmanı:** `scaled_dot_product_attention` donanıma göre Flash veya bellek-verimli
  çekirdeği seçer. Tekrar cezası artık Python döngüsü yerine tek tensör işlemi.
- **Daha verimli eğitim:** Eskiden kuyruktaki 20 kayıttan yalnızca ilki öğreniliyordu. Artık hepsinden
  örnek alınıyor ve hazırlanan veri birkaç adımda kullanılıyor.
- **Doğru büyüme:** Embedding büyürken Q/K/V ağırlıklarının karışması düzeltildi.
- **Güvenli kayıt:** Ağırlık ve vocab dosyaları geçici dosyaya yazılıp tek hamlede değiştiriliyor;
  yazma yarıda kesilirse eski dosya bozulmuyor.
- **Hafıza:** Kaynak URL indeksi (içe aktarma büyüdükçe yavaşlamıyor), SQL içinde ön filtreli arama,
  toplu güncelleme ve tek sorguluk istatistik.

## Dosyalar

```
main.py          terminal sohbeti + arka plan döngüsü
nova_launcher.py Hugging Face akışlı gelişmiş başlatıcı (--term / --gui)
brain.py         büyüyen Transformer
memory.py        SQLite hafıza ve RAG
body.py          tarayıcı, yetenekler, ses / görüntü / bilgisayar kontrolü
yetenekler.py    Nova'nın kendi yazdığı fonksiyonlar (canlı yüklenir)
ayarlar.json     tüm ayarlar
```

Platforma özel sürümler ayrı dallarda: [`windows-part`](https://github.com/lonlyexe0/NovaAGI/tree/windows-part)
(WPF arayüz, DirectML) ve [`claude-verison`](https://github.com/lonlyexe0/NovaAGI/tree/claude-verison)
(Linux, Avalonia arayüz, web/telefon erişimi).

## Lisans

[GPL-3.0](LICENSE)
