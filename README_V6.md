# Cartoon Studio V6 — RealityBlend

This is an additive V6 feature for the existing `jbnikky13/-cartoon-studio`
repository.

## What it adds

- Real photo background + cartoon character compositing
- Transparent PNG character support
- Simple background removal for flat backgrounds
- Optional green-screen/chroma-key preparation
- Multiple characters
- Position, scale and depth ordering
- Lightweight contact shadows
- Idle/talking/bounce/nervous/nod/wave/point motion
- Slow camera drift/zoom
- TikTok/Shorts 9:16, YouTube 16:9 and square output
- Frame-by-frame streaming directly into FFmpeg
- No Blender/OpenGL required for RealityBlend

## Additive integration

Do NOT delete the existing cartoon renderer.

Copy these files into the repository root:

    realityblend_engine.py
    realityblend_models.py
    realityblend_ui.py

Install the dependencies from `requirements_v6.txt`.

Then add these two lines to the existing `app.py`:

    from realityblend_ui import render_realityblend

and, somewhere in the Streamlit UI where you want the new mode:

    with st.expander("🌍 RealityBlend — Cartoon characters in real environments", expanded=False):
        render_realityblend()

This keeps the existing Cartoon Studio UI and adds RealityBlend beneath/alongside it.

## Render strategy

RealityBlend renders one PIL frame at a time and pipes raw RGB frames into
FFmpeg. This avoids retaining hundreds of full-resolution frames in Python.

FFmpeg officially supports image overlay/filter graphs and chromakey-style
transparency; this V6 implementation uses the simpler Python compositor so the
Render deployment stays lightweight.

## Best input

For the cleanest result, upload character PNGs that already have transparent
backgrounds. The simple remover is intentionally conservative and is not a
replacement for a heavy AI segmentation model.

## Next stage

The next upgrade should add a true puppet rig for prepared character assets:
head, eyes, mouth, arms and torso as separate layers. That can be added without
changing the RealityBlend renderer API.
