import os
import time
import uuid
import threading
from datetime import datetime

import requests
import torch
import uvicorn
import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from audiocraft.models import MusicGen
from audiocraft.data.audio import audio_write


MODEL_NAME = "facebook/musicgen-medium"
OUTPUT_DIR = os.path.expanduser("~/musicgen/output")

# S3 upload target
S3_BUCKET = "bb-audio-test1"
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "ap-southeast-1")
# How long the download link in the email stays valid (7 days)
PRESIGNED_EXPIRY = 7 * 24 * 3600

# Notification email settings
NOTIFY_EMAIL = "tiennsloit@gmail.com"
MAILER_URL = (
    "https://l6514unzid.execute-api.ap-southeast-1.amazonaws.com"
    "/prod/mailer/command/send"
)

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
# get_pretrained() already places the model on the right device
# (CUDA when available, CPU otherwise) — do not force "cuda" here.
print(f"Model device: {model.device}")

print("MusicGen loaded successfully.")

# In-memory job registry: job_id -> job info dict
JOBS = {}
JOBS_LOCK = threading.Lock()

# Serialize GPU/generation work so concurrent requests don't collide
GENERATE_LOCK = threading.Lock()


class GenerateRequest(BaseModel):
    prompt: str
    duration: int = 30
    email: str = NOTIFY_EMAIL


def set_job(job_id, **fields):
    with JOBS_LOCK:
        JOBS[job_id].update(fields)


def send_email(to, subject, html):
    """Send a notification email through the mailer webhook.

    Retries a few times because the mailer (API Gateway + Lambda)
    intermittently returns 5xx.
    """
    last_status = None
    for attempt in range(1, 4):
        try:
            resp = requests.post(
                MAILER_URL,
                json={"to": to, "subject": subject, "html": html},
                timeout=30,
            )
            last_status = resp.status_code
            print(
                f"Mailer attempt {attempt}: "
                f"{resp.status_code} {resp.text[:200]}"
            )
            if 200 <= resp.status_code < 300:
                return resp.status_code
        except Exception as e:
            print(f"Mailer attempt {attempt} failed: {e}")
        time.sleep(2 * attempt)
    return last_status


def upload_to_s3(file_path, key):
    """Upload file to S3; return (s3_url, presigned_download_url)."""
    s3 = boto3.client("s3")
    s3.upload_file(file_path, S3_BUCKET, key)
    s3_url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"
    download_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=PRESIGNED_EXPIRY,
    )
    return s3_url, download_url


def run_generation_job(job_id, request):
    """Background job: generate audio, upload to S3, email the user."""
    try:
        set_job(job_id, status="generating")

        with GENERATE_LOCK:
            model.set_generation_params(duration=request.duration)
            wav = model.generate([request.prompt])

        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{job_id}"
        output_path = os.path.join(OUTPUT_DIR, filename)

        audio_write(
            output_path,
            wav[0].cpu(),
            model.sample_rate,
            strategy="loudness",
            loudness_compressor=True,
        )

        wav_path = f"{output_path}.wav"
        print(f"Generated: {wav_path}")

        set_job(job_id, status="uploading")
        key = f"{filename}.wav"
        s3_url, download_url = upload_to_s3(wav_path, key)
        print(f"Uploaded to S3: {s3_url}")

        set_job(job_id, status="emailing", s3_url=s3_url)
        subject = "Your MusicGen audio is ready"
        html = (
            f"<p>Your audio for prompt "
            f"<b>{request.prompt}</b> is ready.</p>"
            f"<p>Download it here (link valid 7 days): "
            f"<a href=\"{download_url}\">{download_url}</a></p>"
            f"<p>S3 location: {s3_url}</p>"
            f"<p>Job ID: {job_id}</p>"
        )
        status_code = send_email(request.email, subject, html)

        set_job(
            job_id,
            status="done",
            filename=key,
            path=wav_path,
            s3_url=s3_url,
            download_url=download_url,
            email_sent_to=request.email,
            email_status_code=status_code,
            finished_at=datetime.now().isoformat(),
        )

    except ClientError as e:
        print(f"S3 upload failed for job {job_id}: {e}")
        set_job(job_id, status="failed", error=f"S3 upload failed: {e}")
    except Exception as e:
        print(f"Job {job_id} failed: {e}")
        set_job(job_id, status="failed", error=str(e))


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


@app.post("/generate", status_code=202)
def generate(request: GenerateRequest):
    """Trigger an async generation job; responds immediately."""

    if request.duration < 1 or request.duration > 120:
        raise HTTPException(
            status_code=400,
            detail="Duration must be between 1 and 120 seconds."
        )

    job_id = uuid.uuid4().hex[:8]

    with JOBS_LOCK:
        JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "prompt": request.prompt,
            "duration": request.duration,
            "email": request.email,
            "created_at": datetime.now().isoformat(),
        }

    thread = threading.Thread(
        target=run_generation_job,
        args=(job_id, request),
        daemon=True,
    )
    thread.start()

    print(f"Job {job_id} triggered: '{request.prompt}' "
          f"({request.duration}s) -> notify {request.email}")

    return {
        "success": True,
        "job_id": job_id,
        "status": "queued",
        "message": (
            "Generation job triggered. The audio will be uploaded "
            f"to S3 and a link emailed to {request.email}."
        ),
        "status_url": f"/jobs/{job_id}",
    }


@app.get("/jobs/{job_id}")
def job_status(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@app.get("/jobs")
def list_jobs():
    with JOBS_LOCK:
        return {"jobs": list(JOBS.values())}


if __name__ == "__main__":
    # Start the API server so the endpoints are actually reachable,
    # e.g. curl http://localhost:8000/
    uvicorn.run(app, host="0.0.0.0", port=8000)
