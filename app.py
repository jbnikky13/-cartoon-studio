"""
Cartoon Studio V6
=================
RealityBlend-integrated Streamlit application.

This app is intentionally lightweight:
- No Blender/OpenGL/EGL
- Pillow compositing
- imageio-ffmpeg for MP4 rendering
- edge-tts for optional narration
- RealityBlend is a first-class mode
- Existing character PNGs can be used directly

Place this file in the repository root as app.py.
Keep:
    realityblend_engine.py
    realityblend_models.py
    realityblend_ui.py

If those files are missing, the app will still open and show a useful
installation message instead of crashing.
"""

import os
import sys
import tempfile
import uuid
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="Cartoon Studio V6",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Optional V6 modules
# ---------------------------------------------------------------------------

REALITYBLEND_AVAILABLE = False
REALITYBLEND_ERROR = None

try:
    from realityblend_ui import render_realityblend
    REALITYBLEND_AVAILABLE = True
except Exception as exc:
    REALITYBLEND_ERROR = exc

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
st.caption("2D Cartoon Animation + RealityBlend Faceless Video Engine")

st.markdown(
    """
    <div class="v6-card">
    <span class="v6-badge">V6</span>
    &nbsp; Create cartoon videos, or place your cartoon characters inside
    realistic environments for social-media videos.
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("🎛️ Studio")
    mode = st.radio(
        "Creation mode",
        [
            "🌍 RealityBlend",
            "🎭 Classic Cartoon",
            "📊 Explainer",
            "🎞️ Join Clips",
        ],
        index=0,
    )

    st.divider()
    st.caption("V6 lightweight renderer")
    st.caption("Designed to avoid Blender/OpenGL/EGL memory problems.")

# ---------------------------------------------------------------------------
# RealityBlend
# ---------------------------------------------------------------------------

if mode == "🌍 RealityBlend":
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

            Then restart/redeploy the Streamlit app.
            """
        )

# ---------------------------------------------------------------------------
# Classic Cartoon
# ---------------------------------------------------------------------------

elif mode == "🎭 Classic Cartoon":
    st.header("🎭 Classic Cartoon")
    st.info(
        "Your original cartoon engine can be connected here. "
        "RealityBlend does not replace your existing character assets."
    )

    assets_dir = Path("char_assets")
    if assets_dir.exists():
        images = sorted(
            [
                p for p in assets_dir.rglob("*")
                if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
            ]
        )
        if images:
            st.subheader("Character Library")
            cols = st.columns(min(4, len(images)))
            for i, image_path in enumerate(images):
                with cols[i % len(cols)]:
                    st.image(str(image_path), caption=image_path.stem,
                             use_container_width=True)
        else:
            st.warning("No character images found in `char_assets/`.")
    else:
        st.warning("The `char_assets/` directory was not found.")

    st.markdown(
        """
        ### Existing Cartoon Engine

        Keep your previous cartoon-rendering implementation if you already
        have one. V6's RealityBlend renderer is deliberately isolated so
        adding it does not break the existing cartoon workflow.

        If your legacy engine has a dedicated module, import it here and
        call it from this mode.
        """
    )

# ---------------------------------------------------------------------------
# Explainer
# ---------------------------------------------------------------------------

elif mode == "📊 Explainer":
    st.header("📊 Explainer Studio")
    st.write(
        "Use this area for the existing explainer workflow. "
        "RealityBlend can later share the same script/voice/subtitle pipeline."
    )

    script = st.text_area(
        "Explainer script",
        placeholder="Paste your explanation here...",
        height=220,
    )

    if st.button("Prepare Explainer"):
        if not script.strip():
            st.warning("Enter a script first.")
        else:
            st.success(
                "Script loaded. Connect your existing explainer renderer "
                "here without changing RealityBlend."
            )

# ---------------------------------------------------------------------------
# Join clips
# ---------------------------------------------------------------------------

elif mode == "🎞️ Join Clips":
    st.header("🎞️ Join Clips")
    st.write("Combine exported clips from Cartoon Studio or RealityBlend.")

    uploads = st.file_uploader(
        "Upload MP4 clips",
        type=["mp4", "mov", "m4v"],
        accept_multiple_files=True,
    )

    if uploads:
        st.success(f"{len(uploads)} clip(s) uploaded.")

        for i, upload in enumerate(uploads, start=1):
            st.write(f"{i}. {upload.name}")

        st.info(
            "Your existing clip-joining implementation can be connected here. "
            "The V6 RealityBlend renderer intentionally remains independent."
        )

# ---------------------------------------------------------------------------
# Footer / diagnostics
# ---------------------------------------------------------------------------

st.divider()

with st.expander("🔧 V6 Diagnostics"):
    st.write("Python:", sys.version.split()[0])
    st.write("Working directory:", os.getcwd())
    st.write("RealityBlend available:", REALITYBLEND_AVAILABLE)

    if REALITYBLEND_ERROR:
        st.write("RealityBlend import error:", repr(REALITYBLEND_ERROR))

    st.write(
        "Required V6 modules:",
        {
            "realityblend_engine.py": Path("realityblend_engine.py").exists(),
            "realityblend_models.py": Path("realityblend_models.py").exists(),
            "realityblend_ui.py": Path("realityblend_ui.py").exists(),
        },
    )

st.caption("Cartoon Studio V6 • RealityBlend")
