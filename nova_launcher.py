#!python3.10
from __future__ import annotations
# ═══════════════════════════════════════════════════════════════════════════════
# nova_launcher.py  —  Nova AGI Ana Başlatıcı v3  [Python 3.10]
# ═══════════════════════════════════════════════════════════════════════════════
#
# !istatistik komutu artık şunu gösterir:
#   • Mevcut mimari (embed, kafa, blok, ff, parametre)
#   • Büyüme geçmişi tablosu (her büyüme: tip, parametre, saat)
#   • HuggingFace akış durumu
#   • Ses/Görüntü/Bilgisayar kontrol durumu
#   • Merak motoru istatistikleri
# ═══════════════════════════════════════════════════════════════════════════════

import sys, os, time, signal, logging, argparse, threading, queue
from typing import Optional
from datetime import datetime

# PyInstaller / Standalone bundle yol desteği
_bundle_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
if _bundle_dir not in sys.path:
    sys.path.insert(0, _bundle_dir)
_curr_dir = os.path.dirname(os.path.abspath(__file__))
if _curr_dir not in sys.path:
    sys.path.insert(0, _curr_dir)

class _NullWriter:
    def write(self, s): pass
    def flush(self): pass
    def reconfigure(self, **kwargs): pass

if sys.stdout is None:
    sys.stdout = _NullWriter()
if sys.stderr is None:
    sys.stderr = _NullWriter()

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# GPU / DirectML ve Donanım Optimizasyonu
try:
    import gpu_setup
    gpu_setup.gpu_hazirla()
except Exception:
    pass

import torch
torch.set_num_threads(12)
torch.set_num_interop_threads(4)


# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════
def logging_kur(debug: bool = False):
    from config_manager import get_data_path
    log_file = get_data_path("nova.log")
    seviye  = logging.DEBUG if debug else logging.INFO
    fmt     = "%(asctime)s [%(name)-18s] %(levelname)-7s %(message)s"
    handlers = [logging.StreamHandler(sys.stdout)]
    try:
        handlers.insert(0, logging.FileHandler(log_file, encoding="utf-8"))
    except Exception:
        pass
    logging.basicConfig(
        level=seviye, format=fmt, datefmt="%H:%M:%S",
        handlers=handlers,
        force=True,
    )
    for lib in ("urllib3","requests","charset_normalizer",
                "datasets","huggingface_hub","filelock","fsspec","aiohttp"):
        logging.getLogger(lib).setLevel(logging.WARNING)

logger = logging.getLogger("nova.launcher")


# ═══════════════════════════════════════════════════════════════════════════════
# RENK KODLARI
# ═══════════════════════════════════════════════════════════════════════════════
class R:
    KIRMIZI = "\033[91m";  YESIL  = "\033[92m";  MAVI   = "\033[94m"
    SARI    = "\033[93m";  CYAN   = "\033[96m";  BEYAZ  = "\033[97m"
    GRI     = "\033[90m";  SIFIR  = "\033[0m";   KALIN  = "\033[1m"
    def r(t,*k): return "".join(k)+t+R.SIFIR


# ═══════════════════════════════════════════════════════════════════════════════
# ARGÜMANLAR
# ═══════════════════════════════════════════════════════════════════════════════
def arguman_isle() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Nova AGI v3 — Sınırsız Büyüyen Beyin")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--gui",  action="store_true")
    g.add_argument("--term", action="store_true")
    g.add_argument("--both", action="store_true")
    p.add_argument("--debug",    action="store_true")
    p.add_argument("--no-crawl", action="store_true")
    p.add_argument("--no-hf",    action="store_true")
    p.add_argument("--db",       default="nova.db")
    p.add_argument("--hf-limit", type=int, default=0,
                   help="HF makale limiti (0=sonsuz)")
    p.add_argument("--hf-token", type=str, default=None,
                   help="Hugging Face Access Token (hf_...)")
    p.add_argument("--lang",     type=str, default=None, choices=["en", "tr"],
                   help="Language preference ('en' or 'tr')")
    p.add_argument("--reset-lang", action="store_true",
                   help="Reset language choice")
    return p.parse_args()


# ═══════════════════════════════════════════════════════════════════════════════
# HUGGINGFACE SÜREKLİ AKIŞ
# ═══════════════════════════════════════════════════════════════════════════════
class HuggingFaceAkisi:
    DATASET_ADI = "wikimedia/wikipedia"
    MIN_UZUN    = 300
    MAX_BEKLE   = 5_000
    HATA_BEKLE  = 60
    KAYIT_BEKLE = 5
    LOG_ARALIK  = 100

    def __init__(self, hafiza, dur: threading.Event, limit: int = 0, lang: Optional[str] = None):
        self.hafiza  = hafiza
        self.dur     = dur
        self.limit   = limit
        self.sayac   = 0
        self.atlandi = 0
        self._thread: Optional[threading.Thread] = None
        self._kurulu = True
        self.lang    = lang or "en"

    @property
    def dataset_config(self) -> str:
        return "20231101.en" if self.lang == "en" else "20231101.tr"

    def _kontrol(self) -> bool:
        try:
            import datasets; return True  # noqa
        except ImportError:
            logger.warning("[HF] datasets yok → pip install datasets")
            return False

    def baslat(self):
        if not self._kurulu: return
        self._thread = threading.Thread(
            target=self._dis_dongu, name="NovaHF", daemon=True)
        self._thread.start()
        logger.info(f"[HF] ✅ Başladı — {self.dataset_config} | "
                    f"Limit: {'Sonsuz' if not self.limit else self.limit}")

    def _dis_dongu(self):
        while not self.dur.is_set():
            try:
                self._ic_dongu()
                break
            except Exception as e:
                logger.error(f"[HF] Kesildi: {e}. {self.HATA_BEKLE}s sonra tekrar...")
                self.dur.wait(timeout=self.HATA_BEKLE)
        logger.info(f"[HF] Durdu. Toplam: {self.sayac:,}")

    def _ic_dongu(self):
        from datasets import load_dataset
        from hf_auth import hf_token_al
        logger.info("[HF] Bağlanıyor...")
        token = hf_token_al()
        kwargs = {"split": "train", "streaming": True}
        if token:
            kwargs["token"] = token
        ds = load_dataset(self.DATASET_ADI, self.dataset_config, **kwargs)
        logger.info(f"[HF] Bağlandı ({self.dataset_config}), akıyor...")
        for veri in ds:
            if self.dur.is_set(): return
            if self.limit > 0 and self.sayac >= self.limit:
                logger.info(f"[HF] Limit ({self.limit:,}) doldu."); return
            metin = veri.get("text","")
            url   = veri.get("url",  f"hf://tr-wiki/{self.sayac}")
            konu  = veri.get("title","Genel")
            if len(metin) < self.MIN_UZUN:
                self.atlandi += 1; continue
            # DB doluysa bekle
            while not self.dur.is_set():
                s = self.hafiza.istatistik()
                if s["egitilmemis"] < self.MAX_BEKLE: break
                self.dur.wait(timeout=self.KAYIT_BEKLE)
            try:
                self.hafiza.bilgi_kaydet(url=url, konu=konu, icerik=metin)
                self.sayac += 1
                if self.sayac % self.LOG_ARALIK == 0:
                    s = self.hafiza.istatistik()
                    logger.info(f"[HF] 📚 {self.sayac:>7,} makale | "
                                f"Atlanan: {self.atlandi:,} | "
                                f"İşlenmemiş: {s['egitilmemis']:,}")
            except Exception as e:
                logger.debug(f"[HF] Kayıt hatası: {e}")

    def istatistik(self) -> dict:
        return {"eklenen": self.sayac, "atlandi": self.atlandi,
                "aktif": self._thread.is_alive() if self._thread else False,
                "kurulu": self._kurulu}


# ═══════════════════════════════════════════════════════════════════════════════
# BİLİNÇALTI DÖNGÜSÜ
# ═══════════════════════════════════════════════════════════════════════════════
def bilincalti_dongusu(hafiza, beyin, beden, dur: threading.Event,
                        crawl_aktif: bool = True):
    logger.info("[Bilinçaltı] Başladı.")
    TARA_ARL  = 60
    GOREV_ARL = 8
    son_t = son_g = 0.0
    while not dur.is_set():
        simdi = time.monotonic()
        if crawl_aktif and simdi - son_t >= TARA_ARL:
            try: beden.siradaki_hedef_tara()
            except Exception as e: logger.error(f"[Bilinçaltı] Crawler: {e}")
            son_t = simdi
        if simdi - son_g >= GOREV_ARL:
            try:
                g = hafiza.bekleyen_gorev_getir()
                if g:
                    hafiza.gorev_guncelle(g["id"], "devam_ediyor")
                    try:
                        beden.gorevi_coz(g["tanim"])
                        hafiza.gorev_guncelle(g["id"], "tamamlandi")
                    except Exception:
                        hafiza.gorev_guncelle(g["id"], "basarisiz")
            except Exception as e: logger.error(f"[Bilinçaltı] Görev: {e}")
            son_g = simdi
        dur.wait(timeout=4)
    logger.info("[Bilinçaltı] Durdu.")


# ═══════════════════════════════════════════════════════════════════════════════
# TERMINAL REPL
# ═══════════════════════════════════════════════════════════════════════════════
BANNER = f"""
{R.CYAN}{R.KALIN}
╔══════════════════════════════════════════════════════════════════════╗
║   ███╗   ██╗ ██████╗ ██╗   ██╗ █████╗    v3  BÜYÜYEN BEYİN        ║
║   ████╗  ██║██╔═══██╗██║   ██║██╔══██╗                             ║
║   ██╔██╗ ██║██║   ██║██║   ██║███████║  Sınırsız · Öğrenen · Canlı ║
║   ██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██║                             ║
║   ██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║  CPU + HuggingFace + Merak  ║
╚══════════════════════════════════════════════════════════════════════╝
{R.SIFIR}"""

def bilincli_dongu(hafiza, beyin, beden, dur: threading.Event,
                   hf_akisi: Optional[HuggingFaceAkisi] = None):
    import re as _re

    print(BANNER)
    _istatistik_yazdir(hafiza, beyin, beden, hf_akisi)
    print(f"{R.GRI}  '!yardim' yazın  |  Ctrl+C ile çıkın{R.SIFIR}\n")

    while not dur.is_set():
        try:
            girdi = input(f"{R.YESIL}{R.KALIN}Sen{R.SIFIR} {R.GRI}»{R.SIFIR} ").strip()
        except (EOFError, KeyboardInterrupt):
            dur.set(); break
        if not girdi: continue

        # Dahili komutlar
        if girdi.startswith("!"):
            _komut_isle(girdi, hafiza, beyin, beden, dur, hf_akisi)
            continue

        # Sesli giriş kontrolü
        if girdi.lower() in ("dinle","ses","mic"):
            print(f"{R.GRI}Dinleniyor...{R.SIFIR}")
            girdi = beden.ses.dinle()
            if not girdi:
                print(f"{R.GRI}(Ses algılanamadı){R.SIFIR}")
                continue
            print(f"{R.YESIL}Ses:{R.SIFIR} {girdi}")

        # Nova'nın cevabı
        hafiza.ani_kaydet("kullanici", girdi)
        baglam = hafiza.rag_sorgula(girdi, k=3, max_karakter=350)
        son    = hafiza.son_anilar_getir(limit=6)
        gecmis = ""
        for a in son[-4:]:
            gecmis += f"{'Kullanıcı' if a['rol']=='kullanici' else 'Nova'}: {a['icerik']}\n"

        parcalar = []
        if baglam:    parcalar.append(f"[Bağlam: {baglam[:250]}]")
        if gecmis:    parcalar.append(gecmis.strip())
        parcalar.append(f"Kullanıcı: {girdi}\nNova:")
        tohum = "\n".join(parcalar)

        print(f"{R.CYAN}{R.KALIN}Nova{R.SIFIR} {R.GRI}»{R.SIFIR} ", end="", flush=True)
        try:
            cevap_ham = beyin.uret(tohum, uzunluk=280, sicaklik=0.85, top_k=50, top_p=0.92)
            cevap     = _cevap_temizle(cevap_ham)
            print(cevap)
            hafiza.ani_kaydet("nova", cevap)

            # Sesli okuma (TTS aktifse)
            if beden.ses.tts_aktif_mi():
                beden.ses.konuş(cevap[:300])

            # Eylem etiketi
            m = _re.search(r"\[EYLEM:\s*(.+?)\]", cevap, _re.I | _re.DOTALL)
            if m:
                eylem = m.group(1).strip()
                print(f"{R.GRI}  ↳ Eylem: {eylem}{R.SIFIR}")
                sonuc = beden.gorevi_coz(eylem)
                print(f"{R.GRI}  ↳ Sonuç: {sonuc[:200]}{R.SIFIR}")
        except Exception as e:
            print(f"{R.KIRMIZI}(Hata: {e}){R.SIFIR}")
        print()


def _cevap_temizle(ham: str) -> str:
    import re
    for tag in ["Nova:","Kullanıcı:","[Bağlam:"]:
        i = ham.find(tag)
        if i != -1: ham = ham[:i]
    ham = re.sub(r"\n{3,}","\n\n",ham).strip()
    ps  = [p.strip() for p in ham.split("\n\n") if p.strip()]
    c   = "\n\n".join(ps[:2])
    if len(c) > 800: c = c[:800].rsplit(" ",1)[0] + "..."
    return c or "Anlıyorum. Daha fazla öğrendikçe daha iyi yanıtlar vereceğim."


def _komut_isle(girdi, hafiza, beyin, beden, dur, hf_akisi):
    ps   = girdi[1:].split(maxsplit=1)
    cmd  = ps[0].lower() if ps else ""
    arg  = ps[1].strip() if len(ps) > 1 else ""

    def yaz(t, renk=""):
        print(f"{renk}{t}{R.SIFIR}" if renk else t)

    if cmd == "yardim":
        print(f"""
{R.SARI}{'━'*62}  NOVA v3 KOMUTLAR  {'━'*62}{R.SIFIR}
  {R.CYAN}!istatistik{R.SIFIR}           → Tam sistem durumu + büyüme geçmişi
  {R.CYAN}!buyume{R.SIFIR}               → Büyüme geçmişi tablosu
  {R.CYAN}!mimari{R.SIFIR}               → Mevcut sinir ağı mimarisi
  {R.CYAN}!kaydet{R.SIFIR}               → Modeli kaydet
  {R.CYAN}!cikis{R.SIFIR}                → Güvenli kapat
  {R.CYAN}!anilar [N]{R.SIFIR}           → Son N anı
  {R.CYAN}!tara <url>{R.SIFIR}           → URL'yi tara ve öğren
  {R.CYAN}!yetenekler{R.SIFIR}           → Yetenek listesi
  {R.CYAN}!kod <isim>|<def...>{R.SIFIR}  → Yeni yetenek ekle
  {R.CYAN}!cagir <isim>(<arg>){R.SIFIR}  → Yetenek çağır
  {R.CYAN}!gorev <tanim>{R.SIFIR}        → Görevi kuyruğa ekle
  {R.CYAN}!komut <shell>{R.SIFIR}        → Shell komutu
  {R.CYAN}!ekran [dosya]{R.SIFIR}        → Ekran görüntüsü al
  {R.CYAN}!konuş <metin>{R.SIFIR}        → Sesli oku
  {R.CYAN}!dinle{R.SIFIR}                → Mikrofondan dinle
  {R.CYAN}!kamera ac/kapat/kare{R.SIFIR} → Kamera kontrolü
  {R.CYAN}!tikla <x> <y>{R.SIFIR}        → Fare tıklama
  {R.CYAN}!yaz <metin>{R.SIFIR}          → Klavyeden yaz
  {R.CYAN}!uygulama <komut>{R.SIFIR}     → Uygulama aç
""")

    elif cmd == "istatistik":
        _istatistik_yazdir(hafiza, beyin, beden, hf_akisi)

    elif cmd == "buyume":
        print(f"\n{R.CYAN}{'━'*60}  BÜYÜME GEÇMİŞİ  {'━'*60}{R.SIFIR}")
        print(beyin.model.buyume_tablosu())
        print(f"\n  Toplam büyüme: {beyin.model._toplam_buyume}x")
        print(f"  Mevcut parametre: {beyin.model.param_sayisi():,}")
        print(f"{R.CYAN}{'━'*60}{R.SIFIR}\n")

    elif cmd == "mimari":
        print(f"\n{R.CYAN}Mevcut Mimari:{R.SIFIR}")
        print(f"  {beyin.model.mimari_ozet()}")
        print(f"  Embed boyutu : {beyin.model._e}")
        print(f"  Kafa sayısı  : {beyin.model._h}")
        print(f"  Blok sayısı  : {len(beyin.model.bloklar)}")
        print(f"  FF nöron     : {beyin.model._ff}")
        print(f"  Parametre    : {beyin.model.param_sayisi():,}")
        print(f"  Büyüme sayısı: {beyin.model._toplam_buyume}x\n")

    elif cmd == "kaydet":
        beyin.kaydet(); yaz("✓ Kaydedildi.", R.YESIL)

    elif cmd == "cikis":
        yaz("Kaydediliyor...", R.SARI)
        beyin.kaydet(); yaz("Hoşça kal! 👋", R.YESIL)
        dur.set()

    elif cmd == "anilar":
        n = int(arg) if arg.isdigit() else 5
        for a in hafiza.son_anilar_getir(limit=n):
            renk = R.YESIL if a["rol"]=="kullanici" else R.CYAN
            print(f"  {R.GRI}{a['zaman']}{R.SIFIR} {renk}{a['rol']:<10}{R.SIFIR} {a['icerik'][:80]}")

    elif cmd == "tara":
        if not arg: yaz("Kullanım: !tara <url>", R.SARI)
        elif not arg.startswith(("http://","https://")):
            yaz("Geçerli URL girin.", R.KIRMIZI)
        else:
            print(f"{R.GRI}Taranıyor: {arg}{R.SIFIR}")
            m = beden.url_tara(arg)
            if m:
                hafiza.bilgi_kaydet(arg, arg, m)
                yaz(f"✓ Kaydedildi ({len(m):,} karakter)", R.YESIL)
            else:
                yaz("✗ Taranamadı", R.KIRMIZI)

    elif cmd == "yetenekler":
        yl = beden.yetenek_listele()
        print(f"\n{R.CYAN}Yetenekler ({len(yl)}):{R.SIFIR}")
        for i,y in enumerate(yl):
            print(f"  {R.GRI}{i+1:>2}.{R.SIFIR} {y}")

    elif cmd == "kod":
        if "|" not in arg: yaz("Kullanım: !kod isim|def isim(): ...", R.SARI)
        else:
            isim, kod = arg.split("|",1)
            ok, msg = beden.yetenek_yaz_ve_yukle(isim.strip(), kod.strip())
            yaz(msg, R.YESIL if ok else R.KIRMIZI)

    elif cmd == "cagir":
        if arg: yaz(beden.gorevi_coz(f"YETENEK: {arg}"), R.CYAN)
        else:   yaz("Kullanım: !cagir isim(arg)", R.SARI)

    elif cmd == "gorev":
        if arg:
            gid = hafiza.gorev_ekle(arg)
            yaz(f"✓ Görev eklendi (ID: {gid})", R.YESIL)
        else: yaz("Kullanım: !gorev <tanim>", R.SARI)

    elif cmd == "gorevler":
        gv = hafiza.tum_gorevler()
        if not gv: yaz("Görev kuyruğu boş.", R.GRI)
        else:
            for g in gv:
                renk = {
                    "tamamlandi": R.YESIL,"devam_ediyor": R.SARI,
                    "basarisiz": R.KIRMIZI,"bekliyor": R.GRI,
                }.get(g["durum"], R.BEYAZ)
                print(f"  [{g['id']:>3}] {renk}{g['durum']:<15}{R.SIFIR} {g['tanim'][:50]}")

    elif cmd == "komut":
        if arg: print(f"{R.GRI}{beden.komut_calistir(arg)}{R.SIFIR}")
        else:   yaz("Kullanım: !komut <shell>", R.SARI)

    elif cmd == "ekran":
        dosya = arg.strip() or "ekran.png"
        yaz(beden.goruntu.ekran_kaydet(dosya), R.YESIL)

    elif cmd in ("konuş","konus"):
        if arg: yaz(beden.ses.konuş(arg), R.CYAN)
        else:   yaz("Kullanım: !konuş <metin>", R.SARI)

    elif cmd == "dinle":
        sure = int(arg) if arg.isdigit() else 5
        print(f"{R.GRI}Dinleniyor ({sure}s)...{R.SIFIR}")
        sonuc = beden.ses.dinle(zaman_asimi=sure)
        print(f"{R.CYAN}Duyulan: {sonuc or '(ses algılanamadı)'}{R.SIFIR}")

    elif cmd == "kamera":
        a = arg.strip().lower()
        if a == "ac":       yaz(beden.goruntu.kamera_ac(), R.YESIL)
        elif a == "kapat":  yaz(beden.goruntu.kamera_kapat(), R.YESIL)
        elif a in ("kare","foto"): yaz(beden.goruntu.kamera_kare_al(), R.YESIL)
        else: yaz("Kullanım: !kamera ac|kapat|kare", R.SARI)

    elif cmd == "tikla":
        try:
            parts = arg.split()
            x, y  = int(parts[0]), int(parts[1])
            yaz(beden.bilgisayar.fare_tikla(x, y), R.YESIL)
        except Exception: yaz("Kullanım: !tikla <x> <y>", R.SARI)

    elif cmd == "yaz":
        if arg: yaz(beden.bilgisayar.yaz(arg), R.YESIL)
        else:   yaz("Kullanım: !yaz <metin>", R.SARI)

    elif cmd == "uygulama":
        if arg: yaz(beden.bilgisayar.uygulama_ac(arg), R.YESIL)
        else:   yaz("Kullanım: !uygulama <komut>", R.SARI)

    elif cmd == "oku":
        if arg: print(f"{R.GRI}{beden.dosya_oku(arg)[:2000]}{R.SIFIR}")
        else:   yaz("Kullanım: !oku <dosya>", R.SARI)

    else:
        yaz(f"Bilinmeyen komut: '!{cmd}'. !yardim yazın.", R.KIRMIZI)


# ═══════════════════════════════════════════════════════════════════════════════
# DETAYLI İSTATİSTİK
# ═══════════════════════════════════════════════════════════════════════════════
def _istatistik_yazdir(hafiza, beyin, beden, hf_akisi):
    stat   = hafiza.istatistik()
    lr     = beyin.optimizer.param_groups[0]["lr"]
    model  = beyin.model
    merak  = beden.merak.istatistik()
    goruntu= beden.goruntu.durum()
    hf     = hf_akisi.istatistik() if hf_akisi else {}

    print(f"\n{R.CYAN}{'═'*66}{R.SIFIR}")
    print(f"{R.CYAN}{R.KALIN}  NOVA AGI v3 — TAM SİSTEM DURUMU  "
          f"{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}{R.SIFIR}")
    print(f"{R.CYAN}{'═'*66}{R.SIFIR}")

    # ── Sinir Ağı Mimarisi ────────────────────────────────────────────────────
    print(f"\n{R.SARI}  🧠 SİNİR AĞI (Dinamik — Sınırsız Büyüme){R.SIFIR}")
    print(f"  {'Embedding boyutu':<22}: {model._e:>8,}")
    print(f"  {'Dikkat kafası':<22}: {model._h:>8,}")
    print(f"  {'Transformer bloğu':<22}: {len(model.bloklar):>8,}")
    print(f"  {'FF nöron sayısı':<22}: {model._ff:>8,}")
    print(f"  {'Toplam parametre':<22}: {model.param_sayisi():>8,}")
    print(f"  {'Toplam büyüme':<22}: {model._toplam_buyume:>8}x")
    print(f"  {'Eğitim adımı':<22}: {beyin.adim:>8,}")
    print(f"  {'Son loss':<22}: {beyin.son_loss():>8.4f}")
    print(f"  {'Öğrenme hızı':<22}: {lr:>8.2e}")
    print(f"  {'Vocab boyutu':<22}: {len(beyin.char2id):>8,}")

    # ── Büyüme Geçmişi ────────────────────────────────────────────────────────
    print(f"\n{R.SARI}  📈 BÜYÜME GEÇMİŞİ{R.SIFIR}")
    if model.buyume_gecmisi:
        print(f"  {'No':>3} {'Tip':<16} {'Parametre':>12} {'Saat':>8}")
        print("  " + "─"*42)
        for b in model.buyume_gecmisi[-10:]:
            print(f"  {b['no']:>3} {b['tip']:<16} {b['parametre']:>12,} {b['zaman']:>8}")
        if len(model.buyume_gecmisi) > 10:
            print(f"  ... ve {len(model.buyume_gecmisi)-10} büyüme daha")
    else:
        print("  Henüz büyüme gerçekleşmedi.")

    # ── Hafıza ────────────────────────────────────────────────────────────────
    print(f"\n{R.SARI}  💾 HAFIZA{R.SIFIR}")
    print(f"  {'Anı sayısı':<22}: {stat['ani_sayisi']:>8,}")
    print(f"  {'Bilgi kaydı':<22}: {stat['bilgi_sayisi']:>8,}")
    print(f"  {'İşlenmemiş bilgi':<22}: {stat['egitilmemis']:>8,}")
    print(f"  {'Bekleyen görev':<22}: {stat['gorev_bekleyen']:>8,}")

    # ── HuggingFace ───────────────────────────────────────────────────────────
    print(f"\n{R.SARI}  📚 HUGGINGFACE AKIŞI{R.SIFIR}")
    if hf:
        durum = f"{'🟢 Aktif' if hf['aktif'] else '🔴 Durdu'}"
        print(f"  {'Durum':<22}: {durum}")
        print(f"  {'Eklenen makale':<22}: {hf['eklenen']:>8,}")
        print(f"  {'Atlanan':<22}: {hf['atlandi']:>8,}")
    else:
        print("  HF akışı başlatılmadı.")

    # ── Merak Motoru ──────────────────────────────────────────────────────────
    print(f"\n{R.SARI}  🔍 MERAK MOTORU{R.SIFIR}")
    print(f"  {'Keşif kuyruğu':<22}: {merak['kuyruk']:>8,}")
    print(f"  {'Görülmüş URL':<22}: {merak['gorulmus']:>8,}")
    print(f"  {'Keşfedilen link':<22}: {merak['kesfedilen']:>8,}")

    # ── Donanım Modülleri ─────────────────────────────────────────────────────
    print(f"\n{R.SARI}  🤖 DONANIM MODÜLLERİ{R.SIFIR}")
    b = beden.bilgisayar
    s = beden.ses
    g = beden.goruntu
    print(f"  {'Fare/Klavye':<22}: {'✅ Aktif' if b.aktif else '❌ pip install pyautogui'}")
    print(f"  {'Ses tanıma (STT)':<22}: {'✅ Aktif' if s.ses_aktif_mi() else '❌ pip install speechrecognition pyaudio'}")
    print(f"  {'Sesli okuma (TTS)':<22}: {'✅ Aktif' if s.tts_aktif_mi() else '❌ pip install pyttsx3'}")
    print(f"  {'Görüntü (Pillow)':<22}: {'✅ Aktif' if goruntu['pillow'] else '❌ pip install pillow'}")
    print(f"  {'Görüntü (OpenCV)':<22}: {'✅ Aktif' if goruntu['opencv'] else '❌ pip install opencv-python'}")
    print(f"  {'Kamera':<22}: {'✅ Açık' if goruntu['kamera'] else '❌ Kapalı'}")

    print(f"\n{R.CYAN}{'═'*66}{R.SIFIR}\n")


# ═══════════════════════════════════════════════════════════════════════════════
# GUI BAŞLATICI
# ═══════════════════════════════════════════════════════════════════════════════
def gui_baslat(hafiza, beyin, beden):
    try:
        import tkinter as tk
        from gui import NovaGUI
        root = tk.Tk()
        NovaGUI(root, hafiza, beyin, beden)
        root.mainloop()
    except ImportError as e:
        logger.error(f"[GUI] {e}")
        print(f"❌ GUI açılamadı: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# ANA GİRİŞ
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    args = arguman_isle()
    logging_kur(debug=args.debug)

    # ── Dil Seçimi (İlk Açılışta Sorulur, Sonra Hatırlanır) ────────────────────
    from config_manager import ask_language_on_first_launch, _config_yaz
    if args.reset_lang:
        _config_yaz({})
    aktif_dil = ask_language_on_first_launch(arg_lang=args.lang)

    # ── Hugging Face Girişi ───────────────────────────────────────────────────
    from hf_auth import hf_giris_sor
    hf_giris_sor(arg_token=args.hf_token)

    logger.info("Nova AGI v3 başlatılıyor...")

    dur = threading.Event()

    # Bileşenler
    print(f"{R.GRI}[1/4] Hafıza başlatılıyor...{R.SIFIR}", flush=True)
    from memory import HafizaYoneticisi
    hafiza = HafizaYoneticisi(db_yolu=args.db)

    from brain import BeynYoneticisi, Config
    print(f"{R.GRI}[2/4] Beyin yükleniyor ({Config.device.upper()})...{R.SIFIR}", flush=True)
    beyin = BeynYoneticisi(hafiza)

    print(f"{R.GRI}[3/4] Beden başlatılıyor (Bilgisayar+Ses+Görüntü+Merak)...{R.SIFIR}", flush=True)
    from body import AjanBeden
    beden = AjanBeden(hafiza, beyin)

    wiki_src = "English Wikipedia (20231101.en)" if aktif_dil == "en" else "Türkçe Wikipedia (20231101.tr)"
    print(f"{R.GRI}[4/4] HuggingFace akışı hazırlanıyor ({wiki_src})...{R.SIFIR}", flush=True)
    hf_akisi = HuggingFaceAkisi(hafiza=hafiza, dur=dur, limit=args.hf_limit, lang=aktif_dil)

    # Eğitim ve arka plan thread'leri
    beyin.surekli_egitim_baslat()
    if not args.no_hf:
        hf_akisi.baslat()

    t_bilincalti = threading.Thread(
        target=bilincalti_dongusu,
        args=(hafiza, beyin, beden, dur, not args.no_crawl),
        name="NovaBilincalti", daemon=True,
    )
    t_bilincalti.start()

    def sinyal_isle(sig, frame):
        print(f"\n{R.SARI}[Launcher] Kapatılıyor...{R.SIFIR}", flush=True)
        dur.set()

    try:
        signal.signal(signal.SIGINT,  sinyal_isle)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, sinyal_isle)
    except Exception:
        pass

    # Mod seçimi
    mod = "gui" if not (args.term or args.both) else ("term" if args.term else "both")
    print(f"\n{R.YESIL}✅ Hazır. Mod: {mod.upper()} | "
          f"Parametre: {beyin.model.param_sayisi():,} | "
          f"Büyüme: {beyin.model._toplam_buyume}x{R.SIFIR}\n", flush=True)

    if mod == "gui":
        print(f"{R.CYAN}🖥️ Nova AGI Grafik Penceresi açıldı (Masaüstünüzü kontrol edin).{R.SIFIR}", flush=True)

    try:
        if mod == "gui":
            gui_baslat(hafiza, beyin, beden)
        elif mod == "term":
            bilincli_dongu(hafiza, beyin, beden, dur, hf_akisi)
        elif mod == "both":
            t_term = threading.Thread(
                target=bilincli_dongu,
                args=(hafiza, beyin, beden, dur, hf_akisi),
                name="NovaTerm", daemon=True,
            )
            t_term.start()
            gui_baslat(hafiza, beyin, beden)
    except KeyboardInterrupt:
        print(f"\n{R.SARI}Ctrl+C{R.SIFIR}")
    finally:
        dur.set()
        print(f"{R.GRI}Kaydediliyor...{R.SIFIR}")
        try: beyin.kaydet()
        except Exception: pass
        hf = hf_akisi.istatistik()
        print(f"{R.YESIL}Kapatıldı — "
              f"HF: {hf['eklenen']:,} makale | "
              f"Eğitim: {beyin.adim:,} adım | "
              f"Parametre: {beyin.model.param_sayisi():,} | "
              f"Büyüme: {beyin.model._toplam_buyume}x 🌟{R.SIFIR}")


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
