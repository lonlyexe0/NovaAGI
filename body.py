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
import config_manager
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
    Konuşma: Hızlı Neural TTS (edge-tts / F.R.I.D.A.Y. - Kerry Condon Irish Neural) + pyttsx3 fallback
    """

    def __init__(self):
        self._sr_aktif  = False
        self._tts_aktif = False
        self._tts_kuyruk: queue.Queue = queue.Queue()
        self._tts_thread = None
        self._stop_event = threading.Event()

        # F.R.I.D.A.Y. ses yolu (varsa)
        self._base_dir = os.path.dirname(os.path.abspath(__file__))
        self._speaker_wav = os.path.join(self._base_dir, "kerry_condon_friday.wav")

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

        # TTS Başlat
        self._tts_aktif = True
        self._tts_thread = threading.Thread(
            target=self._tts_dongusu, daemon=True, name="NovaTTS"
        )
        self._tts_thread.start()
        logger.info("[Ses] Nova TTS Servisi başlatıldı (Neural edge-tts + SAPI pyttsx3).")

    def _metin_temizle(self, metin: str) -> str:
        """Metindeki kod bloklarını, linkleri ve markdown işaretlerini temizler."""
        metin = re.sub(r'```[\s\S]*?```', '', metin)
        metin = re.sub(r'`[^`]*`', '', metin)
        metin = re.sub(r'http\S+|www\.\S+', '', metin)
        metin = re.sub(r'[*#_~\[\]\(\)>]', ' ', metin)
        metin = re.sub(r'\s+', ' ', metin).strip()
        return metin

    def _cal_ses_dosyasi(self, dosya_yolu: str) -> bool:
        """Windows mciSendString kullanarak MP3 veya WAV dosyasını sorunsuz çalar."""
        import ctypes
        try:
            abs_path = os.path.abspath(dosya_yolu)
            winmm = ctypes.windll.winmm
            alias = f"novatts_{int(time.time()*1000)}"
            winmm.mciSendStringW(f'open "{abs_path}" type mpegvideo alias {alias}', None, 0, None)
            winmm.mciSendStringW(f'play {alias} wait', None, 0, None)
            winmm.mciSendStringW(f'close {alias}', None, 0, None)
            return True
        except Exception as e:
            logger.debug(f"[Ses] Ses çalma hatası: {e}")
            return False

    def _tts_dongusu(self):
        """TTS kuyruğunu işleyen arka plan thread'i.
        Önce ultra-hızlı Neural edge-tts (Kerry Condon İrlanda kadın sesi) dener,
        çevrimdışıysa COM korumalı pyttsx3 SAPI'ye geçer.
        """
        import tempfile
        import asyncio

        # Thread içinde COM başlat (Windows SAPI için zorunlu)
        has_com = False
        try:
            import pythoncom
            pythoncom.CoInitialize()
            has_com = True
        except Exception:
            pass

        # Yedek pyttsx3 motoru (thread-safe yerel kurulum)
        pyttsx_eng = None
        try:
            import pyttsx3
            pyttsx_eng = pyttsx3.init()
            pyttsx_eng.setProperty("rate", 175)
            pyttsx_eng.setProperty("volume", 0.95)
            # Kadın sesini önceliklendir (Zira / Female)
            for ses in pyttsx_eng.getProperty("voices"):
                s_name = getattr(ses, "name", "").lower()
                s_id = getattr(ses, "id", "").lower()
                if "zira" in s_name or "zira" in s_id or "female" in s_name:
                    pyttsx_eng.setProperty("voice", ses.id)
                    break
        except Exception as e:
            logger.debug(f"[TTS] pyttsx3 thread motoru başlatılamadı: {e}")

        while True:
            try:
                metin = self._tts_kuyruk.get(timeout=1)
                if metin is None:
                    break

                temiz = self._metin_temizle(metin)
                if not temiz:
                    self._tts_kuyruk.task_done()
                    continue

                # Kısalt (uzun yanıtları 450 karakterde sınırla)
                temiz = temiz[:450]
                lang = config_manager.get_language() or "en"
                konusuldu = False

                # 1. Aşama: edge-tts (F.R.I.D.A.Y. stili Kerry Condon / Neural Ses)
                try:
                    import edge_tts
                    # İngilizce: Kerry Condon'ın İrlanda kadın sesi; Türkçe: Emel Neural
                    voice_name = "en-IE-EmilyNeural" if lang == "en" else "tr-TR-EmelNeural"
                    mp3_path = os.path.join(tempfile.gettempdir(), f"nova_speech_{int(time.time()*1000)}.mp3")
                    
                    async def _uret():
                        communicate = edge_tts.Communicate(temiz, voice_name)
                        await communicate.save(mp3_path)

                    asyncio.run(_uret())

                    if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 0:
                        konusuldu = self._cal_ses_dosyasi(mp3_path)
                        try:
                            os.remove(mp3_path)
                        except Exception:
                            pass
                except Exception as e:
                    logger.debug(f"[TTS] edge-tts atlandı ({e}), SAPI'ye geçiliyor...")

                # 2. Aşama: Çevrimdışı SAPI (pyttsx3) Fallback
                if not konusuldu and pyttsx_eng:
                    try:
                        pyttsx_eng.say(temiz)
                        pyttsx_eng.runAndWait()
                        konusuldu = True
                    except Exception as e:
                        logger.debug(f"[TTS pyttsx3] Hata: {e}")

                self._tts_kuyruk.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.debug(f"[TTS Döngü] Hata: {e}")

        if has_com:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

    def konuş(self, metin: str, bloke: bool = False):
        """Nova'nın sesi: metni sesli oku."""
        if not self._tts_aktif:
            return "TTS aktif değil"
        metin_kisa = metin[:500]
        self._tts_kuyruk.put(metin_kisa)
        if bloke:
            self._tts_kuyruk.join()
        return f"Sesli okunuyor: {metin_kisa[:60]}..."
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

        try:
            import cv2
            self._cv2      = cv2
            self._cv_aktif = True
            logger.info("[Görüntü] OpenCV hazır.")
        except ImportError:
            logger.warning("[Görüntü] OpenCV bulunamadı → pip install opencv-python")

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
# 3.1 OTONOM GÖRSEL GÖZLEMCİ & EKRAN/VİDEO ANALİZİ
# ═══════════════════════════════════════════════════════════════════════════════
class GorselGozlemci:
    """
    Nova'nın görsel dünyayı gözlemleme ve anlama yeteneği:
    - İsteğe göre otonom olarak tek kare fotoğraf mı yoksa kısa video/hareket analizi mi yapacağına karar verir.
    - OpenCV ile hareket alanı, yoğunluğu, sahne geçişlerini ve dominant renkleri hesaplar.
    - Windows yerel OCR ile ekrandaki başlıkları ve arayüzü çıkarır.
    - Nova için doğal dilde görsel durum raporu hazırlar ve F.R.I.D.A.Y. ile seslendirir.
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
        """Masaüstünden ekran görüntüsü alır (Windows GDI ve PIL desteğiyle kesintisiz)."""
        import ctypes
        from PIL import Image
        try:
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32
            w = user32.GetSystemMetrics(0)
            h = user32.GetSystemMetrics(1)
            hdc_screen = user32.GetDC(0)
            hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
            hbm = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
            gdi32.SelectObject(hdc_mem, hbm)
            gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, 0, 0, 0x00CC0020)

            bmi = ctypes.create_string_buffer(40)
            ctypes.memmove(bmi, (40).to_bytes(4, 'little'), 4)
            ctypes.memmove(ctypes.addressof(bmi)+4, w.to_bytes(4, 'little', signed=True), 4)
            ctypes.memmove(ctypes.addressof(bmi)+8, (-h).to_bytes(4, 'little', signed=True), 4)
            ctypes.memmove(ctypes.addressof(bmi)+12, (1).to_bytes(2, 'little'), 2)
            ctypes.memmove(ctypes.addressof(bmi)+14, (32).to_bytes(2, 'little'), 2)

            buf = ctypes.create_string_buffer(w * h * 4)
            gdi32.GetDIBits(hdc_mem, hbm, 0, h, buf, bmi, 0)

            gdi32.DeleteObject(hbm)
            gdi32.DeleteDC(hdc_mem)
            user32.ReleaseDC(0, hdc_screen)

            return Image.frombuffer('RGBA', (w, h), buf, 'raw', 'BGRA', 0, 1).convert('RGB')
        except Exception:
            try:
                from PIL import ImageGrab
                return ImageGrab.grab().convert('RGB')
            except Exception as e:
                logger.debug(f"[Gözlemci] Ekran yakalanamadı: {e}")
                return None

    def _ocr_metin_cikar(self, img) -> str:
        """Görüntüden metinleri hızlıca çıkarır (Windows yerel OCR veya pytesseract)."""
        if img is None:
            return ""
        # 1. Windows 10/11 yerel OCR
        try:
            import io, asyncio
            import winsdk.windows.media.ocr as ocr
            import winsdk.windows.graphics.imaging as imaging
            import winsdk.windows.storage.streams as streams

            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="PNG")
            png_bytes = buf.getvalue()

            async def _win_ocr():
                writer = streams.DataWriter()
                writer.write_bytes(png_bytes)
                ibuf = writer.detach_buffer()
                stream = streams.InMemoryRandomAccessStream()
                await stream.write_async(ibuf)
                stream.seek(0)
                decoder = await imaging.BitmapDecoder.create_async(stream)
                bitmap = await decoder.get_software_bitmap_async()
                engine = ocr.OcrEngine.try_create_from_user_profile_languages()
                if not engine and ocr.OcrEngine.available_recognizer_languages:
                    engine = ocr.OcrEngine.try_create_from_language(ocr.OcrEngine.available_recognizer_languages[0])
                if engine:
                    res = await engine.recognize_async(bitmap)
                    return [line.text for line in res.lines]
                return []

            lines = asyncio.run(_win_ocr())
            if lines:
                return "\n".join(lines[:20])
        except Exception as e:
            logger.debug(f"[Gözlemci] Windows OCR atlandı: {e}")

        # 2. pytesseract fallback
        try:
            import pytesseract
            return pytesseract.image_to_string(img, lang="tur+eng")[:1000]
        except Exception:
            pass

        return ""

    def _statik_analiz(self, img) -> Dict[str, Any]:
        """Tek kare görüntüyü analiz eder: çözünürlük, parlaklık, renk paleti, OCR metinleri."""
        if img is None:
            return {"hata": "Görüntü yakalanamadı"}

        w, h = img.size
        img_small = img.convert("RGB").resize((100, 100))
        pixels = list(img_small.getdata())
        avg_r = sum(p[0] for p in pixels) / len(pixels)
        avg_g = sum(p[1] for p in pixels) / len(pixels)
        avg_b = sum(p[2] for p in pixels) / len(pixels)
        parlaklik = (avg_r * 299 + avg_g * 587 + avg_b * 114) / 1000
        tema = "Karanlık Mod (Dark Mode)" if parlaklik < 120 else "Aydınlık Mod (Light Mode)"

        metin = self._ocr_metin_cikar(img)

        return {
            "mod": "snapshot",
            "boyut": f"{w}x{h}",
            "tema": tema,
            "parlaklik": round(parlaklik, 1),
            "metin": metin.strip()
        }

    def _video_analiz(self, sure_sn: float = 2.4, fps: int = 4) -> Dict[str, Any]:
        """2-3 saniye boyunca ekran kareleri yakalayarak hareket, değişim ve video akışını inceler."""
        import numpy as np

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
            try:
                self.hafiza.bilgi_kaydet(konu, res[:2000], lang)
            except Exception: pass
            return res

        if pl.startswith("!ara ") or pl.startswith("!search "):
            sorgu = p.split(" ", 1)[1]
            res = yetenekler.web_ara(sorgu)
            try:
                self.hafiza.bilgi_kaydet(sorgu, res[:2000], lang)
            except Exception: pass
            return res

        if pl.startswith("!oku ") or pl.startswith("!read "):
            dosya = p.split(" ", 1)[1]
            return yetenekler.dosya_oku(dosya)

        if pl.startswith("!python ") or pl.startswith("!kod "):
            kod = p.split(" ", 1)[1]
            return yetenekler.python_calistir(kod)

        if pl.startswith("!zaman") or pl.startswith("!saat") or pl.startswith("!time"):
            return f"⏰ **Tarih & Saat**: {yetenekler.tarih_saat()} ({yetenekler.bugun_gun()})"

        # 2. Matematik Hesabı Niyet Tespiti (örn: 154 * 28 + 19 kaç eder)
        math_match = re.search(r"(\d+\s*[\+\-\*\/\^%]\s*\d+[\s\d\+\-\*\/\^%]*)", p)
        if math_match and any(w in pl for w in ["hesapla", "kaç eder", "sonucu", "eşittir", "=", "calculate", "what is"]):
            expr = math_match.group(1).replace("^", "**")
            res = yetenekler.hesapla(expr)
            if "Hata" not in res:
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
            if "hata" not in wiki_res.lower() and len(wiki_res) > 50:
                try:
                    self.hafiza.bilgi_kaydet(query, wiki_res[:2000], lang)
                except Exception: pass
                return wiki_res
            
            # Wikipedia yetersizse DuckDuckGo / Web araması yap
            web_res = yetenekler.web_ara(query)
            if "hata" not in web_res.lower() and len(web_res) > 50:
                try:
                    self.hafiza.bilgi_kaydet(query, web_res[:2000], lang)
                except Exception: pass
                return web_res

        return None


    def __repr__(self) -> str:
        return (f"AjanBeden("
                f"bilgisayar={'✅' if self.bilgisayar.aktif else '❌'}, "
                f"ses={'✅' if self.ses.ses_aktif_mi() else '❌'}, "
                f"tts={'✅' if self.ses.tts_aktif_mi() else '❌'}, "
                f"goruntu={'✅' if self.goruntu._pil_aktif else '❌'}, "
                f"merak_kuyruk={self.merak.kuyruk_boyutu()})")

