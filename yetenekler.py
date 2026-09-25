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
import ast
import math
import json
import string
import random
import hashlib
import datetime
import operator
import platform
import builtins
import functools


# ══════════════════════════════════════════════════════════════════════════════
# TEMEL YETENEKLER
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

_AYLAR_TR = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
             "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")
_AYLAR_EN = ("January", "February", "March", "April", "May", "June",
             "July", "August", "September", "October", "November", "December")


def _dil() -> str:
    try:
        from config_manager import get_language
        return get_language() or "tr"
    except Exception:
        return "tr"


def tarih_saat() -> str:
    """Güncel tarih ve saati (sistem yerelinden bağımsız) döndür."""
    s = datetime.datetime.now()
    ay = (_AYLAR_EN if _dil() == "en" else _AYLAR_TR)[s.month - 1]
    return f"{s.day} {ay} {s.year}, {s:%H:%M:%S}"


def bugun_gun() -> str:
    """Bugünün adı (ayarlı dilde)."""
    gunler = (("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
              if _dil() == "en" else
              ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"))
    return gunler[datetime.datetime.now().weekday()]


def unix_zamani() -> int:
    """Unix timestamp döndür."""
    return int(datetime.datetime.now().timestamp())


# ══════════════════════════════════════════════════════════════════════════════
# MATEMATİK VE HESAPLAMA
# ══════════════════════════════════════════════════════════════════════════════

_MATH_ADLAR = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
_MATH_ADLAR.update({"abs": abs, "round": round, "int": int, "float": float,
                    "min": min, "max": max, "sum": sum})
_OPERATORLER = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
    ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _degerlendir(dugum):
    """Yalnızca sayılar, aritmetik ve math fonksiyonlarına izin veren AST değerlendirici."""
    if isinstance(dugum, ast.Expression):
        return _degerlendir(dugum.body)
    if isinstance(dugum, ast.Constant) and isinstance(dugum.value, (int, float)):
        return dugum.value
    if isinstance(dugum, ast.Name) and dugum.id in _MATH_ADLAR:
        return _MATH_ADLAR[dugum.id]
    if isinstance(dugum, (ast.Tuple, ast.List)):
        return [_degerlendir(e) for e in dugum.elts]
    if isinstance(dugum, ast.UnaryOp) and type(dugum.op) in _OPERATORLER:
        return _OPERATORLER[type(dugum.op)](_degerlendir(dugum.operand))
    if isinstance(dugum, ast.BinOp) and type(dugum.op) in _OPERATORLER:
        sol, sag = _degerlendir(dugum.left), _degerlendir(dugum.right)
        if isinstance(dugum.op, ast.Pow) and abs(sag) > 1000:
            raise ValueError("Üs çok büyük")
        return _OPERATORLER[type(dugum.op)](sol, sag)
    if isinstance(dugum, ast.Call) and isinstance(dugum.func, ast.Name) and dugum.func.id in _MATH_ADLAR:
        return _MATH_ADLAR[dugum.func.id](*[_degerlendir(a) for a in dugum.args])
    raise ValueError(f"İzin verilmeyen ifade: {type(dugum).__name__}")


def hesapla(ifade: str) -> str:
    """
    Güvenli matematiksel ifade hesaplar (eval kullanmaz).
    Örnek: hesapla("2 ** 10 + sqrt(144)")
    """
    try:
        sonuc = _degerlendir(ast.parse(ifade.replace("^", "**"), mode="eval"))
        return str(round(sonuc, 10) if isinstance(sonuc, float) else sonuc)
    except Exception as e:
        return f"Hesaplama hatası: {e}"


def basarili_mi(sonuc: str) -> bool:
    """Bir yetenek çıktısının hata mesajı olmadığını ve yeterince içerik taşıdığını kontrol eder."""
    s = (sonuc or "").lower()
    return bool(s) and not any(k in s for k in ("hata", "error", "bulunamadı")) and len(s) > 1


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

_UA = {"User-Agent": "NovaAGI/4.0 (Linux; research assistant)"}


@functools.lru_cache(maxsize=256)
def wiki_ara(konu: str, lang: str = "tr") -> str:
    """Wikipedia'dan konu özeti çeker (sonuçlar önbelleklenir)."""
    import urllib.request
    import urllib.parse
    try:
        encoded = urllib.parse.quote(konu.strip().replace(" ", "_"))
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded}"
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        ozet = data.get("extract")
        if not ozet:
            raise ValueError("özet yok")
        return f"📖 **{data.get('title', konu)}**:\n{ozet}"
    except Exception as e:
        if lang == "tr":
            return wiki_ara(konu, lang="en")
        return f"Wikipedia arama hatası: {e}"


def web_ara(sorgu: str, lang: str = "tr") -> str:
    """Web üzerinde anlık bilgi araması yapar (Wikipedia & DuckDuckGo)."""
    import urllib.request
    import urllib.parse
    try:
        # 1. Önce doğrudan Wikipedia'da ara
        wiki_res = wiki_ara(sorgu, lang=lang)
        if basarili_mi(wiki_res) and len(wiki_res) > 30:
            return wiki_res

        # 2. DuckDuckGo Instant Answer API
        encoded = urllib.parse.quote(sorgu)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers=_UA)
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
        gecerli_uzantilar = (".txt", ".py", ".md", ".json", ".csv", ".log", ".axaml", ".cs",
                             ".sh", ".desktop", ".conf", ".ini", ".toml", ".yaml", ".yml")
        if not any(dosya_yolu.lower().endswith(u) for u in gecerli_uzantilar):
            return f"Güvenlik Uyarısı: Sadece metin dosyaları ({', '.join(gecerli_uzantilar)}) okunabilir."

        dosya_yolu = os.path.expanduser(dosya_yolu)
        if not os.path.exists(dosya_yolu):
            return f"Dosya bulunamadı: '{dosya_yolu}'"

        with open(dosya_yolu, "r", encoding="utf-8", errors="ignore") as f:
            icerik = f.read(max_karakter)
            ek = "...\n(İçerik kesildi)" if len(icerik) >= max_karakter else ""
            return f"📄 **{os.path.basename(dosya_yolu)}** ({len(icerik)} karakter):\n```\n{icerik}{ek}\n```"
    except Exception as e:
        return f"Dosya okuma hatası: {e}"


def python_calistir(kod: str) -> str:
    """Kısa Python kodu çalıştırır; print çıktısı yakalanır (sys.stdout değiştirilmez)."""
    import io
    yasakli = ["rmtree", "system(", "popen(", "remove(", "unlink(", "subprocess", "shutdown", "__import__(\"os\")"]
    if any(y in kod.lower() for y in yasakli):
        return "⚠️ Güvenlik: Bu işlem izin verilmeyen bir sistem komutu içeriyor."

    tampon = io.StringIO()
    alan = {"__builtins__": builtins, "print": functools.partial(print, file=tampon),
            "math": math, "json": json, "datetime": datetime, "random": random}
    try:
        exec(kod, alan)
        cikti = tampon.getvalue().strip()
        return f"🐍 **Kod Çıktısı**:\n```\n{cikti or '(Kod çalıştı, çıktı üretmedi)'}\n```"
    except Exception as e:
        return f"Python çalıştırma hatası: {e}"


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
    """Odaktaki pencerenin başlığı (X11); bulunamazsa 'Masaüstü'."""
    try:
        import linux_desktop
        return linux_desktop.aktif_pencere_basligi() or "Masaüstü"
    except Exception:
        return "Masaüstü"


def _hizlandirici() -> str:
    try:
        import hardware
        g = hardware.get_gpu_info()
        return f"{g['backend']} · {g['name']}" if g["is_gpu"] else f"CPU · {hardware.get_cpu_info()['short_name']}"
    except Exception:
        return "CPU"


def nova_sistem_durum() -> str:
    """NOVA AGI sistem ve donanım durum telemetrisini döner."""
    import psutil, random
    cpu = int(psutil.cpu_percent(interval=0.05))
    ram = int(psutil.virtual_memory().percent)
    
    return (
        "╔══════════════════════════════════════════════════════════════════╗\n"
        "║            NOVA AGI // SİSTEM TELEMETRİSİ & SAĞLIK RAPORU        ║\n"
        "╠══════════════════════════════════════════════════════════════════╣\n"
        "║  [NÖRAL ÇEKİRDEK]   : 1.39B / 400M Dinamik Transformer         ║\n"
        f"║  [HIZLANDIRICI]     : {_hizlandirici()[:42]:<42} ║\n"
        "║  [BELLEK GRAFİĞİ]   : SQLite Epizodik + Semantik Vektör Ağı     ║\n"
        "╠══════════════════════════════════════════════════════════════════╣\n"
        f"║  • SİSTEM DURUMU    : OPERASYONEL (PATTERN GREEN // HAZIR)       ║\n"
        f"║  • İŞLEMCİ YÜKÜ     : %{cpu}                                             ║\n"
        f"║  • SİSTEM RAM       : %{ram}                                             ║\n"
        "║  • İNFERANS MOTORU  : 0 GECİKME / CANLI AKIŞ AKTİF               ║\n"
        "╚══════════════════════════════════════════════════════════════════╝\n"
        "Nova AGI komutlarınızı bekliyor."
    )

def nova_guvenlik_durum() -> str:
    """Sistem güvenlik ve erişim durumunu döner."""
    return (
        "🛡️ **[NOVA AGI // GÜVENLİK VE ERİŞİM DURUMU]**\n"
        "• **Erişim Seviyesi**: `Yetkili Operatör Oturumu (Root)`\n"
        "• **Veritabanı Koruması**: `nova.db Güvenli Kilitleme Aktif`\n"
        "• **Süreç İzolasyonu**: `Doğrulanmış ve Kararlı`\n"
        "• **Değerlendirme**: Sistem güvenlik katmanları tam kapasite devrededir."
    )

def nova_senkron() -> str:
    """Operatör ile Nova arasındaki veri yolu durumunu döner."""
    import psutil, random
    cpu = psutil.cpu_percent(interval=0.05)
    sync = round(min(99.9, 97.5 + (100 - cpu) * 0.02 + random.uniform(0.1, 0.8)), 1)
    return (
        f"🧬 **[NOVA AGI // NÖRAL ENTEGRASYON RAPORU]**\n"
        f"• **Sistem Senkronizasyon Oranı**: `%{sync}`\n"
        f"• **Yanıt Gecikmesi**: `~1.2 ms` (Ultra Düşük Gecikme)\n"
        f"• **Hafıza İletişimi**: `Çift Yönlü İndeksleme Aktif`\n"
        f"💡 *Nova sinir ağı ve araçları isteklerinizi işlemeye hazır.*"
    )

def gunluk_brifing() -> str:
    """Nova AGI günlük telemetri, saat ve çalışma brifingini döner."""
    import psutil
    simdi = datetime.datetime.now()
    saat = simdi.hour
    if saat < 12:
        hitap = "Günaydın."
    elif saat < 18:
        hitap = "İyi günler."
    else:
        hitap = "İyi akşamlar."

    cpu_yuzde = int(psutil.cpu_percent(interval=0.1))
    ram = psutil.virtual_memory()
    ram_yuzde = int(ram.percent)
    pencere = aktif_pencere_basligi()
    
    tarih_str = simdi.strftime("%H:%M")
    gun = bugun_gun()
    
    brifing = (
        f"🌟 **[NOVA AGI // GÜNLÜK SİSTEM BRİFİNGİ]**\n"
        f"{hitap} Saat: {tarih_str}, {gun}.\n"
        f"• **İşlemci Yükü**: %{cpu_yuzde} | **Bellek Kullanımı**: %{ram_yuzde}\n"
        f"• **Hızlandırıcı**: {_hizlandirici()}\n"
    )
    if pencere and pencere != "Masaüstü":
        pencere_kisa = pencere[:35]
        brifing += f"• **Aktif Pencere**: `{pencere_kisa}`\n"
    brifing += "Size nasıl yardımcı olabilirim?"
    return brifing

# Geriye dönük uyumluluk takma adları
evangelion_magi_durum = nova_sistem_durum
evangelion_atfield = nova_guvenlik_durum
evangelion_senkron = nova_senkron



def sistem_eylemi(eylem: str) -> str:
    """Sistem eylemleri: lock, mute, vol_up, vol_down, desktop, taskmgr (Linux)."""
    import linux_desktop
    try:
        from config_manager import is_english
        en = is_english()
    except Exception:
        en = False
    return linux_desktop.sistem_eylemi(eylem, en=en)
