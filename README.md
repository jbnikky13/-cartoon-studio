# Cartoon Studio V1.2

A beginner-friendly Streamlit app for creating original 2D cartoon videos from scripts and joining short clips into longer videos.

## Included

- 12 original character choices
- Multiple cartoon styles, including an original urban animated-comedy style
- `Character: dialogue` script parsing
- Animated character motion and mouth movement timed to dialogue
- Voice-selection UI prepared for a TTS backend
- MP4 export
- Short-video joining

## Deploy

Upload `app.py`, `requirements.txt`, `packages.txt`, and `README.md` to GitHub.

In Streamlit Community Cloud, choose the repository and `app.py` as the main file. `packages.txt` installs FFmpeg.

## Important

The current version has voice-selection controls but does not call an external TTS provider yet. The next backend step can connect an AI TTS service to generate spoken audio for each character and mux it into the rendered video.
