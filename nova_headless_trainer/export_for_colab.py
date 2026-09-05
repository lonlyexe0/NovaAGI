# -*- coding: utf-8 -*-
"""
export_for_colab.py - Google Colab İçin Nova Eğitim Paketini Hazırlar
Bu script, Google Colab'a tek tıkla yükleyebileceğiniz 'nova_colab_package.zip' dosyasını oluşturur.
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
logger = logging.getLogger("nova.colab_export")

DOSYALAR = [
    "config.py",
    "model.py",
    "tokenizer.py",
    "db_manager.py",
    "train.py",
    "spark_data_pipeline.py",
    "nova_vocab.json",
    "nova_weights.pth",
    "nova.db"
]

def paketi_olustur():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    zip_path = os.path.join(base_dir, "nova_colab_package.zip")
    
    logger.info(f"📦 Google Colab paketi hazırlanıyor: {zip_path}")
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for dosya in DOSYALAR:
            tam_yol = os.path.join(base_dir, dosya)
            if not os.path.exists(tam_yol):
                # Eğer burada yoksa ana dizine bak
                alt_yol = os.path.join(base_dir, "..", dosya)
                if os.path.exists(alt_yol):
                    tam_yol = alt_yol
            
            if os.path.exists(tam_yol):
                boyut_mb = os.path.getsize(tam_yol) / (1024 * 1024)
                zf.write(tam_yol, dosya)
                logger.info(f"  + Eklendi: {dosya} ({boyut_mb:.2f} MB)")
            else:
                logger.warning(f"  - Bulunamadı, atlandı: {dosya}")

    toplam_mb = os.path.getsize(zip_path) / (1024 * 1024)
    logger.info(f"🎉 Paket hazır! Toplam Boyut: {toplam_mb:.2f} MB -> {zip_path}")
    print(f"\nColab paketi hazırlandı: {zip_path}")
    print("Bu zip dosyasını Google Colab'a yükleyerek eğitimi başlatabilirsiniz.\n")

if __name__ == "__main__":
    paketi_olustur()
