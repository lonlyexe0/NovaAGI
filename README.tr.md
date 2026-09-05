<div align="right">
  <strong>Diller:</strong> 
  <a href="README.md">English</a> | <b>Türkçe</b>
</div>

<div align="center">

# 🌟 NOVA AGI v3.5
### *Otonom Büyüyen Sinirsel Yapay Zeka & Bilinç Mimarisi*

[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-blue?style=for-the-badge&logo=windows)](https://github.com/lonlyexe0/NovaAGI)
[![Runtime](https://img.shields.io/badge/.NET-9.0%20WPF-purple?style=for-the-badge&logo=dotnet)](https://dotnet.microsoft.com/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-yellow?style=for-the-badge&logo=python)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-DirectML%20%7C%20CUDA-red?style=for-the-badge&logo=pytorch)](https://pytorch.org/)
[![FlashAttention](https://img.shields.io/badge/FlashAttention-2%20Aktif-orange?style=for-the-badge)](https://pytorch.org/)
[![Ses Motoru](https://img.shields.io/badge/Ses-F.R.I.D.A.Y.%20Nöral%20TTS-brightgreen?style=for-the-badge)](https://github.com/rany2/edge-tts)
[![Lisans](https://img.shields.io/badge/Lisans-GPL--3.0-green?style=for-the-badge)](LICENSE)

```
███╗   ██╗ ██████╗ ██╗   ██╗ █████╗     █████╗  ██████╗ ██╗
████╗  ██║██╔═══██╗██║   ██║██╔══██╗   ██╔══██╗██╔════╝ ██║
██╔██╗ ██║██║   ██║██║   ██║███████║   ███████║██║  ███╗██║
██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██║   ██╔══██║██║   ██║██║
██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║   ██║  ██║╚██████╔╝██║
╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝
```

*Nova; dinamik network morphism ile kendi sinir ağını büyüten, F.R.I.D.A.Y. nöral ses teknolojisiyle konuşup dinleyebilen, ChatGPT tarzı harf harf canlı daktilo akışı sunan ve ultra modern C# .NET 9 WPF masaüstü arayüzüne sahip bağımsız bir yapay genel zeka (AGI) sistemidir.*

</div>

---

## 🚀 Öne Çıkan Özellikler

### 🌟 1. Yerel C# .NET 9.0 WPF Arayüzü & Canlı Daktilo Akışı (Streaming)
- **ChatGPT Tarzı Canlı Akış**: Cevabın tamamlanmasını 15 saniye beklemek yok! Sinir ağının ürettiği her harf milisaniyesinde ekrana dökülür (`chat_chunk`). Akıcı daktilo efektiyle ilk andan itibaren yanıtı okuyabilirsiniz.
- **Yüksek Performanslı Masaüstü**: .NET 9.0 WPF ve asenkron çift yönlü IPC köprüsü ile sıfır donma, anlık arayüz tepkisi.
- **Canlı Çift Dilli Arayüz**: Yeniden başlatmaya gerek kalmadan **Türkçe** ve **İngilizce** arasında anında geçiş.
- **Donanım & Telemetri HUD**: Ekran kartı VRAM kullanımı, anlık loss grafiği, eğitim adımları ve parametre büyüme sayısının canlı takibi.

### 🎙️ 2. F.R.I.D.A.Y. Nöral Ses Motoru (Konuşma & Dinleme)
- **Nöral Seslendirme (TTS)**: Marvel evrenindeki F.R.I.D.A.Y. yapay zekasından ilham alan, yüksek kaliteli Microsoft Edge Neural TTS entegrasyonu (İrlanda aksanlı İngilizce ve doğal Türkçe Emel Neural). İnternet kesilirse otomatik Windows SAPI sesine geçer.
- **Sesle Yazma (STT)**: Mikrofon butonuna basarak doğrudan sesle soru sorma ve komut verme (gürültü filtreli dinamik eşikli ses tanıma).
- **Sesli Komutlar**: *"Geçmişi oku"* dediğinizde Nova son sohbet geçmişini özetleyip sesli olarak okur.
- **Tek Tıkla Ses Kontrolü**: Mesaj kutusunun yanındaki mikrofon ve hoparlör simgeleriyle sesli giriş ve çıkışı tek tıkla açıp kapatabilme.

### 🧠 3. Kendi Kendine Büyüyen Sinir Ağı (Network Morphism)
- **Kayıpsız Büyüme (Zero-Loss Growth)**: Eğitim loss değeri platoya girdiğinde sinir ağı geçmiş bilgilerini unutmadan katmanlarını, embedding boyutunu ve Feed-Forward nöronlarını otonom olarak genişletir.
- **400M'den 1.4 Milyar+ Parametreye**: 32 katmandan 36+ katmana, 4.096 nörondan 13.440 nörona kadar kendi kendini büyütebilen devrimsel mimari.
- **Atomik Kalıcı Kayıt**: Model mimarisi ve ağırlıkları Windows kilit korumasıyla kaydedilir; uygulama yeniden açıldığında büyütülen boyutlar eksiksiz korunur.

### ⚡ 4. Bağımsız Bulut & Küme Eğitimi (`nova_headless_trainer`)
- **FlashAttention-2 & BFloat16**: `F.scaled_dot_product_attention` ile %70 VRAM tasarrufu ve 3 kat hızlanma. NVIDIA A100/H100 ve RTX Tensor Core'ları üzerinde karma hassasiyetli (Mixed Precision) eğitim.
- **Büyük Veri Havuzu**: 600.000'den fazla kayıt; Vikipedi ansiklopedisi, CodeAlpaca yazılım görevleri, Python kod talimatları ve Türkçe günlük diyalog veri setleri hazır entegre.
- **Çoklu GPU Desteği**: PyTorch `DataParallel` ile birden fazla ekran kartına otomatik iş dağıtımı.
- **AMD DirectML Desteği**: AMD Radeon ekran kartları için özel sıfır CPU-fallback `DirectMLAdamW` optimizer'ı.

### 🕸️ 5. İnteraktif 2D Bilgi & Hafıza Grafiği Gezgini
- **2 Boyutlu Dinamik Ağ**: Kullanıcı sohbetlerinin (epizodik anılar) ve Wikipedia makalelerinin (semantik bilgiler) kümelenmiş etkileşimli görselleştirmesi.
- **Canlı Otomatik Yenileme**: Arka planda yeni bir bilgi öğrenildiğinde grafiği titreşimsiz olarak anında günceller.
- **Anında Madde İndirici**: İstediğiniz konuyu yazıp tek tıkla doğrudan Wikipedia'dan çekerek grafiğe ekleme imkanı.

### 🌐 6. Web Sunucusu & Cloudflare ile Uzaktan Erişim
- **Mobil & Web Arayüzü**: 8080/9090 portunda çalışan modern web gösterge paneli (`baslat_web.bat`).
- **Cloudflare Tüneli**: Tek tıkla güvenli genel bağlantı oluşturarak (`baslat_tunnel.bat`) evde değilken cep telefonunuzdan veya tabletinizden Nova ile sohbet edebilme.

---

## 🎙️ Ses Özellikleri Nasıl Kullanılır?

Nova, kutudan çıktığı anda gelişmiş ses yetenekleriyle birlikte gelir:

### 1. Nova ile Sesli Konuşma (Mikrofon / STT)
1. Masaüstü uygulamasında (`NovaAGI.exe`), mesaj yazma kutusunun solundaki **Mikrofon (🎤)** simgesine tıklayın.
2. Buton parladığında mikrofonunuza doğru konuşun.
3. Nova sesinizi metne dönüştürerek doğrudan sinir ağına iletir ve cevap üretir.

### 2. Nova'nın Sesini Dinleme (Nöral TTS)
1. Gönder butonunun yanındaki **Hoparlör (🔊)** simgesine tıklayarak sesli okumayı açıp kapatabilirsiniz.
2. Açık olduğunda Nova tüm yanıtları insan doğallığında seslendirir:
   * **Türkçe Modunda**: `tr-TR-EmelNeural`
   * **İngilizce Modunda**: F.R.I.D.A.Y. İrlanda aksanı `en-IE-EmilyNeural`
3. İnternet bağlantısı olmasa bile sistem çökmez; çevrimdışı Windows yerel sesine (SAPI) otomatik geçiş yapar.

### 3. Sesli Özel Komutlar
* *"Geçmişi oku"* veya *"Sohbet geçmişini oku"*: Nova son konuşmalarınızı özetleyerek baştan sona sesli olarak okur.

---

## 🏛️ Sistem Mimarisi

```
c:/NOVA/
├── NovaApp/                 ← C# .NET 9.0 WPF Masaüstü Uygulaması
│   ├── MainWindow.xaml      ← Ana sohbet paneli, canlı daktilo akışı & telemetri HUD
│   ├── MemoryGraphWindow    ← İnteraktif 2D Hafıza Grafiği Gezgini
│   ├── SettingsWindow       ← Donanım, hiperparametre ve veri ayarları
│   └── Services/            ← JSON-Lines tabanlı düşük gecikmeli IPC köprüsü
│
├── brain.py                 ← PyTorch Transformer + Network Morphism + uret_stream jeneratörü
├── memory.py                ← SQLite3 Çift Katmanlı Hafıza (Epizodik + Semantik Bilgi Ağacı)
├── body.py                  ← F.R.I.D.A.Y. Nöral Ses Motoru + Sistem Araçları + Python Sandbox
├── yetenekler.py            ← Wikipedia REST API & Canlı Web Arama Motoru
├── web_server.py            ← Asenkron HTTP Web ve Mobil Gösterge Paneli
├── hardware.py              ← Çoklu GPU, DirectML, CPU thread & VRAM telemetri tarayıcısı
├── gpu_setup.py             ← Donanıma özel PyTorch hızlandırıcı yapılandırıcı
├── nova_bridge.py           ← C# ve Python motorunu senkronize eden IPC sunucusu
│
├── nova_headless_trainer/   ← Bağımsız Bulut / Küme Eğitim Sistemi
│   ├── train.py             ← FlashAttention-2 + BFloat16 Eğitim Motoru
│   ├── model.py             ← Büyüyebilir DinamikNovaLM sinir ağı
│   ├── db_manager.py        ← Öncelikli sohbet ve bilgi veritabanı yöneticisi
│   └── sync_manager.py      ← Bulut ile yerel PC arasında model/db eşitleme
│
├── baslat_cs_gui.bat        ← Tek Tıkla Masaüstü Arayüzünü Başlat (.NET 9 Release)
├── baslat_web.bat           ← Tek Tıkla Web ve Mobil Sunucusunu Başlat
├── baslat_tunnel.bat        ← Tek Tıkla Cloudflare Mobil Erişim Tünelini Başlat
├── install.bat              ← Otomatik Python ve Bağımlılık Yükleyici
└── requirements.txt         ← Çekirdek Python kütüphaneleri
```

---

## ⚡ Hızlı Başlangıç & Kurulum

### Gereksinimler
- **İşletim Sistemi**: Windows 10 / 11 (64-bit) veya Linux
- **Python**: Python 3.10 veya üzeri
- **.NET SDK**: [.NET 9.0 SDK](https://dotnet.microsoft.com/download/dotnet/9.0) (C# WPF arayüzünü derlemek için)
- **Ses Donanımı**: Mikrofon ve hoparlör / kulaklık

### 1. Otomatik Kurulum
Kurulum betiğini çalıştırın:
```powershell
.\install.bat
```
*Veya kütüphaneleri elle yükleyin:*
```powershell
pip install -r requirements.txt
pip install edge-tts speechrecognition pyaudio
```

### 2. Nova Masaüstü Arayüzünü Başlatma
Tek tıkla modern arayüzü açın:
```powershell
.\baslat_cs_gui.bat
```

### 3. Web & Mobil Arayüzünü Başlatma (İsteğe Bağlı)
```powershell
.\baslat_web.bat
```
Tarayıcınızdan `http://localhost:8080` adresine (veya telefonunuzdan aynı Wi-Fi üzerindeki bilgisayarınızın yerel IP'sine) bağlanabilirsiniz.

---

## ☁️ Bulut ve Küme Eğitimi (Google Colab / Uzak Sunucular)

Nova'yı güçlü bulut GPU'larında (örn: NVIDIA A100 / H100) eğitmek için:

```bash
cd nova_headless_trainer
python train.py --db nova.db --weights nova_weights.pth --batch_size 32 --continuous
```

- **Hız**: FlashAttention-2 ve BFloat16 otomatik devreye girer.
- **Otomatik Büyüme**: Model öğrendikçe Network Morphism ile katmanlarını ve nöronlarını genişletir.
- **Bilgisayara Aktarma**: Eğitim tamamlandığında güncellenen `nova_weights.pth` ve `nova.db` dosyalarını `c:\NOVA` klasörüne kopyalamanız yerel bilgisayarda çalıştırmak için yeterlidir.

---

## 💬 Sohbet İçi Komutlar & Kısayollar

Sohbet çubuğuna doğrudan komut yazabilir veya üstteki hızlı butonları kullanabilirsiniz:

| Komut | Açıklama |
| :--- | :--- |
| `!istatistik` / `!stats` | Canlı sinir ağı parametrelerini, hafıza düğümlerini ve eğitim adımlarını gösterir. |
| `!wiki <konu>` | Wikipedia'da canlı arama yapar ve makaleyi hafızaya ekler. |
| `!ara <sorgu>` | DuckDuckGo / web araması yapar ve bulduklarını özetler. |
| `!hesapla <matematik>` | Matematik işlemlerini çözer (örn: `2^10 + sqrt(144)`). |
| `!python <kod>` | Python kodlarını güvenli sanal alanda çalıştırır. |
| `!anilar [N]` | Son `N` adet sohbet anısını listeler. |
| `!kaydet` / `!save` | Model ağırlıklarını anında atomik olarak diske kaydeder. |
| `!buyut` / `!grow` | Sinir ağını manuel olarak bir kademe genişletir. |
| `!lang <tr/en>` | Arayüz ve yanıt dilini anında Türkçe/İngilizce olarak değiştirir. |

---

## 🛠️ Donanım Uyumluluğu

| Seviye | Donanım | Desteklenen Hızlandırma Motoru |
| :--- | :--- | :--- |
| **Giriş / Laptop** | 4 Çekirdekli CPU, 8 GB RAM | Çok İş Parçacıklı CPU BLAS |
| **Standart Masaüstü** | Ryzen 5 5600X / Intel i5, 16 GB RAM, 4GB+ GPU | AMD Radeon (DirectML), NVIDIA GTX/RTX (CUDA) |
| **İş İstasyonu / Bulut** | NVIDIA A100 / H100 / Çoklu RTX, 32GB+ RAM | FlashAttention-2 + BFloat16 Tensor Core + PyTorch DataParallel |

---

## 📄 Lisans

Bu proje **GNU General Public License v3.0 (GPL-3.0)** lisansı ile korunmaktadır. Ayrıntılar için [LICENSE](LICENSE) dosyasına göz atabilirsiniz.
