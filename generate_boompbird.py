import os
import torch
from audiocraft.models import MusicGen
from audiocraft.data.audio import audio_write

MODEL = "facebook/musicgen-medium"
OUTPUT = os.path.expanduser("~/musicgen/boompbird_musicgen_medium")
DURATION = 30

PROMPT = """
cheerful upbeat arcade mobile game background music,
instrumental only, no vocals, no singing, no speech,
catchy playful melody, bright happy energetic atmosphere,
bouncy rhythm, fun arcade drums, light percussion,
playful synths, colorful game soundtrack,
simple memorable melodic hook,
fast but relaxed enough for continuous gameplay,
clean polished production, seamless game music feeling,
suitable for a cute bird jumping and avoiding obstacles,
positive joyful exciting mood,
no dark mood, no cinematic orchestral music
"""

print("=" * 60)
print("Boomp Bird Music Generator")
print("=" * 60)

print(f"PyTorch: {torch.__version__}")
print(f"CUDA: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")

print(f"\nLoading {MODEL}...")

model = MusicGen.get_pretrained(MODEL)

# AudioCraft manages the model device this way.
model.device = "cuda"

model.set_generation_params(
    duration=DURATION,
    temperature=1.0,
    top_k=250,
    top_p=0.0,
    cfg_coef=3.0,
)

print(f"Generating {DURATION} seconds...")
print("Prompt:")
print(PROMPT)
print()

with torch.no_grad():
    wav = model.generate(
        descriptions=[PROMPT],
        progress=True
    )

print("\nSaving audio...")

audio_write(
    OUTPUT,
    wav[0].cpu(),
    model.sample_rate,
    strategy="loudness",
    loudness_compressor=True,
)

print("\nDONE!")
print(f"Output: {OUTPUT}.wav")
