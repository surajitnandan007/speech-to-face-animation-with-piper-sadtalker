# SadTalker Runpod Worker

This workspace packages the SadTalker demo logic as a Runpod Serverless worker.

## What this image does

- Accepts a job with either input text or a WAV file, plus an optional source face image
- Reuses the same SadTalker subprocess flow from the original demo
- Synthesizes speech with Piper when you send text
- Runs `inference.py` inside a Runpod worker
- Returns job metadata and, optionally, a base64-encoded MP4

## Input shape

Send either:

- `text`

Or one of these for `audio`:

- `audio_url`
- `audio_base64`
- `audio_path` for local testing

If `DEFAULT_SOURCE_IMAGE` points to a face image on your mounted Runpod volume, callers can omit the source image entirely.

Send one of these for `source_image` only when you want to override the default face:

- `source_image_url`
- `source_image_base64`
- `source_image_path` for local testing

Example:

```json
{
  "input": {
    "text": "Hello from the text to video SadTalker pipeline.",
    "source_image_path": "C:/temp/source.jpg",
    "options": {
      "preprocess": "full",
      "pose_style": 0,
      "expression_scale": 1.0,
      "size": 256,
      "still_mode": true,
      "enhancer": null
    },
    "return_video_base64": false
  }
}
```

## Build

Build the image for Runpod with `linux/amd64`:

```bash
docker build --platform linux/amd64 -t <docker-user>/sadtalker-runpod:0.1.0 .
```

If you want to pin a specific SadTalker commit or tag:

```bash
docker build --platform linux/amd64 \
  --build-arg SADTALKER_REPO_REF=main \
  -t <docker-user>/sadtalker-runpod:0.1.0 .
```

## Important model note

The Dockerfile clones the SadTalker source repo, but it does not download model weights automatically. Put the SadTalker checkpoints under `models/checkpoints/` before building if you want them baked into the image.

That keeps the worker image compatible with your "scale to zero" billing goal, because you can avoid paid persistent volumes.

The worker also uses `piper-tts` for text-to-speech. You can point `PIPER_VOICE` to a voice file on the mounted Runpod volume, for example `/runpod-volume/piper-voices/en_US-amy-medium.onnx`. Override this with:

- `PIPER_VOICE`
- `PIPER_DATA_DIR`
- `PIPER_DOWNLOAD_DIR`

## Local test

Update `test_input.json`, then run:

```bash
python handler.py
```

Or start the local Runpod API simulator:

```bash
python handler.py --rp_server_api --rp_api_host 0.0.0.0 --rp_api_port 8000
```

Use the PowerShell client for remote tests:

```powershell
powershell -ExecutionPolicy Bypass -File .\test_runpod.ps1 -ApiKey "<key>" -EndpointId "<endpoint-id>" -Text "Hello from Piper" -ImagePath "C:\temp\face.jpg"
```

## Deploy

1. Push the image to Docker Hub or GHCR.
2. Create a Runpod Serverless Queue endpoint.
3. Set `Active workers = 0`.
4. Set a low idle timeout such as `5s`.
5. Start with `Max workers = 1`.

For production output delivery, prefer uploading the MP4 to object storage from inside the worker and returning a URL instead of returning the video as base64.
