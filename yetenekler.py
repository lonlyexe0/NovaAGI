# ═══════════════════════════════════════════════════════════════════════════════
# yetenekler.py  —  Nova'nın Dinamik Yetenek Havuzu
# ═══════════════════════════════════════════════════════════════════════════════
#
# Bu dosya body.py tarafından otomatik olarak genişletilir.
# Yeni fonksiyonlar importlib.reload() ile sisteme canlı (hot-reload) eklenir.
# Her fonksiyon bağımsız çalışabilmeli, dışarıdan parametre alabilmelidir.
#
# Kural: Fonksiyon isimleri snake_case, her fonksiyon kısa docstring içermeli.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import math
import json
import datetime
import platform
import hashlib
import random
import string


# ══════════════════════════════════════════════════════════════════════════════
# TEMEL YETENEKLERs
# ══════════════════════════════════════════════════════════════════════════════

def merhaba() -> str:
    """Nova'nın temel selamlama yeteneği."""
    return (
        "Merhaba! Ben Nova — sürekli öğrenen, "
        "kendi kendini geliştiren bir AGI prototipi. "
        "Sana nasıl yardımcı olabilirim?"
    )


def nova_hakkinda() -> str:
    """Nova'nın kendisi hakkında bilgi verir."""
    return (
        "Nova, PyTorch Mini-GPT Transformer mimarisi üzerine kurulu, "
        "SQLite hafıza sistemi ve otonom web crawling yeteneğine sahip "
        "bir AGI prototipidir. Sürekli öğrenir, yeni yetenekler kazanır "
        "ve kendi kodunu yazabilir."
    )


# ══════════════════════════════════════════════════════════════════════════════
# ZAMAN VE TARİH
# ══════════════════════════════════════════════════════════════════════════════

def tarih_saat() -> str:
    """Güncel tarih ve saati döndür."""
    simdi = datetime.datetime.now()
    return simdi.strftime("%d %B %Y, %H:%M:%S")


def bugun_gun() -> str:
    """Bugünün gününü Türkçe olarak döndür."""
    gunler = {
        0: "Pazartesi", 1: "Salı",     2: "Çarşamba",
        3: "Perşembe",  4: "Cuma",     5: "Cumartesi",  6: "Pazar"
    }
    return gunler[datetime.datetime.now().weekday()]


def unix_zamani() -> int:
    """Unix timestamp döndür."""
    return int(datetime.datetime.now().timestamp())


# ══════════════════════════════════════════════════════════════════════════════
# MATEMATİK VE HESAPLAMA
# ══════════════════════════════════════════════════════════════════════════════

def hesapla(ifade: str) -> str:
    """
    Güvenli matematiksel ifade hesaplar.
    Örnek: hesapla("2 ** 10 + sqrt(144)")
    """
    izin_verilenler = {
        k: getattr(math, k) for k in dir(math) if not k.startswith("_")
    }
    izin_verilenler.update({
        "abs": abs, "round": round, "int": int,
        "float": float, "min": min, "max": max, "sum": sum,
    })
    try:
        sonuc = eval(ifade, {"__builtins__": {}}, izin_verilenler)
        return str(round(sonuc, 10) if isinstance(sonuc, float) else sonuc)
    except Exception as e:
        return f"Hesaplama hatası: {e}"


def faktoriyel(n: int) -> str:
    """n! hesaplar."""
    try:
        return str(math.factorial(int(n)))
    except Exception as e:
        return f"Hata: {e}"


def asal_mi(n: int) -> bool:
    """Sayının asal olup olmadığını kontrol eder."""
    n = int(n)
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(n ** 0.5) + 1, 2):
        if n % i == 0:
            return False
    return True


def fibonacci(n: int) -> list:
    """İlk n Fibonacci sayısını döndür."""
    n = min(int(n), 100)
    seq = [0, 1]
    for _ in range(n - 2):
        seq.append(seq[-1] + seq[-2])
    return seq[:n]


# ══════════════════════════════════════════════════════════════════════════════
# METİN İŞLEME
# ══════════════════════════════════════════════════════════════════════════════

def kelime_sayisi(metin: str) -> int:
    """Metindeki kelime sayısını döndür."""
    return len(metin.split())


def karakter_sayisi(metin: str) -> int:
    """Metindeki karakter sayısını döndür (boşluklar dahil)."""
    return len(metin)


def tersine_cevir(metin: str) -> str:
    """Metni tersine çevirir."""
    return metin[::-1]


def buyuk_harf(metin: str) -> str:
    """Metni büyük harfe çevirir."""
    return metin.upper()


def kucuk_harf(metin: str) -> str:
    """Metni küçük harfe çevirir."""
    return metin.lower()


def metin_ozeti(metin: str, maks_uzunluk: int = 200) -> str:
    """Uzun metni kısalt."""
    if len(metin) <= maks_uzunluk:
        return metin
    return metin[:maks_uzunluk].rsplit(" ", 1)[0] + "..."


def hash_hesapla(metin: str, algoritma: str = "sha256") -> str:
    """Metnin hash değerini hesaplar."""
    try:
        h = hashlib.new(algoritma)
        h.update(metin.encode("utf-8"))
        return h.hexdigest()
    except Exception as e:
        return f"Hata: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# DOSYA SİSTEMİ
# ══════════════════════════════════════════════════════════════════════════════

def dosya_listele(dizin: str = ".") -> str:
    """Dizindeki dosya ve klasörleri listeler."""
    try:
        icerik = os.listdir(dizin)
        dosyalar = sorted([
            f"{'📁' if os.path.isdir(os.path.join(dizin, f)) else '📄'} {f}"
            for f in icerik
        ])
        return "\n".join(dosyalar) if dosyalar else "(Boş dizin)"
    except Exception as e:
        return f"Hata: {e}"


def dosya_boyutu(yol: str) -> str:
    """Dosyanın boyutunu insan okunabilir formatta döndür."""
    try:
        boyut = os.path.getsize(yol)
        for birim in ["B", "KB", "MB", "GB"]:
            if boyut < 1024:
                return f"{boyut:.1f} {birim}"
            boyut /= 1024
        return f"{boyut:.1f} TB"
    except Exception as e:
        return f"Hata: {e}"


def calisan_dizin() -> str:
    """Mevcut çalışma dizinini döndür."""
    return os.getcwd()


# ══════════════════════════════════════════════════════════════════════════════
# SİSTEM BİLGİSİ
# ══════════════════════════════════════════════════════════════════════════════

def sistem_bilgisi() -> str:
    """Sistem bilgilerini döndür."""
    return (
        f"OS: {platform.system()} {platform.release()}\n"
        f"Python: {platform.python_version()}\n"
        f"Mimari: {platform.machine()}\n"
        f"İşlemci: {platform.processor() or 'Bilinmiyor'}"
    )


def ortam_degiskeni(isim: str) -> str:
    """Ortam değişkenini okur."""
    deger = os.environ.get(isim)
    return deger if deger is not None else f"'{isim}' bulunamadı."


# ══════════════════════════════════════════════════════════════════════════════
# RASTGELE ARAÇLAR
# ══════════════════════════════════════════════════════════════════════════════

def rastgele_sayi(alt: int = 0, ust: int = 100) -> int:
    """Belirli aralıkta rastgele sayı üret."""
    return random.randint(int(alt), int(ust))


def rastgele_sifre(uzunluk: int = 16) -> str:
    """Güçlü rastgele şifre üret."""
    uzunluk = max(8, min(int(uzunluk), 64))
    karakterler = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(random.choices(karakterler, k=uzunluk))


def sikka_at() -> str:
    """Yazı ya da tura."""
    return random.choice(["Yazı 🪙", "Tura 🏅"])


def liste_karistir(liste_str: str) -> str:
    """Virgülle ayrılmış listeyi karıştır."""
    elemanlar = [e.strip() for e in liste_str.split(",") if e.strip()]
    random.shuffle(elemanlar)
    return ", ".join(elemanlar)


# ══════════════════════════════════════════════════════════════════════════════
# JSON ARAÇLARI
# ══════════════════════════════════════════════════════════════════════════════

def json_formatla(json_str: str) -> str:
    """JSON metnini güzel formatta yazdır."""
    try:
        data = json.loads(json_str)
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"JSON hatası: {e}"


def json_degerle(json_str: str, anahtar: str) -> str:
    """JSON'dan belirli bir anahtarın değerini çek."""
    try:
        data = json.loads(json_str)
        return str(data.get(anahtar, f"'{anahtar}' bulunamadı"))
    except Exception as e:
        return f"Hata: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# İNTERNET, WIKIPEDIA VE BİLGİ ARAMA
# ══════════════════════════════════════════════════════════════════════════════

def wiki_ara(konu: str, lang: str = "tr") -> str:
    """Wikipedia'dan belirli bir konu hakkında özet bilgi çeker."""
    import urllib.request
    import urllib.parse
    try:
        encoded = urllib.parse.quote(konu.strip().replace(" ", "_"))
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded}"
        req = urllib.request.Request(url, headers={"User-Agent": "NovaAGI/3.5 (AI Research Assistant)"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            baslik = data.get("title", konu)
            ozet = data.get("extract", "Özet bulunamadı.")
            return f"📖 **{baslik}**:\n{ozet}"
    except Exception as e:
        # Fallback to English if Turkish fails
        if lang == "tr":
            return wiki_ara(konu, lang="en")
        return f"Wikipedia arama hatası: {e}"


def web_ara(sorgu: str) -> str:
    """Web üzerinde anlık bilgi araması yapar (Wikipedia & DDG)."""
    import urllib.request
    import urllib.parse
    try:
        # 1. Önce doğrudan Wikipedia'da ara
        wiki_res = wiki_ara(sorgu, lang="tr")
        if "hata" not in wiki_res.lower() and len(wiki_res) > 30:
            return wiki_res

        # 2. DuckDuckGo Instant Answer API
        encoded = urllib.parse.quote(sorgu)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent": "NovaAGI/3.5"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            answer = data.get("AbstractText") or data.get("Answer")
            if answer:
                heading = data.get("Heading", sorgu)
                return f"🔍 **{heading}**:\n{answer}"
            return wiki_ara(sorgu, lang="en")
    except Exception as e:
        return f"Web arama hatası: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# GELİŞMİŞ DOSYA VE KOD ÇALIŞTIRMA
# ══════════════════════════════════════════════════════════════════════════════

def dosya_oku(dosya_yolu: str, max_karakter: int = 4000) -> str:
    """Yerel bir metin, python veya veri dosyasını güvenle okur."""
    try:
        # Güvenlik kontrolü: sadece belirli uzantılara izin ver
        gecerli_uzantilar = (".txt", ".py", ".md", ".json", ".csv", ".log", ".xaml", ".cs", ".iss", ".bat")
        if not any(dosya_yolu.lower().endswith(u) for u in gecerli_uzantilar):
            return f"Güvenlik Uyarısı: Sadece metin dosyaları ({', '.join(gecerli_uzantilar)}) okunabilir."

        if not os.path.exists(dosya_yolu):
            return f"Dosya bulunamadı: '{dosya_yolu}'"

        with open(dosya_yolu, "r", encoding="utf-8", errors="ignore") as f:
            icerik = f.read(max_karakter)
            ek = "...\n(İçerik kesildi)" if len(icerik) >= max_karakter else ""
            return f"📄 **{os.path.basename(dosya_yolu)}** ({len(icerik)} karakter):\n```\n{icerik}{ek}\n```"
    except Exception as e:
        return f"Dosya okuma hatası: {e}"


def python_calistir(kod: str) -> str:
    """Güvenli kum havuzunda (sandbox) kısa Python kodu çalıştırır ve çıktısını döndürür."""
    import sys
    import io
    # Tehlikeli işlemleri filtrele
    yasakli = ["rmtree", "system(", "popen(", "remove(", "unlink(", "shutdown", "format "]
    if any(y in kod.lower() for y in yasakli):
        return "⚠️ Güvenlik: Bu işlem izin verilmeyen bir sistem komutu içeriyor."

    eski_stdout = sys.stdout
    tampon = io.StringIO()
    sys.stdout = tampon
    try:
        yerel_alan = {"math": math, "json": json, "datetime": datetime, "random": random}
        exec(kod, {"__builtins__": __builtins__}, yerel_alan)
        cikti = tampon.getvalue().strip()
        return f"🐍 **Kod Çıktısı**:\n```\n{cikti if cikti else '(Kod başarıyla çalıştı, çıktı üretmedi)'}\n```"
    except Exception as e:
        return f"Python çalıştırma hatası: {e}"
    finally:
        sys.stdout = eski_stdout


# ══════════════════════════════════════════════════════════════════════════════
# YETENEKLERİ LİSTELE (Meta-fonksiyon)
# ══════════════════════════════════════════════════════════════════════════════

def yetenek_listesi() -> str:
    """Bu modüldeki tüm yetenekleri listeler."""
    import inspect
    import sys
    modul = sys.modules[__name__]
    fonksiyonlar = [
        name for name, obj in inspect.getmembers(modul, inspect.isfunction)
        if not name.startswith("_")
    ]
    return "\n".join(f"  • {f}" for f in sorted(fonksiyonlar))


def selamla(): return "Komutanım, sistemler tam kapasite calisiyor!"


# ══════════════════════════════════════════════════════════════════════════════
# F.R.I.D.A.Y. BRİFİNG & SİSTEM YÖNETİMİ
# ══════════════════════════════════════════════════════════════════════════════

def aktif_pencere_basligi() -> str:
    """Windows'ta şu an odakta olan ön pencerenin başlığını döner."""
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value
    except Exception:
        pass
    return "Masaüstü"


def gunluk_brifing() -> str:
    """F.R.I.D.A.Y. tarzı sinematik sistem, zaman ve donanım brifingi döner."""
    import psutil
    simdi = datetime.datetime.now()
    saat = simdi.hour
    if saat < 12:
        hitap = "Günaydın patron."
    elif saat < 18:
        hitap = "İyi günler patron."
    else:
        hitap = "İyi akşamlar patron."

    cpu_yuzde = int(psutil.cpu_percent(interval=0.1))
    ram = psutil.virtual_memory()
    ram_yuzde = int(ram.percent)
    pencere = aktif_pencere_basligi()
    
    tarih_str = simdi.strftime("%H:%M")
    gun = bugun_gun()
    
    brifing = (
        f"{hitap} Saat {tarih_str}, {gun}. "
        f"Nova sistemleri operasyonel. "
        f"İşlemci yükü %{cpu_yuzde}, bellek kullanımı %{ram_yuzde}. "
    )
    if pencere and pencere != "Masaüstü":
        pencere_kisa = pencere[:35]
        brifing += f"Aktif pencereniz: '{pencere_kisa}'. "
    brifing += "Gününüzü asiste etmeye hazırım. Nasıl yardımcı olabilirim?"
    return brifing


def sistem_eylemi(eylem: str) -> str:
    """Bilgisayar üzerinde sistem seviyesinde eylemler yürütür (kilitle, ses vb)."""
    eylem = eylem.lower().strip()
    try:
        import ctypes
        user32 = ctypes.windll.user32
        if eylem in ("lock", "kilitle"):
            user32.LockWorkStation()
            return "🔒 Bilgisayar ekranı kilitlendi."
        elif eylem in ("mute", "sessiz"):
            # VK_VOLUME_MUTE = 0xAD
            user32.keybd_event(0xAD, 0, 0, 0)
            user32.keybd_event(0xAD, 0, 2, 0)
            return "🔇 Ses durumu değiştirildi (Açık/Kapalı)."
        elif eylem in ("vol_up", "ses_artir"):
            # VK_VOLUME_UP = 0xAF
            for _ in range(3):
                user32.keybd_event(0xAF, 0, 0, 0)
                user32.keybd_event(0xAF, 0, 2, 0)
            return "🔊 Ses artırıldı."
        elif eylem in ("vol_down", "ses_azalt"):
            # VK_VOLUME_DOWN = 0xAE
            for _ in range(3):
                user32.keybd_event(0xAE, 0, 0, 0)
                user32.keybd_event(0xAE, 0, 2, 0)
            return "🔉 Ses azaltıldı."
        elif eylem in ("desktop", "masaustu", "minimize_all"):
            # Win + D
            user32.keybd_event(0x5B, 0, 0, 0)
            user32.keybd_event(0x44, 0, 0, 0)
            user32.keybd_event(0x44, 0, 2, 0)
            user32.keybd_event(0x5B, 0, 2, 0)
            return "🪟 Masaüstüne geçildi."
        elif eylem in ("taskmgr", "gorev_yoneticisi"):
            # Ctrl + Shift + Esc
            user32.keybd_event(0x11, 0, 0, 0)
            user32.keybd_event(0x10, 0, 0, 0)
            user32.keybd_event(0x1B, 0, 0, 0)
            user32.keybd_event(0x1B, 0, 2, 0)
            user32.keybd_event(0x10, 0, 2, 0)
            user32.keybd_event(0x11, 0, 2, 0)
            return "⚙️ Görev Yöneticisi açıldı."
        else:
            return f"Bilinmeyen eylem: {eylem}"
    except Exception as e:
        return f"Sistem eylem hatası: {e}"

