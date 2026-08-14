import streamlit as st
from pathlib import Path
import tempfile
import subprocess
import shutil
import re
import math
import os
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

st.set_page_config(
    page_title="Cartoon Studio",
    page_icon="🎬",
    layout="wide"
)

WORK = Path(tempfile.gettempdir()) / "cartoon_studio"
WORK.mkdir(exist_ok=True)


# ============================================================
# CHARACTERS
# ============================================================

CHARACTERS = {
    "Alex": ("👨", "young man"),
    "Maya": ("👩", "young woman"),
    "Jay": ("👦", "teen boy"),
    "Nia": ("👧", "teen girl"),
    "Dr. James": ("🧑‍⚕️", "doctor"),
    "Pharmacist": ("💊", "pharmacist"),
    "Teacher": ("🧑‍🏫", "teacher"),
    "Mr. Cole": ("👔", "businessman"),
    "Chris": ("🎓", "student"),
    "Uncle Ben": ("👴", "elder"),
    "Officer Ray": ("👮", "police officer"),
    "DJ K": ("🎤", "performer"),
}

VOICE_OPTIONS = [
    "Warm narrator",
    "Young male",
    "Young female",
    "Deep male",
    "Bright female",
    "Calm adult",
    "Energetic",
    "Comic",
]

STYLE_OPTIONS = [
    "Classic 2D",
    "Modern 2D",
    "Anime-inspired",
    "Comic-book",
    "Urban animated comedy",
    "Kids cartoon",
    "Educational cartoon",
]


# ============================================================
# FFMPEG
# ============================================================

def ffmpeg():
    return imageio_ffmpeg.get_ffmpeg_exe()


# ============================================================
# FONTS
# ============================================================

def get_font(size=32, bold=False):

    paths = [
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ),
        (
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"
        ),
    ]

    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)

    return ImageFont.load_default()


# ============================================================
# TEXT WRAPPING
# ============================================================

def wrap_text(text, width=45):

    words = text.split()

    lines = []
    current = ""

    for word in words:

        candidate = f"{current} {word}".strip()

        if len(candidate) <= width:
            current = candidate

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

def parse_script(script):

    rows = []

    for raw in script.splitlines():

        line = raw.strip()

        if not line:
            continue

        match = re.match(
            r"^([^:]{1,40}):\s*(.+)$",
            line
        )

        if match:

            speaker = match.group(1).strip()
            dialogue = match.group(2).strip()

            rows.append(
                (speaker, dialogue)
            )

        else:

            rows.append(
                ("Narrator", line)
            )

    return rows


# ============================================================
# DRAW CARTOON FRAME
# ============================================================

def frame(
    dialogue,
    speaker,
    scene_no,
    total,
    frame_no,
    frame_total,
    character,
    style,
    size=(1280, 720)
):

    width, height = size

    img = Image.new(
        "RGB",
        size,
        (245, 247, 250)
    )

    draw = ImageDraw.Draw(img)

    # --------------------------------------------------------
    # BACKGROUND STYLE
    # --------------------------------------------------------

    if style == "Urban animated comedy":

        sky = (150, 190, 225)
        ground = (105, 115, 105)
        building = (185, 175, 160)

    elif style == "Anime-inspired":

        sky = (180, 225, 250)
        ground = (145, 210, 140)
        building = (230, 220, 210)

    else:

        sky = (178, 224, 255)
        ground = (151, 211, 128)
        building = (236, 220, 196)

    draw.rectangle(
        [0, 0, width, 475],
        fill=sky
    )

    draw.rectangle(
        [0, 475, width, height],
        fill=ground
    )

    # Sun

    draw.ellipse(
        [85, 60, 225, 200],
        fill=(255, 222, 90)
    )

    # --------------------------------------------------------
    # BUILDING
    # --------------------------------------------------------

    draw.rectangle(
        [760, 250, 1165, 475],
        fill=building,
        outline=(70, 70, 70),
        width=5
    )

    for x in (805, 925, 1045):

        draw.rectangle(
            [x, 315, x + 75, 400],
            fill=(190, 225, 245),
            outline=(65, 65, 65),
            width=3
        )

    draw.text(
        (800, 265),
        "CARTOON CITY",
        font=get_font(27, True),
        fill=(45, 45, 45)
    )

    # --------------------------------------------------------
    # CHARACTER COLORS
    # --------------------------------------------------------

    colors = {

        "Alex": (70, 130, 220),
        "Maya": (205, 95, 150),
        "Jay": (75, 160, 105),
        "Nia": (165, 100, 205),

        "Dr. James": (235, 235, 235),
        "Pharmacist": (65, 170, 150),
        "Teacher": (220, 155, 65),

        "Mr. Cole": (55, 65, 95),
        "Chris": (95, 125, 190),

        "Uncle Ben": (145, 100, 65),
        "Officer Ray": (55, 95, 155),
        "DJ K": (155, 75, 180),
    }

    shirt = colors.get(
        character,
        (78, 132, 225)
    )

    # --------------------------------------------------------
    # CHARACTER ANIMATION
    # --------------------------------------------------------

    bob = int(
        8 *
        math.sin(
            frame_no /
            max(frame_total, 1) *
            math.pi *
            4
        )
    )

    walk = int(
        10 *
        math.sin(
            frame_no /
            max(frame_total, 1) *
            math.pi *
            2
        )
    )

    cx = 430 + walk
    cy = 380 + bob

    # Shadow

    draw.ellipse(
        [cx - 90, 535, cx + 90, 570],
        fill=(80, 100, 80)
    )

    # Legs

    draw.line(
        [cx - 28, cy + 135, cx - 42, 535],
        fill=(45, 45, 55),
        width=18
    )

    draw.line(
        [cx + 28, cy + 135, cx + 48, 535],
        fill=(45, 45, 55),
        width=18
    )

    # Body

    draw.rounded_rectangle(
        [
            cx - 75,
            cy + 10,
            cx + 75,
            cy + 155
        ],
        radius=35,
        fill=shirt,
        outline=(40, 55, 80),
        width=5
    )

    # Head

    draw.ellipse(
        [
            cx - 78,
            cy - 105,
            cx + 78,
            cy + 50
        ],
        fill=(244, 194, 145),
        outline=(90, 65, 45),
        width=5
    )

    # Hair

    if character in ("Maya", "Nia"):

        draw.ellipse(
            [
                cx - 88,
                cy - 125,
                cx + 88,
                cy + 25
            ],
            outline=(45, 30, 25),
            width=25
        )

    elif character in ("Uncle Ben", "Dr. James"):

        draw.arc(
            [
                cx - 80,
                cy - 120,
                cx + 80,
                cy + 15
            ],
            180,
            355,
            fill=(150, 150, 150),
            width=16
        )

    else:

        draw.arc(
            [
                cx - 80,
                cy - 120,
                cx + 80,
                cy + 15
            ],
            180,
            355,
            fill=(55, 40, 30),
            width=22
        )

    # Eyes

    draw.ellipse(
        [cx - 38, cy - 45, cx - 20, cy - 27],
        fill=(25, 25, 25)
    )

    draw.ellipse(
        [cx + 20, cy - 45, cx + 38, cy - 27],
        fill=(25, 25, 25)
    )

    # --------------------------------------------------------
    # MOUTH ANIMATION
    # --------------------------------------------------------

    mouth_height = (
        8 +
        int(
            9 *
            abs(
                math.sin(frame_no / 3)
            )
        )
    )

    draw.arc(
        [
            cx - 22,
            cy - 10,
            cx + 22,
            cy + mouth_height + 8
        ],
        0,
        180,
        fill=(100, 35, 35),
        width=5
    )

    # --------------------------------------------------------
    # SPEECH BUBBLE
    # --------------------------------------------------------

    bx = 60
    by = 215
    bw = 590
    bh = 235

    draw.rounded_rectangle(
        [
            bx,
            by,
            bx + bw,
            by + bh
        ],
        radius=28,
        fill="white",
        outline=(55, 55, 55),
        width=4
    )

    draw.polygon(
        [
            (bx + 470, by + bh),
            (bx + 510, by + bh + 48),
            (bx + 420, by + bh - 8)
        ],
        fill="white",
        outline=(55, 55, 55)
    )

    draw.text(
        (bx + 25, by + 18),
        speaker,
        font=get_font(28, True),
        fill=(35, 35, 35)
    )

    y = by + 58

    for line in wrap_text(dialogue, 42)[:4]:

        draw.text(
            (bx + 25, y),
            line,
            font=get_font(28),
            fill=(35, 35, 35)
        )

        y += 35

    # Scene number

    draw.rounded_rectangle(
        [35, 25, 310, 75],
        radius=18,
        fill="white",
        outline=(70, 70, 70),
        width=3
    )

    draw.text(
        (55, 36),
        f"Scene {scene_no}/{total}",
        font=get_font(25, True),
        fill=(40, 40, 40)
    )

    return img


# ============================================================
# ERROR HANDLING
# ============================================================

def show_ffmpeg_error(result):

    text = (
        result.stderr
        or result.stdout
        or "Unknown FFmpeg error"
    ).strip()

    tail = "\n".join(
        text.splitlines()[-18:]
    )

    st.error(
        "Video generation failed. FFmpeg returned an error."
    )

    st.code(
        tail,
        language="text"
    )


# ============================================================
# CREATE VIDEO
# ============================================================

def make_video(
    rows,
    selected,
    style,
    seconds=3,
    fps=8
):

    output = (
        WORK /
        f"cartoon_{os.getpid()}.mp4"
    )

    frames_folder = (
        WORK /
        f"frames_{os.getpid()}"
    )

    frames_folder.mkdir(
        exist_ok=True
    )

    index = 0

    chosen_map = {
        x.lower(): x
        for x in selected
    }

    try:

        for scene_no, (
            speaker,
            dialogue
        ) in enumerate(rows, 1):

            character = chosen_map.get(
                speaker.lower(),
                selected[0]
                if selected
                else "Alex"
            )

            duration = max(
                seconds,
                min(
                    8,
                    1.5 +
                    len(dialogue) / 16
                )
            )

            total_frames = max(
                1,
                int(duration * fps)
            )

            for f in range(total_frames):

                image = frame(
                    dialogue,
                    speaker,
                    scene_no,
                    len(rows),
                    f,
                    total_frames,
                    character,
                    style
                )

                image.save(
                    frames_folder /
                    f"frame_{index:06d}.png"
                )

                index += 1

        result = subprocess.run(
            [
                ffmpeg(),
                "-y",
                "-framerate",
                str(fps),
                "-i",
                str(
                    frames_folder /
                    "frame_%06d.png"
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

        if result.returncode != 0:

            show_ffmpeg_error(
                result
            )

            return None

        return output

    finally:

        shutil.rmtree(
            frames_folder,
            ignore_errors=True
        )


# ============================================================
# JOIN VIDEOS
# ============================================================

def join_videos(uploaded):

    work = (
        WORK /
        f"join_{os.getpid()}"
    )

    work.mkdir(
        exist_ok=True
    )

    normalized = []

    try:

        for i, item in enumerate(uploaded):

            source = work / f"source_{i}"

            source.write_bytes(
                item.getvalue()
            )

            target = work / f"clip_{i}.mp4"

            result = subprocess.run(
                [
                    ffmpeg(),
                    "-y",
                    "-i",
                    str(source),

                    "-vf",
                    "scale=1280:720:"
                    "force_original_aspect_ratio=decrease,"
                    "pad=1280:720:"
                    "(ow-iw)/2:(oh-ih)/2,"
                    "format=yuv420p",

                    "-r",
                    "30",

                    "-c:v",
                    "libx264",

                    "-preset",
                    "veryfast",

                    "-c:a",
                    "aac",

                    "-ar",
                    "48000",

                    "-ac",
                    "2",

                    str(target)
                ],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:

                show_ffmpeg_error(
                    result
                )

                return None

            normalized.append(
                target
            )

        manifest = (
            work /
            "concat.txt"
        )

        manifest.write_text(
            "\n".join(
                f"file '{p.as_posix()}'"
                for p in normalized
            )
        )

        output = (
            WORK /
            f"joined_{os.getpid()}.mp4"
        )

        result = subprocess.run(
            [
                ffmpeg(),
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

        if result.returncode != 0:

            show_ffmpeg_error(
                result
            )

            return None

        return output

    finally:

        shutil.rmtree(
            work,
            ignore_errors=True
        )


# ============================================================
# PAGE DESIGN
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        max-width: 1180px;
        padding-top: 2rem;
    }

    .big-title {
        font-size: 3rem;
        font-weight: 800;
    }

    .subtitle {
        font-size: 1.15rem;
        opacity: 0.75;
        margin-bottom: 1.5rem;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="big-title">🎬 Cartoon Studio</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Create original animated 2D cartoons or join short clips into one long video.'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# TABS
# ============================================================

create_tab, join_tab, help_tab = st.tabs(
    [
        "✨ Create Cartoon",
        "🎞️ Join Videos",
        "ℹ️ Help"
    ]
)


# ============================================================
# CREATE CARTOON
# ============================================================

with create_tab:

    st.subheader(
        "1. Choose characters"
    )

    selected = st.multiselect(
        "Characters",
        list(CHARACTERS.keys()),
        default=[
            "Alex",
            "Maya"
        ]
    )

    if not selected:

        selected = [
            "Alex"
        ]

    columns = st.columns(4)

    for i, name in enumerate(
        selected[:12]
    ):

        emoji, role = CHARACTERS[name]

        with columns[i % 4]:

            st.markdown(
                f"**{emoji} {name}**  \n"
                f"{role}"
            )

    # --------------------------------------------------------
    # STYLE
    # --------------------------------------------------------

    st.subheader(
        "2. Cartoon style"
    )

    style = st.selectbox(
        "Style",
        STYLE_OPTIONS
    )

    if style == "Urban animated comedy":

        st.info(
            "Original urban-comedy presentation "
            "with bold outlines, expressive faces "
            "and city settings. It does not copy "
            "characters or artwork from existing shows."
        )

    # --------------------------------------------------------
    # VOICES
    # --------------------------------------------------------

    st.subheader(
        "3. Voice choices"
    )

    for name in selected:

        st.selectbox(
            f"Voice for {name}",
            VOICE_OPTIONS,
            key=f"voice_{name}"
        )

    st.caption(
        "Voice controls are ready for the TTS backend. "
        "Actual spoken audio will be added when a "
        "TTS provider/API is connected."
    )

    # --------------------------------------------------------
    # SCRIPT
    # --------------------------------------------------------

    st.subheader(
        "4. Write your script"
    )

    st.markdown(
        "Use **Character: dialogue** on each line."
    )

    script = st.text_area(
        "Script",
        height=230,
        placeholder=(
            "Alex: Good morning! How can I help you?\n"
            "Maya: I'm looking for some medicine.\n"
            "Alex: Sure, let me check."
        ),
        label_visibility="collapsed"
    )

    # --------------------------------------------------------
    # GENERATE
    # --------------------------------------------------------

    if st.button(
        "✨ Generate Cartoon",
        type="primary",
        use_container_width=True
    ):

        if not script.strip():

            st.warning(
                "Write a script first."
            )

        else:

            rows = parse_script(
                script
            )

            st.session_state.rows = rows

            with st.spinner(
                "Animating your cartoon..."
            ):

                video = make_video(
                    rows,
                    selected,
                    style
                )

                if video:

                    st.session_state.video = str(
                        video
                    )

                    st.success(
                        "Your animated cartoon is ready!"
                    )

    # --------------------------------------------------------
    # STORYBOARD
    # --------------------------------------------------------

    if st.session_state.get(
        "rows"
    ):

        st.subheader(
            "Storyboard"
        )

        for i, (
            speaker,
            line
        ) in enumerate(
            st.session_state.rows,
            1
        ):

            st.write(
                f"**Scene {i} — {speaker}:** "
                f"{line}"
            )

    # --------------------------------------------------------
    # VIDEO
    # --------------------------------------------------------

    if st.session_state.get(
        "video"
    ):

        video_path = Path(
            st.session_state.video
        )

        if video_path.exists():

            st.video(
                str(video_path)
            )

            st.download_button(
                "⬇️ Download Cartoon",
                video_path.read_bytes(),
                "my_cartoon.mp4",
                "video/mp4",
                use_container_width=True
            )


# ============================================================
# JOIN VIDEOS
# ============================================================

with join_tab:

    st.subheader(
        "🎞️ Join short videos"
    )

    uploads = st.file_uploader(
        "Upload your clips",
        type=[
            "mp4",
            "mov",
            "m4v",
            "webm"
        ],
        accept_multiple_files=True
    )

    if uploads:

        for i, item in enumerate(
            uploads,
            1
        ):

            st.write(
                f"**{i}.** {item.name}"
            )

        if st.button(
            "🎬 Create Long Video",
            type="primary",
            use_container_width=True
        ):

            with st.spinner(
                "Joining clips..."
            ):

                result = join_videos(
                    uploads
                )

                if result:

                    st.session_state.long = str(
                        result
                    )

                    st.success(
                        "Long video created!"
                    )

    if st.session_state.get(
        "long"
    ):

        video_path = Path(
            st.session_state.long
        )

        if video_path.exists():

            st.video(
                str(video_path)
            )

            st.download_button(
                "⬇️ Download Long Video",
                video_path.read_bytes(),
                "joined_cartoon.mp4",
                "video/mp4",
                use_container_width=True
            )


# ============================================================
# HELP
# ============================================================

with help_tab:

    st.subheader(
        "Simple workflow"
    )

    st.markdown(
        """
1. Choose characters.
2. Choose a style.
3. Choose voice profiles.
4. Write `Character: dialogue`.
5. Generate and preview.
6. Join episodes with **Join Videos**.

This version uses an original 2D renderer.
The voice UI is prepared for the next TTS integration.
"""
    )


st.caption(
    "Cartoon Studio V1.2.1 • Streamlit Cloud reliability update"
) 
