import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
BLENDER_ENGINE = ROOT / "blender" / "engine.py"
OUTPUT = ROOT / "output"
PROJECTS = ROOT / "projects"
OUTPUT.mkdir(exist_ok=True)
PROJECTS.mkdir(exist_ok=True)

st.set_page_config(page_title="3D Cartoon Studio", page_icon="🎬", layout="wide")

st.title("🎬 3D Cartoon Studio")
st.caption("Original stylized 3D cartoon generation powered by Blender")

with st.sidebar:
    st.header("Render")
    blender = st.text_input("Blender executable", os.getenv("BLENDER_PATH", "blender"))
    resolution = st.selectbox("Resolution", ["1280x720", "1920x1080", "854x480"])
    fps = st.selectbox("FPS", [24, 25, 30], index=0)
    quality = st.selectbox("Quality", ["Fast", "Balanced", "High"], index=1)

    st.header("Characters")
    zuri = st.checkbox("Zuri Spark", True)
    milo = st.checkbox("Milo Quirk", True)

    st.header("Scene")
    environment = st.selectbox(
        "Environment",
        ["studio", "classroom", "park", "bedroom", "street", "pharmacy"]
    )

    st.header("Animation")
    gestures = st.checkbox("Gestures", True)
    expressions = st.checkbox("Facial expressions", True)
    blinking = st.checkbox("Blinking", True)

    st.header("Subtitles")
    use_subtitles = st.checkbox("Subtitles", True)

st.subheader("📝 Script")
st.caption("Use one dialogue line per row: Character: dialogue. Optional actions: [wave], [point], [walk], [sit], [nod], [shake], [laugh], [surprised].")

default = """Zuri Spark: [wave] Hey Milo! Are you ready?
Milo Quirk: [nod] Absolutely. What are we making?
Zuri Spark: [point] Our first 3D cartoon!
Milo Quirk: [laugh] This is going to be amazing!"""

script = st.text_area("Dialogue", default, height=220)

audio = st.file_uploader(
    "Optional voice/audio track",
    type=["wav", "mp3", "ogg", "m4a"],
    help="If supplied, it is added to the rendered video. Without audio, the engine uses timed procedural lip-sync."
)

col1, col2 = st.columns([1, 1])
with col1:
    st.subheader("Character staging")
    st.write("Zuri Spark stays on the left and Milo Quirk stays on the right. Speaking does not reposition them.")
with col2:
    st.subheader("Render pipeline")
    st.write("Streamlit → scene JSON → Blender → 3D animation → subtitles → MP4")

config = {
    "scene_name": "Cartoon Studio Scene",
    "environment": environment,
    "characters": [c for c, enabled in [("Zuri Spark", zuri), ("Milo Quirk", milo)] if enabled],
    "script": script,
    "fps": fps,
    "resolution": resolution,
    "quality": quality,
    "gestures": gestures,
    "expressions": expressions,
    "blinking": blinking,
    "subtitles": use_subtitles,
}

if st.button("🎬 BUILD 3D CARTOON", type="primary", use_container_width=True):
    if not config["characters"]:
        st.error("Select at least one character.")
        st.stop()

    project = PROJECTS / "scene.json"
    project.write_text(json.dumps(config, indent=2), encoding="utf-8")

    audio_path = None
    if audio:
        audio_path = PROJECTS / audio.name
        audio_path.write_bytes(audio.getbuffer())

    output = OUTPUT / "cartoon.mp4"
    if output.exists():
        output.unlink()

    cmd = [
        blender, "--background", "--python", str(BLENDER_ENGINE),
        "--", str(project), str(output),
        str(audio_path) if audio_path else ""
    ]

    st.info("Starting Blender. Rendering can take time depending on your computer.")
    log_box = st.empty()
    logs = []

    try:
        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        for line in p.stdout:
            logs.append(line.rstrip())
            logs = logs[-20:]
            log_box.code("\n".join(logs), language="text")
        code = p.wait()

        if code != 0:
            st.error("Blender returned an error. Check the log above.")
        elif output.exists():
            st.success("3D cartoon rendered successfully.")
            st.video(str(output))
            st.download_button(
                "⬇️ Download MP4",
                output.read_bytes(),
                file_name="cartoon.mp4",
                mime="video/mp4",
            )
        else:
            st.error("Blender finished but no MP4 was produced.")
    except FileNotFoundError:
        st.error("Blender was not found. Install Blender and put its executable path in the sidebar.")

st.divider()
st.markdown(
    "**Important:** this is a real Blender-based 3D pipeline, not a PIL/2D renderer. "
    "The GitHub files alone do not contain commercial 3D character assets; the engine creates original procedural characters."
)
