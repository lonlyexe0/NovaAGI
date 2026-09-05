# -*- coding: utf-8 -*-
"""
tokenizer.py - Nova Bağımsız Karakter/Token Yöneticisi
Karakter seviyesi kodlama, dinamik sözlük güncelleme ve JSON serileştirme.
"""
import os
import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger("nova.trainer.tokenizer")

class NovaTokenizer:
    def __init__(self, vocab_path: Optional[str] = None, max_vocab_size: int = 1024):
        self.vocab_path = vocab_path
        self.max_vocab_size = max_vocab_size
        self.char2id: Dict[str, int] = {}
        self.id2char: Dict[int, str] = {}
        
        if vocab_path and os.path.exists(vocab_path):
            self.yukle(vocab_path)
        else:
            self._varsayilan_olustur()
            if vocab_path:
                self.kaydet(vocab_path)

    def _varsayilan_olustur(self):
        """Temel harf, sayı ve sembollerle varsayılan sözlüğü kurar."""
        self.char2id.clear()
        self.id2char.clear()

        ozel_tokenlar = ["<PAD>", "<UNK>", "<BOS>", "<EOS>", "<SEP>"]
        for tok in ozel_tokenlar:
            idx = len(self.char2id)
            self.char2id[tok] = idx
            self.id2char[idx] = tok

        temel_alfabe = (
            " \n\t\r"
            "abcçdefgğhıijklmnoöpqrsştuüvwxyz"
            "ABCÇDEFGĞHIİJKLMNOÖPQRSŞTUÜVWXYZ"
            "0123456789.,!?;:'\"-()[]{}@#$%&*+=/<>\\|`~^_"
        )
        for ch in temel_alfabe:
            if ch not in self.char2id and len(self.char2id) < self.max_vocab_size:
                idx = len(self.char2id)
                self.char2id[ch] = idx
                self.id2char[idx] = ch

    def guncelle(self, metin: str) -> bool:
        """Yeni karakterleri sözlüğe ekler (kapasite elveriyorsa)."""
        degisti = False
        for ch in metin:
            if ch not in self.char2id:
                if len(self.char2id) < self.max_vocab_size:
                    idx = len(self.char2id)
                    self.char2id[ch] = idx
                    self.id2char[idx] = ch
                    degisti = True
        return degisti

    def encode(self, metin: str) -> List[int]:
        """Metni token ID dizisine dönüştürür."""
        unk_id = self.char2id.get("<UNK>", 1)
        return [self.char2id.get(ch, unk_id) for ch in metin]

    def decode(self, ids: List[int]) -> str:
        """Token ID dizisini metne dönüştürür."""
        return "".join(self.id2char.get(i, "") for i in ids)

    def kaydet(self, path: Optional[str] = None):
        target = path or self.vocab_path
        if not target:
            return
        os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
        tmp = target + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({
                "char2id": self.char2id,
                "id2char": {str(k): v for k, v in self.id2char.items()}
            }, f, ensure_ascii=False, indent=2)
        if os.path.exists(tmp) and os.path.getsize(tmp) > 10:
            import shutil
            shutil.copyfile(tmp, target)
            try:
                os.remove(tmp)
            except Exception:
                pass

    def yukle(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        self.char2id = d["char2id"]
        self.id2char = {int(k): v for k, v in d["id2char"].items()}
        logger.info(f"[Tokenizer] Sözlük yüklendi: {len(self.char2id)} token ({path})")
