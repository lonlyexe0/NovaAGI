import os
import sys

# Windows UTF-8 konsol ayarı
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Coqui Lisansını otomatik onayla
os.environ["COQUI_TOS_AGREED"] = "1"

print("[1/4] TTS kütüphanesi yükleniyor...")
from TTS.api import TTS

print("[2/4] XTTS-v2 modeli yükleniyor (İlk çalıştırmada model HuggingFace'ten indirilir)...")
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)

speaker_path = "kerry_condon_friday.wav"
output_path = "nova_friday_test.wav"
sample_text = "Merhaba patron! Ben Nova. Artık Friday'ın ses tonuyla Türkçe konuşabiliyorum, nasıl buldun?"

print(f"[3/4] Ses klonlanıyor ve Türkçe seslendiriliyor...")
print(f"Metin: '{sample_text}'")
print(f"Referans Ses: {speaker_path}")

tts.tts_to_file(
    text=sample_text,
    speaker_wav=speaker_path,
    language="tr",
    file_path=output_path
)

print(f"[4/4] ✅ Başarılı! Ses '{output_path}' olarak kaydedildi.")
