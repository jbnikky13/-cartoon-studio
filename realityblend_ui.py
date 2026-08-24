"""
Streamlit UI for RealityBlend.

Import and call render_realityblend() from the existing Cartoon Studio app.
This keeps the legacy cartoon workflow intact.
"""
from pathlib import Path
import tempfile
import streamlit as st
from PIL import Image

from realityblend_engine import (
    Character, Scene, load_rgba, remove_simple_background, chroma_key,
    render_video, render_timeline_video, EDGE_TTS_AVAILABLE
)
from realityblend_models import build_timeline


NARRATOR_VOICES = {
    "Bright / Female": "en-US-AriaNeural",
    "Warm / Female": "en-US-JennyNeural",
    "Calm / Male": "en-US-DavisNeural",
    "Deep / Male": "en-US-GuyNeural",
}


def _save_upload(upload, suffix):
    p = Path(tempfile.gettempdir()) / f"cartoon_studio_v6_{suffix}"
    p.write_bytes(upload.getbuffer())
    return p


def render_realityblend():
    st.header("🌍 RealityBlend V6")
    st.caption("Put your cartoon characters inside real-world photo/video-style scenes.")

    bg_file = st.file_uploader(
        "1. Upload a real background",
        type=["png", "jpg", "jpeg"],
        key="rb_background",
    )

    if not bg_file:
        st.info("Upload a kitchen, bedroom, office, street, classroom, or any other background image.")
        return

    bg = Image.open(bg_file).convert("RGB")
    st.image(bg, caption="Background", use_container_width=True)

    st.subheader("2. Characters")
    char_files = st.file_uploader(
        "Upload one or more character PNGs",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="rb_chars",
    )

    if not char_files:
        st.warning("Upload at least one character.")
        return

    prepared = []
    for i, f in enumerate(char_files):
        img = load_rgba(f)
        c1, c2 = st.columns([2, 1])
        with c1:
            st.image(img, caption=f.name, width=180)
        with c2:
            prep = st.selectbox(
                f"Preparation · {f.name}",
                ["Keep alpha", "Remove simple background", "Green-screen key"],
                key=f"prep_{i}",
            )
            if prep == "Remove simple background":
                img = remove_simple_background(img)
            elif prep == "Green-screen key":
                img = chroma_key(img)
        prepared.append((f.name, img))

    st.subheader("3. Script")
    script = st.text_area(
        "Dialogue",
        value="Character 1: What are you doing?\nCharacter 2: I'm trying to fix this.\nCharacter 1: Again?!",
        height=150,
        key="rb_script",
    )

    rows, duration = build_timeline(script)
    st.caption(f"Estimated duration: {duration:.1f}s")

    st.subheader("4. Scene controls")
    col1, col2, col3 = st.columns(3)
    with col1:
        aspect = st.selectbox("Format", ["TikTok / Shorts 9:16", "YouTube 16:9", "Square 1:1"])
        fps = st.select_slider("FPS", options=[8, 10, 12, 15, 18, 24], value=12)
    with col2:
        zoom = st.slider("Camera depth / zoom", 1.0, 1.35, 1.04, 0.01)
        brightness = st.slider("Background brightness", 0.75, 1.25, 1.0, 0.01)
    with col3:
        contrast = st.slider("Background contrast", 0.75, 1.30, 1.0, 0.01)
        saturation = st.slider("Background saturation", 0.70, 1.30, 1.0, 0.01)

    if aspect == "TikTok / Shorts 9:16":
        width, height = 540, 960
    elif aspect == "YouTube 16:9":
        width, height = 640, 360
    else:
        width, height = 540, 540

    if not EDGE_TTS_AVAILABLE:

        st.warning(
            "⚠️ edge-tts isn't installed, so beats will render "
            "silent. Add `edge-tts>=6.1.12` to requirements_v6.txt."
        )

    st.subheader("5. Character placement")
    chars = {}
    voices = {}
    cols = st.columns(min(3, len(prepared)))
    for i, (name, img) in enumerate(prepared):
        with cols[i % len(cols)]:
            st.markdown(f"**{name}**")
            x = st.slider("X", 0.05, 0.95, min(0.85, 0.28 + i * 0.38), 0.01, key=f"x_{i}")
            y = st.slider("Base/Y", 0.35, 0.98, 0.84, 0.01, key=f"y_{i}")
            scale = st.slider("Size", 0.15, 0.90, 0.55, 0.01, key=f"s_{i}")
            voice_label = st.selectbox(
                "Voice (used when this name speaks in the script)",
                list(NARRATOR_VOICES.keys()),
                index=i % len(NARRATOR_VOICES),
                key=f"v_{i}",
            )
            # display name without extension, so it can match
            # "Name:" lines in the script naturally
            char_key = Path(name).stem
            chars[char_key] = Character(
                name=char_key, image=img, x=x, y=y, scale=scale,
                z=i + 10, motion="idle", shadow=True
            )
            voices[char_key] = NARRATOR_VOICES[voice_label]

    st.caption(
        "Tip: name your script lines to match the character names "
        "above (e.g. if your file is `zuri.png`, write `zuri: ...` "
        "in the script) so the right voice and \"talk\" motion get "
        "used for each line."
    )

    st.subheader("6. Generate")
    if st.button("🎬 Render RealityBlend Video", type="primary", use_container_width=True):
        out = Path(tempfile.gettempdir()) / "cartoon_studio_v6_realityblend.mp4"
        scene_template = Scene(
            background=bg,
            fps=fps,
            width=width,
            height=height,
            camera_zoom=zoom,
            brightness=brightness,
            contrast=contrast,
            saturation=saturation,
        )
        progress = st.progress(0.0)
        status = st.empty()
        status.text("Rendering beats (audio + captions + timeline)...")
        try:
            render_timeline_video(
                scene_template, chars, rows, voices, out,
                progress=lambda p: progress.progress(min(1.0, p))
            )
            status.success("RealityBlend video created.")
            st.video(str(out))
            st.download_button(
                "⬇️ Download MP4",
                data=out.read_bytes(),
                file_name="realityblend_v6.mp4",
                mime="video/mp4",
            )
        except Exception as exc:
            status.error(f"Render failed: {exc}")
