"""
Evidence Board mode UI — upload items manually or derive a starter board
from a public article/webpage URL.
"""

from pathlib import Path
import tempfile
import io

import streamlit as st
from PIL import Image
import requests

from evidence_board_renderer import (
    BoardItem, Beat,
    generate_default_corkboard,
    render_evidence_board_video,
    EDGE_TTS_AVAILABLE,
)
from evidence_link_story import fetch_story, make_story_beats

NARRATOR_VOICES = {
    "Bright / Female": "en-US-AriaNeural",
    "Warm / Female": "en-US-JennyNeural",
    "Calm / Male": "en-US-DavisNeural",
    "Deep / Male": "en-US-GuyNeural",
}


def _default_positions(n):
    layouts = {
        1: [(0.5, 0.5)],
        2: [(0.32, 0.42), (0.68, 0.55)],
        3: [(0.22, 0.35), (0.52, 0.55), (0.80, 0.32)],
        4: [(0.20, 0.30), (0.45, 0.60), (0.68, 0.28), (0.85, 0.58)],
        5: [(0.16, 0.30), (0.38, 0.55), (0.58, 0.28), (0.78, 0.55), (0.90, 0.25)],
        6: [(0.14, 0.28), (0.32, 0.58), (0.50, 0.25), (0.68, 0.58), (0.84, 0.28), (0.92, 0.62)],
    }
    return layouts.get(n, layouts[6][:n] if n <= 6 else [(0.1 + 0.8 * (i / max(1, n - 1)), 0.4) for i in range(n)])


def _download_image(url):
    try:
        r = requests.get(url, headers={"User-Agent": "CartoonStudioEvidenceBoard/1.0"}, timeout=12)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGBA")
        if img.width < 120 or img.height < 80:
            return None
        return img
    except Exception:
        return None


def render_evidence_board_studio():
    st.header("🕵️ Evidence Board")
    st.caption("Turn a public article into a starter evidence-board scene, or build one manually.")

    if not EDGE_TTS_AVAILABLE:
        st.warning("⚠️ edge-tts isn't installed, so beats will render silent. Add `edge-tts>=6.1.12` to requirements.txt.")

    # ------------------------------------------------------------
    # URL STORY IMPORT
    # ------------------------------------------------------------
    st.subheader("✨ Auto-create from a story link")
    st.caption("Paste a public article/webpage URL. Cartoon Studio extracts the page title, readable text, and available public article images, then creates an editable board draft. It does not bypass paywalls, logins, or access controls.")

    story_url = st.text_input("Public story URL", placeholder="https://example.com/news/story", key="eb_story_url")
    if st.button("🔎 Derive Story + Pictures", type="secondary", use_container_width=True):
        if not story_url.strip():
            st.warning("Paste a public webpage URL first.")
        else:
            try:
                with st.spinner("Reading the public page and collecting available images..."):
                    story = fetch_story(story_url)
                    downloaded = [_download_image(u) for u in story["image_urls"]]
                    downloaded = [img for img in downloaded if img is not None][:6]
                    beats = make_story_beats(story, count=max(2, len(downloaded) or 4))
                    st.session_state["eb_story"] = story
                    st.session_state["eb_auto_images"] = downloaded
                    st.session_state["eb_auto_beats"] = beats
                st.success(f"Draft created: {story['title']} — {len(downloaded)} usable image(s) found.")
            except Exception as exc:
                st.error(f"Could not read that page: {exc}")

    if st.session_state.get("eb_story"):
        story = st.session_state["eb_story"]
        st.markdown(f"**{story.get('title', 'Story')}**")
        if story.get("description"):
            st.caption(story["description"][:500])
        st.info("Review the extracted text and images before publishing. Image availability depends on what the public webpage exposes.")
        with st.expander("📖 Extracted story text"):
            st.write(story.get("text", "")[:12000])

    # ------------------------------------------------------------
    # BOARD BACKGROUND
    # ------------------------------------------------------------
    st.subheader("1. Board background")
    bg_upload = st.file_uploader("Upload a corkboard/wall photo (optional — a default board texture is used if you skip this)", type=["png", "jpg", "jpeg"], key="eb_bg")
    if bg_upload:
        board_bg = Image.open(bg_upload).convert("RGB").resize((1280, 720))
    else:
        board_bg = generate_default_corkboard()
    st.image(board_bg, caption="Board background", width=400)

    # ------------------------------------------------------------
    # ITEMS: AUTO OR MANUAL
    # ------------------------------------------------------------
    st.subheader("2. Pin items")
    auto_images = st.session_state.get("eb_auto_images", [])
    item_uploads = st.file_uploader("Or upload 2-6 photos/documents manually", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="eb_items")

    source_mode = st.radio("Image source", ["Use derived pictures", "Use uploaded pictures"], horizontal=True, key="eb_source_mode")
    if source_mode == "Use derived pictures" and auto_images:
        images = auto_images[:6]
        names = [f"article_image_{i+1}.jpg" for i in range(len(images))]
    elif source_mode == "Use uploaded pictures" and item_uploads:
        uploads = item_uploads[:6]
        images = [Image.open(u).convert("RGBA") for u in uploads]
        names = [u.name for u in uploads]
    else:
        st.info("Paste a public story link above and derive pictures, or choose uploaded pictures.")
        return

    if len(images) < 2:
        st.warning("Need at least 2 usable pictures to create connected evidence.")
        return

    positions = _default_positions(len(images))
    default_beats = st.session_state.get("eb_auto_beats", [])

    st.subheader("3. Narration — edit the generated reveal lines")
    st.caption("The imported story creates starter narration only. You can edit every line before rendering.")

    items = []
    beats = []
    cols = st.columns(min(3, len(images)))

    for i, img in enumerate(images):
        x, y = positions[i]
        with cols[i % len(cols)]:
            st.image(img, caption=names[i], width=120)
            x = st.slider("X", 0.05, 0.95, x, 0.01, key=f"eb_x_{i}")
            y = st.slider("Y", 0.10, 0.90, y, 0.01, key=f"eb_y_{i}")
            rotation = st.slider("Tilt", -20, 20, (-8 if i % 2 == 0 else 8), key=f"eb_rot_{i}")
            scale = st.slider("Size", 0.10, 0.40, 0.22, 0.01, key=f"eb_scale_{i}")
            generated = default_beats[i] if i < len(default_beats) else f"Item {i + 1}."
            line_text = st.text_area("Narration for this reveal", value=generated, key=f"eb_line_{i}", height=90)

        items.append(BoardItem(name=names[i], image=img, x=x, y=y, scale=scale, rotation=rotation))
        beats.append(Beat(text=line_text or f"Item {i + 1}.", item_index=i, connect_from_index=(i - 1) if i > 0 else None))

    st.subheader("4. Final stamp (optional)")
    stamp_text = st.text_input("Big bold text shown at the end (e.g. CONNECTED, key number or conclusion)", key="eb_stamp")
    narrator_label = st.selectbox("Narrator voice", list(NARRATOR_VOICES.keys()))

    st.subheader("5. Generate")
    if st.button("🎬 Render Evidence Board Video", type="primary", use_container_width=True):
        out = Path(tempfile.gettempdir()) / "evidence_board_output.mp4"
        progress = st.progress(0.0)
        status = st.empty()
        status.text("Rendering narration + evidence reveals...")
        voice_id = NARRATOR_VOICES[narrator_label]
        result_path, err = render_evidence_board_video(board_bg, items, beats, out, narrator_voice=voice_id, stamp_text=stamp_text or None, progress_cb=lambda p: progress.progress(min(1.0, p)))
        if err:
            status.error(f"Render failed: {err}")
        elif result_path and Path(result_path).exists():
            status.success("Evidence board video created.")
            video_bytes = Path(result_path).read_bytes()
            st.video(video_bytes)
            st.download_button("⬇️ Download MP4", data=video_bytes, file_name="evidence_board.mp4", mime="video/mp4")
            try:
                Path(result_path).unlink()
            except Exception:
                pass
        else:
            status.error("Render finished, but no video file was produced.")
