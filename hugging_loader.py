import time
from datasets import load_dataset
from memory import HafizaYoneticisi

import time
from datasets import load_dataset
from memory import HafizaYoneticisi

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
        # Resmi Wikimedia kaydı ('streaming=True' sayesinde anında akmaya başlar)
        kwargs = {"split": "train", "streaming": True}
        if token:
            kwargs["token"] = token
        dataset = load_dataset("wikimedia/wikipedia", ds_config, **kwargs)
        
        sayac = 0
        print("🔥 İşlemci ziyafeti başlıyor, veritabanına taze bilgiler akıyor...")
        
        url_base = "https://en.wikipedia.org/wiki/article_" if lang == "en" else "https://tr.wikipedia.org/wiki/madde_"
        for veri in dataset:
            if sayac >= limit:
                break
            
            metin = veri['text']
            
            # URL ve Konu başlığını veriden alıyoruz
            url_gercek = veri.get('url', f"{url_base}{sayac}")
            konu_gercek = veri.get('title', "General Knowledge (Wiki)" if lang == "en" else "Genel Kültür (Wiki)")
            
            if len(metin) > 300: # Çok kısa (boş) sayfaları ele
                hafiza.bilgi_kaydet(url=url_gercek, konu=konu_gercek, icerik=metin)
                sayac += 1
                
                if sayac % 50 == 0:
                    print(f"✅ {sayac} makale hafızaya eklendi (Hız: {sayac/(time.time()-baslangic):.1f} mb/sn)...")

        print(f"\n🌟 MÜKEMMEL! {sayac} makale başarıyla yüklendi.")
        print("Şimdi main.py'yi aç ve işlemcinin nasıl kükrediğini izle!")

    except Exception as e:
        print(f"🛑 Bir hata oluştu: {e}")
        print("\nİpucu: 'pip install apache_beam' yazman gerekebilir (bazı büyük setler için gerekebiliyor).")

if __name__ == "__main__":
    from config_manager import ask_language_on_first_launch
    ask_language_on_first_launch()
    from hf_auth import hf_giris_sor
    hf_giris_sor()
    baslangic = time.time()
    veri_enjekte_et(limit=500000)
