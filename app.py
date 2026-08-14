import streamlit as st
from pathlib import Path
import tempfile
import subprocess
import shutil
import re
import os
import json
import math
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

# ============================================================
# CARTOON STUDIO V3
# ============================================================

st.set_page_config(
    page_title="Cartoon Studio V3",
    page_icon="🎬",
    layout="wide"
)

WORK = Path(tempfile.gettempdir()) / "cartoon_studio_v3"
WORK.mkdir(exist_ok=True)


# ============================================================
# ORIGINAL CHARACTER CAST
# ============================================================

CHARACTERS = {
    "Zuri Spark": {
        "tag": "The fast-talking optimist",
        "skin": (132, 82, 61),
        "hair": (38, 24, 25),
        "shirt": (224, 92, 80),
        "pants": (45, 55, 75),
        "accent": "🌟"
    },

    "Milo Quirk": {
        "tag": "The deadpan problem-solver",
        "skin": (177, 118, 84),
        "hair": (55, 38, 28),
        "shirt": (65, 145, 180),
        "pants": (48, 55, 70),
        "accent": "🧠"
    },

    "Kemi Bolt": {
        "tag": "The fearless tinkerer",
        "skin": (105, 68, 52),
        "hair": (28, 22, 20),
        "shirt": (230, 164, 58),
        "pants": (55, 65, 75),
        "accent": "⚡"
    },

    "Tari Reed": {
        "tag": "The calm observer",
        "skin": (154, 96, 69),
        "hair": (42, 28, 25),
        "shirt": (92, 170, 130),
        "pants": (50, 60, 75),
        "accent": "👀"
    },

    "Biko Bean": {
        "tag": "The snack-loving philosopher",
        "skin": (124, 77, 58),
        "hair": (70, 48, 35),
        "shirt": (155, 100, 190),
        "pants": (55, 55, 70),
        "accent": "🍪"
    },

    "Nala Vee": {
        "tag": "The ambitious overachiever",
        "skin": (184, 121, 88),
        "hair": (30, 24, 22),
        "shirt": (70, 115, 205),
        "pants": (55, 55, 80),
        "accent": "🚀"
    },

    "Dex Orbit": {
        "tag": "The conspiracy-minded friend",
        "skin": (145, 91, 66),
        "hair": (35, 27, 24),
        "shirt": (100, 105, 120),
        "pants": (45, 50, 65),
        "accent": "🛰️"
    },

    "Ayo Finch": {
        "tag": "The quiet comedian",
        "skin": (111, 70, 53),
        "hair": (26, 22, 20),
        "shirt": (205, 90, 135),
        "pants": (55, 60, 70),
        "accent": "😏"
    },

    "Rhea Moss": {
        "tag": "The practical realist",
        "skin": (160, 103, 75),
        "hair": (82, 52, 35),
        "shirt": (85, 150, 190),
        "pants": (50, 60, 75),
        "accent": "📌"
    },

    "Professor Pogo": {
        "tag": "The eccentric explainer",
        "skin": (185, 125, 92),
        "hair": (145, 145, 145),
        "shirt": (225, 225, 220),
        "pants": (65, 75, 85),
        "accent": "💡"
    },

    "Jax Noon": {
        "tag": "The dramatic storyteller",
        "skin": (119, 75, 57),
        "hair": (30, 24, 21),
        "shirt": (190, 75, 70),
        "pants": (48, 52, 65),
        "accent": "🎭"
    },

    "Simi Ray": {
        "tag": "The curious newcomer",
        "skin": (137, 85, 62),
        "hair": (44, 29, 24),
        "shirt": (75, 180, 165),
        "pants": (55, 60, 75),
        "accent": "🔎"
    }
}


# ============================================================
# ORIGINAL VISUAL STYLES
# ============================================================

STYLES = {
    "Bold 2D Comedy":
        "clean original 2D cartoon, expressive faces, strong silhouettes, playful comedy energy",

    "Flat Vector":
        "clean flat vector illustration, simple shapes and crisp outlines",

    "Comic Panel":
        "original comic-panel illustration, dynamic framing and expressive poses",

    "Storybook":
        "warm hand-drawn storybook illustration with textured linework",

    "Retro Cartoon":
        "original retro television cartoon aesthetic with expressive poses",

    "Sketch Motion":
        "loose animated sketch aesthetic with energetic linework",

    "Anime-Inspired":
        "original anime-inspired 2D illustration with expressive faces",

    "Noir Cartoon":
        "original noir cartoon aesthetic with dramatic framing"
}


LOCATIONS = [
    "Apartment",
    "Classroom",
    "Pharmacy",
    "Office",
    "Street",
    "Restaurant",
    "Park",
    "Bus Stop",
    "Corner Shop",
    "Rooftop"
]


EXPRESSIONS = [
    "Neutral",
    "Happy",
    "Surprised",
    "Thinking",
    "Annoyed",
    "Laughing",
    "Confused",
    "Excited"
]


ACTIONS = [
    "Talking",
    "Listening",
    "Pointing",
    "Waving",
    "Thinking",
    "Walking",
    "Laughing",
    "Reacting"
]


# ============================================================
# FONT
# ============================================================

def get_font(size=28, bold=False):

    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",

        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"
    ]

    for path in candidates:

        if Path(path).exists():
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


# ============================================================
# TEXT WRAPPING
# ============================================================

def wrap(text, limit=55):

    words = text.split()

    lines = []
    current = ""

    for word in words:

        test = (current + " " + word).strip()

        if len(test) <= limit:
            current = test

        else:

            if current:
                lines.append(current)

            current = word

    if current:
        lines.append(current)

    return lines


# ============================================================
# SCRIPT PARSER
# ============================================================

def parse_script(text):

    rows = []

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        match = re.match(
            r"^([^:]{1,40}):\s*(.+)$",
            line
        )

        if match:

            speaker = match.group(1).strip()
            dialogue = match.group(2).strip()

        else:

            speaker = "Narrator"
            dialogue = line

        rows.append((speaker, dialogue))

    return rows


# ============================================================
# BACKGROUND
# ============================================================

def draw_background(draw, location, width, height):

    draw.rectangle(
        [0, 0, width, height],
        fill=(195, 220, 238)
    )

    draw.rectangle(
        [0, int(height * 0.68), width, height],
        fill=(145, 135, 115)
    )

    draw.rectangle(
        [55, 70, width - 55, int(height * 0.68)],
        fill=(232, 225, 211),
        outline=(65, 65, 65),
        width=4
    )

    labels = {

        "Apartment": "LIVING ROOM",
        "Classroom": "CLASSROOM",
        "Pharmacy": "COMMUNITY PHARMACY",
        "Office": "OFFICE",
        "Street": "CITY STREET",
        "Restaurant": "RESTAURANT",
        "Park": "PARK",
        "Bus Stop": "BUS STOP",
        "Corner Shop": "CORNER SHOP",
        "Rooftop": "ROOFTOP"
    }

    title = labels[location]

    draw.text(
        (width // 2 - 120, 95),
        title,
        font=get_font(30, True),
        fill=(50, 50, 55)
    )

    if location in [
        "Apartment",
        "Office",
        "Classroom",
        "Pharmacy",
        "Restaurant",
        "Corner Shop"
    ]:

        for x in [140, 470, 800]:

            draw.rectangle(
                [x, 300, x + 210, 440],
                fill=(150, 120, 95),
                outline=(70, 60, 55),
                width=3
            )

    elif location in ["Park", "Rooftop"]:

        draw.rectangle(
            [0, 500, width, height],
            fill=(105, 170, 100)
        )

        for x in [150, 1000]:

            draw.rectangle(
                [x, 300, x + 28, 500],
                fill=(105, 70, 45)
            )

            draw.ellipse(
                [x - 55, 220, x + 85, 360],
                fill=(70, 145, 75)
            )

    else:

        draw.rectangle(
            [0, 480, width, height],
            fill=(90, 92, 96)
        )

        for x in range(80, width, 240):

            draw.rectangle(
                [x, 200, x + 160, 480],
                fill=(170, 160, 150),
                outline=(75, 70, 68),
                width=3
            )


# ============================================================
# CHARACTER
# ============================================================

def draw_character(
    draw,
    name,
    x,
    ground,
    scale,
    expression,
    talking,
    frame,
    action
):

    character = CHARACTERS[name]

    head_size = int(58 * scale)

    bob = int(
        5 * math.sin(frame / 5)
    )

    x += int(
        3 * math.sin(frame / 8)
    )

    ground += bob

    head_y = ground - int(300 * scale)

    body_top = ground - int(235 * scale)

    # Shadow

    draw.ellipse(
        [
            x - 75,
            ground - 4,
            x + 75,
            ground + 15
        ],
        fill=(80, 80, 80)
    )

    # Legs

    draw.line(
        [x - 20, ground - 95, x - 35, ground],
        fill=(45, 45, 50),
        width=13
    )

    draw.line(
        [x + 20, ground - 95, x + 35, ground],
        fill=(45, 45, 50),
        width=13
    )

    # Body

    draw.rounded_rectangle(
        [
            x - 46,
            body_top,
            x + 46,
            ground - 80
        ],
        radius=20,
        fill=character["shirt"],
        outline=(45, 45, 50),
        width=4
    )

    # Arms

    arm_y = body_top + 45

    lift = 25 if action in [
        "Waving",
        "Pointing",
        "Excited"
    ] else 0

    draw.line(
        [
            x - 45,
            arm_y,
            x - 80,
            arm_y - 20 - lift
        ],
        fill=character["shirt"],
        width=20
    )

    draw.line(
        [
            x + 45,
            arm_y,
            x + 80,
            arm_y - 20 - lift
        ],
        fill=character["shirt"],
        width=20
    )

    # Head

    draw.ellipse(
        [
            x - head_size,
            head_y - head_size,
            x + head_size,
            head_y + head_size
        ],
        fill=character["skin"],
        outline=(55, 45, 40),
        width=4
    )

    # Hair

    draw.arc(
        [
            x - head_size - 3,
            head_y - head_size - 5,
            x + head_size + 3,
            head_y + 20
        ],
        180,
        360,
        fill=character["hair"],
        width=16
    )

    # Eyes

    eye_y = head_y - 12
    dx = 22

    eye_height = (
        15
        if expression in ["Surprised", "Excited"]
        else 8
    )

    draw.ellipse(
        [
            x - dx - 11,
            eye_y - eye_height,
            x - dx + 11,
            eye_y + eye_height
        ],
        fill=(25, 25, 25)
    )

    draw.ellipse(
        [
            x + dx - 11,
            eye_y - eye_height,
            x + dx + 11,
            eye_y + eye_height
        ],
        fill=(25, 25, 25)
    )

    # Mouth

    mouth_y = head_y + 35

    if expression in ["Laughing", "Happy"]:

        draw.arc(
            [
                x - 28,
                mouth_y - 15,
                x + 28,
                mouth_y + 25
            ],
            0,
            180,
            fill=(80, 25, 30),
            width=5
        )

    elif talking:

        opening = int(
            9 + 10 * abs(
                math.sin(frame / 2.2)
            )
        )

        draw.ellipse(
            [
                x - 23,
                mouth_y,
                x + 23,
                mouth_y + opening
            ],
            fill=(85, 25, 30)
        )

    elif expression == "Surprised":

        draw.ellipse(
            [
                x - 14,
                mouth_y,
                x + 14,
                mouth_y + 25
            ],
            fill=(85, 25, 30)
        )

    else:

        draw.line(
            [
                x - 18,
                mouth_y + 8,
                x + 18,
                mouth_y + 8
            ],
            fill=(80, 35, 35),
            width=4
        )

    # Name tag

    label = f"{character['accent']} {name}"

    box = draw.textbbox(
        (0, 0),
        label,
        font=get_font(20, True)
    )

    text_width = box[2] - box[0]

    draw.rounded_rectangle(
        [
            x - text_width // 2 - 10,
            ground + 22,
            x + text_width // 2 + 10,
            ground + 55
        ],
        radius=10,
        fill="white",
        outline=(70, 70, 70),
        width=2
    )

    draw.text(
        (
            x - text_width // 2,
            ground + 27
        ),
        label,
        font=get_font(20, True),
        fill=(35, 35, 35)
    )


# ============================================================
# RENDER FRAME
# ============================================================

def render_frame(
    dialogue,
    speaker,
    location,
    left,
    right,
    expression_left,
    expression_right,
    action,
    frame,
    size=(1280, 720)
):

    width, height = size

    image = Image.new(
        "RGB",
        size,
        (240, 240, 240)
    )

    draw = ImageDraw.Draw(image)

    draw_background(
        draw,
        location,
        width,
        height
    )

    draw_character(
        draw,
        left,
        330,
        650,
        1.0,
        expression_left,
        speaker == left,
        frame,
        action
    )

    if right:

        draw_character(
            draw,
            right,
            900,
            650,
            1.0,
            expression_right,
            speaker == right,
            frame,
            "Listening"
        )

    # Dialogue bubble

    draw.rounded_rectangle(
        [45, 35, 1235, 180],
        radius=24,
        fill=(255, 255, 255),
        outline=(45, 45, 50),
        width=4
    )

    draw.text(
        (70, 58),
        speaker,
        font=get_font(30, True),
        fill=(35, 35, 40)
    )

    y = 105

    for line in wrap(dialogue, 76)[:2]:

        draw.text(
            (70, y),
            line,
            font=get_font(27),
            fill=(40, 40, 45)
        )

        y += 34

    return image


# ============================================================
# VIDEO RENDERER
# ============================================================

def render_video(rows, project):

    fps = 12

    frames_dir = (
        WORK / f"frames_{os.getpid()}"
    )

    frames_dir.mkdir(
        exist_ok=True
    )

    output = (
        WORK /
        f"cartoon_v3_{os.getpid()}.mp4"
    )

    frame_index = 0

    try:

        for speaker, text in rows:

            if speaker not in project["cast"]:

                speaker = project["cast"][0]

            other = next(
                (
                    x
                    for x in project["cast"]
                    if x != speaker
                ),
                None
            )

            duration = max(
                2.2,
                min(
                    8.0,
                    1.8 + len(text) / 20
                )
            )

            frame_count = int(
                duration * fps
            )

            for frame in range(frame_count):

                image = render_frame(
                    text,
                    speaker,
                    project["location"],
                    speaker,
                    other,
                    project["expressions"].get(
                        speaker,
                        "Happy"
                    ),
                    project["expressions"].get(
                        other,
                        "Neutral"
                    )
                    if other
                    else "Neutral",
                    project["actions"].get(
                        speaker,
                        "Talking"
                    ),
                    frame
                )

                image.save(
                    frames_dir /
                    f"f_{frame_index:06d}.png"
                )

                frame_index += 1

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

        result = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-framerate",
                str(fps),
                "-i",
                str(
                    frames_dir /
                    "f_%06d.png"
                ),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(output)
            ],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:

            return output, None

        return None, result.stderr[-3000:]

    finally:

        shutil.rmtree(
            frames_dir,
            ignore_errors=True
        )


# ============================================================
# VIDEO JOINER
# ============================================================

def join_videos(files):

    work = (
        WORK /
        f"join_{os.getpid()}"
    )

    work.mkdir(
        exist_ok=True
    )

    clips = []

    try:

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

        for i, uploaded in enumerate(files):

            source = work / f"source{i}.mp4"
            clip = work / f"clip{i}.mp4"

            source.write_bytes(
                uploaded.getvalue()
            )

            result = subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-i",
                    str(source),
                    "-vf",
                    "scale=1280:720:force_original_aspect_ratio=decrease,"
                    "pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
                    "format=yuv420p",
                    "-r",
                    "30",
                    "-c:v",
                    "libx264",
                    "-c:a",
                    "aac",
                    str(clip)
                ],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:

                return None, result.stderr[-2500:]

            clips.append(clip)

        manifest = work / "concat.txt"

        manifest.write_text(
            "\n".join(
                f"file '{clip.as_posix()}'"
                for clip in clips
            )
        )

        output = (
            WORK /
            f"episode_{os.getpid()}.mp4"
        )

        result = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(manifest),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(output)
            ],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:

            return output, None

        return None, result.stderr[-2500:]

    finally:

        shutil.rmtree(
            work,
            ignore_errors=True
        )


# ============================================================
# SESSION STATE
# ============================================================

if "project" not in st.session_state:

    st.session_state.project = {

        "name": "Untitled Cartoon",

        "style": "Bold 2D Comedy",

        "location": "Apartment",

        "cast": [
            "Zuri Spark",
            "Milo Quirk"
        ],

        "expressions": {},

        "actions": {},

        "script": ""
    }


if "scenes" not in st.session_state:

    st.session_state.scenes = []


# ============================================================
# HEADER
# ============================================================

st.markdown(
    "<h1>🎬 Cartoon Studio V3</h1>",
    unsafe_allow_html=True
)

st.caption(
    "Write → Cast → Storyboard → Animate → Assemble"
)


# ============================================================
# TABS
# ============================================================

tabs = st.tabs(
    [
        "✨ New Cartoon",
        "🧩 Storyboard",
        "🎭 Character Library",
        "🎞️ Join Videos",
        "📁 Project"
    ]
)


# ============================================================
# NEW CARTOON
# ============================================================

with tabs[0]:

    st.subheader(
        "1. Choose your cartoon style"
    )

    style_columns = st.columns(4)

    styles = list(STYLES)

    for i, style in enumerate(styles):

        with style_columns[i % 4]:

            if st.button(
                f"🎨 {style}",
                key=f"style_{i}",
                use_container_width=True
            ):

                st.session_state.project[
                    "style"
                ] = style

    selected_style = (
        st.session_state.project["style"]
    )

    st.info(
        f"Selected style: **{selected_style}**\n\n"
        f"{STYLES[selected_style]}"
    )

    # --------------------------------------------------------

    st.subheader(
        "2. Choose your cast"
    )

    cast = st.multiselect(
        "Choose up to 4 characters",
        list(CHARACTERS),
        default=st.session_state.project["cast"],
        max_selections=4
    )

    if not cast:

        cast = ["Zuri Spark"]

    st.session_state.project[
        "cast"
    ] = cast

    columns = st.columns(
        min(4, len(cast))
    )

    for i, name in enumerate(cast):

        with columns[i]:

            character = CHARACTERS[name]

            st.markdown(
                f"### {character['accent']} {name}"
            )

            st.caption(
                character["tag"]
            )

            st.session_state.project[
                "expressions"
            ][name] = st.selectbox(
                "Expression",
                EXPRESSIONS,
                index=1,
                key=f"expression_{name}"
            )

            st.session_state.project[
                "actions"
            ][name] = st.selectbox(
                "Action",
                ACTIONS,
                index=0,
                key=f"action_{name}"
            )

    # --------------------------------------------------------

    st.subheader(
        "3. Story setup"
    )

    left, right = st.columns(2)

    with left:

        st.session_state.project[
            "name"
        ] = st.text_input(
            "Project name",
            st.session_state.project["name"]
        )

    with right:

        current_location = (
            st.session_state.project["location"]
        )

        st.session_state.project[
            "location"
        ] = st.selectbox(
            "Main location",
            LOCATIONS,
            index=LOCATIONS.index(
                current_location
            )
        )

    # --------------------------------------------------------

    st.subheader(
        "4. Paste your script"
    )

    script = st.text_area(
        "Dialogue",
        height=240,
        value=st.session_state.project["script"],
        placeholder=(
            "Zuri Spark: I have a question.\n"
            "Milo Quirk: That sounds dangerous already.\n"
            "Zuri Spark: Why does the fridge light turn off when we close the door?"
        )
    )

    st.session_state.project[
        "script"
    ] = script

    if st.button(
        "🧠 Build Storyboard",
        type="primary",
        use_container_width=True
    ):

        if not script.strip():

            st.warning(
                "Add a script first."
            )

        else:

            rows = parse_script(script)

            st.session_state.scenes = []

            for i, (speaker, dialogue) in enumerate(rows):

                if speaker not in cast:

                    speaker = cast[0]

                duration = max(
                    2.2,
                    min(
                        8,
                        1.8 + len(dialogue) / 20
                    )
                )

                st.session_state.scenes.append(
                    {
                        "id": i + 1,
                        "speaker": speaker,
                        "dialogue": dialogue,
                        "location": st.session_state.project["location"],
                        "duration": duration,
                        "shot": "Medium shot",
                        "action": st.session_state.project[
                            "actions"
                        ].get(
                            speaker,
                            "Talking"
                        )
                    }
                )

            st.success(
                f"Storyboard created with {len(rows)} shots."
            )


# ============================================================
# STORYBOARD
# ============================================================

with tabs[1]:

    st.subheader(
        "🧩 Storyboard"
    )

    if not st.session_state.scenes:

        st.info(
            "Build a storyboard from the New Cartoon tab first."
        )

    else:

        for i, scene in enumerate(
            st.session_state.scenes
        ):

            with st.expander(
                f"SHOT {scene['id']} · "
                f"{scene['speaker']} · "
                f"{scene['duration']:.1f}s",
                expanded=(i == 0)
            ):

                col1, col2, col3 = st.columns(
                    [1.2, 1.8, 1]
                )

                with col1:

                    st.write(
                        f"**📍 {scene['location']}**"
                    )

                    camera_options = [
                        "Wide shot",
                        "Medium shot",
                        "Close-up",
                        "Over-the-shoulder"
                    ]

                    scene["shot"] = st.selectbox(
                        "Camera",
                        camera_options,
                        index=camera_options.index(
                            scene["shot"]
                        ),
                        key=f"camera_{i}"
                    )

                    scene["duration"] = st.slider(
                        "Duration",
                        1.5,
                        12.0,
                        float(scene["duration"]),
                        0.5,
                        key=f"duration_{i}"
                    )

                with col2:

                    scene["dialogue"] = st.text_area(
                        "Dialogue",
                        scene["dialogue"],
                        key=f"dialogue_{i}",
                        height=110
                    )

                with col3:

                    scene["action"] = st.selectbox(
                        "Action",
                        ACTIONS,
                        index=(
                            ACTIONS.index(
                                scene["action"]
                            )
                            if scene["action"]
                            in ACTIONS
                            else 0
                        ),
                        key=f"scene_action_{i}"
                    )

                    if st.button(
                        "🗑️ Remove",
                        key=f"remove_{i}"
                    ):

                        st.session_state.scenes.pop(i)

                        st.rerun()

        # ----------------------------------------------------

        st.divider()

        if st.button(
            "🎬 Generate Cartoon From Storyboard",
            type="primary",
            use_container_width=True
        ):

            rows = [
                (
                    scene["speaker"],
                    scene["dialogue"]
                )
                for scene in st.session_state.scenes
            ]

            with st.spinner(
                "Rendering animated cartoon..."
            ):

                video, error = render_video(
                    rows,
                    st.session_state.project
                )

            if video:

                st.session_state.output = str(
                    video
                )

                st.success(
                    "Cartoon generated!"
                )

            else:

                st.error(
                    error or
                    "Rendering failed."
                )

        # ----------------------------------------------------

        if (
            st.session_state.get("output")
            and
            Path(
                st.session_state.output
            ).exists()
        ):

            st.video(
                st.session_state.output
            )

            st.download_button(
                "⬇️ Download MP4",
                Path(
                    st.session_state.output
                ).read_bytes(),
                "cartoon_v3.mp4",
                "video/mp4",
                use_container_width=True
            )


# ============================================================
# CHARACTER LIBRARY
# ============================================================

with tabs[2]:

    st.subheader(
        "🎭 Original Character Library"
    )

    st.write(
        "These characters are original Cartoon Studio characters "
        "designed as recurring personalities."
    )

    columns = st.columns(3)

    for i, (name, character) in enumerate(
        CHARACTERS.items()
    ):

        with columns[i % 3]:

            st.markdown(
                f"### {character['accent']} {name}"
            )

            st.caption(
                character["tag"]
            )

            st.write(
                "🎨 Bold 2D Comedy"
            )


# ============================================================
# VIDEO JOINER
# ============================================================

with tabs[3]:

    st.subheader(
        "🎞️ Turn shorts into a full episode"
    )

    files = st.file_uploader(
        "Upload MP4/MOV clips in episode order",
        type=[
            "mp4",
            "mov",
            "m4v"
        ],
        accept_multiple_files=True
    )

    if files:

        st.write(
            "### Episode order"
        )

        for i, file in enumerate(files, 1):

            st.write(
                f"{i}. {file.name}"
            )

        if st.button(
            "🔗 Join Into Long Video",
            type="primary",
            use_container_width=True
        ):

            with st.spinner(
                "Assembling full episode..."
            ):

                output, error = join_videos(
                    files
                )

            if output:

                st.session_state.joined = str(
                    output
                )

                st.success(
                    "Full episode ready!"
                )

            else:

                st.error(
                    error or
                    "Video joining failed."
                )

    if (
        st.session_state.get("joined")
        and
        Path(
            st.session_state.joined
        ).exists()
    ):

        st.video(
            st.session_state.joined
        )

        st.download_button(
            "⬇️ Download Full Episode",
            Path(
                st.session_state.joined
            ).read_bytes(),
            "full_episode.mp4",
            "video/mp4",
            use_container_width=True
        )


# ============================================================
# PROJECT
# ============================================================

with tabs[4]:

    st.subheader(
        "📁 Project"
    )

    st.json(
        {
            "name": st.session_state.project["name"],
            "style": st.session_state.project["style"],
            "location": st.session_state.project["location"],
            "cast": st.session_state.project["cast"],
            "shots": len(
                st.session_state.scenes
            )
        }
    )

    project_json = json.dumps(
        {
            "project":
                st.session_state.project,
            "scenes":
                st.session_state.scenes
        },
        indent=2
    )

    st.download_button(
        "💾 Save Project JSON",
        project_json,
        "cartoon_project_v3.json",
        "application/json",
        use_container_width=True
    )

    uploaded_project = st.file_uploader(
        "Load a saved project JSON",
        type=["json"],
        key="project_loader"
    )

    if uploaded_project:

        if st.button(
            "Load Project"
        ):

            data = json.loads(
                uploaded_project
                .read()
                .decode()
            )

            st.session_state.project = (
                data["project"]
            )

            st.session_state.scenes = (
                data["scenes"]
            )

            st.rerun()


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "🎬 Cartoon Studio V3 · "
    "Original characters · "
    "Storyboard-first workflow"
)
