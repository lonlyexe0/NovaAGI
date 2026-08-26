import time
from datasets import load_dataset
from memory import HafizaYoneticisi

def veri_enjekte_et(limit=500000):
    hafiza = HafizaYoneticisi()
    print(f"🚀 Hugging Face Hub üzerinden Resmi Türkçe Wikipedia çekiliyor...")
    
    try:
        # Resmi Wikimedia kaydını kullanıyoruz (2023 tarihli en güncel TR seti)
        # 'streaming=True' sayesinde veriyi indirmeyi beklemez, anında akmaya başlar.
        dataset = load_dataset("wikimedia/wikipedia", "20231101.tr", split="train", streaming=True)
        
        sayac = 0
        print("🔥 İşlemci ziyafeti başlıyor, veritabanına taze bilgiler akıyor...")
        
        for veri in dataset:
            if sayac >= limit:
                break
            
            # Bu veri setinde metin 'text' alanında gelir
            metin = veri['text']
            
            # URL ve Konu başlığını veriden alıyoruz
            url_gercek = veri.get('url', f"https://tr.wikipedia.org/wiki/madde_{sayac}")
            konu_gercek = veri.get('title', "Genel Kültür (Wiki)")
            
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
    baslangic = time.time()
    veri_enjekte_et(limit=500000)
