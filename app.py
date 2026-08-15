import json
import os
import subprocess
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
ENGINE = ROOT / "blender" / "engine.py"
PROJECTS = ROOT / "projects"
OUTPUT = ROOT / "output"

PROJECTS.mkdir(exist_ok=True)
OUTPUT.mkdir(exist_ok=True)

st.set_page_config(
    page_title="3D Cartoon Studio",
    page_icon="🎬",
    layout="wide",
)

st.title("🎬 3D Cartoon Studio")
st.caption("Procedural 3D cartoon animation powered by Blender")

with st.sidebar:
    st.header("Render")
    blender_path = st.text_input(
        "Blender executable",
        os.getenv("BLENDER_PATH", "blender"),
    )
    resolution = st.selectbox(
        "Resolution",
        ["854x480", "1280x720", "1920x1080"],
        index=1,
    )
    fps = st.selectbox("FPS", [24, 25, 30], index=0)
    quality = st.selectbox(
        "Quality",
        ["Fast", "Balanced", "High"],
        index=1,
    )

    st.header("Characters")
    zuri_enabled = st.checkbox("Zuri Spark", True)
    milo_enabled = st.checkbox("Milo Quirk", True)

    st.header("Scene")
    environment = st.selectbox(
        "Environment",
        ["studio", "classroom", "park", "bedroom", "street", "pharmacy"],
    )

    st.header("Animation")
    gestures = st.checkbox("Gestures", True)
    expressions = st.checkbox("Facial expressions", True)
    blinking = st.checkbox("Blinking", True)

    st.header("Subtitles")
    subtitles = st.checkbox("Subtitles", True)

st.subheader("📝 Script")
st.caption(
    "One line per dialogue: Character: dialogue. "
    "Actions: [wave] [point] [walk] [sit] [nod] [shake] [laugh] [surprised]"
)

default_script = """Zuri Spark: [wave] Hey Milo! Are you ready?
Milo Quirk: [nod] Absolutely. What are we making?
Zuri Spark: [point] Our first 3D cartoon!
Milo Quirk: [laugh] This is going to be amazing!"""

script = st.text_area("Dialogue", default_script, height=220)

audio = st.file_uploader(
    "Optional voice/audio track",
    type=["wav", "mp3", "ogg", "m4a"],
    help="The uploaded audio is mixed into the final MP4.",
)

config = {
    "scene_name": "Cartoon Studio Scene",
    "environment": environment,
    "characters": [
        name
        for name, enabled in [
            ("Zuri Spark", zuri_enabled),
            ("Milo Quirk", milo_enabled),
        ]
        if enabled
    ],
    "script": script,
    "fps": fps,
    "resolution": resolution,
    "quality": quality,
    "gestures": gestures,
    "expressions": expressions,
    "blinking": blinking,
    "subtitles": subtitles,
}

if st.button("🎬 BUILD 3D CARTOON", type="primary", use_container_width=True):
    if not config["characters"]:
        st.error("Select at least one character.")
        st.stop()

    if not ENGINE.exists():
        st.error(f"Blender engine not found: {ENGINE}")
        st.stop()

    project = PROJECTS / "scene.json"
    project.write_text(
        json.dumps(config, indent=2),
        encoding="utf-8",
    )

    audio_path = ""
    if audio is not None:
        audio_path = str(PROJECTS / audio.name)
        Path(audio_path).write_bytes(audio.getbuffer())

    output = OUTPUT / "cartoon.mp4"
    if output.exists():
        output.unlink()

    cmd = [
        blender_path,
        "--background",
        "--python",
        str(ENGINE),
        "--",
        str(project),
        str(output),
        audio_path,
    ]

    st.info("Blender is rendering the scene. Please wait...")
    log_box = st.empty()
    logs = []

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        for line in process.stdout:
            logs.append(line.rstrip())
            log_box.code("\n".join(logs[-30:]), language="text")

        return_code = process.wait()

        if return_code != 0:
            st.error("Blender returned an error.")
        elif not output.exists():
            st.error("Blender finished, but no MP4 was created.")
        else:
            st.success("3D cartoon rendered successfully.")
            st.video(str(output))
            st.download_button(
                "⬇️ Download MP4",
                output.read_bytes(),
                file_name="cartoon.mp4",
                mime="video/mp4",
            )

    except FileNotFoundError:
        st.error(
            "Blender was not found. Install Blender locally or set "
            "BLENDER_PATH to the Blender executable."
        )
    except Exception as exc:
        st.exception(exc)
