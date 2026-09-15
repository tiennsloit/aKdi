import torch
from audiocraft.models import MusicGen
from audiocraft.data.audio import audio_write

print("CUDA available:", torch.cuda.is_available())
print("GPU:", torch.cuda.get_device_name(0))

print("Loading MusicGen Small...")
model = MusicGen.get_pretrained("facebook/musicgen-small")

# Force model onto GPU
# AudioCraft handles GPU placement internally
model.device = "cuda"
model.set_generation_params(
    duration=5
)

prompt = """
cheerful upbeat arcade game background music,
instrumental only, no vocals, no singing,
catchy playful melody, energetic drums,
bright and fun, suitable for a mobile bird game
"""

print("Generating 5 seconds on GPU...")

with torch.no_grad():
    wav = model.generate(
        descriptions=[prompt],
        progress=True
    )

audio_write(
    "~/musicgen/boompbird_gpu_test",
    wav[0].cpu(),
    model.sample_rate,
    strategy="loudness"
)

print("DONE")
print("Output: ~/musicgen/boompbird_gpu_test.wav")
