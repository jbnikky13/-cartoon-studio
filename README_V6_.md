# Cartoon Studio V6 — RealityBlend

This package adds a lightweight RealityBlend mode to the existing Cartoon Studio.

## Files

- realityblend_models.py — project/character data models
- realityblend_engine.py — low-memory compositor + FFmpeg renderer
- realityblend_ui.py — Streamlit interface
- app_v6_realityblend_patch.py — exact integration instructions
- requirements_v6.txt — dependencies
- README_V6_INSTALL.md — installation guide

## Codespaces / GitHub

Copy these files into the root of the existing repository.

Merge `requirements_v6.txt` into `requirements.txt` (the dependency list is intentionally compatible with the current repo).

Then edit `app.py`.

Add:

    from realityblend_ui import render_realityblend

Add a new tab or expander:

    with st.expander("🌍 RealityBlend V6 — Real Background + Cartoon Characters"):
        render_realityblend()

Commit and push.

## Render

Keep the existing Start Command. Render should redeploy after the GitHub commit.

## Character assets

Transparent PNGs give the best results. Green-screen cleanup is available as an optional preparation step.

## Important

This V6 renderer is intentionally CPU/light-memory oriented. It does not use Blender, OpenGL, EGL, or a full-video in-memory frame buffer.

The current repository already uses Streamlit, Pillow, imageio-ffmpeg and edge-tts, so no large rendering framework is required.
