"""
Cartoon Studio V6
=================
Shell app with three real modes:

- RealityBlend: cartoon characters composited onto real photo
  backgrounds, with per-line TTS audio, captions, and a proper
  per-line timeline.
- Classic Cartoon: the full character-dialogue engine (TTS voices,
  gestures, sprite art, blinking, memory-safe rendering).
- Explainer: faceless kinetic-caption narrator videos.

Each mode is a real, tested rendering pipeline — none of these are
placeholders. If a mode's files are missing, this shell shows a
clear diagnostic instead of crashing or silently doing nothing.
"""

import sys
import os
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="Cartoon Studio V6",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Load each mode's real implementation. Each is independent — one
# missing/broken module doesn't take down the others.
# ---------------------------------------------------------------------------

REALITYBLEND_AVAILABLE = False
REALITYBLEND_ERROR = None

try:
    from realityblend_ui import render_realityblend
    REALITYBLEND_AVAILABLE = True
except Exception as exc:
    REALITYBLEND_ERROR = exc

CLASSIC_AVAILABLE = False
CLASSIC_ERROR = None

try:
    from classic_cartoon_ui import render_classic_cartoon, join_videos
    CLASSIC_AVAILABLE = True
except Exception as exc:
    CLASSIC_ERROR = exc

EXPLAINER_STUDIO_AVAILABLE = False
EXPLAINER_STUDIO_ERROR = None

try:
    from explainer_studio_ui import render_explainer_studio
    EXPLAINER_STUDIO_AVAILABLE = True
except Exception as exc:
    EXPLAINER_STUDIO_ERROR = exc

EVIDENCE_BOARD_AVAILABLE = False
EVIDENCE_BOARD_ERROR = None

try:
    from evidence_board_ui import render_evidence_board_studio
    EVIDENCE_BOARD_AVAILABLE = True
except Exception as exc:
    EVIDENCE_BOARD_ERROR = exc

# ---------------------------------------------------------------------------
# Basic styling
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 3rem; }
    .v6-card {
        padding: 1rem 1.2rem;
        border: 1px solid rgba(128,128,128,.25);
        border-radius: 14px;
        margin-bottom: 1rem;
    }
    .v6-badge {
        display:inline-block;
        padding:.25rem .6rem;
        border-radius:999px;
        font-size:.8rem;
        font-weight:600;
        background:rgba(70,130,180,.14);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("🎬 Cartoon Studio V6")
st.caption(
    "Character dialogue cartoons, faceless explainer videos, and "
    "cartoon-characters-on-real-photos — three modes, one app."
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:

    st.header("🎛️ Studio")

    mode = st.radio(
        "Creation mode",
        [
            "🎭 Classic Cartoon",
            "🌍 RealityBlend",
            "📊 Explainer",
            "🕵️ Evidence Board",
            "🎞️ Join Clips",
        ],
        index=0,
    )

    st.divider()

    st.caption("Mode status:")
    st.caption(
        f"{'✅' if CLASSIC_AVAILABLE else '❌'} Classic Cartoon"
    )
    st.caption(
        f"{'✅' if REALITYBLEND_AVAILABLE else '❌'} RealityBlend"
    )
    st.caption(
        f"{'✅' if EXPLAINER_STUDIO_AVAILABLE else '❌'} Explainer"
    )
    st.caption(
        f"{'✅' if EVIDENCE_BOARD_AVAILABLE else '❌'} Evidence Board"
    )

# ---------------------------------------------------------------------------
# Classic Cartoon — the full character-dialogue engine
# ---------------------------------------------------------------------------

if mode == "🎭 Classic Cartoon":

    if CLASSIC_AVAILABLE:
        render_classic_cartoon()
    else:
        st.error("Classic Cartoon mode could not be loaded.")
        st.code(str(CLASSIC_ERROR))
        st.markdown(
            """
            Make sure these files are in the repository root:

            - `classic_cartoon_ui.py`
            - `sprite_renderer.py`
            - `explainer_renderer.py`
            - `char_assets/` (character art folder)

            Then restart/redeploy.
            """
        )

# ---------------------------------------------------------------------------
# RealityBlend
# ---------------------------------------------------------------------------

elif mode == "🌍 RealityBlend":

    if REALITYBLEND_AVAILABLE:
        render_realityblend()
    else:
        st.error("RealityBlend could not be loaded.")
        st.code(str(REALITYBLEND_ERROR))
        st.markdown(
            """
            Make sure these files are in the repository root:

            - `realityblend_engine.py`
            - `realityblend_models.py`
            - `realityblend_ui.py`

            Then restart/redeploy.
            """
        )

# ---------------------------------------------------------------------------
# Explainer
# ---------------------------------------------------------------------------

elif mode == "📊 Explainer":

    if EXPLAINER_STUDIO_AVAILABLE:
        render_explainer_studio()
    else:
        st.error("Explainer mode could not be loaded.")
        st.code(str(EXPLAINER_STUDIO_ERROR))
        st.markdown(
            """
            Make sure these files are in the repository root:

            - `explainer_studio_ui.py`
            - `explainer_renderer.py`
            - `classic_cartoon_ui.py`

            Then restart/redeploy.
            """
        )

elif mode == "🕵️ Evidence Board":

    if EVIDENCE_BOARD_AVAILABLE:
        render_evidence_board_studio()
    else:
        st.error("Evidence Board could not be loaded.")
        st.code(str(EVIDENCE_BOARD_ERROR))
        st.markdown(
            """
            Make sure this file is in the repository root:

            - `evidence_board_renderer.py`
            - `evidence_board_ui.py`

            Then restart/redeploy.
            """
        )

# ---------------------------------------------------------------------------
# Join clips — now wired to the real join_videos function
# ---------------------------------------------------------------------------

elif mode == "🎞️ Join Clips":

    st.header("🎞️ Join Clips")
    st.write(
        "Combine exported clips from any of the modes above into "
        "one video."
    )

    if not CLASSIC_AVAILABLE:

        st.error(
            "Join Clips needs classic_cartoon_ui.py (it provides "
            "the actual video-joining function)."
        )
        st.code(str(CLASSIC_ERROR))

    else:

        uploads = st.file_uploader(
            "Upload MP4 clips, in the order you want them joined",
            type=["mp4", "mov", "m4v"],
            accept_multiple_files=True,
        )

        if uploads:

            st.success(f"{len(uploads)} clip(s) ready.")

            for i, upload in enumerate(uploads, start=1):
                st.write(f"{i}. {upload.name}")

            if st.button(
                "🔗 Join Clips", type="primary"
            ):

                with st.spinner("Joining clips..."):

                    result_path, err = join_videos(uploads)

                if err:

                    st.error(f"Join failed: {err}")

                elif result_path and Path(result_path).exists():

                    st.success("Joined successfully.")

                    with open(result_path, "rb") as f:
                        video_bytes = f.read()

                    st.video(video_bytes)

                    st.download_button(
                        "⬇️ Download Joined MP4",
                        data=video_bytes,
                        file_name="joined_episode.mp4",
                        mime="video/mp4"
                    )

                    try:
                        Path(result_path).unlink()
                    except Exception:
                        pass

                else:

                    st.error(
                        "Join finished, but no output file was "
                        "produced."
                    )

# ---------------------------------------------------------------------------
# Footer / diagnostics
# ---------------------------------------------------------------------------

st.divider()

with st.expander("🔧 V6 Diagnostics"):

    st.write("Python:", sys.version.split()[0])
    st.write("Working directory:", os.getcwd())

    st.write(
        "Modes:",
        {
            "Classic Cartoon": CLASSIC_AVAILABLE,
            "RealityBlend": REALITYBLEND_AVAILABLE,
            "Explainer": EXPLAINER_STUDIO_AVAILABLE,
            "Evidence Board": EVIDENCE_BOARD_AVAILABLE,
        },
    )

    if CLASSIC_ERROR:
        st.write("Classic Cartoon import error:", repr(CLASSIC_ERROR))

    if REALITYBLEND_ERROR:
        st.write("RealityBlend import error:", repr(REALITYBLEND_ERROR))

    if EXPLAINER_STUDIO_ERROR:
        st.write("Explainer import error:", repr(EXPLAINER_STUDIO_ERROR))

    if EVIDENCE_BOARD_ERROR:
        st.write("Evidence Board import error:", repr(EVIDENCE_BOARD_ERROR))

    st.write(
        "Required files present:",
        {
            "classic_cartoon_ui.py": Path("classic_cartoon_ui.py").exists(),
            "sprite_renderer.py": Path("sprite_renderer.py").exists(),
            "explainer_renderer.py": Path("explainer_renderer.py").exists(),
            "explainer_studio_ui.py": Path("explainer_studio_ui.py").exists(),
            "realityblend_engine.py": Path("realityblend_engine.py").exists(),
            "realityblend_models.py": Path("realityblend_models.py").exists(),
            "realityblend_ui.py": Path("realityblend_ui.py").exists(),
            "evidence_board_renderer.py": Path("evidence_board_renderer.py").exists(),
            "evidence_board_ui.py": Path("evidence_board_ui.py").exists(),
            "char_assets/": Path("char_assets").exists(),
            "char_assets_fullbody/": Path("char_assets_fullbody").exists(),
        },
    )

st.caption("Cartoon Studio V6")
