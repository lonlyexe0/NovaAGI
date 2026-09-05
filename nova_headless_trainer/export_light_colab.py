# -*- coding: utf-8 -*-
"""
export_light_colab.py - Ultra Hafif (100 KB) Google Colab Paketi
Ağır model ağırlıkları ve veritabanını hariç tutar. 1 saniyede yüklenir.
"""
import os
import sys
import zipfile
import logging

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("nova.colab_light")

DOSYALAR = [
    "config.py",
    "model.py",
    "tokenizer.py",
    "db_manager.py",
    "train.py",
    "spark_data_pipeline.py",
    "nova_vocab.json"
]

def hafif_paketi_olustur():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    zip_path = os.path.join(base_dir, "nova_colab_light.zip")
    
    logger.info(f"⚡ Ultra Hafif Colab paketi hazırlanıyor: {zip_path}")
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for dosya in DOSYALAR:
            tam_yol = os.path.join(base_dir, dosya)
            if not os.path.exists(tam_yol):
                alt_yol = os.path.join(base_dir, "..", dosya)
                if os.path.exists(alt_yol):
                    tam_yol = alt_yol
            
            if os.path.exists(tam_yol):
                boyut_kb = os.path.getsize(tam_yol) / 1024
                zf.write(tam_yol, dosya)
                logger.info(f"  + Eklendi: {dosya} ({boyut_kb:.1f} KB)")

    toplam_kb = os.path.getsize(zip_path) / 1024
    logger.info(f"🎉 Ultra Hafif Paket hazır! Toplam Boyut: {toplam_kb:.1f} KB -> {zip_path}")

if __name__ == "__main__":
    hafif_paketi_olustur()
