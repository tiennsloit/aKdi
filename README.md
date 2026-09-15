# MusicGen API

A FastAPI service that generates music with Meta's MusicGen (audiocraft) and runs as an
async job service: generation requests return immediately, then a background worker
generates the audio, uploads it to S3, and emails the requester a download link.

## Features

- Music generation with `facebook/musicgen-medium` (Meta audiocraft), GPU-accelerated
  (falls back to CPU automatically).
- Async job API: `POST /generate` returns HTTP 202 instantly with a `job_id`; the
  actual work happens in a background thread.
- Uploads the finished `.wav` to S3 bucket `bb-audio-test1` (region `ap-southeast-1`).
- Emails the requester (default `tiennsloit@gmail.com`, overridable per request) with
  the S3 location and a presigned download URL valid for 7 days.
- Job tracking via `GET /jobs/{job_id}` and `GET /jobs`.

## Requirements

- Conda env named `musicgen` with Python 3.10 (audiocraft's spaCy pin does not build
  on Python 3.13):

  ```bash
  conda create -n musicgen python=3.10 -y
  conda activate musicgen
  pip install audiocraft uvicorn fastapi boto3 requests
  # if pip pulled in incompatible versions:
  pip install 'numpy<2' 'transformers<5'
  ```

- AWS credentials configured for the account that owns bucket `bb-audio-test1`
  (e.g. `~/.aws/credentials` or environment variables; region `ap-southeast-1`,
  override with `AWS_DEFAULT_REGION`).

## Running the server

```bash
cd ~/musicgen
./run_musicgen.sh
```

The script cds into its own directory and exec's the `musicgen` conda env's Python,
so it works from anywhere. It serves uvicorn on `0.0.0.0:8000`.

> Note: `cd ~/musicgen ./run_musicgen.sh` is NOT valid shell — they are two commands,
> use `cd ~/musicgen && ./run_musicgen.sh`.

If PM2 is managing the app (it was on this machine), reload it instead:

```bash
pm2 restart <app-name-or-id>
```

## Verify it is up

```bash
curl http://localhost:8000/
# -> {"service":"MusicGen API","status":"running"}

curl http://localhost:8000/health
# -> {"status":"healthy","cuda":true,"gpu":"Quadro M6000 24GB"}
```

## Generating audio (async job + email)

```bash
curl -X POST http://localhost:8000/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"lo-fi hip hop beat","duration":30}'
```

Responds instantly with HTTP 202:

```json
{
  "success": true,
  "job_id": "a3173c56",
  "status": "queued",
  "message": "Generation job triggered. The audio will be uploaded to S3 and a link emailed to tiennsloit@gmail.com.",
  "status_url": "/jobs/a3173c56"
}
```

Optional fields: `duration` (seconds, default 30) and `email` (overrides the default
recipient `tiennsloit@gmail.com`).

Then track the job:

```bash
curl http://localhost:8000/jobs/a3173c56
```

Status flow: `queued` -> `generating` -> `uploading` -> `emailing` -> `done`
(with `s3_url`, `download_url`, `email_status_code`) or `failed` (with the error).
`GET /jobs` lists all jobs.

When the job finishes, the user receives an email (via the mailer webhook
`https://l6514unzid.execute-api.ap-southeast-1.amazonaws.com/prod/mailer/command/send`,
request body `{"to", "subject", "html"}`) containing:

- the S3 object URL, and
- a presigned download URL valid for 7 days (the bucket is private, so the plain S3
  link would return 403 — use the presigned one).

Generation is serialized with a lock so concurrent requests cannot collide on the GPU.
The mailer endpoint intermittently returns 502, so sends are retried up to 3 times
with backoff.

## Other scripts

- `verify_musicgen.py` — smoke test: loads MusicGen and generates a 1s clip.
- `gpu_test.py` — quick CUDA/torch sanity check.
- `upload_s3.py` — standalone S3 upload helper.
- `generate_boompbird.py` — one-off generation script.

Generated `.wav` files are written to `output/` before upload.
