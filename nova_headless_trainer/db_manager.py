# -*- coding: utf-8 -*-
"""
db_manager.py - Nova Bağımsız Veritabanı Yöneticisi
SQLite nova.db üzerinde okuma, toplu veri yazma (Spark için) ve durum takibi.
"""
import sqlite3
import logging
from typing import List, Dict, Tuple, Any, Optional

logger = logging.getLogger("nova.trainer.db")

class TrainerDBManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._kur_tablolar()

    def _baglanti(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        return conn

    def _kur_tablolar(self):
        with self._baglanti() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS anilar (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    rol         TEXT NOT NULL CHECK(rol IN ('kullanici','nova','sistem')),
                    icerik      TEXT NOT NULL,
                    zaman       TEXT DEFAULT (datetime('now','localtime')),
                    onem_skoru  REAL DEFAULT 0.5
                );

                CREATE TABLE IF NOT EXISTS bilgi_agaci (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    kaynak_url  TEXT,
                    konu        TEXT,
                    icerik      TEXT NOT NULL,
                    islendi     INTEGER DEFAULT 0,
                    zaman       TEXT DEFAULT (datetime('now','localtime'))
                );

                CREATE INDEX IF NOT EXISTS idx_bilgi_islendi
                    ON bilgi_agaci(islendi, id ASC);
                CREATE INDEX IF NOT EXISTS idx_anilar_zaman
                    ON anilar(id DESC);
            """)

    def get_unprocessed_knowledge(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Eğitilmemiş bilgi_agaci kayıtlarını (islendi=0) getirir."""
        with self._baglanti() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, kaynak_url, konu, icerik FROM bilgi_agaci WHERE islendi = 0 ORDER BY id ASC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_any_knowledge(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Eğitilmiş dahi olsa rastgele/sıralı bilgi getirir (Sürekli epoch için)."""
        with self._baglanti() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, kaynak_url, konu, icerik FROM bilgi_agaci ORDER BY RANDOM() LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_memories(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Anılar tablosundaki metinleri getirir."""
        with self._baglanti() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, rol, icerik FROM anilar ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def mark_knowledge_processed(self, ids: List[int]) -> int:
        """Eğitimi tamamlanan kayıtları islendi=1 olarak işaretler."""
        if not ids:
            return 0
        with self._baglanti() as conn:
            cursor = conn.cursor()
            cursor.executemany(
                "UPDATE bilgi_agaci SET islendi = 1 WHERE id = ?",
                [(i,) for i in ids]
            )
            conn.commit()
            return cursor.rowcount

    def bulk_insert_knowledge(self, records: List[Tuple[str, str, str]]) -> int:
        """
        Büyük veri / Spark tarafından hazırlanan verileri hızlıca ekler.
        records: [(kaynak_url, konu, icerik), ...]
        """
        if not records:
            return 0
        with self._baglanti() as conn:
            cursor = conn.cursor()
            cursor.executemany(
                "INSERT INTO bilgi_agaci (kaynak_url, konu, icerik, islendi) VALUES (?, ?, ?, 0)",
                records
            )
            conn.commit()
            return len(records)

    def get_stats(self) -> Dict[str, int]:
        """Veritabanı istatistiklerini döndürür."""
        with self._baglanti() as conn:
            cursor = conn.cursor()
            toplam_bilgi = cursor.execute("SELECT COUNT(*) FROM bilgi_agaci").fetchone()[0]
            egitilmemis  = cursor.execute("SELECT COUNT(*) FROM bilgi_agaci WHERE islendi = 0").fetchone()[0]
            egitilmis    = cursor.execute("SELECT COUNT(*) FROM bilgi_agaci WHERE islendi = 1").fetchone()[0]
            anilar       = cursor.execute("SELECT COUNT(*) FROM anilar").fetchone()[0]
            return {
                "toplam_bilgi": toplam_bilgi,
                "egitilmemis_bilgi": egitilmemis,
                "egitilmis_bilgi": egitilmis,
                "toplam_anilar": anilar
            }

    def reset_all_to_unprocessed(self) -> int:
        """Tüm kayıtları tekrar eğitilmemiş (islendi=0) durumuna alır."""
        with self._baglanti() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE bilgi_agaci SET islendi = 0")
            conn.commit()
            return cursor.rowcount
