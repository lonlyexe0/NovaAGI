import torch
import torch_directml

# DirectML cihazını tanımlayalım (AMD için anahtar bu)
device = torch_directml.device()

print(f"Cihaz Adı: {torch_directml.device_name(0)}")
print(f"DirectML Erişilebilir mi: {device is not None}")
