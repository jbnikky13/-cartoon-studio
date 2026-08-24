"""
Evidence Board mode UI — callable from the V6 shell app, same
pattern as realityblend_ui.py / explainer_studio_ui.py.
"""

from pathlib import Path
import tempfile

import streamlit as st
from PIL import Image

from evidence_board_renderer import (
    BoardItem, Beat,
    generate_default_corkboard,
    render_evidence_board_video,
    EDGE_TTS_AVAILABLE,
)


NARRATOR_VOICES = {
    "Bright / Female": "en-US-AriaNeural",
    "Warm / Female": "en-US-JennyNeural",
    "Calm / Male": "en-US-DavisNeural",
    "Deep / Male": "en-US-GuyNeural",
}


def _default_positions(n):
    """A reasonable scattered default layout so items don't need
    manual placement to get a usable first render."""

    layouts = {
        1: [(0.5, 0.5)],
        2: [(0.32, 0.42), (0.68, 0.55)],
        3: [(0.22, 0.35), (0.52, 0.55), (0.80, 0.32)],
        4: [(0.20, 0.30), (0.45, 0.60), (0.68, 0.28), (0.85, 0.58)],
        5: [
            (0.16, 0.30), (0.38, 0.55), (0.58, 0.28),
            (0.78, 0.55), (0.90, 0.25)
        ],
        6: [
            (0.14, 0.28), (0.32, 0.58), (0.50, 0.25),
            (0.68, 0.58), (0.84, 0.28), (0.92, 0.62)
        ],
    }

    return layouts.get(n, layouts[6][:n] if n <= 6 else [
        (0.1 + 0.8 * (i / max(1, n - 1)), 0.4) for i in range(n)
    ])


def render_evidence_board_studio():

    st.header("🕵️ Evidence Board")

    st.caption(
        "Photos/documents pinned to a board, connected by animated "
        "red string as the narration reveals each one \u2014 the "
        "\"detective board\" style."
    )

    if not EDGE_TTS_AVAILABLE:

        st.warning(
            "⚠️ edge-tts isn't installed, so beats will render "
            "silent. Add `edge-tts>=6.1.12` to requirements.txt."
        )

    st.subheader("1. Board background")

    bg_upload = st.file_uploader(
        "Upload a corkboard/wall photo (optional \u2014 a default "
        "board texture is used if you skip this)",
        type=["png", "jpg", "jpeg"],
        key="eb_bg"
    )

    if bg_upload:
        board_bg = Image.open(bg_upload).convert("RGB").resize(
            (1280, 720)
        )
    else:
        board_bg = generate_default_corkboard()

    st.image(board_bg, caption="Board background", width=400)

    st.subheader("2. Pin items")

    item_uploads = st.file_uploader(
        "Upload 2-6 photos/documents to pin to the board",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="eb_items"
    )

    if not item_uploads:

        st.info("Upload at least 2 items to continue.")
        return

    if len(item_uploads) < 2:

        st.warning("Add at least one more item \u2014 need 2+ to connect.")
        return

    if len(item_uploads) > 6:

        st.warning("Using the first 6 uploads; extra ones are ignored.")
        item_uploads = item_uploads[:6]

    positions = _default_positions(len(item_uploads))

    st.subheader("3. Narration \u2014 one line per item, in reveal order")

    st.caption(
        "Item 1's line plays while it's pinned. Each item after "
        "that gets a string drawn back to the previous item while "
        "its line plays."
    )

    items = []
    beats = []

    cols = st.columns(min(3, len(item_uploads)))

    for i, upload in enumerate(item_uploads):

        img = Image.open(upload).convert("RGBA")
        x, y = positions[i]

        with cols[i % len(cols)]:

            st.image(img, caption=upload.name, width=120)

            x = st.slider(
                "X", 0.05, 0.95, x, 0.01, key=f"eb_x_{i}"
            )
            y = st.slider(
                "Y", 0.10, 0.90, y, 0.01, key=f"eb_y_{i}"
            )
            rotation = st.slider(
                "Tilt", -20, 20, (-8 if i % 2 == 0 else 8),
                key=f"eb_rot_{i}"
            )
            scale = st.slider(
                "Size", 0.10, 0.40, 0.22, 0.01, key=f"eb_scale_{i}"
            )

            line_text = st.text_input(
                "Narration for this reveal",
                key=f"eb_line_{i}",
                placeholder=f"Item {i+1}..."
            )

        items.append(BoardItem(
            name=upload.name, image=img, x=x, y=y,
            scale=scale, rotation=rotation
        ))

        beats.append(Beat(
            text=line_text or f"Item {i + 1}.",
            item_index=i,
            connect_from_index=(i - 1) if i > 0 else None
        ))

    st.subheader("4. Final stamp (optional)")

    stamp_text = st.text_input(
        "Big bold text shown at the end (e.g. \"CONNECTED\", "
        "\"239 PEOPLE\", a key number or conclusion)",
        key="eb_stamp"
    )

    narrator_label = st.selectbox(
        "Narrator voice", list(NARRATOR_VOICES.keys())
    )

    st.subheader("5. Generate")

    if st.button(
        "🎬 Render Evidence Board Video",
        type="primary",
        use_container_width=True
    ):

        out = (
            Path(tempfile.gettempdir())
            / "evidence_board_output.mp4"
        )

        progress = st.progress(0.0)
        status = st.empty()
        status.text("Rendering (narration + string reveals)...")

        voice_id = NARRATOR_VOICES[narrator_label]

        result_path, err = render_evidence_board_video(
            board_bg, items, beats, out,
            narrator_voice=voice_id,
            stamp_text=stamp_text or None,
            progress_cb=lambda p: progress.progress(min(1.0, p))
        )

        if err:

            status.error(f"Render failed: {err}")

        elif result_path and Path(result_path).exists():

            status.success("Evidence board video created.")

            video_bytes = Path(result_path).read_bytes()

            st.video(video_bytes)

            st.download_button(
                "⬇️ Download MP4",
                data=video_bytes,
                file_name="evidence_board.mp4",
                mime="video/mp4"
            )

            try:
                Path(result_path).unlink()
            except Exception:
                pass

        else:

            status.error(
                "Render finished, but no video file was produced."
            )
