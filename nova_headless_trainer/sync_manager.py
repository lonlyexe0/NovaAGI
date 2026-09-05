# -*- coding: utf-8 -*-
"""
sync_manager.py - DB ve Model Ağırlıkları Senkronizasyon Yöneticisi
Eğitim ortamı ile ana NOVA sistemi arasında nova.db ve model ağırlıklarını güvenle taşır.

Kullanım:
  python sync_manager.py --pull   (Ana NOVA'dan veritabanını ve ağırlıkları buraya çeker)
  python sync_manager.py --push   (Eğitilen DB ve ağırlıkları ana NOVA'ya geri yükler)
  python sync_manager.py --status (Her iki tarafın durumunu ve farklarını gösterir)
"""
import os
import sys
import shutil
import logging
import argparse
from datetime import datetime

from db_manager import TrainerDBManager

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("nova.sync")

DOSYALAR = [
    "nova.db",
    "nova_weights.pth",
    "nova_vocab.json"
]

def backup_al(dosya_yolu: str) -> str:
    """Hedef dosyanın zaman damgalı yedeğini alır."""
    if not os.path.exists(dosya_yolu):
        return ""
    zaman = datetime.now().strftime("%Y%m%d_%H%M%S")
    yedek_yolu = f"{dosya_yolu}.{zaman}.bak"
    shutil.copy2(dosya_yolu, yedek_yolu)
    logger.info(f"🛡️ Güvenlik Yedeği Alındı: {os.path.basename(yedek_yolu)}")
    return yedek_yolu

def durum_goster(kaynak_dir: str, hedef_dir: str):
    print(f"\n{'='*70}")
    print(f"📊 NOVA VERİTABANI VE MODEL DURUM RAPORU")
    print(f"{'='*70}")
    
    # 1. Ana Sistem
    ana_db = os.path.join(kaynak_dir, "nova.db")
    ana_w  = os.path.join(kaynak_dir, "nova_weights.pth")
    print(f"\n🏠 [Ana NOVA Sistemi: {kaynak_dir}]")
    if os.path.exists(ana_db):
        mgr = TrainerDBManager(ana_db)
        st = mgr.get_stats()
        print(f"  • nova.db: {os.path.getsize(ana_db)/(1024*1024):.2f} MB | {st['toplam_bilgi']:,} toplam | {st['egitilmemis_bilgi']:,} eğitilmemiş | {st['egitilmis_bilgi']:,} eğitilmiş")
    else:
        print("  • nova.db bulunamadı.")
    if os.path.exists(ana_w):
        print(f"  • nova_weights.pth: {os.path.getsize(ana_w)/(1024*1024):.2f} MB")
    else:
        print("  • nova_weights.pth bulunamadı.")

    # 2. Eğitim Sistemi
    egitim_db = os.path.join(hedef_dir, "nova.db")
    egitim_w  = os.path.join(hedef_dir, "nova_weights.pth")
    print(f"\n🚀 [Headless Eğitim Ortamı: {hedef_dir}]")
    if os.path.exists(egitim_db):
        mgr = TrainerDBManager(egitim_db)
        st = mgr.get_stats()
        print(f"  • nova.db: {os.path.getsize(egitim_db)/(1024*1024):.2f} MB | {st['toplam_bilgi']:,} toplam | {st['egitilmemis_bilgi']:,} eğitilmemiş | {st['egitilmis_bilgi']:,} eğitilmiş")
    else:
        print("  • nova.db bulunamadı.")
    if os.path.exists(egitim_w):
        print(f"  • nova_weights.pth: {os.path.getsize(egitim_w)/(1024*1024):.2f} MB")
    else:
        print("  • nova_weights.pth bulunamadı.")
    print(f"{'='*70}\n")

def senkronize_et(kaynak_dir: str, hedef_dir: str, yon_aciklama: str):
    logger.info(f"🔄 Senkronizasyon Başlatıldı ({yon_aciklama}):")
    logger.info(f"   Kaynak: {kaynak_dir}")
    logger.info(f"   Hedef:  {hedef_dir}")

    for dosya in DOSYALAR:
        src = os.path.join(kaynak_dir, dosya)
        dst = os.path.join(hedef_dir, dosya)

        if not os.path.exists(src):
            logger.warning(f"⚠️ Kaynak dosya mevcut değil, atlandı: {dosya}")
            continue

        # Hedefte varsa yedek al
        if os.path.exists(dst):
            backup_al(dst)

        shutil.copy2(src, dst)
        boyut_mb = os.path.getsize(dst) / (1024 * 1024)
        logger.info(f"✅ Kopyalandı: {dosya} ({boyut_mb:.2f} MB)")

    logger.info(f"🎉 {yon_aciklama} işlemi başarıyla tamamlandı!")

def main():
    varsayilan_ana = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    varsayilan_egitim = os.path.abspath(os.path.dirname(__file__))

    parser = argparse.ArgumentParser(description="Nova DB ve Ağırlık Senkronizasyon Yöneticisi")
    parser.add_argument("--pull", action="store_true", help="Ana NOVA'dan eğitim klasörüne veri çek")
    parser.add_argument("--push", action="store_true", help="Eğitim klasöründen eğitilmiş verileri ana NOVA'ya aktar")
    parser.add_argument("--status", action="store_true", help="Her iki ortamın durumunu raporla")
    parser.add_argument("--main_dir", type=str, default=varsayilan_ana, help="Ana NOVA proje dizini")
    parser.add_argument("--trainer_dir", type=str, default=varsayilan_egitim, help="Headless eğitim klasörü dizini")

    args = parser.parse_args()

    if args.status:
        durum_goster(args.main_dir, args.trainer_dir)
        return

    if args.pull:
        senkronize_et(args.main_dir, args.trainer_dir, "Ana Sistemden Veri Çekme (PULL)")
        durum_goster(args.main_dir, args.trainer_dir)
        return

    if args.push:
        senkronize_et(args.trainer_dir, args.main_dir, "Ana Sisteme Eğitilmiş Veri Aktarma (PUSH)")
        durum_goster(args.main_dir, args.trainer_dir)
        return

    parser.print_help()
    print("\nÖrnek:")
    print("  python sync_manager.py --status")
    print("  python sync_manager.py --pull")
    print("  python sync_manager.py --push")

if __name__ == "__main__":
    main()
