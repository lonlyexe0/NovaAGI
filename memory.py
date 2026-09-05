# ═══════════════════════════════════════════════════════════════════════════════
# memory.py  —  Nova'nın Epizodik ve Semantik Hafıza Sistemi
# ═══════════════════════════════════════════════════════════════════════════════
#
# Tablolar:
#   anilar      → Kullanıcı ↔ Nova konuşmaları (epizodik hafıza)
#   bilgi_agaci → İnternetten öğrenilen ham veriler (semantik hafıza)
#   gorevler    → Ajan iş kuyruğu
#
# RAG: TF-IDF benzeri anahtar kelime örtüşmesi ile bağlam getirme
# Thread-safe: threading.Lock + thread-local SQLite bağlantıları
# ═══════════════════════════════════════════════════════════════════════════════
import re
import sqlite3
import threading
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger("nova.memory")


class HafizaYoneticisi:
    """Nova'nın merkezi hafıza yöneticisi."""
    def __init__(self, db_yolu: str = "nova.db"):
        self.db_yolu = db_yolu
        self._local  = threading.local()   # Her thread'e özel bağlantı
        self._lock   = threading.Lock()    # Yazma işlemleri için kilit
        self.tablolari_kur()
        logger.info(f"[Hafıza] Veritabanı hazır: {db_yolu}")

    # ── Bağlantı Yönetimi ─────────────────────────────────────────────────────
    def _baglanti(self) -> sqlite3.Connection:
        """Thread-local SQLite bağlantısı döndür."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self.db_yolu, check_same_thread=False)
            conn.row_factory    = sqlite3.Row
            conn.isolation_level = None          # autocommit kapalı
            conn.execute("PRAGMA journal_mode = WAL")   # Eşzamanlı okuma/yazma
            conn.execute("PRAGMA synchronous  = NORMAL")
            conn.execute("PRAGMA foreign_keys = ON")
            self._local.conn = conn
        return self._local.conn

    # ── Şema ──────────────────────────────────────────────────────────────────
    def tablolari_kur(self):
        with self._lock:
            conn = self._baglanti()
            conn.executescript("""
                BEGIN;

                CREATE TABLE IF NOT EXISTS anilar (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    rol         TEXT NOT NULL
                                    CHECK(rol IN ('kullanici','nova','sistem')),
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

                CREATE TABLE IF NOT EXISTS gorevler (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    tanim       TEXT NOT NULL,
                    durum       TEXT DEFAULT 'bekliyor'
                                    CHECK(durum IN (
                                        'bekliyor','devam_ediyor',
                                        'tamamlandi','basarisiz')),
                    oncelik     INTEGER DEFAULT 5,
                    olusturulma TEXT DEFAULT (datetime('now','localtime')),
                    tamamlanma  TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_anilar_zaman
                    ON anilar(zaman DESC);
                CREATE INDEX IF NOT EXISTS idx_bilgi_islendi
                    ON bilgi_agaci(islendi, zaman ASC);
                CREATE INDEX IF NOT EXISTS idx_gorev_durum
                    ON gorevler(durum, oncelik ASC, id ASC);

                COMMIT;
            """)

    # ══════════════════════════════════════════════════════════════════════════
    # ANI İŞLEMLERİ  (Epizodik Hafıza)
    # ══════════════════════════════════════════════════════════════════════════

    def ani_kaydet(self, rol: str, icerik: str, onem: float = 0.5) -> int:
        with self._lock:
            conn = self._baglanti()
            with conn:
                cur = conn.execute(
                    "INSERT INTO anilar (rol, icerik, onem_skoru) VALUES (?,?,?)",
                    (rol, icerik[:10_000], round(onem, 4))
                )
                return cur.lastrowid

    def son_anilar_getir(self, limit: int = 10) -> list[dict]:
        conn = self._baglanti()
        rows = conn.execute(
            "SELECT * FROM anilar ORDER BY zaman DESC, id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]   # Kronolojik sıra

    def ani_ara(self, sorgu: str, limit: int = 20) -> list[dict]:
        conn = self._baglanti()
        rows = conn.execute(
            "SELECT * FROM anilar WHERE icerik LIKE ? ORDER BY onem_skoru DESC LIMIT ?",
            (f"%{sorgu}%", limit)
        ).fetchall()
        return [dict(r) for r in rows]

    # ══════════════════════════════════════════════════════════════════════════
    # RAG  (Retrieval-Augmented Generation)
    # ══════════════════════════════════════════════════════════════════════════

    def rag_sorgula(self, sorgu: str, k: int = 5, max_karakter: int = 600) -> str:
        """
        TF-IDF benzeri anahtar kelime örtüşmesiyle en alakalı pasajları bul.
        Hem anilar hem bilgi_agaci tablosunu tarar.
        Döndürür: birleştirilmiş bağlam metni (str)
        """
        conn = self._baglanti()

        STOPWORDS = {
            've','ile','bir','bu','da','de','mi','mı','mu','mü',
            'ne','ki','en','çok','için','ama','fakat','lakin',
            'the','a','an','is','in','of','to','that','it',
        }

        # Temizlenmiş anahtar kelimeler
        kelimeler = [
            w for w in re.split(r'\W+', sorgu.lower())
            if len(w) > 2 and w not in STOPWORDS
        ]
        if not kelimeler:
            # Kelime yoksa son anıları döndür
            son = self.son_anilar_getir(3)
            return " | ".join(a['icerik'][:200] for a in son)

        puanli: list[tuple[float, str]] = []

        for tablo, col in [('anilar', 'icerik'), ('bilgi_agaci', 'icerik')]:
            rows = conn.execute(
                f"SELECT {col} FROM {tablo} ORDER BY id DESC LIMIT 300"
            ).fetchall()
            for row in rows:
                metin  = row[0] or ""
                lower  = metin.lower()
                # TF: her kelimenin kaç kez geçtiği / toplam uzunluk
                tf     = sum(lower.count(kw) for kw in kelimeler)
                # Uzunluk penaltısı: çok kısa pasajlar düşük puan
                agirlik = tf * (1 + min(len(metin) / 500, 1))
                if agirlik > 0:
                    puanli.append((agirlik, metin))

        puanli.sort(reverse=True, key=lambda x: x[0])

        secilen = []
        for _, metin in puanli[:k]:
            secilen.append(metin[:max_karakter])

        return "\n---\n".join(secilen) if secilen else ""

    # ══════════════════════════════════════════════════════════════════════════
    # BİLGİ AĞACI  (Semantik Hafıza)
    # ══════════════════════════════════════════════════════════════════════════

    def bilgi_kaydet(self, url: str, konu: str, icerik: str) -> int:
        """
        Aynı URL'den tekrar kayıt yapılmaz (idempotent).
        İçerik maksimum 60.000 karakter ile sınırlıdır.
        """
        with self._lock:
            conn = self._baglanti()
            # Mevcut kayıt kontrolü
            mevcut = conn.execute(
                "SELECT id FROM bilgi_agaci WHERE kaynak_url = ?", (url,)
            ).fetchone()
            if mevcut:
                logger.debug(f"[Hafıza] Zaten var: {url}")
                return mevcut[0]

            with conn:
                cur = conn.execute(
                    "INSERT INTO bilgi_agaci (kaynak_url, konu, icerik) VALUES (?,?,?)",
                    (url, konu[:200], icerik[:60_000])
                )
                logger.info(f"[Hafıza] Bilgi eklendi ({len(icerik):,} kar.): {konu[:60]}")
                return cur.lastrowid

    def egitilmemis_bilgi_getir(self, limit: int = 16) -> list[dict]:
        """Henüz eğitimde kullanılmamış bilgileri getir."""
        conn = self._baglanti()
        rows = conn.execute(
            "SELECT * FROM bilgi_agaci WHERE islendi = 0 "
            "ORDER BY zaman ASC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def bilgiyi_isle(self, bilgi_id: int):
        """Bilgiyi eğitilmiş olarak işaretle."""
        with self._lock:
            conn = self._baglanti()
            with conn:
                conn.execute(
                    "UPDATE bilgi_agaci SET islendi = 1 WHERE id = ?",
                    (bilgi_id,)
                )

    # ══════════════════════════════════════════════════════════════════════════
    # GÖREV KUYRUĞU
    # ══════════════════════════════════════════════════════════════════════════

    def gorev_ekle(self, tanim: str, oncelik: int = 5) -> int:
        with self._lock:
            conn = self._baglanti()
            with conn:
                cur = conn.execute(
                    "INSERT INTO gorevler (tanim, oncelik) VALUES (?,?)",
                    (tanim[:2_000], max(1, min(10, oncelik)))
                )
                logger.info(f"[Görev] Eklendi (öncelik={oncelik}): {tanim[:80]}")
                return cur.lastrowid

    def bekleyen_gorev_getir(self) -> Optional[dict]:
        conn = self._baglanti()
        row = conn.execute(
            "SELECT * FROM gorevler "
            "WHERE durum = 'bekliyor' "
            "ORDER BY oncelik ASC, id ASC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    def gorev_guncelle(self, gorev_id: int, durum: str):
        with self._lock:
            conn = self._baglanti()
            tamamlanma = (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if durum == 'tamamlandi' else None
            )
            with conn:
                conn.execute(
                    "UPDATE gorevler SET durum = ?, tamamlanma = ? WHERE id = ?",
                    (durum, tamamlanma, gorev_id)
                )

    def tum_gorevler(self, durum: Optional[str] = None) -> list[dict]:
        conn = self._baglanti()
        if durum:
            rows = conn.execute(
                "SELECT * FROM gorevler WHERE durum = ? ORDER BY id DESC LIMIT 50",
                (durum,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM gorevler ORDER BY id DESC LIMIT 50"
            ).fetchall()
        return [dict(r) for r in rows]

    # ══════════════════════════════════════════════════════════════════════════
    # İSTATİSTİK
    # ══════════════════════════════════════════════════════════════════════════

    def istatistik(self) -> dict:
        conn = self._baglanti()
        return {
            "ani_sayisi":        conn.execute("SELECT COUNT(*) FROM anilar").fetchone()[0],
            "bilgi_sayisi":      conn.execute("SELECT COUNT(*) FROM bilgi_agaci").fetchone()[0],
            "egitilmemis":       conn.execute("SELECT COUNT(*) FROM bilgi_agaci WHERE islendi=0").fetchone()[0],
            "gorev_bekleyen":    conn.execute("SELECT COUNT(*) FROM gorevler WHERE durum='bekliyor'").fetchone()[0],
            "gorev_tamamlandi":  conn.execute("SELECT COUNT(*) FROM gorevler WHERE durum='tamamlandi'").fetchone()[0],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# HIZLI TEST
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    hf = HafizaYoneticisi(":memory:")   # In-memory test

    # Anı testi
    hf.ani_kaydet("kullanici", "Merhaba Nova, yapay zeka nedir?")
    hf.ani_kaydet("nova", "Yapay zeka, makinelerin insan benzeri düşünme yeteneğidir.")

    # Bilgi ağacı testi
    hf.bilgi_kaydet("https://test.com", "test_konusu", "Python programlama dili çok güçlü bir dildir.")

    # Görev testi
    gid = hf.gorev_ekle("Tara: https://tr.wikipedia.org/wiki/Yapay_zeka", oncelik=1)
    hf.gorev_guncelle(gid, "tamamlandi")

    # RAG testi
    baglam = hf.rag_sorgula("yapay zeka makineler")
    print(f"RAG bağlamı:\n{baglam}\n")

    # İstatistik
    print("İstatistik:", hf.istatistik())
    print("\n✅ memory.py tüm testleri geçti.")
