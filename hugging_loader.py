import time
import json
import random
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any, List
from memory import HafizaYoneticisi




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
            req = urllib.request.Request(url, headers={"User-Agent": "NovaAGI/3.5 (Autonomous Research Engine)"})

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


def veri_enjekte_et(limit=500000):
    hafiza = HafizaYoneticisi()
    from hf_auth import hf_token_al
    from config_manager import get_language
    lang = get_language() or "en"
    ds_config = "20231101.en" if lang == "en" else "20231101.tr"
    lang_name = "English" if lang == "en" else "Türkçe"
    token = hf_token_al()
    print(f"🚀 Hugging Face Hub üzerinden Resmi {lang_name} Wikipedia çekiliyor ({ds_config})... (Kimlik: {'Tokenli' if token else 'Anonim'})")
    try:
        from datasets import load_dataset
        kwargs = {"split": "train", "streaming": True}
        if token:
            kwargs["token"] = token
        dataset = load_dataset("wikimedia/wikipedia", ds_config, **kwargs)


        
        sayac = 0
        baslangic = time.time()
        print("🔥 İşlemci ziyafeti başlıyor, veritabanına taze bilgiler akıyor...")
        
        url_base = "https://en.wikipedia.org/wiki/article_" if lang == "en" else "https://tr.wikipedia.org/wiki/madde_"
        for veri in dataset:
            if sayac >= limit:
                break
            
            metin = veri['text']
            url_gercek = veri.get('url', f"{url_base}{sayac}")
            konu_gercek = veri.get('title', "General Knowledge (Wiki)" if lang == "en" else "Genel Kültür (Wiki)")
            
            if len(metin) > 300:
                hafiza.bilgi_kaydet(url=url_gercek, konu=konu_gercek, icerik=metin)
                sayac += 1
                
                if sayac % 50 == 0:
                    print(f"✅ {sayac} makale hafızaya eklendi (Hız: {sayac/(time.time()-baslangic):.1f} mb/sn)...")

        print(f"\n🌟 MÜKEMMEL! {sayac} makale başarıyla yüklendi.")
    except Exception as e:
        print(f"🛑 Bir hata oluştu: {e}")


if __name__ == "__main__":
    from config_manager import ask_language_on_first_launch
    ask_language_on_first_launch()
    from hf_auth import hf_giris_sor
    hf_giris_sor()
    veri_enjekte_et(limit=500000)

