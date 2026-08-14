# Cartoon Studio V1.2.1

Streamlit Cloud reliability update.

### Fix
Uses `imageio-ffmpeg` from Python instead of relying on a system FFmpeg installation. This avoids common Streamlit Cloud FFmpeg/package issues.

### Deploy
Replace the old `app.py` and `requirements.txt` in GitHub with these files. `packages.txt` can be empty or removed.

Features:
- 12 original character choices
- Original urban animated-comedy style
- Script dialogue parsing
- Animated 2D scenes with mouth movement
- Voice-selection UI prepared for TTS
- MP4 export
- Short-video joining
