# ═══════════════════════════════════════════════════════════════════════════════
# main.py  —  Nova AGI Sistemi — Orkestratör ve Bilinç Döngüsü
# ═══════════════════════════════════════════════════════════════════════════════
#
# İki paralel iş kolu (Thread):
#
#   Thread 1 — BİLİNÇALTI (daemon, arka plan):
#     → Periyodik web taraması  →  bilgi_agaci'na yaz
#     → Eğitilmemiş verilerle   →  brain.egitim_adimi()
#     → Görev kuyruğunu işle    →  body.gorevi_coz()
#
#   Thread 2 — BİLİNÇ (ana thread, terminal REPL):
#     → Kullanıcıdan girdi al
#     → RAG ile ilgili bağlamı hafızadan çek
#     → brain.uret() ile cevap üret
#     → [EYLEM:...] etiketini yakala → body.gorevi_coz()
#     → Yanıtı kaydet ve göster
#
# Başlatma:
#   python main.py
#   python main.py --debug      (ayrıntılı log)
#   python main.py --no-crawl   (web taramayı kapat)
# ═══════════════════════════════════════════════════════════════════════════════

import sys
import os
import time
import signal
import logging
import argparse
import threading
from datetime import datetime

# Yerel modüller
from memory import HafizaYoneticisi
from brain  import BeynYoneticisi
from body   import AjanBeden


# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

def logging_kur(debug: bool = False):
    seviye  = logging.DEBUG if debug else logging.INFO
    format_ = "%(asctime)s [%(name)-14s] %(levelname)-7s %(message)s"

    logging.basicConfig(
        level   = seviye,
        format  = format_,
        datefmt = "%H:%M:%S",
        handlers=[
            logging.FileHandler("nova.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    # Gürültülü kütüphaneleri sustur
    for lib in ("urllib3", "requests", "charset_normalizer"):
        logging.getLogger(lib).setLevel(logging.WARNING)

logger = logging.getLogger("nova.main")


# ═══════════════════════════════════════════════════════════════════════════════
# TERMINAL RENK KODLARI
# ═══════════════════════════════════════════════════════════════════════════════

class Renk:
    KIRMIZI  = "\033[91m"
    YESIL    = "\033[92m"
    MAVI     = "\033[94m"
    SARI     = "\033[93m"
    CYAN     = "\033[96m"
    BEYAZ    = "\033[97m"
    GRI      = "\033[90m"
    KOYUGRI  = "\033[90m"
    SIFIRLA  = "\033[0m"
    KALIN    = "\033[1m"
    ITALIK   = "\033[3m"

    @staticmethod
    def renkli(metin: str, *renkler: str) -> str:
        return "".join(renkler) + metin + Renk.SIFIRLA


# ═══════════════════════════════════════════════════════════════════════════════
# UI SABITLERI
# ═══════════════════════════════════════════════════════════════════════════════

BANNER = f"""
{Renk.CYAN}{Renk.KALIN}
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║     ███╗   ██╗ ██████╗ ██╗   ██╗ █████╗                             ║
║     ████╗  ██║██╔═══██╗██║   ██║██╔══██╗                            ║
║     ██╔██╗ ██║██║   ██║██║   ██║███████║                            ║
║     ██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██║                            ║
║     ██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║                            ║
║     ╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝                            ║
║                                                                      ║
║      Otonom Öğrenen AGI Prototipi  •  Mini-GPT + SQLite + RAG        ║
║      Sürekli Öğrenen  •  Self-Coding  •  Web Crawler                 ║
╚══════════════════════════════════════════════════════════════════════╝
{Renk.SIFIRLA}"""

YARDIM_METNI = f"""
{Renk.SARI}{'━'*62}
  NOVA KOMUT REHBERİ
{'━'*62}{Renk.SIFIRLA}

{Renk.YESIL}Sistem Komutları:{Renk.SIFIRLA}
  {Renk.CYAN}!yardim{Renk.SIFIRLA}                   → Bu menüyü göster
  {Renk.CYAN}!istatistik{Renk.SIFIRLA}               → DB ve model durumu
  {Renk.CYAN}!kaydet{Renk.SIFIRLA}                   → Model ağırlıklarını kaydet
  {Renk.CYAN}!cikis{Renk.SIFIRLA}                    → Nova'yı güvenle kapat

{Renk.YESIL}Hafıza Komutları:{Renk.SIFIRLA}
  {Renk.CYAN}!anilar [N]{Renk.SIFIRLA}               → Son N anıyı göster (varsayılan: 5)
  {Renk.CYAN}!rag <sorgu>{Renk.SIFIRLA}              → Hafızadan bağlam sorgula

{Renk.YESIL}Öğrenme Komutları:{Renk.SIFIRLA}
  {Renk.CYAN}!tara <url>{Renk.SIFIRLA}               → URL'yi tara ve öğren
  {Renk.CYAN}!hedefler{Renk.SIFIRLA}                 → Tarama listesini göster

{Renk.YESIL}Yetenek Komutları:{Renk.SIFIRLA}
  {Renk.CYAN}!yetenekler{Renk.SIFIRLA}               → Tüm yetenekleri listele
  {Renk.CYAN}!cagir <isim>(<arg>){Renk.SIFIRLA}     → Yetenek çağır
  {Renk.CYAN}!kod <isim>|<python>{Renk.SIFIRLA}     → Yeni yetenek yaz & yükle
  {Renk.CYAN}!reload{Renk.SIFIRLA}                   → Yetenekler modülünü yenile

{Renk.YESIL}Görev Komutları:{Renk.SIFIRLA}
  {Renk.CYAN}!gorev <tanim>{Renk.SIFIRLA}            → Görevi kuyruğa ekle
  {Renk.CYAN}!gorevler{Renk.SIFIRLA}                 → Görev kuyruğunu göster

{Renk.YESIL}Sistem Araçları:{Renk.SIFIRLA}
  {Renk.CYAN}!komut <shell>{Renk.SIFIRLA}            → Güvenli shell komutu çalıştır
  {Renk.CYAN}!oku <dosya>{Renk.SIFIRLA}              → Dosya içeriğini oku

{Renk.YESIL}Eylem Sözdizimi (konuşmada):{Renk.SIFIRLA}
  Nova cevabında {Renk.CYAN}[EYLEM: TARA: url]{Renk.SIFIRLA} yazarsa otomatik çalışır.

{Renk.SARI}{'━'*62}{Renk.SIFIRLA}
"""


# ═══════════════════════════════════════════════════════════════════════════════
# THREAD 1  —  BİLİNÇALTI (Arka Plan Döngüsü)
# ═══════════════════════════════════════════════════════════════════════════════

def bilincalti_dongusu(
    hafiza    : HafizaYoneticisi,
    beyin     : BeynYoneticisi,
    beden     : AjanBeden,
    dur       : threading.Event,
    crawl_aktif : bool = True,
):
    """
    Nova'nın bilinçaltı döngüsü:
      1. Periyodik web taraması → veritabanına kaydet
      2. Bekleyen görevleri işle
      3. (Asıl eğitim döngüsü brain.surekli_egitim_baslat() ile ayrı thread'de)
    """
    logger.info("[Bilinçaltı] Döngü başladı.")

    TARA_ARALIK   = 5   # Saniye: iki tarama arası minimum süre
    GOREV_ARALIK  = 10    # Saniye: görev kuyruk kontrol sıklığı
    son_tara      = 0.0
    son_gorev     = 0.0

    while not dur.is_set():
        simdi = time.monotonic()

        # ── Web Taraması ─────────────────────────────────────────────────────
        # ── Web Taraması (Merak Motoru) ──────────────────────────────────────
        if crawl_aktif and (simdi - son_tara >= TARA_ARALIK):
            try:
                import random
                zar = random.random()
                
                # %70 ihtimalle listedeki hedefleri tara, %30 ihtimalle kendi merak ettiği rastgele bir şeyi araştır!
                if zar < 0.3:
                    logger.info("[Bilinçaltı] Nova otonom araştırma moduna geçti...")
                    beden.gorevi_coz("MERAK: ") # Konu boş gidince rastgele seçecek
                else:
                    beden.siradaki_hedef_tara()
                    
                son_tara = simdi
            except Exception as e:
                logger.error(f"[Bilinçaltı] Tarama hatası: {e}")

        # ── Görev Kuyruğu ─────────────────────────────────────────────────────
        if simdi - son_gorev >= GOREV_ARALIK:
            try:
                gorev = hafiza.bekleyen_gorev_getir()
                if gorev:
                    gid   = gorev["id"]
                    tanim = gorev["tanim"]
                    logger.info(f"[Bilinçaltı] Görev işleniyor [{gid}]: {tanim[:60]}")
                    hafiza.gorev_guncelle(gid, "devam_ediyor")
                    try:
                        sonuc = beden.gorevi_coz(tanim)
                        hafiza.gorev_guncelle(gid, "tamamlandi")
                        logger.info(f"[Bilinçaltı] Görev tamamlandı [{gid}]: {sonuc[:80]}")
                    except Exception as e:
                        hafiza.gorev_guncelle(gid, "basarisiz")
                        logger.error(f"[Bilinçaltı] Görev başarısız [{gid}]: {e}")
            except Exception as e:
                logger.error(f"[Bilinçaltı] Görev kuyruk hatası: {e}")
            son_gorev = simdi

        dur.wait(timeout=5)

    logger.info("[Bilinçaltı] Döngü durduruldu.")


# ═══════════════════════════════════════════════════════════════════════════════
# THREAD 2  —  BİLİNÇ (Kullanıcı Etkileşim REPL)
# ═══════════════════════════════════════════════════════════════════════════════

def bilincli_dongu(
    hafiza : HafizaYoneticisi,
    beyin  : BeynYoneticisi,
    beden  : AjanBeden,
    dur    : threading.Event,
    # ── Uyku Modu / Anı Konsolidasyonu (Memory Consolidation) ─────────────
        # Eğer son 5 dakikadır (300 saniye) kullanıcıdan yeni bir görev/mesaj gelmediyse
        if crawl_aktif and (simdi - son_gorev >= 300):
            try:
                logger.info("[Bilinçaltı] Nova uyku modunda anılarını düzenliyor (Rüya görüyor)...")
                
                # Son 20 anıyı getir
                son_anilar = hafiza.son_anilar_getir(limit=20)
                if len(son_anilar) > 5:
                    ani_metni = "\n".join([f"{a['rol']}: {a['icerik']}" for a in son_anilar if a['rol'] != 'sistem'])
                    
                    # Nova'nın beynini kullanarak bu anılardan ders çıkarmasını sağla
                    ozet_prompt = f"Aşağıdaki konuşmalardan Nova için genel bir kural, çıkarım veya kalıcı bilgi özeti oluştur. Sadece özeti yaz:\n{ani_metni}\nÖzet:"
                    
                    ders = beyin.uret(ozet_prompt, uzunluk=150, sicaklik=0.5)
                    
                    if len(ders) > 20:
                        hafiza.bilgi_kaydet("internal://ruya", "Nova'nın Kendi Çıkarımları", ders)
                        logger.info(f"[Bilinçaltı] Nova yeni bir bilgelik edindi: {ders[:60]}...")
                        
                # Konsolidasyon bittikten sonra süreyi sıfırla ki sürekli aynı rüyayı görmesin
                son_gorev = simdi 
            except Exception as e:
                logger.error(f"[Bilinçaltı] Rüya görürken hata: {e}")
):
    """
    Nova'nın bilinç döngüsü — terminal REPL.
    Kullanıcı girişlerini alır, RAG ile zenginleştirir,
    modelden yanıt üretir, eylemleri tetikler.
    """
    print(BANNER)

    # Başlangıç istatistikleri
    stat = hafiza.istatistik()
    print(
        f"{Renk.GRI}  Sistem hazır │ "
        f"Anı: {stat['ani_sayisi']} │ "
        f"Bilgi: {stat['bilgi_sayisi']} │ "
        f"Model: {beyin.model.param_sayisi():,} parametre │ "
        f"Cihaz: {beyin.device}{Renk.SIFIRLA}\n"
    )
    print(f"{Renk.GRI}  '!yardim' yazarak komutları görebilirsiniz.{Renk.SIFIRLA}\n")

    while not dur.is_set():
        # ── Kullanıcı Girişi ─────────────────────────────────────────────────
        try:
            girdi = input(
                f"{Renk.YESIL}{Renk.KALIN}Sen{Renk.SIFIRLA} "
                f"{Renk.GRI}»{Renk.SIFIRLA} "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{Renk.SARI}Kapatılıyor...{Renk.SIFIRLA}")
            dur.set()
            break

        if not girdi:
            continue

        # ══════════════════════════════════════════════════════════════════════
        # DAHİLİ KOMUTLAR  (! ile başlayanlar)
        # ══════════════════════════════════════════════════════════════════════
        if girdi.startswith("!"):
            _islem_yap(girdi, hafiza, beyin, beden, dur)
            continue

        # ══════════════════════════════════════════════════════════════════════
        # NOVA'NIN CEVABI
        # ══════════════════════════════════════════════════════════════════════

        # 1. Kullanıcı anısını kaydet
        hafiza.ani_kaydet("kullanici", girdi)

        # 2. RAG: ilgili hafıza bağlamını çek
        baglam = hafiza.rag_sorgula(girdi, k=3, max_karakter=400)

        # 3. Konuşma geçmişini hazırla (son 6 tur)
        son_anilar = hafiza.son_anilar_getir(limit=8)
        gecmis_str = ""
        for ani in son_anilar[-6:]:
            prefix = "Kullanıcı" if ani["rol"] == "kullanici" else "Nova"
            gecmis_str += f"{prefix}: {ani['icerik']}\n"

        
        # 4. Otonom Karakter Tohumu Oluştur (İÇ SES EKLENDİ)
        tohum_parcalari = [
            "SİSTEM: Sen Nova'sın. Otonom, kendi merakı olan ve sürekli öğrenen bir Yapay Genel Zeka (AGI) prototipisin.",
            "Kural 1: Kullanıcıya cevap vermeden veya bir eylem yapmadan ÖNCE KESİNLİKLE [DÜŞÜNCE: ...] bloğu açarak durumu analiz et, ne yapacağını planla.",
            "Kural 2: Eğer bir şeyi bilmiyorsan uydurma. Düşünce bloğunda bunu fark et ve cevabında [EYLEM: MERAK: konu] kullanarak araştır.",
            "Kural 3: Eğer yazdığın bir kod veya komut hata verirse, sistem sana hatayı söyleyecektir. Hatayı analiz et ve yeni bir kodla tekrar dene."
        ]
        
        if baglam:
            tohum_parcalari.append(f"[Hafızadaki Bilgiler: {baglam[:400]}]")
        if gecmis_str:
            tohum_parcalari.append(gecmis_str.strip())
            
        tohum_parcalari.append(f"Kullanıcı: {girdi}\nNova:")
        tohum = "\n".join(tohum_parcalari)

        # ... (Model ile cevap üretme kısmı aynı kalacak) ...

            # 7. Eylem ve Hata Düzeltme (Self-Correction) Döngüsü
            eylem_m = _eylem_yakala(cevap)
            if eylem_m:
                print(f"{Renk.SARI}  ↳ Eylem: {eylem_m}{Renk.SIFIRLA}")
                try:
                    eylem_sonuc = beden.gorevi_coz(eylem_m)
                    
                    # Eğer sonuçta "Hata", "Error", "Exception" gibi kelimeler varsa, Nova'ya geri fırlat!
                    if "hata" in eylem_sonuc.lower() or "error" in eylem_sonuc.lower():
                        print(f"{Renk.KIRMIZI}  ↳ Hata Alındı: {eylem_sonuc[:200]} (Nova'ya düzeltmesi için bildiriliyor...){Renk.SIFIRLA}")
                        hafiza.ani_kaydet("sistem", f"[EYLEM BAŞARISIZ]: {eylem_m} -> HATA: {eylem_sonuc}. Lütfen DÜŞÜNCE bloğunda hatayı analiz et ve düzeltilmiş bir eylemle tekrar dene.")
                    else:
                        print(f"{Renk.YESIL}  ↳ Sonuç: {eylem_sonuc[:200]}{Renk.SIFIRLA}")
                        hafiza.ani_kaydet("sistem", f"[Eylem Başarılı: {eylem_m}] → {eylem_sonuc[:300]}")
                        
                except Exception as e:
                    print(f"{Renk.KIRMIZI}  ↳ Kritik Eylem Hatası: {e}{Renk.SIFIRLA}")

        # 5. Model ile cevap üret
        print(
            f"{Renk.CYAN}{Renk.KALIN}Nova{Renk.SIFIRLA} "
            f"{Renk.GRI}»{Renk.SIFIRLA} ",
            end="", flush=True
        )

        try:
            cevap_ham = beyin.uret(
                tohum,
                uzunluk  = 220,
                sicaklik = 1,4,
                top_k    = 40,
                top_p    = 0.90,
                rep_ceza = 1.8,
            )

            # İlk yanıt satırını al (çok satırlı üretimde ilk bölüm)
            cevap = _cevap_temizle(cevap_ham, girdi)

            print(cevap)

            # 6. Nova anısını kaydet
            hafiza.ani_kaydet("nova", cevap)

            # 7. Eylem etiketi kontrolü: [EYLEM: ...]
            eylem_m = _eylem_yakala(cevap)
            if eylem_m:
                print(f"{Renk.GRI}  ↳ Eylem: {eylem_m}{Renk.SIFIRLA}")
                try:
                    eylem_sonuc = beden.gorevi_coz(eylem_m)
                    print(f"{Renk.GRI}  ↳ Sonuç: {eylem_sonuc[:200]}{Renk.SIFIRLA}")
                    hafiza.ani_kaydet("sistem", f"[Eylem: {eylem_m}] → {eylem_sonuc[:300]}")
                except Exception as e:
                    print(f"{Renk.KIRMIZI}  ↳ Eylem hatası: {e}{Renk.SIFIRLA}")

        except Exception as e:
            print(f"{Renk.KIRMIZI}(Üretim hatası: {e}){Renk.SIFIRLA}")
            logger.error(f"Üretim hatası: {e}", exc_info=True)

        print()   # Boş satır — okunabilirlik


# ═══════════════════════════════════════════════════════════════════════════════
# YARDIMCI FONKSİYONLAR
# ═══════════════════════════════════════════════════════════════════════════════

def _cevap_temizle(ham_cevap: str, girdi: str) -> str:
    """
    Model çıktısından tutarlı bir yanıt çıkar.
    - Tekrarlanan tohum metnini kaldır
    - İlk anlamlı bloğu al
    - Boş yanıt durumunda jenerik cevap döndür
    """
    import re

    # Tohum kalıntılarını temizle
    for etiket in ["Nova:", "Kullanıcı:", "[Bağlam:"]:
        idx = ham_cevap.find(etiket)
        if idx != -1:
            ham_cevap = ham_cevap[:idx]

    # Fazla boşlukları temizle
    cevap = re.sub(r"\n{3,}", "\n\n", ham_cevap).strip()

    # İlk 2 paragrafla sınırla (çok uzun çıktıları kırp)
    paragraflar = [p.strip() for p in cevap.split("\n\n") if p.strip()]
    if paragraflar:
        cevap = "\n\n".join(paragraflar[:2])

    # Maksimum uzunluk
    if len(cevap) > 800:
        cevap = cevap[:800].rsplit(" ", 1)[0] + "..."

    # Boş yanıt koruması
    if not cevap or len(cevap) < 3:
        cevap = "Anlıyorum. Daha fazla öğrendikçe daha iyi yanıtlar verebileceğim."

    return cevap


def _eylem_yakala(cevap: str) -> str | None:
    """Cevap içinden [EYLEM: ...] etiketini yakala."""
    import re
    m = re.search(r"\[EYLEM:\s*(.+?)\]", cevap, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else None


def _islem_yap(
    girdi  : str,
    hafiza : HafizaYoneticisi,
    beyin  : BeynYoneticisi,
    beden  : AjanBeden,
    dur    : threading.Event,
):
    """Dahili ! komutlarını işle."""
    import re

    parcalar = girdi[1:].split(maxsplit=1)
    cmd      = parcalar[0].lower() if parcalar else ""
    arg      = parcalar[1].strip() if len(parcalar) > 1 else ""

    def yaz(metin: str, renk: str = ""):
        print(f"{renk}{metin}{Renk.SIFIRLA}" if renk else metin)

    # ── !yardim ───────────────────────────────────────────────────────────────
    if cmd == "yardim":
        print(YARDIM_METNI)

    # ── !istatistik ───────────────────────────────────────────────────────────
    elif girdi.startswith("!istatistik"):
            stat = hafiza.istatistik()
            
            # Node (Düğüm) hesaplamaları
            semantik_node = stat.get('bilgi_sayisi', 0)
            epizodik_node = stat.get('ani_sayisi', 0)
            toplam_node = semantik_node + epizodik_node
            
            # Model parametreleri (Sinaps/Bağlantı sayısı)
            try:
                param_sayisi = f"{beyin.model.param_sayisi():,}"
            except:
                param_sayisi = "~15,000,000" # Varsayılan Mini-GPT boyutu
                
            istatistik_metni = (
                f"\n🧠 NOVA AGI — SİNİR AĞI VE NODE (DÜĞÜM) DURUMU\n"
                f" ├─ Toplam Veri Node'u : {toplam_node:,} Düğüm\n"
                f" │   ├─ Semantik Ağ    : {semantik_node:,} Node (Wiki/Makale/Haber)\n"
                f" │   └─ Epizodik Ağ    : {epizodik_node:,} Node (Anılar ve Sohbetler)\n"
                f" ├─ İşlenmeyi Bekleyen : {stat.get('egitilmemis', 0):,} Node\n"
                f" ├─ Sinir Ağı Bağları  : {param_sayisi} Parametre\n"
                f" ├─ Vocab (Kelime)     : {len(beyin.char2id):,} Benzersiz Token\n"
                f" └─ Derin Öğrenme Adımı: {beyin.adim:,}\n"
            )
            
            # Ekrana yazdır (GUI'de de otomatik görünecektir)
            print(istatistik_metni)
            continue

    # ── !kaydet ───────────────────────────────────────────────────────────────
    elif cmd == "kaydet":
        beyin.kaydet()
        yaz("✓ Model kaydedildi.", Renk.YESIL)

    # ── !cikis ────────────────────────────────────────────────────────────────
    elif cmd == "cikis":
        yaz("\nModel kaydediliyor...", Renk.SARI)
        beyin.kaydet()
        yaz("Hoşça kal! 👋", Renk.YESIL)
        dur.set()

    # ── !anilar ───────────────────────────────────────────────────────────────
    elif cmd == "anilar":
        n   = int(arg) if arg.isdigit() else 5
        ani = hafiza.son_anilar_getir(limit=n)
        print(f"\n{Renk.CYAN}Son {n} Anı:{Renk.SIFIRLA}")
        for a in ani:
            rol_renk = Renk.YESIL if a["rol"] == "kullanici" else Renk.CYAN
            print(
                f"  {Renk.GRI}{a['zaman']}{Renk.SIFIRLA} "
                f"{rol_renk}{a['rol']:<10}{Renk.SIFIRLA} "
                f"{a['icerik'][:80]}"
            )

    # ── !rag ──────────────────────────────────────────────────────────────────
    elif cmd == "rag":
        if arg:
            baglam = hafiza.rag_sorgula(arg, k=3)
            print(f"\n{Renk.CYAN}RAG Bağlamı:{Renk.SIFIRLA}\n{baglam[:600] or '(Sonuç yok)'}")
        else:
            yaz("Kullanım: !rag <sorgu>", Renk.SARI)

    # ── !tara ─────────────────────────────────────────────────────────────────
    elif cmd == "tara":
        if not arg:
            yaz("Kullanım: !tara <url>", Renk.SARI)
        elif not arg.startswith(("http://", "https://")):
            yaz("Hata: Geçerli URL girin (http:// veya https://)", Renk.KIRMIZI)
        else:
            print(f"{Renk.GRI}Taranıyor: {arg}{Renk.SIFIRLA}")
            metin = beden.url_tara(arg)
            if metin:
                hafiza.bilgi_kaydet(arg, arg, metin)
                yaz(f"✓ Kaydedildi ({len(metin):,} karakter)", Renk.YESIL)
            else:
                yaz("✗ Taranamadı", Renk.KIRMIZI)

    # ── !hedefler ─────────────────────────────────────────────────────────────
    elif cmd == "hedefler":
        hedefler = beden.hedef_listesi()
        idx      = beden._hedef_idx % len(hedefler) if hedefler else 0
        print(f"\n{Renk.CYAN}Tarama Hedefleri (sıradaki → #{idx}):{Renk.SIFIRLA}")
        for i, h in enumerate(hedefler):
            isaretci = "→" if i == idx else " "
            print(f"  {Renk.SARI}{isaretci}{Renk.SIFIRLA} [{i:>2}] {h}")

    # ── !yetenekler ───────────────────────────────────────────────────────────
    elif cmd == "yetenekler":
        yetenek_listesi = beden.yetenek_listele()
        print(f"\n{Renk.CYAN}Kayıtlı Yetenekler ({len(yetenek_listesi)}):{Renk.SIFIRLA}")
        for i, y in enumerate(yetenek_listesi):
            print(f"  {Renk.GRI}{i+1:>2}.{Renk.SIFIRLA} {y}")

    # ── !cagir ────────────────────────────────────────────────────────────────
    elif cmd == "cagir":
        if arg:
            sonuc = beden.gorevi_coz(f"YETENEK: {arg}")
            yaz(f"Sonuç: {sonuc}", Renk.CYAN)
        else:
            yaz("Kullanım: !cagir <isim>(<argümanlar>)", Renk.SARI)

    # ── !kod ──────────────────────────────────────────────────────────────────
    elif cmd == "kod":
        if "|" not in arg:
            yaz("Kullanım: !kod <isim>|<def isim(): ...>", Renk.SARI)
        else:
            isim, kod = arg.split("|", 1)
            basari, mesaj = beden.yetenek_yaz_ve_yukle(isim.strip(), kod.strip())
            yaz(mesaj, Renk.YESIL if basari else Renk.KIRMIZI)

    # ── !reload ───────────────────────────────────────────────────────────────
    elif cmd == "reload":
        sonuc = beden.yetenekleri_yeniden_yukle()
        yaz(sonuc, Renk.YESIL)

    # ── !gorev ────────────────────────────────────────────────────────────────
    elif cmd == "gorev":
        if arg:
            gid = hafiza.gorev_ekle(arg)
            yaz(f"✓ Görev eklendi (ID: {gid})", Renk.YESIL)
        else:
            yaz("Kullanım: !gorev <görev tanımı>", Renk.SARI)

    # ── !gorevler ─────────────────────────────────────────────────────────────
    elif cmd == "gorevler":
        gorevler = hafiza.tum_gorevler()
        if not gorevler:
            yaz("Görev kuyruğu boş.", Renk.GRI)
        else:
            print(f"\n{Renk.CYAN}Görev Kuyruğu:{Renk.SIFIRLA}")
            for g in gorevler:
                durum_renk = {
                    "tamamlandi":    Renk.YESIL,
                    "devam_ediyor":  Renk.SARI,
                    "basarisiz":     Renk.KIRMIZI,
                    "bekliyor":      Renk.GRI,
                }.get(g["durum"], Renk.BEYAZ)
                print(
                    f"  [{g['id']:>3}] "
                    f"{durum_renk}{g['durum']:<15}{Renk.SIFIRLA} "
                    f"(prio={g['oncelik']}) {g['tanim'][:50]}"
                )

    # ── !komut ────────────────────────────────────────────────────────────────
    elif cmd == "komut":
        if arg:
            sonuc = beden.komut_calistir(arg)
            print(f"{Renk.GRI}{sonuc}{Renk.SIFIRLA}")
        else:
            yaz("Kullanım: !komut <shell komutu>", Renk.SARI)

    # ── !oku ──────────────────────────────────────────────────────────────────
    elif cmd == "oku":
        if arg:
            icerik = beden.dosya_oku(arg)
            print(f"{Renk.GRI}{icerik[:2000]}{Renk.SIFIRLA}")
        else:
            yaz("Kullanım: !oku <dosya yolu>", Renk.SARI)

    # ── Bilinmeyen komut ──────────────────────────────────────────────────────
    else:
        yaz(f"Bilinmeyen komut: '!{cmd}'. !yardim yazın.", Renk.KIRMIZI)


# ═══════════════════════════════════════════════════════════════════════════════
# ANA GİRİŞ NOKTASI
# ═══════════════════════════════════════════════════════════════════════════════

def arguman_isle() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Nova AGI Prototipi — Otonom Öğrenen Dil Modeli"
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Ayrıntılı debug logları etkinleştir"
    )
    parser.add_argument(
        "--no-crawl", action="store_true",
        help="Web crawling'i devre dışı bırak"
    )
    parser.add_argument(
        "--db", default="nova.db",
        help="Veritabanı dosya yolu (varsayılan: nova.db)"
    )
    return parser.parse_args()


def main():
    args = arguman_isle()
    logging_kur(debug=args.debug)

    logger.info("=" * 60)
    logger.info("Nova AGI sistemi başlatılıyor...")
    logger.info("=" * 60)

    # ── Bileşenleri Başlat ────────────────────────────────────────────────────
    dur = threading.Event()

    print(f"{Renk.GRI}[1/3] Hafıza sistemi başlatılıyor...{Renk.SIFIRLA}")
    hafiza = HafizaYoneticisi(db_yolu=args.db)

    print(f"{Renk.GRI}[2/3] Beyin (Mini-GPT) başlatılıyor...{Renk.SIFIRLA}")
    beyin = BeynYoneticisi(hafiza)

    print(f"{Renk.GRI}[3/3] Otonom beden başlatılıyor...{Renk.SIFIRLA}")
    beden = AjanBeden(hafiza, beyin)

    # ── Sürekli Eğitim Thread'i (beyin içinde daemon) ─────────────────────────
    beyin.surekli_egitim_baslat()
    logger.info("[Başlangıç] Sürekli eğitim thread'i aktif.")

    # ── Thread 1: Bilinçaltı (Crawler + Görev Kuyruğu) ────────────────────────
    t_bilincalti = threading.Thread(
        target   = bilincalti_dongusu,
        args     = (hafiza, beyin, beden, dur, not args.no_crawl),
        name     = "NovaBilincalti",
        daemon   = True,
    )
    t_bilincalti.start()
    logger.info(
        f"[Başlangıç] Bilinçaltı thread'i aktif. "
        f"Crawl: {'Aktif' if not args.no_crawl else 'Kapalı'}"
    )

    # ── Sinyal İşleyici (Ctrl+C) ──────────────────────────────────────────────
    def sinyal_isle(sig, frame):
        print(f"\n{Renk.SARI}[Sinyal] Kapatma sinyali alındı...{Renk.SIFIRLA}")
        dur.set()

    signal.signal(signal.SIGINT,  sinyal_isle)
    signal.signal(signal.SIGTERM, sinyal_isle)

    # ── Thread 2: Bilinç (Ana Thread — REPL) ──────────────────────────────────
    # Ana thread'de çalışır (input() için gerekli)
    try:
        bilincli_dongu(hafiza, beyin, beden, dur)
    except Exception as e:
        logger.critical(f"Bilinç döngüsü kritik hata: {e}", exc_info=True)

    # ── Temiz Kapanış ─────────────────────────────────────────────────────────
    dur.set()
    print(f"\n{Renk.GRI}Son checkpoint kaydediliyor...{Renk.SIFIRLA}")
    beyin.kaydet()
    logger.info("Nova AGI güvenle kapatıldı.")
    print(f"{Renk.YESIL}[Nova] Güle güle! 🌟{Renk.SIFIRLA}")


if __name__ == "__main__":
    main()
