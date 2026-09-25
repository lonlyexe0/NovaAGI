from __future__ import annotations
# ═══════════════════════════════════════════════════════════════════════════════
# body.py  —  Nova'nın Tam Bedeni  (Linux)
# ═══════════════════════════════════════════════════════════════════════════════
#
# Modüller:
#   🖱  BilgisayarKontrol  → fare, klavye, ekran görüntüsü, uygulama açma
#   🎤  SesMotoru          → mikrofon ile dinle, sesli yanıt ver
#   👁  GoruntMotoru       → ekran/kamera yakala, renk/nesne analiz et
#   🌐  MerakMotoru        → Wikipedia linklerini keşfet, özerk tara
#   🤖  AjanBeden          → hepsini birleştiren ana sınıf
#
# Linux bağımlılıkları (isteğe bağlı, ./install.sh kurar):
#   Ses çıkışı : pipewire (pw-play) veya pulseaudio-utils (paplay), ffmpeg
#   TTS yedeği : espeak-ng        Mikrofon : portaudio19-dev + pyaudio
#   Ekran      : python-mss (X11) / grim / gnome-screenshot (Wayland)
#   OCR        : tesseract-ocr tesseract-ocr-tur
#   Kontrol    : pyautogui (X11), xdotool, wmctrl, xclip / wl-clipboard
# ═══════════════════════════════════════════════════════════════════════════════

import os, re, time, logging, inspect, textwrap, importlib
import subprocess, threading, queue
from typing import Optional, List, Tuple, Dict, Any

import requests
from bs4 import BeautifulSoup

import yetenekler
import config_manager
import linux_desktop
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
        if linux_desktop.oturum_turu() == "tty":
            logger.info("[Bilgisayar] Grafik oturum yok; fare/klavye kontrolü devre dışı.")
            return
        try:
            import pyautogui
            self._gui = pyautogui
            self._gui.FAILSAFE = True   # Sol üst köşeye götürünce dur
            self._gui.PAUSE    = 0.05   # Her eylem arası 50ms — güvenli
            self._aktif = True
            if linux_desktop.oturum_turu() == "wayland":
                logger.info("[Bilgisayar] Wayland: pyautogui yalnızca XWayland pencerelerini kontrol edebilir.")
            else:
                logger.info("[Bilgisayar] pyautogui hazır.")
        except (Exception, SystemExit) as e:
            # pyautogui → mouseinfo, tkinter yoksa sys.exit() çağırır; motoru öldürmemeli
            logger.warning(f"[Bilgisayar] pyautogui kullanılamıyor ({e or 'python3-tk eksik'}) → "
                           "sudo apt install python3-tk && pip install pyautogui")

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
        self._gui.moveTo(x1, y1)
        self._gui.dragTo(x2, y2, duration=sure, button="left")
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
        """Ekran görüntüsü al ve kaydet (X11 ve Wayland)."""
        img = linux_desktop.ekran_goruntusu()
        if img is None:
            return "Ekran görüntüsü alınamadı."
        if bolge:
            x, y, w, h = bolge
            img = img.crop((x, y, x + w, y + h))
        img.save(dosya_yolu)
        return f"Ekran görüntüsü: {dosya_yolu}"

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
        """Uygulama, dosya veya URL aç. Örn: uygulama_ac('gedit'), uygulama_ac('code .')"""
        return linux_desktop.uygulama_ac(komut)

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
    Dinleme : speech_recognition + pyaudio (Google STT, TR/EN otomatik)
    Konuşma : edge-tts nöral ses (en-IE-EmilyNeural / tr-TR-EmelNeural)
              → çevrimdışı yedek: espeak-ng / spd-say / pyttsx3
    """

    SESLER = {"en": "en-IE-EmilyNeural", "tr": "tr-TR-EmelNeural"}

    def __init__(self):
        self._sr_aktif  = False
        self._tts_aktif = True
        self._tts_kuyruk: queue.Queue = queue.Queue()
        self._aktif_surec: Optional[subprocess.Popen] = None
        self._surec_lock = threading.Lock()

        try:
            import speech_recognition as sr
            self._sr = sr
            self._taniyici = sr.Recognizer()
            self._taniyici.energy_threshold = 300
            self._taniyici.dynamic_energy_threshold = True
            self._taniyici.pause_threshold = 0.8
            self._sr_aktif = True
            logger.info("[Ses] speech_recognition hazır.")
        except ImportError:
            logger.warning("[Ses] speech_recognition bulunamadı → pip install SpeechRecognition pyaudio")

        self._tts_thread = threading.Thread(target=self._tts_dongusu, daemon=True, name="NovaTTS")
        self._tts_thread.start()
        logger.info("[Ses] Nova ses servisi başlatıldı.")

    @staticmethod
    def _metin_temizle(metin: str) -> str:
        """Kod bloklarını, linkleri ve markdown işaretlerini temizler."""
        metin = re.sub(r'```[\s\S]*?```', '', metin)
        metin = re.sub(r'`[^`]*`', '', metin)
        metin = re.sub(r'http\S+|www\.\S+', '', metin)
        metin = re.sub(r'[*#_~\[\]\(\)>|═─│├└╔╗╚╝║]', ' ', metin)
        return re.sub(r'\s+', ' ', metin).strip()

    def _surec_calistir(self, surec: Optional[subprocess.Popen]) -> bool:
        if surec is None:
            return False
        with self._surec_lock:
            self._aktif_surec = surec
        try:
            return surec.wait() == 0
        finally:
            with self._surec_lock:
                self._aktif_surec = None

    def _edge_tts(self, metin: str, lang: str) -> bool:
        try:
            import asyncio
            import tempfile
            import edge_tts
        except ImportError:
            return False
        fd, mp3 = tempfile.mkstemp(suffix=".mp3", prefix="nova_tts_")
        os.close(fd)
        try:
            asyncio.run(edge_tts.Communicate(metin, self.SESLER.get(lang, self.SESLER["en"])).save(mp3))
            return os.path.getsize(mp3) > 0 and self._surec_calistir(linux_desktop.ses_cal(mp3))
        except Exception as e:
            logger.debug(f"[TTS] edge-tts atlandı: {e}")
            return False
        finally:
            try:
                os.remove(mp3)
            except OSError:
                pass

    def _yerel_tts(self, metin: str, lang: str) -> bool:
        cmd = linux_desktop.yerel_tts_komutu(metin, lang)
        if cmd:
            try:
                return self._surec_calistir(subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                                             stderr=subprocess.DEVNULL))
            except Exception as e:
                logger.debug(f"[TTS] {cmd[0]} hatası: {e}")
        try:
            import pyttsx3
            eng = pyttsx3.init()
            eng.setProperty("rate", 170)
            eng.say(metin)
            eng.runAndWait()
            return True
        except Exception:
            return False

    def _tts_dongusu(self):
        """TTS kuyruğunu işler: önce nöral edge-tts, olmazsa çevrimdışı motor."""
        while True:
            metin = self._tts_kuyruk.get()
            try:
                if metin is None:
                    break
                temiz = self._metin_temizle(metin)[:450]
                if temiz:
                    lang = config_manager.get_language() or "tr"
                    if not self._edge_tts(temiz, lang) and not self._yerel_tts(temiz, lang):
                        logger.debug("[TTS] Hiçbir TTS motoru çalışmadı (espeak-ng kurun).")
            except Exception as e:
                logger.debug(f"[TTS Döngü] Hata: {e}")
            finally:
                self._tts_kuyruk.task_done()

    def konuş(self, metin: str, bloke: bool = False):
        """Metni sesli oku (yeni metin, çalan sesi keser)."""
        if not self._tts_aktif:
            return "TTS aktif değil"
        self.sustur()
        metin_kisa = metin[:500]
        self._tts_kuyruk.put(metin_kisa)
        if bloke:
            self._tts_kuyruk.join()
        return f"Sesli okunuyor: {metin_kisa[:60]}..."

    konus = konuş

    def sustur(self):
        """Bekleyen konuşmaları siler ve çalan sesi durdurur."""
        try:
            while True:
                self._tts_kuyruk.get_nowait()
                self._tts_kuyruk.task_done()
        except queue.Empty:
            pass
        with self._surec_lock:
            if self._aktif_surec and self._aktif_surec.poll() is None:
                self._aktif_surec.terminate()

    def dinle(self, zaman_asimi: int = 6, dil: Optional[str] = None) -> str:
        """
        Mikrofondan dinler ve metne çevirir. Türkçe/İngilizce otomatik denenir.
        Döner: tanınan metin veya boş string.
        """
        if not self._sr_aktif:
            logger.warning("[Ses] Ses tanıma aktif değil (pip install SpeechRecognition pyaudio)")
            return ""

        if dil:
            diller = [dil, "en-US" if dil.startswith("tr") else "tr-TR"]
        else:
            diller = ["en-US", "tr-TR"] if config_manager.get_language() == "en" else ["tr-TR", "en-US"]

        sr = self._sr
        try:
            with sr.Microphone() as kaynak:
                logger.info(f"[Ses] 🎙️ Dinleniyor... ({diller[0]} / {diller[1]})")
                try:
                    self._taniyici.adjust_for_ambient_noise(kaynak, duration=0.25)
                except Exception:
                    pass
                ses = self._taniyici.listen(kaynak, timeout=zaman_asimi, phrase_time_limit=15)

            for hedef_dil in diller:
                try:
                    metin = self._taniyici.recognize_google(ses, language=hedef_dil)
                    if metin and metin.strip():
                        logger.info(f"[Ses] Algılandı ({hedef_dil}): {metin}")
                        return metin.strip()
                except sr.UnknownValueError:
                    continue
                except Exception as ex:
                    logger.debug(f"[Ses] recognize_google ({hedef_dil}) hatası: {ex}")
            return ""
        except sr.WaitTimeoutError:
            logger.info("[Ses] Dinleme zaman aşımı (ses gelmedi).")
            return ""
        except Exception as e:
            logger.error(f"[Ses] Mikrofon hatası: {e}")
            return ""

    def ses_aktif_mi(self) -> bool:
        return self._sr_aktif

    def tts_aktif_mi(self) -> bool:
        return self._tts_aktif


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
            from PIL import Image, ImageFilter
            self._Image      = Image
            self._ImageFilter= ImageFilter
            self._pil_aktif  = True
            logger.info("[Görüntü] Pillow hazır.")
        except ImportError:
            logger.warning("[Görüntü] Pillow bulunamadı → pip install pillow")

        try:
            import cv2
            self._cv2      = cv2
            self._cv_aktif = True
            logger.info("[Görüntü] OpenCV hazır.")
        except ImportError:
            logger.warning("[Görüntü] OpenCV bulunamadı → pip install opencv-python")

    # ── Ekran ─────────────────────────────────────────────────────────────────
    def ekran_yakala(self, bolge: Optional[Tuple] = None) -> Optional[Any]:
        """Ekran görüntüsünü PIL Image olarak döndür (bolge = (x1, y1, x2, y2))."""
        if not self._pil_aktif: return None
        img = linux_desktop.ekran_goruntusu()
        return img.crop(bolge) if (img is not None and bolge) else img

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
            return "OCR için: sudo apt install tesseract-ocr tesseract-ocr-tur && pip install pytesseract"
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
# 3.1 OTONOM GÖRSEL GÖZLEMCİ & EKRAN/VİDEO ANALİZİ
# ═══════════════════════════════════════════════════════════════════════════════
class GorselGozlemci:
    """
    Nova'nın görsel dünyayı gözlemleme ve anlama yeteneği:
    - İsteğe göre otonom olarak tek kare fotoğraf mı yoksa kısa video/hareket analizi mi yapacağına karar verir.
    - OpenCV ile hareket alanı, yoğunluğu, sahne geçişlerini ve dominant renkleri hesaplar.
    - Tesseract OCR ile ekrandaki başlıkları ve arayüzü çıkarır.
    - Nova için doğal dilde görsel durum raporu hazırlar ve seslendirir.
    """

    def __init__(self, goruntu_motoru: GoruntMotoru, ses_motoru: SesMotoru, hafiza=None):
        self.goruntu = goruntu_motoru
        self.ses = ses_motoru
        self.hafiza = hafiza
        self._cv2 = getattr(goruntu_motoru, "_cv2", None)

    def karar_ver(self, istek: str) -> str:
        """Kullanıcı isteğine göre otonom olarak 'video' mu yoksa 'snapshot' mı olacağını belirler."""
        if not istek:
            return "snapshot"
        il = istek.lower()
        dinamik_anahtarlar = [
            "izle", "video", "hareket", "ne oluyor", "oyun", "animasyon",
            "kaydet", "akış", "takip", "izler misin", "izleyin", "neler dönüyor",
            "watch", "motion", "clip", "dynamic", "happening", "moving", "stream"
        ]
        if any(w in il for w in dinamik_anahtarlar):
            return "video"
        return "snapshot"

    def _ekran_yakala_pil(self):
        """Masaüstü ekran görüntüsü (X11 / Wayland)."""
        return linux_desktop.ekran_goruntusu()

    def _ocr_metin_cikar(self, img) -> str:
        """Görüntüden metin çıkarır (Tesseract; Türkçe + İngilizce)."""
        if img is None:
            return ""
        try:
            import pytesseract
            try:
                return pytesseract.image_to_string(img, lang="tur+eng")[:1000]
            except pytesseract.TesseractError:
                return pytesseract.image_to_string(img, lang="eng")[:1000]
        except Exception as e:
            logger.debug(f"[Gözlemci] OCR atlandı: {e}")
            return ""

    def _statik_analiz(self, img) -> Dict[str, Any]:
        """Tek kare analizi: çözünürlük, parlaklık/tema, OCR metinleri."""
        if img is None:
            return {"hata": "Görüntü yakalanamadı"}
        from PIL import ImageStat
        w, h = img.size
        r, g, b = ImageStat.Stat(img.convert("RGB").resize((100, 100))).mean[:3]
        parlaklik = (r * 299 + g * 587 + b * 114) / 1000
        tema = "Karanlık Mod (Dark Mode)" if parlaklik < 120 else "Aydınlık Mod (Light Mode)"
        return {"mod": "snapshot", "boyut": f"{w}x{h}", "tema": tema,
                "parlaklik": round(parlaklik, 1), "metin": self._ocr_metin_cikar(img).strip()}

    def _video_analiz(self, sure_sn: float = 2.4, fps: int = 4) -> Dict[str, Any]:
        """2-3 saniye boyunca ekran kareleri yakalayarak hareket, değişim ve video akışını inceler."""

        kare_sayisi = int(sure_sn * fps)
        aralik = 1.0 / fps
        kareler_pil = []

        for _ in range(kare_sayisi):
            f = self._ekran_yakala_pil()
            if f:
                kareler_pil.append(f)
            time.sleep(aralik)

        if not kareler_pil:
            return {"hata": "Ekran video kaydı alınamadı."}

        toplam_hareket_orani = 0.0
        hareketli_bolgeler = []
        cv = self._cv2

        if cv and len(kareler_pil) >= 2:
            import numpy as np
            prev_gray = cv.cvtColor(np.array(kareler_pil[0].convert("RGB").resize((320, 180))), cv.COLOR_RGB2GRAY)
            for k in kareler_pil[1:]:
                curr_gray = cv.cvtColor(np.array(k.convert("RGB").resize((320, 180))), cv.COLOR_RGB2GRAY)
                diff = cv.absdiff(prev_gray, curr_gray)
                _, thresh = cv.threshold(diff, 20, 255, cv.THRESH_BINARY)
                hareket_px = cv.countNonZero(thresh)
                oran = (hareket_px / (320 * 180)) * 100
                toplam_hareket_orani += oran

                contours, _ = cv.findContours(thresh, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
                for cnt in contours:
                    if cv.contourArea(cnt) > 250:
                        x, y, w, h = cv.boundingRect(cnt)
                        konum = "Merkez"
                        if x < 100: konum = "Sol Bölge"
                        elif x > 200: konum = "Sağ Bölge"
                        if y < 60: konum += " / Üst"
                        elif y > 120: konum += " / Alt"
                        hareketli_bolgeler.append(konum)

                prev_gray = curr_gray

            ort_hareket = toplam_hareket_orani / (len(kareler_pil) - 1)
        elif len(kareler_pil) >= 2:
            # OpenCV yoksa Pillow ile kaba hareket ölçümü
            from PIL import ImageChops, ImageStat
            kucuk = [k.convert("L").resize((320, 180)) for k in kareler_pil]
            oranlar = [ImageStat.Stat(ImageChops.difference(a, b).point(lambda p: 255 if p > 20 else 0)).mean[0] / 2.55
                       for a, b in zip(kucuk, kucuk[1:])]
            ort_hareket = sum(oranlar) / len(oranlar)
        else:
            ort_hareket = 0.0

        son_kare_metin = self._ocr_metin_cikar(kareler_pil[-1])

        from collections import Counter
        bolge_ozeti = ", ".join([b for b, _ in Counter(hareketli_bolgeler).most_common(3)]) if hareketli_bolgeler else "Genel durağan"

        hareket_seviyesi = "Yüksek (Video oynuyor / Hızlı hareket)" if ort_hareket > 8.0 else \
                           "Orta (Sayfa kaydırma / Arayüz etkileşimi)" if ort_hareket > 1.5 else \
                           "Düşük / Sabit (Statik görüntü veya minimal imleç hareketi)"

        return {
            "mod": "video",
            "sure": f"{sure_sn:.1f} saniye ({len(kareler_pil)} kare)",
            "hareket_seviyesi": hareket_seviyesi,
            "hareket_yuzdesi": f"%{ort_hareket:.1f}",
            "hareket_odaklari": bolge_ozeti,
            "metin": son_kare_metin.strip()
        }

    def goruntule_ve_incele(self, istek: str = "", seslendir: bool = True) -> str:
        """Kullanıcının isteğini anlayıp otonom karar vererek ekranı/videoyu inceler ve açıklar."""
        mod = self.karar_ver(istek)
        lang = config_manager.get_language() or "tr"

        if mod == "video":
            analiz = self._video_analiz(sure_sn=2.4, fps=4)
            if "hata" in analiz:
                return f"⚠️ {analiz['hata']}"

            if lang == "en":
                rapor = (
                    f"📹 **Screen Activity Observation ({analiz['sure']}):**\n"
                    f"• **Motion Intensity:** {analiz['hareket_seviyesi']} ({analiz['hareket_yuzdesi']})\n"
                    f"• **Active Focus Zones:** {analiz['hareket_odaklari']}\n"
                )
                if analiz.get("metin"):
                    rapor += f"• **Visible Text / UI Elements:**\n```\n{analiz['metin'][:400]}\n```"
                ses_ozeti = f"I observed your screen for {analiz['sure']}. Motion level is {analiz['hareket_seviyesi']}. Primary movement detected at {analiz['hareket_odaklari']}."
            else:
                rapor = (
                    f"📹 **Ekran Canlı Hareket Analizi ({analiz['sure']}):**\n"
                    f"• **Hareket / Değişim Düzeyi:** {analiz['hareket_seviyesi']} ({analiz['hareket_yuzdesi']})\n"
                    f"• **Odak Bölgeleri:** {analiz['hareket_odaklari']}\n"
                )
                if analiz.get("metin"):
                    rapor += f"• **Ekranda Tespit Edilen Başlıklar / Yazılar:**\n```\n{analiz['metin'][:400]}\n```"
                ses_ozeti = f"Ekranınızı {analiz['sure']} boyunca izledim. Hareket düzeyi {analiz['hareket_seviyesi']}. Başlıca hareket {analiz['hareket_odaklari']} üzerinde gerçekleşti."
        else:
            img = self._ekran_yakala_pil()
            analiz = self._statik_analiz(img)
            if "hata" in analiz:
                return f"⚠️ {analiz['hata']}"

            if lang == "en":
                rapor = (
                    f"🖼️ **Screen Snapshot Visual Analysis ({analiz['boyut']}):**\n"
                    f"• **Appearance:** {analiz['tema']} (Brightness: {analiz['parlaklik']}/255)\n"
                )
                if analiz.get("metin"):
                    rapor += f"• **Detected Content & Text:**\n```\n{analiz['metin'][:400]}\n```"
                ses_ozeti = f"I captured and inspected your screen. Display is {analiz['tema']} at {analiz['boyut']} resolution."
            else:
                rapor = (
                    f"🖼️ **Ekran Görüntüsü Analizi ({analiz['boyut']}):**\n"
                    f"• **Görünüm:** {analiz['tema']} (Parlaklık: {analiz['parlaklik']}/255)\n"
                )
                if analiz.get("metin"):
                    rapor += f"• **Ekranda Görülen Metin & Başlıklar:**\n```\n{analiz['metin'][:400]}\n```"
                ses_ozeti = f"Ekranınızın görselini inceledim. {analiz['boyut']} çözünürlüğünde, {analiz['tema']} açık görünüyor."

        if self.hafiza:
            try:
                self.hafiza.ani_kaydet("gozlem", rapor[:500])
            except Exception:
                pass

        if seslendir and self.ses:
            self.ses.konuş(ses_ozeti)

        return rapor

    def foto_analiz(self, img_veya_yol, istek: str = "") -> str:
        """Kullanıcının telefondan veya dosya olarak gönderdiği fotoğrafı analiz eder."""
        from PIL import Image
        try:
            if isinstance(img_veya_yol, str):
                img = Image.open(img_veya_yol)
            else:
                img = img_veya_yol

            analiz = self._statik_analiz(img)
            if "hata" in analiz:
                return f"⚠️ Fotoğraf incelenemedi: {analiz['hata']}"

            rapor = (
                f"📸 **Görsel Analiz Raporu ({analiz['boyut']}):**\n"
                f"• **Görsel Teması:** {analiz['tema']} (Parlaklık: {analiz['parlaklik']}/255)\n"
            )
            if analiz.get("metin"):
                rapor += f"• **Tespit Edilen Metin / İçerik:**\n```\n{analiz['metin'][:400]}\n```\n"
            else:
                rapor += "• **Metin Tespiti:** Görselde okunabilir belirgin bir metin saptanmadı.\n"

            if istek:
                rapor += f"• **Kullanıcı Notu:** *{istek}*\n"

            if self.hafiza:
                try:
                    self.hafiza.ani_kaydet("foto_analiz", rapor[:500])
                except Exception:
                    pass

            return rapor
        except Exception as e:
            return f"⚠️ Görsel işleme hatası: {e}"


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
    "rm -rf /", "rm -rf ~", "rm -rf --no-preserve-root", "mkfs", "dd if=", "> /dev/sd", "> /dev/nvme",
    "shutdown", "reboot", "poweroff", "halt", "init 0", "systemctl poweroff", "chmod -r 777 /",
    ":(){ :|:& };:", "wget -o- |", "curl | bash", "curl | sh",
]


# ═══════════════════════════════════════════════════════════════════════════════
# 5. AJAN BEDENİ — hepsini birleştiren ana sınıf
# ═══════════════════════════════════════════════════════════════════════════════
class AjanBeden:
    YETENEKLER_DOSYASI = os.path.abspath(yetenekler.__file__)
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
        self.gozlemci   = GorselGozlemci(self.goruntu, self.ses, hafiza)

        logger.info(
            f"[Beden] Hazır | "
            f"Bilgisayar: {'✅' if self.bilgisayar.aktif else '❌'} | "
            f"Ses: {'✅' if self.ses.ses_aktif_mi() else '❌'} | "
            f"TTS: {'✅' if self.ses.tts_aktif_mi() else '❌'} | "
            f"Görüntü: {'✅' if self.goruntu._pil_aktif else '❌'} | "
            f"Gözlemci: ✅"
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
            "MERAK":     self._cmd_merak,
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

    def _cmd_merak(self, arg: str) -> str:
        """Merak kuyruğundan (veya verilen URL'den) bir sayfa keşfeder."""
        if arg.startswith(("http://", "https://")):
            return self._cmd_tara(arg)
        metin = self.siradaki_hedef_tara()
        return f"✓ Keşfedildi ({len(metin):,} karakter)" if metin else "Keşfedilecek yeni sayfa yok."

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
            r = subprocess.run(cmd, shell=True, executable="/bin/bash", capture_output=True,
                               text=True, timeout=zaman_asimi, errors="replace",
                               env={**os.environ, "PYTHONIOENCODING": "utf-8", "LC_ALL": "C.UTF-8"})
            o = (r.stdout + r.stderr).strip()
            return o[:5_000] if o else f"(Çıktı yok, kod: {r.returncode})"
        except subprocess.TimeoutExpired: return f"⏱ Zaman aşımı ({zaman_asimi}s)"
        except Exception as e: return f"Hata: {e}"

    # ══ AKILLI ARAÇ VE YETENEK YÖNETİCİSİ ═════════════════════════════════════
    def akilli_arac_isleyici(self, prompt: str) -> Optional[str]:
        """
        Kullanıcı mesajındaki araç niyetlerini (hesaplama, arama, dosya okuma, kod çalıştırma)
        otonom olarak algılar ve uygun yetenek fonksiyonunu çalıştırır.
        """
        p = prompt.strip()
        pl = p.lower()
        lang = config_manager.get_language() or "tr"

        # 1. Doğrudan Komutlar
        if pl.startswith("!izle") or pl.startswith("!ekran") or pl.startswith("!gozlem") or pl.startswith("!watch"):
            arg = p.split(" ", 1)[1] if " " in p else ""
            return self.gozlemci.goruntule_ve_incele(arg or p)

        if pl.startswith("!hesapla ") or pl.startswith("!calc "):
            ifade = p.split(" ", 1)[1]
            return f"🧮 **Hesaplama Sonucu**: `{yetenekler.hesapla(ifade)}`"

        if pl.startswith("!wiki ") or pl.startswith("!vikipedi "):
            konu = p.split(" ", 1)[1]
            res = yetenekler.wiki_ara(konu, lang=lang)
            self._bilgi_sakla(konu, res)
            return res

        if pl.startswith("!ara ") or pl.startswith("!search "):
            sorgu = p.split(" ", 1)[1]
            res = yetenekler.web_ara(sorgu, lang=lang)
            self._bilgi_sakla(sorgu, res)
            return res

        if pl.startswith("!oku ") or pl.startswith("!read "):
            dosya = p.split(" ", 1)[1]
            return yetenekler.dosya_oku(dosya)

        if pl.startswith("!python ") or pl.startswith("!kod "):
            kod = p.split(" ", 1)[1]
            return yetenekler.python_calistir(kod)

        if pl.startswith("!zaman") or pl.startswith("!saat") or pl.startswith("!time"):
            return f"⏰ **Tarih & Saat**: {yetenekler.tarih_saat()} ({yetenekler.bugun_gun()})"

        if pl.startswith("!nova") or pl.startswith("!durum") or pl.startswith("!teshis") or pl.startswith("!magi") or any(w in pl for w in ["nova durumu", "sistem durumu", "magi durumu", "sağlık raporu"]):
            return yetenekler.nova_sistem_durum()

        if pl.startswith("!guvenlik") or pl.startswith("!atfield") or any(w in pl for w in ["güvenlik durumu", "erişim durumu", "kalkan durumu"]):
            return yetenekler.nova_guvenlik_durum()

        if pl.startswith("!senkron") or pl.startswith("!sync") or any(w in pl for w in ["senkronizasyon", "senkron oranı", "sync ratio", "nöral bağ"]):
            return yetenekler.nova_senkron()

        if pl.startswith("!brifing") or pl.startswith("!briefing") or any(w in pl for w in ["günlük brifing", "sabah brifingi", "durum brifingi", "sistem brifingi", "brifing ver"]):
            return yetenekler.gunluk_brifing()

        if pl.startswith("!eylem ") or pl.startswith("!action "):
            eylem_adi = p.split(" ", 1)[1]
            return linux_desktop.sistem_eylemi(eylem_adi, en=(lang == "en"))


        # 2. Matematik Hesabı Niyet Tespiti (örn: 154 * 28 + 19 kaç eder)
        math_match = re.search(r"(\d+\s*[\+\-\*\/\^%]\s*\d+[\s\d\+\-\*\/\^%]*)", p)
        if math_match and any(w in pl for w in ["hesapla", "kaç eder", "sonucu", "eşittir", "=", "calculate", "what is"]):
            expr = math_match.group(1).replace("^", "**")
            res = yetenekler.hesapla(expr)
            if yetenekler.basarili_mi(res):
                return f"🧮 `{expr.strip()}` = **{res}**"

        # 3. Saat / Tarih Niyeti (Türkçe & İngilizce)
        if any(w in pl for w in ["saat kaç", "bugün ayın kaçı", "hangi gündeyiz", "tarih ne", "what time is it", "current time", "what day is it"]):
            return f"⏰ Şu an: **{yetenekler.tarih_saat()}**, **{yetenekler.bugun_gun()}**."

        # 3.1 Görsel Gözlem ve Ekran/Video İzleme Niyeti (Otonom Karar)
        gorsel_tetikleyiciler = [
            "ekranımı izle", "ekranıma bak", "ekranda ne var", "ekranda ne oluyor",
            "ekranımı gör", "ekranı incele", "fotoğrafı incele", "resme bak", "görsele bak",
            "videoyu izle", "burada ne oluyor", "ne değişti", "ekranı gözlemle", "ekranı izle",
            "watch my screen", "look at my screen", "what is on my screen",
            "observe screen", "what is happening", "inspect screen"
        ]
        if any(t in pl for t in gorsel_tetikleyiciler):
            return self.gozlemci.goruntule_ve_incele(p)

        # 4. İnternet / Wikipedia Canlı Araştırma Tespiti (Genişletilmiş Doğal Dil)
        search_triggers_tr = [
            r"(.+?)\s+(nedir\??|kimdir\??|nerededir\??|nelerdir\??)",
            r"(.+?)\s+hakkında\s+(bilgi\s+ver|bilgi|ne\s+biliyorsun|anlat)",
            r"(.+?)\s+(nasıl\s+çalışır|tarihçesi|açıkla|özetle)",
            r"(araştır|ara|bilgi\s+ver)\s+[:\s]*(.+)",
        ]
        search_triggers_en = [
            r"(what is|who is|where is|tell me about|explain|describe)\s+([a-zA-Z0-9\s_\-]+)",
            r"([a-zA-Z0-9\s_\-]+)\s+(definition|history|overview|explained)",
            r"(search for|search|lookup)\s+([a-zA-Z0-9\s_\-]+)",
        ]

        query = None
        for pat in search_triggers_tr + search_triggers_en:
            m = re.search(pat, p, re.IGNORECASE)
            if m:
                groups = [g for g in m.groups() if g and len(g) > 2]
                for g in groups:
                    clean_g = re.sub(r"(nedir\??|kimdir\??|nerededir\??|hakkında|bilgi\s+ver|anlat|açıkla|what is|who is|tell me about|search for)", "", g, flags=re.IGNORECASE).strip()
                    if len(clean_g) > 2 and not any(w == clean_g.lower() for w in ["sen", "ben", "bu", "o", "biz", "siz", "you", "me", "it", "adın", "your name"]):
                        query = clean_g
                        break
                if query:
                    break

        if query:
            wiki_res = yetenekler.wiki_ara(query, lang=lang)
            if yetenekler.basarili_mi(wiki_res):
                self._bilgi_sakla(query, wiki_res)
                return wiki_res

            # Wikipedia yetersizse DuckDuckGo / Web araması yap
            web_res = yetenekler.web_ara(query, lang=lang)
            if yetenekler.basarili_mi(web_res):
                self._bilgi_sakla(query, web_res)
                return web_res

        return None


    def _bilgi_sakla(self, konu: str, icerik: str):
        if yetenekler.basarili_mi(icerik):
            try:
                self.hafiza.bilgi_kaydet(konu=konu, icerik=icerik[:2000],
                                         url=f"nova://arama/{konu.strip().replace(' ', '_')}")
            except Exception as e:
                logger.debug(f"[Beden] Bilgi kaydedilemedi: {e}")

    def __repr__(self) -> str:
        return (f"AjanBeden("
                f"bilgisayar={'✅' if self.bilgisayar.aktif else '❌'}, "
                f"ses={'✅' if self.ses.ses_aktif_mi() else '❌'}, "
                f"tts={'✅' if self.ses.tts_aktif_mi() else '❌'}, "
                f"goruntu={'✅' if self.goruntu._pil_aktif else '❌'}, "
                f"merak_kuyruk={self.merak.kuyruk_boyutu()})")

