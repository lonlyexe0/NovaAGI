# -*- coding: utf-8 -*-
"""
spark_data_pipeline.py - Apache Spark ile Büyük Veri Hazırlama & Nova.db Aktarımı
Spark Quick Start mantığıyla metinleri dağıtık okur, filtreler, temizler ve SQLite nova.db'ye yazar.

Kullanım:
  python spark_data_pipeline.py --input "metinler/*.txt" --format text --db nova.db --topic "Wikipedia"
  python spark_data_pipeline.py --demo (Örnek README.md üzerinde test)
"""
import os
import sys
import argparse
import logging
from typing import Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("nova.spark")

def spark_oturum_olustur():
    """Apache Spark oturumu başlatır."""
    try:
        from pyspark.sql import SparkSession
    except ImportError:
        logger.error("PySpark kurulu değil! Lütfen çalıştırın: pip install pyspark")
        sys.exit(1)

    logger.info("⚡ Apache Spark oturumu başlatılıyor...")
    spark = (
        SparkSession.builder
        .appName("NovaSparkDataPipeline")
        .master("local[*]")
        .config("spark.driver.memory", "4g")
        .config("spark.sql.execution.arrow.pyspark.enabled", "true")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark

def veriyi_isle_ve_aktar(
    input_path: str,
    db_path: str,
    file_format: str = "text",
    topic: str = "Genel",
    source_url: str = "spark://local",
    min_length: int = 40,
    max_chunk_length: int = 1000
):
    from pyspark.sql import functions as F
    from db_manager import TrainerDBManager

    spark = spark_oturum_olustur()
    logger.info(f"📂 Veri okunuyor: {input_path} (Format: {file_format})")

    # 1. Spark ile Dağıtık Okuma (Spark Quick Start Mantığı)
    if file_format == "text":
        df = spark.read.text(input_path)
        # Sütun adı 'value' olarak gelir
    elif file_format == "parquet":
        df = spark.read.parquet(input_path)
        if "value" not in df.columns and "text" in df.columns:
            df = df.withColumnRenamed("text", "value")
    elif file_format == "csv":
        df = spark.read.option("header", "true").csv(input_path)
        if "value" not in df.columns and "text" in df.columns:
            df = df.withColumnRenamed("text", "value")
    elif file_format == "json":
        df = spark.read.json(input_path)
        if "value" not in df.columns and "text" in df.columns:
            df = df.withColumnRenamed("text", "value")
    else:
        raise ValueError(f"Desteklenmeyen format: {file_format}")

    ham_sayi = df.count()
    logger.info(f"📊 Okunan ham satır sayısı: {ham_sayi:,}")

    # 2. Spark Dönüşümleri (Temizleme & Filtreleme)
    # Boş satırları ve çok kısa metinleri ele
    df_clean = (
        df.filter(F.col("value").isNotNull())
          .withColumn("value", F.trim(F.col("value")))
          .filter(F.length(F.col("value")) >= min_length)
          .dropDuplicates(["value"])
    )

    temiz_sayi = df_clean.count()
    logger.info(f"✨ Filtrelenmiş & Tekilleştirilmiş kayıt sayısı: {temiz_sayi:,}")

    if temiz_sayi == 0:
        logger.warning("Filtreleme sonrası veri kalmadı!")
        spark.stop()
        return

    # 3. SQLite nova.db'ye Toplu Yazma (Toplu Batch Ekleme)
    logger.info(f"💾 Veriler SQLite veritabanına aktarılıyor: {db_path}")
    db = TrainerDBManager(db_path)

    # Spark DataFrame'den satırları çekip batch halinde ekle
    batch = []
    toplam_eklenen = 0
    batch_boyutu = 2000

    # toLocalIterator bellek dostu bir şekilde driver'a akıtır
    for row in df_clean.select("value").toLocalIterator():
        metin = row["value"]
        # Çok uzun metinleri parçala
        if len(metin) > max_chunk_length:
            for s in range(0, len(metin), max_chunk_length - 100):
                parca = metin[s:s + max_chunk_length].strip()
                if len(parca) >= min_length:
                    batch.append((source_url, topic, parca))
        else:
            batch.append((source_url, topic, metin))

        if len(batch) >= batch_boyutu:
            eklenen = db.bulk_insert_knowledge(batch)
            toplam_eklenen += eklenen
            batch.clear()
            logger.info(f"  ➜ {toplam_eklenen:,} kayıt aktarıldı...")

    if batch:
        eklenen = db.bulk_insert_knowledge(batch)
        toplam_eklenen += eklenen
        batch.clear()

    logger.info(f"🎉 Aktarım tamamlandı! Toplam {toplam_eklenen:,} yeni kayıt bilgi_agaci'na (islendi=0) eklendi.")
    stats = db.get_stats()
    logger.info(f"📈 Güncel DB Durumu: {stats}")

    spark.stop()


def main():
    parser = argparse.ArgumentParser(description="Nova Spark Büyük Veri Hazırlama Boru Hattı")
    parser.add_argument("--input", type=str, help="Giriş dosya/klasör yolu (örn: data/*.txt)")
    parser.add_argument("--format", type=str, default="text", choices=["text", "parquet", "csv", "json"], help="Dosya formatı")
    parser.add_argument("--db", type=str, default="nova.db", help="Hedef SQLite nova.db yolu")
    parser.add_argument("--topic", type=str, default="Genel Bilgi", help="Veri konusu/etiketi")
    parser.add_argument("--url", type=str, default="spark://import", help="Kaynak referansı")
    parser.add_argument("--min_len", type=int, default=30, help="Minimum karakter uzunluğu")
    parser.add_argument("--demo", action="store_true", help="Proje içindeki README üzerinde demo çalıştır")

    args = parser.parse_args()

    if args.demo:
        logger.info("🧪 Demo Modu: Spark ile örnek metin işleniyor...")
        root_readme = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "README.md"))
        if not os.path.exists(root_readme):
            root_readme = os.path.join(os.path.dirname(__file__), "demo_metin.txt")
            with open(root_readme, "w", encoding="utf-8") as f:
                f.write(
                    "Nova AGI Yapay Zeka ve Büyük Veri Mimarisi.\n"
                    "Nova, dinamik olarak büyüyen ve sürekli öğrenen bir sinir ağı mimarisidir.\n"
                    "Apache Spark, büyük veri kümelerini temizlemek ve filtrelemek için kullanılır.\n"
                    "Derin öğrenme modelleri GPU üzerinde tensör hesaplamalarıyla eğitilir.\n"
                    "Network Morphism, sinir ağının sıfır kayıpla büyümesini sağlayan modern bir tekniktir.\n"
                    "Kuantum bilgisayarları ve yapay sinir ağları geleceğin teknolojilerini şekillendirir.\n"
                )
        veriyi_isle_ve_aktar(
            input_path=root_readme,
            db_path=args.db,
            file_format="text",
            topic="Nova Dokümantasyon",
            source_url="local://demo_metin.txt"
        )
        return

    if not args.input:
        parser.print_help()
        print("\nÖrnek kullanım:\n  python spark_data_pipeline.py --demo\n  python spark_data_pipeline.py --input \"data/*.txt\" --db nova.db")
        sys.exit(1)

    veriyi_isle_ve_aktar(
        input_path=args.input,
        db_path=args.db,
        file_format=args.format,
        topic=args.topic,
        source_url=args.url,
        min_length=args.min_len
    )

if __name__ == "__main__":
    main()
