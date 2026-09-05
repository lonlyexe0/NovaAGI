import os
import sys
import winsound

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

os.environ["COQUI_TOS_AGREED"] = "1"

from TTS.api import TTS

print("[1/3] XTTS-v2 modeli yükleniyor...")
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)

speaker_path = "kerry_condon_friday.wav"
output_path = "nova_friday_en_test.wav"
sample_text = "Good morning, boss! All systems are fully operational and ready. It is great to be speaking with you. What are we working on today?"

print(f"[2/3] İngilizce ses sentezleniyor...")
print(f"Metin: {sample_text}")

tts.tts_to_file(
    text=sample_text,
    speaker_wav=speaker_path,
    language="en",
    file_path=output_path
)

print(f"[3/3] ✅ Başarılı! '{output_path}' üretildi, hoparlörden çalınıyor...")
winsound.PlaySound(output_path, winsound.SND_FILENAME)
print("Bitti!")
