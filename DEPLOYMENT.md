# Cartoon Studio V6 deployment

## Render

This repository is configured for Render with `render.yaml`.

1. Connect `jbnikky13/-cartoon-studio` to Render.
2. Create the web service from the repository.
3. Render installs `requirements.txt` and starts Streamlit on `$PORT`.
4. The health check uses `/_stcore/health`.
5. Auto-deploy is enabled, so pushes to `main` trigger a new deployment.

Python is pinned to 3.12.10 in `render.yaml` for a predictable runtime.

## Docker

The repository also includes a `Dockerfile` for container deployment. It installs the same `requirements.txt` dependencies and launches Streamlit on port 8501.

## Runtime notes

- FFmpeg is supplied by `imageio-ffmpeg`; a system FFmpeg installation is not required by the application.
- `edge-tts` provides optional online text-to-speech. If it cannot reach the TTS service, the rendering pipeline should report the resulting error rather than crashing the whole app.
- Render's free instance has limited memory. Use the lower FPS/resolution options for longer videos.
- Generated video/audio files are temporary and should not be committed to Git.
- Do not commit `.env` or `.streamlit/secrets.toml`.

## Main V6 modes

- Classic Cartoon
- RealityBlend
- Explainer
- Evidence Board
- Join Clips

## Local run

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```
