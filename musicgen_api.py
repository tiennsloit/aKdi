import os
import uuid
from datetime import datetime

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from audiocraft.models import MusicGen
from audiocraft.data.audio import audio_write


MODEL_NAME = "facebook/musicgen-medium"
OUTPUT_DIR = os.path.expanduser("~/musicgen/output")

os.makedirs(OUTPUT_DIR, exist_ok=True)

app = FastAPI(
    title="MusicGen API",
    description="Music generation service",
    version="1.0"
)

print("=" * 60)
print("Loading MusicGen...")
print(f"Model: {MODEL_NAME}")
print(f"CUDA available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")

model = MusicGen.get_pretrained(MODEL_NAME)
model.device = "cuda"

print("MusicGen loaded successfully.")


class GenerateRequest(BaseModel):
    prompt: str
    duration: int = 30


@app.get("/")
def root():
    return {
        "service": "MusicGen API",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "cuda": torch.cuda.is_available(),
        "gpu": torch.cuda.get_device_name(0)
        if torch.cuda.is_available()
        else None
    }


@app.post("/generate")
def generate(request: GenerateRequest):

    if request.duration < 1 or request.duration > 120:
        raise HTTPException(
            status_code=400,
            detail="Duration must be between 1 and 120 seconds."
        )

    print("\n" + "=" * 60)
    print("NEW GENERATION")
    print(f"Duration: {request.duration}")
    print(f"Prompt: {request.prompt}")

    model.set_generation_params(
        duration=request.duration,
        temperature=1.0,
        top_k=250,
        top_p=0.0,
        cfg_coef=3.0,
    )

    try:
        with torch.no_grad():
            wav = model.generate(
                descriptions=[request.prompt],
                progress=True
            )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]

        filename = f"music_{timestamp}_{unique_id}"

        output_path = os.path.join(
            OUTPUT_DIR,
            filename
        )

        audio_write(
            output_path,
            wav[0].cpu(),
            model.sample_rate,
            strategy="loudness",
            loudness_compressor=True,
        )

        print(f"Generated: {output_path}.wav")

        return {
            "success": True,
            "filename": f"{filename}.wav",
            "path": f"{output_path}.wav"
        }

    except Exception as e:
        print(f"Generation failed: {e}")

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
