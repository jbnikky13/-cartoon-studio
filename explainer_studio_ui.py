"""
Standalone Explainer / faceless-video mode UI, callable from the
V6 shell app.

Reuses render_explainer_video() and NARRATOR_VOICES from
classic_cartoon_ui.py (the same tested TTS + kinetic-caption
pipeline), just exposed as its own top-level mode instead of being
nested inside the character-dialogue tabs.
"""

from pathlib import Path

import streamlit as st

from classic_cartoon_ui import (
    render_explainer_video,
    NARRATOR_VOICES,
    EXPLAINER_AVAILABLE,
    EXPLAINER_IMPORT_ERROR,
)


def render_explainer_studio():

    st.header("📊 Explainer Studio")

    st.caption(
        "Bold kinetic captions, narrator voice-over, no "
        "characters \u2014 a separate style from the character "
        "dialogue cartoon."
    )

    if not EXPLAINER_AVAILABLE:

        st.error(
            "⚠️ explainer_renderer.py isn't loading. "
            f"Import error: `{EXPLAINER_IMPORT_ERROR}`. "
            "Check that explainer_renderer.py sits in the repo "
            "root, alongside app.py."
        )
        return

    st.markdown(
        "**Script** \u2014 one beat per line. Wrap a line in "
        "`**stars**` to render it as a big stat/number callout "
        "instead of flowing text."
    )

    script = st.text_area(
        "Script",
        height=220,
        placeholder=(
            "Water is stranger than you think.\n"
            "**90%**\n"
            "of the ocean has never been explored.\n"
            "And we've mapped more of Mars than our own seafloor."
        ),
        label_visibility="collapsed"
    )

    narrator_label = st.selectbox(
        "Narrator voice",
        list(NARRATOR_VOICES.keys())
    )

    if st.button(
        "🚀 Render Explainer Video",
        key="render_explainer_studio_btn",
        type="primary"
    ):

        raw_lines = [
            line.strip()
            for line in script.splitlines()
            if line.strip()
        ]

        if not raw_lines:

            st.error("Add at least one line of script first.")
            return

        beats = []

        for line in raw_lines:

            is_stat = (
                line.startswith("**")
                and line.endswith("**")
                and len(line) > 4
            )

            text = line.strip("*") if is_stat else line

            beats.append({"text": text, "is_stat": is_stat})

        progress_bar = st.progress(0)
        status_text = st.empty()

        def _progress(pct):
            progress_bar.progress(min(1.0, pct))
            status_text.text(f"Rendering... {pct*100:.0f}%")

        status_text.text("Building explainer video...")

        voice_id = NARRATOR_VOICES[narrator_label]

        result_path, err = render_explainer_video(
            beats,
            narrator_voice=voice_id,
            progress_cb=_progress
        )

        if err:

            st.error(f"Render failed: {err}")

        elif result_path and Path(result_path).exists():

            status_text.text("Done!")
            progress_bar.progress(1.0)

            with open(result_path, "rb") as f:
                video_bytes = f.read()

            st.video(video_bytes)

            st.download_button(
                "⬇️ Download Explainer MP4",
                data=video_bytes,
                file_name="explainer_video.mp4",
                mime="video/mp4"
            )

            try:
                Path(result_path).unlink()
            except Exception:
                pass

        else:

            st.error(
                "Render finished, but no video file was produced."
            )
