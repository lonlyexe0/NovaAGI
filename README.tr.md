<div align="right">
  <strong>Diller / Languages:</strong> 
  <a href="README.md">English</a> | <b>Türkçe</b>
</div>

<div align="center">

# 🤖 Nova AGI — Windows Kurulum Paketi

```
███╗   ██╗ ██████╗ ██╗   ██╗ █████╗ 
████╗  ██║██╔═══██╗██║   ██║██╔══██╗
██╔██╗ ██║██║   ██║██║   ██║███████║
██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██║
██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║
╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝
```

**Nova Otonom Öğrenen AGI Projesi için Resmi Windows Kurulum Dosyası**

[![GitHub Repository](https://img.shields.io/badge/GitHub-NovaAGI%20Ana%20Depo-blue?logo=github)](https://github.com/lonlyexe0/NovaAGI)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011%20(64--bit)-0078D6?logo=windows)](https://github.com/lonlyexe0/NovaAGI)
[![Lisans: GPL v3](https://img.shields.io/badge/Lisans-GPLv3-blue.svg)](LICENSE)
[![Durum](https://img.shields.io/badge/Durum-Beta%20%2F%20Deneysel-orange)](#-önemli-uyumluluk-ve-bilgilendirme-notu)

</div>

---

> [!WARNING]
> ### ⚠️ ÖNEMLİ UYUMLULUK VE BİLGİLENDİRME NOTU
> **İndirmeden ve kurmadan önce lütfen okuyunuz:**
> - Bu kurulum dosyası (`NovaAGI_v3_Setup.exe`) şu an **erken prototip / beta (deneysel)** aşamadadır.
> - **Henüz her bilgisayarda veya tüm donanım kombinasyonlarında sorunsuz çalışmayabilir.**
> - **Şu an üzerinde aktif olarak çalışıyorum!** Sistem uyumluluğunu genişletmek, hataları gidermek, performansı artırmak ve kararlılık sağlamak için sürekli güncellemeler yapıyorum.
> - Eğer bilgisayarınızda kurulum veya çalıştırma esnasında herhangi bir sorun, çökme veya hata ile karşılaşırsanız, lütfen sistem özelliklerinizle birlikte [GitHub Issues](https://github.com/lonlyexe0/NovaAGI/issues) üzerinden bildirin. Bu sayede en kısa sürede düzeltebilirim!

---

## 📦 Paket İçeriği

| Dosya | Açıklama | Boyut |
| :--- | :--- | :--- |
| `NovaAGI_v3_Setup.exe` | Nova AGI için bağımsız Windows Kurulum Yükleyicisi | ~285 MB |

---

## 💻 Sistem Gereksinimleri

| Bileşen | Minimum | Önerilen |
| :--- | :--- | :--- |
| **İşletim Sistemi** | Windows 10 (64-bit) | Windows 11 (64-bit) |
| **İşlemci (CPU)** | Intel Core i3 / AMD Ryzen 3 (Dört Çekirdek) | Intel Core i5/i7 veya AMD Ryzen 5/7 |
| **Bellek (RAM)** | 8 GB RAM | 16 GB+ RAM |
| **Depolama** | 2 GB boş disk alanı | 5 GB+ SSD alanı |
| **Ekran Kartı (GPU)** | Sadece CPU modu desteklenir | CUDA destekli NVIDIA Ekran Kartı (Yapay zeka hızlandırması için) |

---

## 🚀 Kurulum Rehberi

1. **Kurulum Dosyasını İndirin:**
   - Depoyu klonlayarak veya `NovaAGI_v3_Setup.exe` dosyasını doğrudan indirerek edinin.

2. **Yükleyiciyi Çalıştırın:**
   - `NovaAGI_v3_Setup.exe` dosyasına çift tıklayarak kurulum sihirbazını başlatın.

3. **Windows SmartScreen Uyarısı Çıkarsa:**
   - Windows Defender veya SmartScreen *"Windows kişisel bilgisayarınızı korudu"* veya *"Bilinmeyen Yayıncı"* uyarısı verirse:
     1. **"Ek bilgi"** (*More info*) yazısına tıklayın.
     2. **"Yine de çalıştır"** (*Run anyway*) butonuna basın.

4. **Kurulum Adımlarını Tamamlayın:**
   - Kurulum sihirbazındaki adımları izleyerek yükleme konumunu seçin ve masaüstü kısayollarını oluşturun.

5. **Nova AGI'yi Başlatın:**
   - Kurulum tamamlandıktan sonra masaüstündeki Nova AGI simgesinden uygulamayı başlatabilirsiniz.

---

## 🔧 Sorun Giderme ve Bilinen Durumlar

- **Kurulum başlamıyor veya Antivirüs engelliyor:**
  - Açık kaynaklı ve bağımsız bir geliştirici yazılımı olduğu için (pahalı kurumsal dijital sertifika bulunmadığından) Windows SmartScreen veya antivirüsler uyarı verebilir. Güvenle istisna/izin verebilirsiniz.
- **Açılışta çöküyor veya hata veriyor:**
  - Bilgisayarınızda [Microsoft Visual C++ Yeniden Dağıtılabilir (Redistributable)](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist) paketinin kurulu olduğundan emin olun.
  - Ekran kartı (NVIDIA GPU) kullanıyorsanız sürücülerinizin ve CUDA sürümünüzün güncel olduğundan emin olun.
- **Hala sorun mu yaşıyorsunuz?**
  - Unutmayın, **proje üzerinde aktif olarak çalışmaya devam ediyorum**. Lütfen [NovaAGI Issues](https://github.com/lonlyexe0/NovaAGI/issues) adresinden aşağıdaki bilgileri içeren bir hata bildirimi açın:
    - Windows sürümünüz
    - İşlemci (CPU) ve Ekran Kartı (GPU) modeliniz
    - RAM miktarınız
    - Hata mesajı veya ekran görüntüsü

---

## 📄 Lisans

Bu proje **GNU Genel Kamu Lisansı v3.0 (GPL-3.0)** ile lisanslanmıştır. Ayrıntılar için [LICENSE](LICENSE) dosyasına göz atabilirsiniz.

---

## 🔗 İlgili Bağlantılar

- **Ana Nova AGI Deposu:** [github.com/lonlyexe0/NovaAGI](https://github.com/lonlyexe0/NovaAGI)
- **Hata Bildirimi ve Geri Bildirim:** [github.com/lonlyexe0/NovaAGI/issues](https://github.com/lonlyexe0/NovaAGI/issues)

---

<div align="center">
  <sub>Geliştirici: <b>lonlyexe0</b> • Nova AGI Otonom Sistemi</sub>
</div>
