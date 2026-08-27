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
[![License](https://img.shields.io/badge/Lisans-GPL--3.0-green?style=for-the-badge)](LICENSE)

```
███╗   ██╗ ██████╗ ██╗   ██╗ █████╗     █████╗  ██████╗ ██╗
████╗  ██║██╔═══██╗██║   ██║██╔══██╗   ██╔══██╗██╔════╝ ██║
██╔██╗ ██║██║   ██║██║   ██║███████║   ███████║██║  ███╗██║
██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██║   ██╔══██║██║   ██║██║
██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║   ██║  ██║╚██████╔╝██║
╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝
```

*Nova; arka planda sürekli öğrenen, sinir ağını kendi kendine büyüten (Network Morphism), canlı web ve Wikipedia taraması yapan ve ultra modern yerel masaüstü arayüzüne sahip otonom bir yapay zeka prototipidir.*

</div>

---

## 🚀 Öne Çıkan Özellikler

### 🌟 1. Yerel C# .NET 9.0 WPF Masaüstü Arayüzü
- **Yüksek Performanslı GUI**: .NET 9.0 ve C# WPF ile inşa edilmiş, Python PyTorch arka ucu ile asenkron IPC köprüsü üzerinden haberleşen akıcı masaüstü arayüzü.
- **Canlı Çift Dilli Arayüz**: Uygulamayı yeniden başlatmaya gerek kalmadan **Türkçe** ve **İngilizce** arasında anında dil geçişi.
- **Donanım & Telemetri HUD**: Ekran kartı VRAM kullanımı, anlık loss grafiği, eğitim adımları ve parametre büyüme sayısının canlı takibi.

### 🧠 2. Kendi Kendine Büyüyen Sinir Ağı (Network Morphism)
- **Kayıpsız Büyüme (Zero-Loss Growth)**: Eğitim loss değeri platoya girdiğinde (öğrenme yavaşladığında), sinir ağı önceki ağırlıklarını unutmadan katmanlarını, embedding boyutunu ve Feed-Forward nöronlarını otonom olarak genişletir.
- **Kalıcı Ağırlık Kaydı**: Model mimarisi ve ağırlıkları Windows kilit korumasıyla atomik olarak diske yazılır; uygulama kapatılıp açıldığında büyütülen boyutlar eksiksiz korunur.

### 🕸️ 3. İnteraktif 2D Bilgi & Hafıza Grafiği Gezgini
- **2 Boyutlu Dinamik Ağ**: Epizodik anıların (kullanıcı sohbetleri) ve semantik bilgilerin (Wikipedia makaleleri) kümelenmiş etkileşimli görselleştirmesi.
- **Canlı Otomatik Yenileme (`⚡ Canlı Otomatik 4s`)**: Arka planda yeni bir bilgi öğrenildiğinde veya konuşulduğunda grafiği ekranda titreme olmadan dinamik olarak günceller.
- **Anında Madde İndirici**: İstediğiniz konuyu yazıp tek tıkla doğrudan Wikipedia'dan çekerek grafiğe ekleme imkanı.

### ⚡ 4. Donanıma Uyumlu Hızlandırma & Çoklu GPU Desteği
- **Otomatik Donanım Algılama**: **AMD Radeon** (DirectML), **NVIDIA GeForce / RTX** (CUDA), **ROCm** ve çok çekirdekli CPU desteği.
- **Çoklu GPU Paralelizmi**: Sistemde birden fazla GPU varsa PyTorch `DataParallel` ile eğitimi tüm ekran kartlarına paylaştırır.

### 🌐 5. Canlı Web Taraması & Otonom Merak Motoru
- **Anlık Wikipedia & Web Sorgulama**: Gerçek dünya sorularında canlı Wikipedia REST API üzerinden doğrulanmış bilgiyi çeker, özetler ve veritabanına kaydeder.
- **Otonom Merak Motoru**: Nova boştayken arka planda bilim, tarih, felsefe ve teknoloji konularını sürekli araştırıp öğrenir.
- **Toplu Veri İndirme**: Hugging Face resmi Wikimedia veri setinden tek tıkla 100 ile 10.000 arasında makaleyi yerel hafızaya (`nova.db`) akıtma.

### 🎙️ 6. Sesli Arayüz (Sesli Komut & Okuma)
- **Sesle Yazma (STT)**: Mikrofon butonuna basarak Nova ile sesli konuşabilme.
- **Sesli Okuma (TTS)**: Nova'nın ürettiği yanıtları sesli olarak dinleyebilme.

### 📦 7. Model Dışa Aktarma & Paketleme
- **Evrensel ONNX Formatı**: Eğitilmiş sinir ağını tek tıkla web veya gömülü sistemlerde çalıştırılabilir `.onnx` modeline dönüştürme.
- **Taşınabilir ZIP Paketi**: Model ağırlıklarını ve mimarisini paylaşılabilir `.zip` arşivi olarak kaydetme.

---

## 🏛️ Sistem Mimarisi

```
c:/NOVA/
├── NovaApp/                 ← C# .NET 9.0 WPF Masaüstü Uygulaması
│   ├── MainWindow.xaml      ← Ana sohbet paneli ve donanım HUD'u
│   ├── MemoryGraphWindow    ← İnteraktif 2D Hafıza Grafiği Gezgini
│   ├── SettingsWindow       ← Donanım, hiperparametre ve veri ayarları
│   └── Services/            ← JSON-Lines tabanlı düşük gecikmeli IPC köprüsü
│
├── brain.py                 ← PyTorch Transformer + Network Morphism + Sürekli Eğitim
├── memory.py                ← SQLite3 Çift Katmanlı Hafıza (Epizodik + Semantik)
├── body.py                  ← Doğal Dil Niyet Ayrıştırıcı + Sistem Araçları + Python Sandbox
├── yetenekler.py            ← Wikipedia REST API & Canlı Web Arama Motoru
├── hugging_loader.py        ← Otonom Merak Motoru + HuggingFace Toplu Veri Akışı
├── hardware.py              ← Çoklu GPU, DirectML, CPU thread & VRAM telemetri tarayıcısı
├── gpu_setup.py             ← Donanıma özel PyTorch hızlandırıcı yapılandırıcı
├── nova_bridge.py           ← C# ve Python motorunu senkronize eden IPC sunucusu
│
├── baslat_cs_gui.bat        ← Tek Tıkla Başlatma Betiği (Önerilen)
├── install.bat              ← Otomatik Kurulum Betiği
└── requirements.txt         ← Python bağımlılıkları
```

---

## ⚡ Hızlı Başlangıç & Kurulum

### Gereksinimler
- **İşletim Sistemi**: Windows 10 / 11 (64-bit) veya Linux
- **Python**: Python 3.10 veya üzeri
- **.NET SDK**: [.NET 9.0 SDK](https://dotnet.microsoft.com/download/dotnet/9.0) (C# WPF arayüzünü derlemek için)

### 1. Kurulum
Kurulum betiğini çalıştırın:
```powershell
.\install.bat
```
*Veya bağımlılıkları manuel yükleyin:*
```powershell
pip install -r requirements.txt
```

### 2. Uygulamayı Başlatma
Masaüstü uygulamasını tek tıkla başlatın:
```powershell
.\baslat_cs_gui.bat
```
*Veya .NET CLI ile:*
```powershell
dotnet run --project NovaApp/NovaApp.csproj
```

---

## 💬 Sohbet İçi Komutlar

Arayüzde doğrudan yazabileceğiniz komutlar:

| Komut | Açıklama |
| :--- | :--- |
| `!istatistik` / `!stats` | Model parametre sayısı, hafıza düğüm sayısı ve eğitim adımlarını listeler. |
| `!wiki <konu>` | Canlı Wikipedia makalesini çeker ve hafıza ağına kaydeder. |
| `!ara <sorgu>` | DuckDuckGo üzerinden web araştırması yapar. |
| `!hesapla <işlem>` | Matematiksel işlemleri çözer (Örn: `2^10 + sqrt(144)`). |
| `!python <kod>` | Python kodunu izole sandbox ortamında çalıştırır. |
| `!anilar [N]` | Son `N` adet konuşma anısını listeler. |
| `!kaydet` / `!save` | Model ağırlıklarını diske güvenli şekilde kaydeder. |
| `!buyut` / `!grow` | Sinir ağını manuel olarak bir kademe büyütür. |
| `!lang <tr/en>` | Aktif arayüz dilini değiştirir. |

---

## 🛠️ Donanım Uyumluluğu

| Seviye | Donanım | Desteklenen Hızlandırma |
| :--- | :--- | :--- |
| **Minimum** | Çift Çekirdek CPU, 4 GB RAM | CPU (Çok İş Parçacıklı BLAS) |
| **Önerilen** | 6 Çekirdek CPU (Ryzen 5600X vb.), 16 GB RAM, 4GB+ GPU | AMD Radeon (DirectML), NVIDIA GTX/RTX (CUDA) |
| **Yüksek Performans**| Çoklu Ekran Kartı (Multi-GPU), 32 GB RAM | Tüm kartlarda eşzamanlı PyTorch DataParallel |

---

## 📄 Lisans

Bu proje **GNU General Public License v3.0 (GPL-3.0)** lisansı ile korunmaktadır. Detaylar için [LICENSE](LICENSE) dosyasına göz atabilirsiniz.
