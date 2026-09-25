# ═══════════════════════════════════════════════════════════════════════════════
# hugging_loader.py  —  Otonom merak motoru ve Hugging Face Wikipedia içe aktarıcı
# ═══════════════════════════════════════════════════════════════════════════════
import time
import json
import random
import logging
import urllib.request
import urllib.parse
from typing import Optional
from memory import HafizaYoneticisi

logger = logging.getLogger("nova.hf_loader")




class OtonomMerakMotoru:
    """
    Nova'nın otonom merak ve internet keşif motoru.
    Kullanıcının ilgi alanlarına ve rastgele bilim/teknoloji tohumlarına göre
    Wikipedia ve web kaynaklarını arka planda otonom tarar ve hafızaya kaydeder.
    """
    VARSAYILAN_TOHUMLAR_TR = [
        "Yapay zekâ", "Kuantum bilgisayarı", "Derin öğrenme", "Bilişsel bilim",
        "Nörobilim", "Büyük Dil Modeli", "Transformatör (makine öğrenimi)",
        "Karadelik", "Evrenin genişlemesi", "Genetik mühendisliği", "Sibernetik",
        "Graf teorisi", "Robotik", "Evrimsel algoritmalar", "Astronomi"
    ]

    VARSAYILAN_TOHUMLAR_EN = [
        "Artificial intelligence", "Quantum computing", "Deep learning", "Cognitive science",
        "Neuroscience", "Large language model", "Transformer (deep learning architecture)",
        "Black hole", "Expansion of the universe", "Genetic engineering", "Cybernetics",
        "Graph theory", "Robotics", "Evolutionary algorithm", "Astronomy"
    ]

    def __init__(self, hafiza: HafizaYoneticisi):
        self.hafiza = hafiza
        self._islenmis_konular = set()
        self._ozel_tohumlar = []

    def tohum_ekle(self, custom_topics_str: str, lang: str = "tr"):
        """Kullanıcının belirlediği özel araştırma konularını ekler."""
        if not custom_topics_str: return
        konular = [k.strip() for k in custom_topics_str.replace(";", ",").replace("\n", ",").split(",") if k.strip()]
        for k in konular:
            if k not in self._ozel_tohumlar:
                self._ozel_tohumlar.append(k)

    def merak_adimi(self, lang: str = "tr") -> Optional[str]:
        """Tek bir otonom merak adımı yürütür: bir konu seçer, araştırır ve hafızaya kaydeder."""
        try:
            # 1. Konu belirle (Özel tohumlar > Hafızadaki son anılar > Varsayılan tohumlar)
            tohumlar = (self._ozel_tohumlar + self.VARSAYILAN_TOHUMLAR_TR) if lang == "tr" else (self._ozel_tohumlar + self.VARSAYILAN_TOHUMLAR_EN)
            anilar = self.hafiza.son_anilar_getir(limit=5)
            aday_konu = None


            if anilar and random.random() < 0.6:
                for a in anilar:
                    kelimeler = [k for k in a["icerik"].split() if len(k) > 4 and k.isalpha()]
                    if kelimeler:
                        secilen = random.choice(kelimeler)
                        if secilen.lower() not in self._islenmis_konular:
                            aday_konu = secilen
                            break

            if not aday_konu:
                kalan_tohumlar = [t for t in tohumlar if t.lower() not in self._islenmis_konular]
                aday_konu = random.choice(kalan_tohumlar if kalan_tohumlar else tohumlar)

            self._islenmis_konular.add(aday_konu.lower())

            # 2. Wikipedia API'den özet çek
            encoded = urllib.parse.quote(aday_konu.strip().replace(" ", "_"))
            url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded}"
            req = urllib.request.Request(url, headers={"User-Agent": "NovaAGI/4.0 (Linux; autonomous research)"})

            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                baslik = data.get("title", aday_konu)
                icerik = data.get("extract", "")
                sayfa_url = data.get("content_urls", {}).get("desktop", {}).get("page", f"https://{lang}.wikipedia.org/wiki/{encoded}")

                if icerik and len(icerik) >= 60:
                    self.hafiza.bilgi_kaydet(url=sayfa_url, konu=baslik, icerik=icerik)
                    return f"🌐 [Merak Motoru] '{baslik}' konusu keşfedildi ve hafızaya eklendi."
        except Exception:
            pass
        return None


def veri_enjekte_et(limit: int = 500000, lang: Optional[str] = None) -> int:
    """
    Hugging Face 'wikimedia/wikipedia' veri setini akış halinde okuyup hafızaya ekler.
    Çıktı stdout yerine loglara yazılır (masaüstü köprüsünün JSON kanalını bozmaz).
    """
    from hf_auth import hf_token_al
    from config_manager import get_language
    hafiza = HafizaYoneticisi()
    lang = lang or get_language() or "en"
    ds_config = "20231101.en" if lang == "en" else "20231101.tr"
    token = hf_token_al()
    logger.info(f"[Wiki] {ds_config} akışı başlıyor ({'tokenli' if token else 'anonim'}), hedef: {limit:,}")
    sayac = 0
    try:
        from datasets import load_dataset
        kwargs = {"split": "train", "streaming": True}
        if token:
            kwargs["token"] = token
        dataset = load_dataset("wikimedia/wikipedia", ds_config, **kwargs)
        baslangic = time.time()
        for veri in dataset:
            if sayac >= limit:
                break
            metin = veri["text"]
            if len(metin) <= 300:
                continue
            hafiza.bilgi_kaydet(url=veri.get("url") or f"https://{lang}.wikipedia.org/wiki/?curid={veri.get('id', sayac)}",
                                konu=veri.get("title") or "Wikipedia", icerik=metin)
            sayac += 1
            if sayac % 100 == 0:
                logger.info(f"[Wiki] {sayac:,} makale eklendi ({sayac / (time.time() - baslangic):.1f} makale/sn)")
        logger.info(f"[Wiki] ✅ {sayac:,} makale yüklendi.")
    except ImportError:
        logger.error("[Wiki] 'datasets' paketi kurulu değil → pip install datasets")
    except Exception as e:
        logger.error(f"[Wiki] Hata: {e}")
    return sayac


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    from config_manager import ask_language_on_first_launch
    ask_language_on_first_launch()
    from hf_auth import hf_giris_sor
    hf_giris_sor()
    veri_enjekte_et(limit=int(sys.argv[1]) if len(sys.argv) > 1 else 500000)

