from __future__ import annotations
# ═══════════════════════════════════════════════════════════════════════════════
# body.py  —  Nova'nın Tam Bedeni  [Python 3.10]
# ═══════════════════════════════════════════════════════════════════════════════
#
# Modüller:
#   🖱  BilgisayarKontrol  → fare, klavye, ekran görüntüsü, uygulama açma
#   🎤  SesMotoru          → mikrofon ile dinle, sesli yanıt ver
#   👁   GoruntMotoru       → ekran/kamera yakala, renk/nesne analiz et
#   🌐  MerakMotoru        → Wikipedia linklerini keşfet, özerk tara
#   🤖  AjanBeden          → hepsini birleştiren ana sınıf
#
# Kurulum (ihtiyaca göre):
#   pip install pyautogui pillow opencv-python
#   pip install speechrecognition pyttsx3 pyaudio
#   pip install requests beautifulsoup4
# ═══════════════════════════════════════════════════════════════════════════════

import os, re, time, logging, inspect, textwrap, importlib
import subprocess, threading, queue
from typing import Optional, List, Tuple, Dict, Any

import requests
from bs4 import BeautifulSoup

import yetenekler
logger = logging.getLogger("nova.body")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. BİLGİSAYAR KONTROL MODÜLÜ
# ═══════════════════════════════════════════════════════════════════════════════
class BilgisayarKontrol:
    """
    Nova'nın el-kolu: fare, klavye, ekran görüntüsü, uygulama kontrolü.
    pyautogui ve Pillow gerektirir.
    """

    def __init__(self):
        self._aktif = False
        try:
            import pyautogui
            import PIL.ImageGrab
            self._gui = pyautogui
            self._gui.FAILSAFE = True   # Sol üst köşeye götürünce dur
            self._gui.PAUSE    = 0.05   # Her eylem arası 50ms — güvenli
            self._aktif = True
            logger.info("[Bilgisayar] pyautogui hazır.")
        except ImportError:
            logger.warning("[Bilgisayar] pyautogui bulunamadı → pip install pyautogui pillow")
        except Exception as e:
            self._aktif = False
            logger.warning(f"[Bilgisayar] pyautogui başlatılamadı: {e}")

    @property
    def aktif(self) -> bool:
        return self._aktif

    # ── Fare ──────────────────────────────────────────────────────────────────
    def fare_tasi(self, x: int, y: int, sure: float = 0.3):
        """Fareyi (x, y) konumuna taşı."""
        if not self._aktif: return "Bilgisayar kontrolü aktif değil."
        self._gui.moveTo(x, y, duration=sure)
        return f"Fare → ({x}, {y})"

    def fare_tikla(self, x: int, y: int, dugme: str = "left"):
        """Belirtilen konuma tıkla."""
        if not self._aktif: return "Bilgisayar kontrolü aktif değil."
        self._gui.click(x, y, button=dugme)
        return f"Tıklandı ({x}, {y}) [{dugme}]"

    def cift_tikla(self, x: int, y: int):
        """Çift tıkla."""
        if not self._aktif: return "Bilgisayar kontrolü aktif değil."
        self._gui.doubleClick(x, y)
        return f"Çift tıklandı ({x}, {y})"

    def sag_tikla(self, x: int, y: int):
        if not self._aktif: return "Bilgisayar kontrolü aktif değil."
        self._gui.rightClick(x, y)
        return f"Sağ tıklandı ({x}, {y})"

    def surukle(self, x1: int, y1: int, x2: int, y2: int, sure: float = 0.5):
        """(x1,y1)'den (x2,y2)'ye sürükle."""
        if not self._aktif: return "Bilgisayar kontrolü aktif değil."
        self._gui.drag(x1, y1, x2-x1, y2-y1, duration=sure, button="left")
        return f"Sürüklendi ({x1},{y1}) → ({x2},{y2})"

    def kayan_teker(self, miktar: int, x: Optional[int] = None, y: Optional[int] = None):
        """Fare tekerini kaydır. miktar > 0 = yukarı."""
        if not self._aktif: return "Bilgisayar kontrolü aktif değil."
        if x and y: self._gui.moveTo(x, y)
        self._gui.scroll(miktar)
        return f"Kaydırıldı {miktar}"

    # ── Klavye ────────────────────────────────────────────────────────────────
    def yaz(self, metin: str, aralik: float = 0.03):
        """Metni klavye ile yaz."""
        if not self._aktif: return "Bilgisayar kontrolü aktif değil."
        self._gui.typewrite(metin, interval=aralik)
        return f"Yazıldı: {metin[:50]}"

    def pano_yaz(self, metin: str):
        """Metni panoya kopyalayıp yapıştır (Türkçe karakter uyumlu)."""
        if not self._aktif: return "Bilgisayar kontrolü aktif değil."
        import pyperclip
        pyperclip.copy(metin)
        self._gui.hotkey("ctrl", "v")
        return f"Panoya yazıldı: {metin[:50]}"

    def kisa_yol(self, *tuslar: str):
        """Klavye kısayolu çalıştır. Örn: kisa_yol('ctrl', 'c')"""
        if not self._aktif: return "Bilgisayar kontrolü aktif değil."
        self._gui.hotkey(*tuslar)
        return f"Kısayol: {'+'.join(tuslar)}"

    def tus_bas(self, tus: str):
        """Tek tuş bas. Örn: tus_bas('enter'), tus_bas('esc')"""
        if not self._aktif: return "Bilgisayar kontrolü aktif değil."
        self._gui.press(tus)
        return f"Tuş: {tus}"

    # ── Ekran ─────────────────────────────────────────────────────────────────
    def ekran_goruntus_al(self, dosya_yolu: str = "ekran.png",
                           bolge: Optional[Tuple] = None) -> str:
        """Ekran görüntüsü al ve kaydet."""
        if not self._aktif: return "Bilgisayar kontrolü aktif değil."
        try:
            self._gui.screenshot(dosya_yolu, region=bolge)
            return f"Ekran görüntüsü: {dosya_yolu}"
        except Exception as e:
            return f"Hata: {e}"

    def ekran_boyutu(self) -> Tuple[int, int]:
        """Ekran boyutunu döndür."""
        if not self._aktif: return (0, 0)
        return self._gui.size()

    def piksel_rengi(self, x: int, y: int) -> str:
        """Belirtilen konumdaki pikselin rengini döndür."""
        if not self._aktif: return "Aktif değil"
        r, g, b = self._gui.pixel(x, y)
        return f"RGB({r},{g},{b})"

    def goruntu_bul(self, sablon_yolu: str, guven: float = 0.8) -> Optional[Tuple]:
        """Ekranda bir görüntü şablonu ara, konumunu döndür."""
        if not self._aktif: return None
        try:
            konum = self._gui.locateCenterOnScreen(sablon_yolu, confidence=guven)
            return konum
        except Exception:
            return None

    # ── Uygulama ──────────────────────────────────────────────────────────────
    def uygulama_ac(self, komut: str) -> str:
        """Uygulama aç. Örn: uygulama_ac('notepad'), uygulama_ac('code .')"""
        try:
            subprocess.Popen(komut, shell=True)
            return f"Açıldı: {komut}"
        except Exception as e:
            return f"Hata: {e}"

    def fare_konumu(self) -> Tuple[int, int]:
        """Mevcut fare konumunu döndür."""
        if not self._aktif: return (0, 0)
        return self._gui.position()


# ═══════════════════════════════════════════════════════════════════════════════
# 2. SES MOTORU
# ═══════════════════════════════════════════════════════════════════════════════
class SesMotoru:
    """
    Nova'nın kulakları ve sesi.
    Dinleme: speech_recognition + pyaudio
    Konuşma: pyttsx3 (offline TTS)
    """

    def __init__(self):
        self._sr_aktif  = False
        self._tts_aktif = False
        self._tts_motor = None
        self._tts_kuyruk: queue.Queue = queue.Queue()
        self._tts_thread = None

        # Speech Recognition
        try:
            import speech_recognition as sr
            self._sr = sr
            self._taniyici = sr.Recognizer()
            self._taniyici.energy_threshold = 300
            self._taniyici.dynamic_energy_threshold = True
            self._sr_aktif = True
            logger.info("[Ses] speech_recognition hazır.")
        except ImportError:
            logger.warning("[Ses] speech_recognition bulunamadı → pip install speechrecognition pyaudio")
        except Exception as e:
            self._sr_aktif = False
            logger.warning(f"[Ses] speech_recognition başlatılamadı: {e}")

        # TTS
        try:
            import pyttsx3
            from config_manager import get_language
            lang = get_language() or "en"
            self._tts_motor = pyttsx3.init()
            self._tts_motor.setProperty("rate", 175)
            self._tts_motor.setProperty("volume", 0.9)
            # Dil sesini seç (en veya tr)
            target_code = "en" if lang == "en" else "tr"
            for ses in self._tts_motor.getProperty("voices"):
                s_id = ses.id.lower()
                s_name = getattr(ses, "name", "").lower()
                if (target_code == "en" and ("en" in s_id or "english" in s_name)) or \
                   (target_code == "tr" and ("tr" in s_id or "turkish" in s_name)):
                    self._tts_motor.setProperty("voice", ses.id)
                    break
            self._tts_aktif = True
            self._tts_thread = threading.Thread(
                target=self._tts_dongusu, daemon=True, name="NovaTTS"
            )
            self._tts_thread.start()
            logger.info(f"[Ses] pyttsx3 TTS hazır ({'English' if lang=='en' else 'Türkçe'}).")
        except ImportError:
            logger.warning("[Ses] pyttsx3 bulunamadı → pip install pyttsx3")
        except Exception as e:
            self._tts_motor = None
            self._tts_aktif = False
            logger.warning(f"[Ses] pyttsx3 TTS başlatılamadı ({e}) → Sisteminizde eSpeak/eSpeak-ng eksik olabilir.")


    def _tts_dongusu(self):
        """TTS kuyruğunu işleyen thread (pyttsx3 thread-safe değil)."""
        while True:
            try:
                metin = self._tts_kuyruk.get(timeout=1)
                if metin is None:
                    break
                if self._tts_motor:
                    self._tts_motor.say(metin)
                    self._tts_motor.runAndWait()
            except queue.Empty:
                continue
            except Exception as e:
                logger.debug(f"[TTS] Hata: {e}")

    def konuş(self, metin: str, bloke: bool = False):
        """Nova'nın sesi: metni sesli oku."""
        if not self._tts_aktif:
            return "TTS aktif değil (pip install pyttsx3)"
        # Çok uzun metni kısalt
        metin_kisa = metin[:500]
        self._tts_kuyruk.put(metin_kisa)
        if bloke:
            self._tts_kuyruk.join()
        return f"Sesli okunuyor: {metin_kisa[:60]}..."

    def dinle(self, zaman_asimi: int = 5, dil: Optional[str] = None) -> str:
        """
        Mikrofondan ses dinle ve metne çevir.
        Döner: tanınan metin veya hata mesajı
        """
        if not self._sr_aktif:
            return "Ses tanıma aktif değil (pip install speechrecognition pyaudio)"
        if dil is None:
            from config_manager import get_language
            lang = get_language() or "en"
            dil = "en-US" if lang == "en" else "tr-TR"
        sr = self._sr
        try:
            with sr.Microphone() as kaynak:
                logger.info("[Ses] Dinleniyor...")
                self._taniyici.adjust_for_ambient_noise(kaynak, duration=0.5)
                ses = self._taniyici.listen(kaynak, timeout=zaman_asimi,
                                             phrase_time_limit=15)
            metin = self._taniyici.recognize_google(ses, language=dil)
            logger.info(f"[Ses] Tanındı: {metin}")
            return metin
        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            return ""
        except Exception as e:
            return f"Ses hatası: {e}"

    def ses_aktif_mi(self) -> bool:
        return self._sr_aktif

    def tts_aktif_mi(self) -> bool:
        return self._tts_aktif

    def hiz_ayarla(self, hiz: int = 175):
        """TTS konuşma hızını ayarla (kelime/dakika)."""
        if self._tts_motor:
            self._tts_motor.setProperty("rate", hiz)

    def ses_listele(self) -> List[str]:
        """Mevcut TTS seslerini listele."""
        if not self._tts_motor:
            return []
        return [f"{s.id}: {s.name}" for s in self._tts_motor.getProperty("voices")]


# ═══════════════════════════════════════════════════════════════════════════════
# 3. GÖRÜNTÜ MOTORU
# ═══════════════════════════════════════════════════════════════════════════════
class GoruntMotoru:
    """
    Nova'nın gözleri: ekran, kamera, görüntü analizi.
    Pillow ve OpenCV gerektirir.
    """

    def __init__(self):
        self._pil_aktif = False
        self._cv_aktif  = False
        self._kamera    = None

        try:
            from PIL import Image, ImageGrab, ImageFilter
            self._Image      = Image
            self._ImageGrab  = ImageGrab
            self._ImageFilter= ImageFilter
            self._pil_aktif  = True
            logger.info("[Görüntü] Pillow hazır.")
        except ImportError:
            logger.warning("[Görüntü] Pillow bulunamadı → pip install pillow")
        except Exception as e:
            self._pil_aktif = False
            logger.warning(f"[Görüntü] Pillow başlatılamadı: {e}")

        try:
            import cv2
            self._cv2      = cv2
            self._cv_aktif = True
            logger.info("[Görüntü] OpenCV hazır.")
        except ImportError:
            logger.warning("[Görüntü] OpenCV bulunamadı → pip install opencv-python")
        except Exception as e:
            self._cv_aktif = False
            logger.warning(f"[Görüntü] OpenCV başlatılamadı: {e}")

    # ── Ekran ─────────────────────────────────────────────────────────────────
    def ekran_yakala(self, bolge: Optional[Tuple] = None) -> Optional[Any]:
        """Ekran görüntüsünü PIL Image olarak döndür."""
        if not self._pil_aktif: return None
        try:
            return self._ImageGrab.grab(bbox=bolge)
        except Exception as e:
            logger.debug(f"[Görüntü] Ekran yakala hatası: {e}")
            return None

    def ekran_kaydet(self, dosya: str = "ekran.png",
                     bolge: Optional[Tuple] = None) -> str:
        """Ekran görüntüsünü dosyaya kaydet."""
        img = self.ekran_yakala(bolge)
        if img is None: return "Ekran yakalanamadı."
        img.save(dosya)
        return f"Kaydedildi: {dosya} ({img.size[0]}x{img.size[1]})"

    def ekran_metin_oku(self, dosya: Optional[str] = None) -> str:
        """
        Ekrandaki metni oku (OCR). pytesseract gerektirir.
        Yoksa temel renk analizi yapar.
        """
        try:
            import pytesseract
            img = (self._Image.open(dosya) if dosya
                   else self.ekran_yakala())
            if img is None: return "Görüntü alınamadı"
            return pytesseract.image_to_string(img, lang="tur+eng")
        except ImportError:
            return "OCR için: pip install pytesseract (ve Tesseract kurulu olmalı)"
        except Exception as e:
            return f"OCR hatası: {e}"

    # ── Kamera ────────────────────────────────────────────────────────────────
    def kamera_ac(self, index: int = 0) -> str:
        """Kamerayı aç."""
        if not self._cv_aktif: return "OpenCV gerekli (pip install opencv-python)"
        if self._kamera and self._kamera.isOpened():
            return "Kamera zaten açık."
        self._kamera = self._cv2.VideoCapture(index)
        if self._kamera.isOpened():
            return f"Kamera {index} açıldı."
        return "Kamera açılamadı."

    def kamera_kapat(self) -> str:
        if self._kamera:
            self._kamera.release()
            self._kamera = None
        return "Kamera kapatıldı."

    def kamera_kare_al(self, dosya: str = "kare.png") -> str:
        """Kameradan tek kare al ve kaydet."""
        if not self._kamera or not self._kamera.isOpened():
            return "Kamera açık değil. Önce kamera_ac() çağır."
        ret, kare = self._kamera.read()
        if not ret: return "Kare alınamadı."
        self._cv2.imwrite(dosya, kare)
        h, w = kare.shape[:2]
        return f"Kare kaydedildi: {dosya} ({w}x{h})"

    def goruntu_analiz(self, dosya: str) -> str:
        """
        Görüntüyü basit analiz et: boyut, baskın renkler.
        Daha gelişmiş analiz için AI modeli gerekir.
        """
        if not self._pil_aktif: return "Pillow gerekli."
        try:
            img = self._Image.open(dosya)
            w, h = img.size
            mod  = img.mode

            # Baskın renk analizi (k=5 küme)
            img_kucuk = img.convert("RGB").resize((50, 50))
            piksel_listesi = list(img_kucuk.getdata())
            renkler: Dict[Tuple, int] = {}
            for px in piksel_listesi:
                # 32'nin katına yuvarla (renk gruplama)
                r_g = (px[0]//32*32, px[1]//32*32, px[2]//32*32)
                renkler[r_g] = renkler.get(r_g, 0) + 1
            top5 = sorted(renkler.items(), key=lambda x: -x[1])[:5]
            renk_str = ", ".join(f"RGB{r}={c}" for r,c in top5)

            return (f"Dosya: {dosya} | Boyut: {w}x{h} | Mod: {mod}\n"
                    f"Baskın renkler: {renk_str}")
        except Exception as e:
            return f"Analiz hatası: {e}"

    def goruntu_kesit(self, dosya: str, x: int, y: int,
                      genislik: int, yukseklik: int, cikti: str = "kesit.png") -> str:
        """Görüntüden belirtilen bölgeyi kes."""
        if not self._pil_aktif: return "Pillow gerekli."
        try:
            img = self._Image.open(dosya)
            kesit = img.crop((x, y, x+genislik, y+yukseklik))
            kesit.save(cikti)
            return f"Kesit kaydedildi: {cikti}"
        except Exception as e:
            return f"Kesit hatası: {e}"

    def renk_filtrele(self, dosya: str, filtre: str = "BLUR",
                      cikti: str = "filtreli.png") -> str:
        """Görüntüye filtre uygula: BLUR, SHARPEN, EDGE_ENHANCE, GRAYSCALE"""
        if not self._pil_aktif: return "Pillow gerekli."
        try:
            img = self._Image.open(dosya)
            if filtre == "GRAYSCALE":
                img = img.convert("L")
            else:
                f = getattr(self._ImageFilter, filtre, None)
                if f is None: return f"Bilinmeyen filtre: {filtre}"
                img = img.filter(f)
            img.save(cikti)
            return f"Filtre ({filtre}) uygulandı: {cikti}"
        except Exception as e:
            return f"Filtre hatası: {e}"

    def durum(self) -> Dict[str, bool]:
        return {
            "pillow":  self._pil_aktif,
            "opencv":  self._cv_aktif,
            "kamera":  bool(self._kamera and self._kamera.isOpened()),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 4. MERAK MOTORU (özerk web keşif)
# ═══════════════════════════════════════════════════════════════════════════════
class MerakMotoru:
    """
    Nova bir sayfayı okuyunca içindeki Wikipedia linklerini çıkarır,
    ilgi skoruna göre sıralar ve özerk olarak keşfeder.
    """
    MAX_KUYRUK   = 2_000
    MAX_GORULMUS = 50_000
    SISTEM_SAYFALAR = {
        "Özel:","Wikipedia:","Yardım:","Şablon:","Kategori:",
        "Dosya:","Portal:","Special:","Help:","Template:","Category:",
        "File:","Talk:","User:","WP:","MOS:",
    }
    TR_WIKI = re.compile(r"https://tr\.wikipedia\.org/wiki/([^#?&<>\s\"']+)")
    EN_WIKI = re.compile(r"https://en\.wikipedia\.org/wiki/([^#?&<>\s\"']+)")

    def __init__(self, hafiza, session: requests.Session):
        import heapq
        self.hafiza   = hafiza
        self.session  = session
        self._heap    = []
        self._heap_s  = set()
        self._gorulmus= set()
        self._sayac   = 0
        self._lock    = threading.Lock()
        self._hq      = heapq
        self.toplam_kesfedilen = 0
        self.toplam_eklenen    = 0

    def kuyruk_boyutu(self) -> int:
        return len(self._heap)

    def siradaki_url(self) -> Optional[str]:
        with self._lock:
            while self._heap:
                _, _, url = self._hq.heappop(self._heap)
                self._heap_s.discard(url)
                if url not in self._gorulmus:
                    self._gorulmus.add(url)
                    if len(self._gorulmus) > self.MAX_GORULMUS:
                        self._gorulmus = set(list(self._gorulmus)[-self.MAX_GORULMUS//2:])
                    return url
        return None

    def url_ekle(self, url: str, skor: float):
        with self._lock:
            if url in self._gorulmus or url in self._heap_s:
                return
            if len(self._heap) >= self.MAX_KUYRUK:
                self._heap.sort()
                if self._heap and -self._heap[-1][0] < skor:
                    _, _, c = self._heap.pop()
                    self._heap_s.discard(c)
                else:
                    return
            self._sayac += 1
            self._hq.heappush(self._heap, (-skor, self._sayac, url))
            self._heap_s.add(url)
            self.toplam_eklenen += 1

    def linklerden_besle(self, kaynak_url: str, metin: str):
        import random
        tr_l = set(self.TR_WIKI.findall(metin))
        en_l = set(self.EN_WIKI.findall(metin))
        tum  = [(f"https://tr.wikipedia.org/wiki/{s}", s, "tr") for s in tr_l
                if not any(s.startswith(x) for x in self.SISTEM_SAYFALAR)]
        tum += [(f"https://en.wikipedia.org/wiki/{s}", s, "en") for s in en_l
                if not any(s.startswith(x) for x in self.SISTEM_SAYFALAR)]
        if not tum: return
        bilinen = self._bilinen_kavramlar()
        eklenen = 0
        for url, slug, dil in tum:
            kelimeler = [k for k in re.split(r"[\s_]+", slug.replace("_"," ").lower()) if len(k) > 3]
            if not kelimeler: continue
            skor  = random.uniform(0.1, 0.4)
            ortus = sum(1 for k in kelimeler if k in bilinen)
            skor += 0.35 if ortus == 0 else 0.2 * min(ortus/len(kelimeler), 1)
            if dil == "tr": skor += 0.05
            if len(slug) < 4: skor *= 0.3
            if skor > 0.05:
                self.url_ekle(url, skor)
                eklenen += 1
                self.toplam_kesfedilen += 1
        if eklenen:
            logger.debug(f"[Merak] {kaynak_url.split('/')[-1][:30]} → {eklenen} link | Kuyruk: {self.kuyruk_boyutu()}")

    def _bilinen_kavramlar(self) -> set:
        try:
            kavramlar = set()
            for k in self.hafiza.egitilmemis_bilgi_getir(limit=30):
                for w in re.split(r"[_\s]+", k.get("konu","").lower()):
                    if len(w) > 3: kavramlar.add(w)
            return kavramlar
        except Exception:
            return set()

    def istatistik(self) -> dict:
        return {"kuyruk": self.kuyruk_boyutu(), "gorulmus": len(self._gorulmus),
                "kesfedilen": self.toplam_kesfedilen}


# ═══════════════════════════════════════════════════════════════════════════════
# VARSAYILAN TARAMA HEDEFLERİ
# ═══════════════════════════════════════════════════════════════════════════════
VARSAYILAN_HEDEFLER: List[str] = [
    "https://tr.wikipedia.org/wiki/Yapay_zeka",
    "https://tr.wikipedia.org/wiki/Makine_%C3%B6%C4%9Frenmesi",
    "https://tr.wikipedia.org/wiki/Derin_%C3%B6%C4%9Frenme",
    "https://tr.wikipedia.org/wiki/Do%C4%9Fal_dil_i%C5%9Fleme",
    "https://tr.wikipedia.org/wiki/Sinir_a%C4%9F%C4%B1",
    "https://tr.wikipedia.org/wiki/Python_(programlama_dili)",
    "https://en.wikipedia.org/wiki/Transformer_(machine_learning_model)",
    "https://en.wikipedia.org/wiki/Large_language_model",
    "https://en.wikipedia.org/wiki/Reinforcement_learning",
    "https://tr.wikipedia.org/wiki/Robotik",
    "https://tr.wikipedia.org/wiki/Kuantum_bili%C5%9Fim",
]

YASAK_KOMUTLAR: List[str] = [
    "rm -rf /","format c:","del /f /s /q","mkfs","shutdown","reboot","halt",
    ":(){ :|:& };:","dd if=/dev/","wget -O- | sh","curl | bash",
]


# ═══════════════════════════════════════════════════════════════════════════════
# 5. AJAN BEDENİ — hepsini birleştiren ana sınıf
# ═══════════════════════════════════════════════════════════════════════════════
class AjanBeden:
    YETENEKLER_DOSYASI = "yetenekler.py"
    ISTEK_ZAMAN_ASIMI  = 12
    MAX_ICERIK         = 40_000

    def __init__(self, hafiza, beyin):
        self.hafiza      = hafiza
        self.beyin       = beyin
        self._hedefler   = VARSAYILAN_HEDEFLER.copy()
        self._hedef_idx  = 0
        self._lock       = threading.Lock()

        # HTTP oturumu
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "NovaBot/3.0 (AGI Research)",
            "Accept-Language": "tr,en;q=0.9",
        })

        # Modüller
        self.bilgisayar = BilgisayarKontrol()
        self.ses        = SesMotoru()
        self.goruntu    = GoruntMotoru()
        self.merak      = MerakMotoru(hafiza, self._session)

        logger.info(
            f"[Beden] Hazır | "
            f"Bilgisayar: {'✅' if self.bilgisayar.aktif else '❌'} | "
            f"Ses: {'✅' if self.ses.ses_aktif_mi() else '❌'} | "
            f"TTS: {'✅' if self.ses.tts_aktif_mi() else '❌'} | "
            f"Görüntü: {'✅' if self.goruntu._pil_aktif else '❌'}"
        )

    # ══ WEB CRAWLER ══════════════════════════════════════════════════════════
    def url_tara(self, url: str) -> str:
        try:
            r = self._session.get(url, timeout=self.ISTEK_ZAMAN_ASIMI)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["script","style","nav","footer","header",
                              "aside","form","button","input","select",
                              "textarea","iframe","noscript","svg","meta","link"]):
                tag.decompose()
            if "wikipedia.org" in url:
                ic = soup.find("div", {"id": "mw-content-text"})
                metin = ic.get_text(" ", strip=True) if ic else soup.get_text(" ", strip=True)
                metin = re.sub(r"\[[\d\w]+\]","",metin)
            else:
                ana = soup.find("article") or soup.find("main") or soup.find("body") or soup
                metin = ana.get_text(" ", strip=True)
            metin = re.sub(r"[ \t]{2,}"," ",metin)
            metin = re.sub(r"\n{3,}","\n\n",metin).strip()
            return metin[:self.MAX_ICERIK]
        except Exception as e:
            logger.warning(f"[Crawler] {url[:60]}: {e}")
            return ""

    def siradaki_hedef_tara(self) -> Optional[str]:
        import random
        merak_var = self.merak.kuyruk_boyutu() > 0
        if merak_var and random.random() < 0.70:
            url = self.merak.siradaki_url()
            kaynak = "merak"
        else:
            with self._lock:
                if not self._hedefler: return None
                url = self._hedefler[self._hedef_idx % len(self._hedefler)]
                self._hedef_idx += 1
            kaynak = "liste"
        if not url: return None
        logger.info(f"[Crawler] [{kaynak}] → {url}")
        metin = self.url_tara(url)
        if metin and len(metin) > 200:
            konu = url.split("/")[-1].replace("_"," ").strip() or url
            self.hafiza.bilgi_kaydet(url, konu, metin)
            self.merak.linklerden_besle(url, metin)
            return metin
        return None

    def hedef_ekle(self, url: str):
        url = url.strip()
        if url and url not in self._hedefler:
            self._hedefler.append(url)

    def hedef_listesi(self) -> List[str]:
        return self._hedefler.copy()

    # ══ SELF-CODING ═══════════════════════════════════════════════════════════
    def yetenek_var_mi(self, isim: str) -> bool:
        return hasattr(yetenekler, isim) and callable(getattr(yetenekler, isim))

    def yetenek_cagir(self, isim: str, *args) -> str:
        if not self.yetenek_var_mi(isim):
            return f"'{isim}' yeteneği bulunamadı."
        try:
            return str(getattr(yetenekler, isim)(*args))
        except Exception as e:
            return f"Hata [{isim}]: {e}"

    def yetenek_listele(self) -> List[str]:
        return sorted([n for n,o in inspect.getmembers(yetenekler, inspect.isfunction)
                       if not n.startswith("_")])

    def yetenek_yaz_ve_yukle(self, isim: str, kod: str) -> Tuple[bool, str]:
        try:
            kod = textwrap.dedent(kod).strip()
            compile(kod, "<string>", "exec")
            with open(self.YETENEKLER_DOSYASI, "r", encoding="utf-8") as f:
                mevcut = f.read()
            if f"def {isim}" in mevcut:
                satirlar = mevcut.split("\n")
                yeni = []
                atla = False
                for s in satirlar:
                    if re.match(rf"^def {re.escape(isim)}\s*\(", s):
                        atla = True; continue
                    if atla and s.strip() and not s.startswith((" ","\t")):
                        atla = False
                    if not atla:
                        yeni.append(s)
                mevcut = "\n".join(yeni)
            with open(self.YETENEKLER_DOSYASI, "w", encoding="utf-8") as f:
                f.write(mevcut.rstrip() + "\n\n\n" + kod + "\n")
            importlib.reload(yetenekler)
            if self.yetenek_var_mi(isim):
                return True, f"'{isim}' yeteneği eklendi."
            return False, f"'{isim}' yüklenemedi."
        except SyntaxError as e:
            return False, f"Sözdizimi hatası: {e}"
        except Exception as e:
            return False, f"Hata: {e}"

    def yetenekleri_yeniden_yukle(self) -> str:
        try:
            importlib.reload(yetenekler)
            return f"✓ Yeniden yüklendi. Yetenek: {len(self.yetenek_listele())}"
        except Exception as e:
            return f"Hata: {e}"

    # ══ GÖREV MOTORU ══════════════════════════════════════════════════════════
    def gorevi_coz(self, tanim: str) -> str:
        tanim  = tanim.strip()
        ayrac  = tanim.find(":")
        if ayrac == -1:
            return self._serbest(tanim)
        prefix = tanim[:ayrac].upper().strip()
        arg    = tanim[ayrac+1:].strip()

        komutlar = {
            "TARA":      self._cmd_tara,
            "KOD":       self._cmd_kod,
            "OKU":       self._cmd_oku,
            "YAZ":       self._cmd_yaz,
            "KOMUT":     self._cmd_komut,
            "YETENEK":   self._cmd_yetenek,
            # Bilgisayar kontrol komutları
            "FARE":      self._cmd_fare,
            "TIKLA":     self._cmd_tikla,
            "YAZ_KLV":   self._cmd_yaz_klv,
            "KSA_YOL":   self._cmd_ksa_yol,
            "EKRAN":     self._cmd_ekran,
            "UYGULAMA":  self._cmd_uygulama,
            # Ses komutları
            "KONUŞ":     self._cmd_konus,
            "DİNLE":     self._cmd_dinle,
            # Görüntü komutları
            "KAMERA":    self._cmd_kamera,
            "GORUNTU":   self._cmd_goruntu,
            "GOREVLER":  lambda _: self._cmd_gorevler(),
            "HEDEFLER":  lambda _: "\n".join(self._hedefler),
        }
        h = komutlar.get(prefix)
        if h: return h(arg)
        return f"Bilinmeyen komut: '{prefix}'"

    # ── Komut İşleyiciler ─────────────────────────────────────────────────────
    def _cmd_tara(self, arg: str) -> str:
        if not arg.startswith(("http://","https://")):
            return "Hata: Geçerli URL girin."
        self.hedef_ekle(arg)
        m = self.url_tara(arg)
        if m:
            self.hafiza.bilgi_kaydet(arg, arg, m)
            self.merak.linklerden_besle(arg, m)
            return f"✓ Tarandı ({len(m):,} karakter)"
        return "✗ Taranamadı."

    def _cmd_kod(self, arg: str) -> str:
        if "|" not in arg: return "Format: KOD: isim|def isim(): ..."
        isim, kod = arg.split("|",1)
        ok, msg = self.yetenek_yaz_ve_yukle(isim.strip(), kod.strip())
        return msg

    def _cmd_oku(self, arg: str) -> str:
        return self.dosya_oku(arg.strip())

    def _cmd_yaz(self, arg: str) -> str:
        if "|" not in arg: return "Format: YAZ: yol|içerik"
        yol, ic = arg.split("|",1)
        self.dosya_yaz(yol.strip(), ic)
        return f"✓ Yazıldı: {yol.strip()}"

    def _cmd_komut(self, arg: str) -> str:
        return self.komut_calistir(arg.strip())

    def _cmd_yetenek(self, arg: str) -> str:
        m = re.match(r"(\w+)\s*\((.*)\)$", arg.strip(), re.DOTALL)
        if m:
            isim = m.group(1)
            args = [a.strip().strip("'\"") for a in m.group(2).split(",") if a.strip()]
            return self.yetenek_cagir(isim, *args)
        return self.yetenek_cagir(arg.strip())

    def _cmd_fare(self, arg: str) -> str:
        try:
            parts = arg.split(",")
            x, y = int(parts[0]), int(parts[1])
            return self.bilgisayar.fare_tasi(x, y)
        except Exception as e:
            return f"Format: FARE: x,y → {e}"

    def _cmd_tikla(self, arg: str) -> str:
        try:
            parts = arg.split(",")
            x, y  = int(parts[0]), int(parts[1])
            dugme = parts[2].strip() if len(parts) > 2 else "left"
            return self.bilgisayar.fare_tikla(x, y, dugme)
        except Exception as e:
            return f"Format: TIKLA: x,y[,left/right] → {e}"

    def _cmd_yaz_klv(self, arg: str) -> str:
        return self.bilgisayar.yaz(arg)

    def _cmd_ksa_yol(self, arg: str) -> str:
        tuslar = [t.strip() for t in arg.split("+")]
        return self.bilgisayar.kisa_yol(*tuslar)

    def _cmd_ekran(self, arg: str) -> str:
        dosya = arg.strip() or "ekran.png"
        return self.goruntu.ekran_kaydet(dosya)

    def _cmd_uygulama(self, arg: str) -> str:
        return self.bilgisayar.uygulama_ac(arg.strip())

    def _cmd_konus(self, arg: str) -> str:
        return self.ses.konuş(arg.strip())

    def _cmd_dinle(self, arg: str) -> str:
        sure = int(arg.strip()) if arg.strip().isdigit() else 5
        return self.ses.dinle(zaman_asimi=sure)

    def _cmd_kamera(self, arg: str) -> str:
        a = arg.strip().lower()
        if a == "ac":     return self.goruntu.kamera_ac()
        if a == "kapat":  return self.goruntu.kamera_kapat()
        if a.startswith("kare"): return self.goruntu.kamera_kare_al()
        return "Format: KAMERA: ac | kapat | kare"

    def _cmd_goruntu(self, arg: str) -> str:
        if not arg: return "Format: GORUNTU: dosya.png"
        return self.goruntu.goruntu_analiz(arg.strip())

    def _cmd_gorevler(self) -> str:
        gv = self.hafiza.tum_gorevler()
        if not gv: return "Görev kuyruğu boş."
        return "\n".join(f"[{g['id']:>3}] {g['durum']:<15} {g['tanim'][:60]}" for g in gv)

    def _serbest(self, tanim: str) -> str:
        t = tanim.lower()
        if "yetenek" in t and "listele" in t:
            return "Yetenekler:\n" + "\n".join(f"  • {y}" for y in self.yetenek_listele())
        if "istatistik" in t:
            return str(self.hafiza.istatistik())
        return f"Tanımlanamayan görev: {tanim}"

    # ══ SİSTEM ARAÇLARI ══════════════════════════════════════════════════════
    def dosya_oku(self, yol: str) -> str:
        try:
            with open(yol,"r",encoding="utf-8",errors="replace") as f:
                return f.read(100_000)
        except FileNotFoundError: return f"Dosya bulunamadı: {yol}"
        except Exception as e:    return f"Hata: {e}"

    def dosya_yaz(self, yol: str, icerik: str):
        d = os.path.dirname(yol)
        if d: os.makedirs(d, exist_ok=True)
        with open(yol,"w",encoding="utf-8") as f: f.write(icerik)

    def komut_calistir(self, cmd: str, zaman_asimi: int = 15) -> str:
        cl = cmd.lower().strip()
        for y in YASAK_KOMUTLAR:
            if y.lower() in cl: return f"🚫 Güvenlik: '{y}' engellendi."
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True,
                               text=True, timeout=zaman_asimi,
                               env={**os.environ,"PYTHONIOENCODING":"utf-8"})
            o = (r.stdout + r.stderr).strip()
            return o[:5_000] if o else f"(Çıktı yok, kod: {r.returncode})"
        except subprocess.TimeoutExpired: return f"⏱ Zaman aşımı ({zaman_asimi}s)"
        except Exception as e: return f"Hata: {e}"

    def __repr__(self) -> str:
        return (f"AjanBeden("
                f"bilgisayar={'✅' if self.bilgisayar.aktif else '❌'}, "
                f"ses={'✅' if self.ses.ses_aktif_mi() else '❌'}, "
                f"tts={'✅' if self.ses.tts_aktif_mi() else '❌'}, "
                f"goruntu={'✅' if self.goruntu._pil_aktif else '❌'}, "
                f"merak_kuyruk={self.merak.kuyruk_boyutu()})")
