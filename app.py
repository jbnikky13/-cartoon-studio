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

# ============================================================
# CARTOON STUDIO V2.0
# Animated original 2D character video creator
# ============================================================

st.set_page_config(
    page_title="Cartoon Studio V2",
    page_icon="🎬",
    layout="wide"
)

WORK = Path(tempfile.gettempdir()) / "cartoon_studio_v2"
WORK.mkdir(exist_ok=True)

# ------------------------------------------------------------
# ORIGINAL CHARACTER LIBRARY
# ------------------------------------------------------------

CHARACTERS = {
    "Alex": {
        "role": "young man",
        "skin": (176, 116, 82),
        "hair": (38, 28, 25),
        "shirt": (60, 120, 215),
        "pants": (45, 55, 75)
    },
    "Maya": {
        "role": "young woman",
        "skin": (120, 78, 58),
        "hair": (35, 22, 20),
        "shirt": (205, 85, 145),
        "pants": (55, 60, 75)
    },
    "Jay": {
        "role": "teen boy",
        "skin": (150, 92, 62),
        "hair": (25, 22, 20),
        "shirt": (55, 160, 105),
        "pants": (50, 70, 100)
    },
    "Nia": {
        "role": "teen girl",
        "skin": (145, 92, 68),
        "hair": (30, 22, 20),
        "shirt": (150, 95, 205),
        "pants": (60, 55, 80)
    },
    "Dr. James": {
        "role": "doctor",
        "skin": (125, 82, 62),
        "hair": (80, 65, 55),
        "shirt": (238, 238, 238),
        "pants": (65, 75, 90)
    },
    "Pharmacist": {
        "role": "pharmacist",
        "skin": (105, 70, 54),
        "hair": (35, 28, 25),
        "shirt": (65, 175, 155),
        "pants": (45, 60, 70)
    },
    "Teacher": {
        "role": "teacher",
        "skin": (180, 120, 88),
        "hair": (90, 65, 45),
        "shirt": (220, 150, 65),
        "pants": (60, 70, 80)
    },
    "Mr. Cole": {
        "role": "businessman",
        "skin": (125, 82, 60),
        "hair": (35, 28, 25),
        "shirt": (50, 58, 88),
        "pants": (42, 48, 65)
    },
    "Chris": {
        "role": "student",
        "skin": (170, 110, 80),
        "hair": (40, 28, 25),
        "shirt": (90, 125, 195),
        "pants": (55, 65, 85)
    },
    "Uncle Ben": {
        "role": "elder",
        "skin": (125, 82, 62),
        "hair": (145, 145, 145),
        "shirt": (145, 100, 70),
        "pants": (55, 60, 70)
    },
    "Officer Ray": {
        "role": "police officer",
        "skin": (145, 92, 65),
        "hair": (35, 28, 25),
        "shirt": (55, 90, 155),
        "pants": (45, 55, 80)
    },
    "DJ K": {
        "role": "performer",
        "skin": (105, 68, 54),
        "hair": (25, 20, 20),
        "shirt": (150, 70, 180),
        "pants": (45, 45, 65)
    }
}

EXPRESSIONS = [
    "Neutral",
    "Happy",
    "Surprised",
    "Thinking",
    "Angry",
    "Laughing"
]

SCENES = {
    "Living Room": "home",
    "Classroom": "school",
    "Pharmacy": "pharmacy",
    "Hospital": "hospital",
    "Office": "office",
    "City Street": "street",
    "Restaurant": "restaurant",
    "Park": "park"
}

VOICE_OPTIONS = [
    "Warm adult",
    "Young male",
    "Young female",
    "Deep adult",
    "Bright adult",
    "Energetic",
    "Calm",
    "Comic"
]

# ------------------------------------------------------------
# UTILITIES
# ------------------------------------------------------------

def ffmpeg():
    return imageio_ffmpeg.get_ffmpeg_exe()


def font(size=32, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",

        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"
    ]

    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)

    return ImageFont.load_default()


def wrap(text, chars=43):
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = f"{current} {word}".strip()

        if len(test) <= chars:
            current = test
        else:
            if current:
                lines.append(current)

            current = word

    if current:
        lines.append(current)

    return lines


def parse_script(script):
    rows = []

    for raw in script.splitlines():

        line = raw.strip()

        if not line:
            continue

        m = re.match(
            r"^([^:]{1,40}):\s*(.+)$",
            line
        )

        if m:
            rows.append(
                (
                    m.group(1).strip(),
                    m.group(2).strip()
                )
            )
        else:
            rows.append(
                ("Narrator", line)
            )

    return rows


# ------------------------------------------------------------
# BACKGROUNDS
# ------------------------------------------------------------

def draw_background(d, scene, w, h):

    sky = (185, 220, 245)
    floor = (150, 145, 125)

    d.rectangle(
        [0, 0, w, int(h * .67)],
        fill=sky
    )

    d.rectangle(
        [0, int(h * .67), w, h],
        fill=floor
    )

    if scene == "home":

        d.rectangle(
            [90, 115, 1190, 500],
            fill=(235, 220, 195),
            outline=(80, 70, 65),
            width=5
        )

        d.rectangle(
            [150, 200, 480, 390],
            fill=(125, 95, 75),
            outline=(70, 60, 55),
            width=5
        )

        d.rectangle(
            [210, 235, 420, 345],
            fill=(80, 160, 205),
            outline=(60, 60, 60),
            width=4
        )

        d.rectangle(
            [720, 325, 1040, 465],
            fill=(115, 80, 60),
            outline=(70, 55, 45),
            width=5
        )

        d.text(
            (500, 135),
            "LIVING ROOM",
            font=font(34, True),
            fill=(55, 50, 45)
        )

    elif scene == "school":

        d.rectangle(
            [80, 90, 1200, 505],
            fill=(235, 225, 190),
            outline=(70, 65, 55),
            width=5
        )

        d.rectangle(
            [280, 150, 1000, 315],
            fill=(45, 80, 60),
            outline=(40, 45, 40),
            width=5
        )

        d.text(
            (330, 195),
            "TODAY'S LESSON",
            font=font(42, True),
            fill=(245, 245, 235)
        )

        for x in [150, 470, 790]:

            d.rectangle(
                [x, 380, x + 210, 470],
                fill=(125, 90, 65),
                outline=(70, 55, 45),
                width=4
            )

        d.text(
            (510, 105),
            "CLASSROOM",
            font=font(34, True),
            fill=(55, 50, 45)
        )

    elif scene == "pharmacy":

        d.rectangle(
            [70, 95, 1210, 505],
            fill=(220, 238, 230),
            outline=(55, 80, 70),
            width=5
        )

        d.rectangle(
            [100, 125, 1180, 210],
            fill=(65, 160, 140)
        )

        d.text(
            (410, 145),
            "COMMUNITY PHARMACY",
            font=font(38, True),
            fill="white"
        )

        for x in [140, 440, 740]:

            d.rectangle(
                [x, 260, x + 210, 450],
                fill=(245, 245, 240),
                outline=(75, 85, 80),
                width=4
            )

            for yy in [290, 335, 380]:

                d.rectangle(
                    [x + 25, yy, x + 180, yy + 28],
                    fill=(180, 210, 205),
                    outline=(80, 100, 95),
                    width=2
                )

    elif scene == "hospital":

        d.rectangle(
            [80, 90, 1200, 510],
            fill=(235, 240, 245),
            outline=(70, 80, 90),
            width=5
        )

        d.rectangle(
            [500, 145, 780, 300],
            fill=(65, 110, 170),
            outline=(50, 70, 95),
            width=5
        )

        d.rectangle(
            [610, 175, 670, 270],
            fill="white"
        )

        d.rectangle(
            [570, 210, 710, 235],
            fill="white"
        )

        d.text(
            (475, 110),
            "HOSPITAL",
            font=font(38, True),
            fill=(50, 60, 70)
        )

    elif scene == "office":

        d.rectangle(
            [70, 90, 1210, 500],
            fill=(215, 215, 220),
            outline=(70, 70, 75),
            width=5
        )

        d.rectangle(
            [150, 160, 470, 420],
            fill=(130, 145, 155),
            outline=(65, 70, 75),
            width=5
        )

        d.rectangle(
            [700, 330, 1080, 460],
            fill=(100, 75, 55),
            outline=(60, 50, 45),
            width=5
        )

        d.text(
            (500, 120),
            "OFFICE",
            font=font(38, True),
            fill=(50, 50, 55)
        )

    elif scene == "street":

        d.rectangle(
            [0, 430, w, h],
            fill=(95, 95, 100)
        )

        d.rectangle(
            [0, 500, w, 540],
            fill=(245, 225, 100)
        )

        for x in range(0, w, 180):

            d.rectangle(
                [x, 200, x + 120, 430],
                fill=(180, 165, 150),
                outline=(80, 75, 70),
                width=4
            )

            d.rectangle(
                [x + 25, 240, x + 55, 290],
                fill=(120, 180, 210)
            )

            d.rectangle(
                [x + 70, 240, x + 100, 290],
                fill=(120, 180, 210)
            )

        d.text(
            (535, 105),
            "CITY STREET",
            font=font(38, True),
            fill=(50, 50, 55)
        )

    elif scene == "restaurant":

        d.rectangle(
            [70, 95, 1210, 500],
            fill=(245, 215, 190),
            outline=(80, 65, 60),
            width=5
        )

        for x in [180, 520, 860]:

            d.ellipse(
                [x, 300, x + 210, 430],
                fill=(150, 80, 65),
                outline=(80, 55, 50),
                width=5
            )

            d.line(
                [x + 30, 430, x + 20, 500],
                fill=(60, 55, 50),
                width=8
            )

            d.line(
                [x + 180, 430, x + 190, 500],
                fill=(60, 55, 50),
                width=8
            )

        d.text(
            (500, 125),
            "RESTAURANT",
            font=font(38, True),
            fill=(60, 45, 40)
        )

    elif scene == "park":

        d.rectangle(
            [0, 0, w, 500],
            fill=(165, 220, 245)
        )

        d.rectangle(
            [0, 440, w, h],
            fill=(115, 175, 100)
        )

        for x, y in [
            (120, 220),
            (1030, 185),
            (760, 240)
        ]:

            d.rectangle(
                [x + 35, y + 120, x + 65, 440],
                fill=(105, 70, 45)
            )

            d.ellipse(
                [x - 40, y, x + 140, y + 160],
                fill=(70, 145, 75),
                outline=(55, 105, 60),
                width=4
            )

        d.text(
            (550, 105),
            "PARK",
            font=font(38, True),
            fill=(50, 70, 50)
        )


# ------------------------------------------------------------
# CHARACTER DRAWING
# ------------------------------------------------------------

def draw_character(
    d,
    name,
    x,
    ground_y,
    scale,
    expression,
    talking,
    frame_no
):

    c = CHARACTERS[name]

    s = scale

    bob = int(
        5 * math.sin(frame_no / 4.0)
    )

    sway = int(
        3 * math.sin(frame_no / 7.0)
    )

    x += sway
    ground_y += bob

    head_r = int(58 * s)

    body_w = int(92 * s)
    body_h = int(135 * s)

    # Shadow
    d.ellipse(
        [
            x - int(80 * s),
            ground_y - 5,
            x + int(80 * s),
            ground_y + int(15 * s)
        ],
        fill=(70, 80, 75)
    )

    # Legs
    leg_y = ground_y - int(110 * s)

    d.line(
        [
            x - int(22 * s),
            leg_y + int(70 * s),
            x - int(38 * s),
            ground_y
        ],
        fill=(45, 45, 50),
        width=max(5, int(13 * s))
    )

    d.line(
        [
            x + int(22 * s),
            leg_y + int(70 * s),
            x + int(38 * s),
            ground_y
        ],
        fill=(45, 45, 50),
        width=max(5, int(13 * s))
    )

    # Body
    body_top = ground_y - int(235 * s)

    d.rounded_rectangle(
        [
            x - int(body_w * s / 2),
            body_top,
            x + int(body_w * s / 2),
            ground_y - int(80 * s)
        ],
        radius=int(25 * s),
        fill=c["shirt"],
        outline=(45, 50, 60),
        width=max(2, int(4 * s))
    )

    # Arms
    arm_y = body_top + int(48 * s)

    if expression in ["Happy", "Laughing"]:

        left_end = (
            x - int(80 * s),
            arm_y - int(25 * s)
        )

        right_end = (
            x + int(80 * s),
            arm_y - int(25 * s)
        )

    elif expression == "Surprised":

        left_end = (
            x - int(78 * s),
            arm_y + int(20 * s)
        )

        right_end = (
            x + int(78 * s),
            arm_y + int(20 * s)
        )

    elif expression == "Thinking":

        left_end = (
            x - int(72 * s),
            arm_y + int(45 * s)
        )

        right_end = (
            x + int(25 * s),
            body_top + int(5 * s)
        )

    else:

        left_end = (
            x - int(70 * s),
            arm_y + int(45 * s)
        )

        right_end = (
            x + int(70 * s),
            arm_y + int(45 * s)
        )

    d.line(
        [
            x - int(body_w * s / 2),
            arm_y,
            left_end[0],
            left_end[1]
        ],
        fill=c["shirt"],
        width=max(8, int(22 * s))
    )

    d.line(
        [
            x + int(body_w * s / 2),
            arm_y,
            right_end[0],
            right_end[1]
        ],
        fill=c["shirt"],
        width=max(8, int(22 * s))
    )

    # Head
    head_y = body_top - int(58 * s)

    d.ellipse(
        [
            x - head_r,
            head_y - head_r,
            x + head_r,
            head_y + head_r
        ],
        fill=c["skin"],
        outline=(55, 45, 40),
        width=max(2, int(4 * s))
    )

    # Hair
    hair_box = [
        x - head_r - int(4 * s),
        head_y - head_r - int(8 * s),
        x + head_r + int(4 * s),
        head_y + int(15 * s)
    ]

    d.arc(
        hair_box,
        180,
        360,
        fill=c["hair"],
        width=max(8, int(16 * s))
    )

    # Ears
    d.ellipse(
        [
            x - head_r - int(9 * s),
            head_y - int(12 * s),
            x - head_r + int(10 * s),
            head_y + int(12 * s)
        ],
        fill=c["skin"]
    )

    d.ellipse(
        [
            x + head_r - int(10 * s),
            head_y - int(12 * s),
            x + head_r + int(9 * s),
            head_y + int(12 * s)
        ],
        fill=c["skin"]
    )

    # Eyes
    eye_y = head_y - int(12 * s)
    eye_dx = int(22 * s)

    eye_h = 9
    eye_w = 12

    if expression == "Surprised":

        eye_h = 15
        eye_w = 15

    elif expression == "Angry":

        eye_h = 6

    d.ellipse(
        [
            x - eye_dx - eye_w,
            eye_y - eye_h,
            x - eye_dx + eye_w,
            eye_y + eye_h
        ],
        fill=(25, 25, 25)
    )

    d.ellipse(
        [
            x + eye_dx - eye_w,
            eye_y - eye_h,
            x + eye_dx + eye_w,
            eye_y + eye_h
        ],
        fill=(25, 25, 25)
    )

    # Eyebrows
    brow_y = eye_y - int(15 * s)

    if expression == "Angry":

        d.line(
            [
                x - eye_dx - int(15 * s),
                brow_y - int(5 * s),
                x - eye_dx + int(8 * s),
                brow_y + int(7 * s)
            ],
            fill=(40, 30, 25),
            width=max(3, int(5 * s))
        )

        d.line(
            [
                x + eye_dx - int(8 * s),
                brow_y + int(7 * s),
                x + eye_dx + int(15 * s),
                brow_y - int(5 * s)
            ],
            fill=(40, 30, 25),
            width=max(3, int(5 * s))
        )

    elif expression == "Surprised":

        d.arc(
            [
                x - eye_dx - int(12 * s),
                brow_y - int(12 * s),
                x - eye_dx + int(12 * s),
                brow_y + int(12 * s)
            ],
            180,
            360,
            fill=(40, 30, 25),
            width=max(2, int(4 * s))
        )

        d.arc(
            [
                x + eye_dx - int(12 * s),
                brow_y - int(12 * s),
                x + eye_dx + int(12 * s),
                brow_y + int(12 * s)
            ],
            180,
            360,
            fill=(40, 30, 25),
            width=max(2, int(4 * s))
        )

    # Nose
    d.line(
        [
            x,
            head_y,
            x - int(7 * s),
            head_y + int(18 * s),
            x + int(5 * s),
            head_y + int(20 * s)
        ],
        fill=(105, 65, 50),
        width=max(2, int(3 * s))
    )

    # Mouth / lip sync
    mouth_y = head_y + int(34 * s)

    if expression in ["Happy", "Laughing"]:

        if talking:

            d.ellipse(
                [
                    x - int(25 * s),
                    mouth_y - int(5 * s),
                    x + int(25 * s),
                    mouth_y + int(25 * s)
                ],
                fill=(90, 30, 35)
            )

        else:

            d.arc(
                [
                    x - int(28 * s),
                    mouth_y - int(15 * s),
                    x + int(28 * s),
                    mouth_y + int(22 * s)
                ],
                0,
                180,
                fill=(80, 25, 30),
                width=max(2, int(5 * s))
            )

    elif expression == "Surprised":

        d.ellipse(
            [
                x - int(16 * s),
                mouth_y - int(3 * s),
                x + int(16 * s),
                mouth_y + int(28 * s)
            ],
            fill=(80, 25, 30)
        )

    elif expression == "Thinking":

        d.arc(
            [
                x - int(22 * s),
                mouth_y,
                x + int(22 * s),
                mouth_y + int(22 * s)
            ],
            180,
            360,
            fill=(80, 35, 35),
            width=max(2, int(4 * s))
        )

    elif talking:

        mouth_open = int(
            (
                12 +
                10 *
                abs(
                    math.sin(
                        frame_no / 2.2
                    )
                )
            ) * s
        )

        d.ellipse(
            [
                x - int(23 * s),
                mouth_y - int(2 * s),
                x + int(23 * s),
                mouth_y + mouth_open
            ],
            fill=(85, 25, 30)
        )

    else:

        d.line(
            [
                x - int(18 * s),
                mouth_y + int(8 * s),
                x + int(18 * s),
                mouth_y + int(8 * s)
            ],
            fill=(80, 35, 35),
            width=max(2, int(4 * s))
        )

    # Name tag
    tag_y = ground_y + int(20 * s)

    label = name

    box = d.textbbox(
        (0, 0),
        label,
        font=font(20, True)
    )

    tw = box[2] - box[0]

    d.rounded_rectangle(
        [
            x - tw // 2 - 10,
            tag_y,
            x + tw // 2 + 10,
            tag_y + 32
        ],
        radius=10,
        fill=(255, 255, 255),
        outline=(70, 70, 70),
        width=2
    )

    d.text(
        (x - tw // 2, tag_y + 5),
        label,
        font=font(20, True),
        fill=(35, 35, 35)
    )


# ------------------------------------------------------------
# FRAME RENDERING
# ------------------------------------------------------------

def render_scene(
    dialogue,
    speaker,
    scene,
    left_character,
    right_character,
    left_expression,
    right_expression,
    frame_no,
    total_frames,
    size=(1280, 720)
):

    w, h = size

    img = Image.new(
        "RGB",
        size,
        (240, 240, 240)
    )

    d = ImageDraw.Draw(img)

    draw_background(
        d,
        scene,
        w,
        h
    )

    talking = frame_no % 6 in [0, 1, 2, 4]

    left_x = 330
    right_x = 900
    ground = 650

    camera = int(
        4 * math.sin(frame_no / 15)
    )

    draw_character(
        d,
        left_character,
        left_x + camera,
        ground,
        1.0,
        (
            "Happy"
            if speaker == left_character
            and left_expression == "Neutral"
            else left_expression
        ),
        speaker == left_character and talking,
        frame_no
    )

    if right_character:

        draw_character(
            d,
            right_character,
            right_x + camera,
            ground,
            1.0,
            (
                "Happy"
                if speaker == right_character
                and right_expression == "Neutral"
                else right_expression
            ),
            speaker == right_character and talking,
            frame_no
        )

    # Dialogue panel
    panel_x = 55
    panel_y = 35
    panel_w = 1170
    panel_h = 145

    d.rounded_rectangle(
        [
            panel_x,
            panel_y,
            panel_x + panel_w,
            panel_y + panel_h
        ],
        radius=25,
        fill=(255, 255, 255),
        outline=(50, 50, 55),
        width=4
    )

    d.text(
        (panel_x + 25, panel_y + 18),
        speaker,
        font=font(30, True),
        fill=(40, 40, 45)
    )

    lines = wrap(
        dialogue,
        75
    )[:3]

    yy = panel_y + 62

    for line in lines:

        d.text(
            (panel_x + 25, yy),
            line,
            font=font(28),
            fill=(40, 40, 45)
        )

        yy += 34

    # Scene label
    d.rounded_rectangle(
        [40, 675, 270, 710],
        radius=12,
        fill=(255, 255, 255),
        outline=(70, 70, 70),
        width=2
    )

    d.text(
        (55, 682),
        scene,
        font=font(20, True),
        fill=(45, 45, 45)
    )

    return img


# ------------------------------------------------------------
# VIDEO GENERATION
# ------------------------------------------------------------

def make_video(rows, settings):

    out = WORK / f"cartoon_v2_{os.getpid()}.mp4"

    frames_dir = WORK / f"frames_v2_{os.getpid()}"

    frames_dir.mkdir(
        exist_ok=True
    )

    fps = 12
    index = 0

    try:

        for scene_index, row in enumerate(rows):

            speaker, dialogue = row

            selected = settings["characters"]

            known = {
                n.lower(): n
                for n in selected
            }

            if speaker.lower() in known:

                actual_speaker = known[
                    speaker.lower()
                ]

            else:

                actual_speaker = selected[0]

            others = [
                n
                for n in selected
                if n != actual_speaker
            ]

            second = (
                others[0]
                if others
                else None
            )

            scene = settings["scene"]

            speaker_expression = (
                settings["expressions"].get(
                    actual_speaker,
                    "Happy"
                )
            )

            second_expression = (
                settings["expressions"].get(
                    second,
                    "Neutral"
                )
                if second
                else "Neutral"
            )

            duration = max(
                2.5,
                min(
                    10,
                    1.8 + len(dialogue) / 18
                )
            )

            frame_count = int(
                duration * fps
            )

            for f in range(frame_count):

                image = render_scene(
                    dialogue,
                    actual_speaker,
                    scene,
                    actual_speaker,
                    second,
                    speaker_expression,
                    second_expression,
                    f,
                    frame_count
                )

                image.save(
                    frames_dir /
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
                    frames_dir /
                    "frame_%06d.png"
                ),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(out)
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:

            return None, result.stderr[-4000:]

        return out, None

    finally:

        shutil.rmtree(
            frames_dir,
            ignore_errors=True
        )


# ------------------------------------------------------------
# JOIN VIDEOS
# ------------------------------------------------------------

def join_videos(files):

    work = WORK / f"join_{os.getpid()}"

    work.mkdir(
        exist_ok=True
    )

    try:

        clips = []

        for i, file in enumerate(files):

            source = work / f"source_{i}"
            target = work / f"clip_{i}.mp4"

            source.write_bytes(
                file.getvalue()
            )

            result = subprocess.run(
                [
                    ffmpeg(),
                    "-y",
                    "-i",
                    str(source),
                    "-vf",
                    (
                        "scale=1280:720:"
                        "force_original_aspect_ratio=decrease,"
                        "pad=1280:720:(ow-iw)/2:"
                        "(oh-ih)/2,"
                        "format=yuv420p"
                    ),
                    "-r",
                    "30",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-c:a",
                    "aac",
                    str(target)
                ],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:

                return None, result.stderr[-4000:]

            clips.append(target)

        manifest = work / "concat.txt"

        manifest.write_text(
            "\n".join(
                f"file '{p.as_posix()}'"
                for p in clips
            )
        )

        output = WORK / (
            f"joined_v2_{os.getpid()}.mp4"
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

            return None, result.stderr[-4000:]

        return output, None

    finally:

        shutil.rmtree(
            work,
            ignore_errors=True
        )


# ============================================================
# UI
# ============================================================

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1200px;
        padding-top: 1.5rem;
    }

    .title {
        font-size: 3rem;
        font-weight: 800;
    }

    .subtitle {
        font-size: 1.15rem;
        opacity: .72;
        margin-bottom: 1.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    '<div class="title">🎬 Cartoon Studio V2</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Create animated 2D cartoon scenes from simple dialogue.'
    '</div>',
    unsafe_allow_html=True
)

create_tab, join_tab, help_tab = st.tabs(
    [
        "✨ Create Cartoon",
        "🎞️ Join Videos",
        "ℹ️ How It Works"
    ]
)

# ============================================================
# CREATE CARTOON
# ============================================================

with create_tab:

    st.header(
        "Build your cartoon"
    )

    col1, col2 = st.columns(
        [1, 1]
    )

    with col1:

        st.subheader(
            "Characters"
        )

        selected = st.multiselect(
            "Choose characters",
            list(CHARACTERS.keys()),
            default=[
                "Alex",
                "Maya",
                "Jay"
            ]
        )

        if not selected:

            selected = ["Alex"]

        st.write(
            "Selected characters:"
        )

        for name in selected:

            st.write(
                f"• **{name}** — "
                f"{CHARACTERS[name]['role']}"
            )

    with col2:

        st.subheader(
            "Scene"
        )

        scene = st.selectbox(
            "Choose the main location",
            list(SCENES.keys())
        )

        st.subheader(
            "Character expressions"
        )

        expressions = {}

        for name in selected:

            expressions[name] = st.selectbox(
                f"{name}",
                EXPRESSIONS,
                index=1,
                key=f"expression_{name}"
            )

    st.divider()

    st.subheader(
        "Character voices"
    )

    voice_map = {}

    voice_columns = st.columns(
        min(3, max(1, len(selected)))
    )

    for i, name in enumerate(selected):

        with voice_columns[
            i % len(voice_columns)
        ]:

            voice_map[name] = st.selectbox(
                name,
                VOICE_OPTIONS,
                key=f"voice_{name}"
            )

    st.caption(
        "Voice profiles are saved with the project. "
        "V2.0 prepares the animation pipeline; "
        "real AI voice synthesis is the next voice backend upgrade."
    )

    st.divider()

    st.subheader(
        "Write your script"
    )

    st.markdown(
        "Use one dialogue line per scene:"
    )

    st.code(
        "Alex: Did you know that honey can last for years?\n"
        "Maya: Seriously? Even without refrigeration?\n"
        "Jay: Wait... so honey basically has a superpower?"
    )

    script = st.text_area(
        "Script",
        height=240,
        placeholder=(
            "Alex: Did you know that honey can last for years?\n"
            "Maya: Seriously?\n"
            "Jay: That's crazy!"
        ),
        label_visibility="collapsed"
    )

    if st.button(
        "🎬 Generate Animated Cartoon",
        type="primary",
        use_container_width=True
    ):

        if not script.strip():

            st.warning(
                "Please enter a script."
            )

        elif len(selected) < 1:

            st.warning(
                "Choose at least one character."
            )

        else:

            rows = parse_script(
                script
            )

            settings = {
                "characters": selected,
                "scene": scene,
                "expressions": expressions,
                "voices": voice_map
            }

            with st.spinner(
                "Animating characters and scenes..."
            ):

                video, error = make_video(
                    rows,
                    settings
                )

            if video:

                st.session_state.v2_video = str(
                    video
                )

                st.success(
                    "🎉 Cartoon generated!"
                )

            else:

                st.error(
                    "Video generation failed."
                )

                if error:

                    st.code(
                        error,
                        language="text"
                    )

    if st.session_state.get(
        "v2_video"
    ):

        path = Path(
            st.session_state.v2_video
        )

        if path.exists():

            st.subheader(
                "Preview"
            )

            st.video(
                str(path)
            )

            st.download_button(
                "⬇️ Download Cartoon",
                path.read_bytes(),
                "cartoon_v2.mp4",
                "video/mp4",
                use_container_width=True
            )


# ============================================================
# JOIN VIDEOS
# ============================================================

with join_tab:

    st.header(
        "🎞️ Join short videos"
    )

    st.write(
        "Upload multiple clips and combine them "
        "into one longer MP4."
    )

    uploads = st.file_uploader(
        "Choose video clips",
        type=[
            "mp4",
            "mov",
            "m4v",
            "webm"
        ],
        accept_multiple_files=True
    )

    if uploads:

        st.write(
            f"**{len(uploads)} clips selected**"
        )

        for i, file in enumerate(
            uploads,
            1
        ):

            st.write(
                f"{i}. {file.name}"
            )

        if st.button(
            "🎬 Join Into Long Video",
            type="primary",
            use_container_width=True
        ):

            with st.spinner(
                "Combining videos..."
            ):

                result, error = join_videos(
                    uploads
                )

            if result:

                st.session_state.joined = str(
                    result
                )

                st.success(
                    "Long video created!"
                )

            else:

                st.error(
                    "Could not join the videos."
                )

                if error:

                    st.code(
                        error,
                        language="text"
                    )

    if st.session_state.get(
        "joined"
    ):

        path = Path(
            st.session_state.joined
        )

        if path.exists():

            st.video(
                str(path)
            )

            st.download_button(
                "⬇️ Download Long Video",
                path.read_bytes(),
                "long_cartoon.mp4",
                "video/mp4",
                use_container_width=True
            )


# ============================================================
# HELP
# ============================================================

with help_tab:

    st.header(
        "How V2 works"
    )

    st.markdown(
        """
### 1. Pick your characters

Choose from 12 original cartoon characters.

### 2. Pick a location

Choose a home, school, pharmacy, hospital,
office, street, restaurant or park.

### 3. Give characters expressions

Each character can be happy, surprised,
thinking, angry, laughing or neutral.

### 4. Write dialogue

Use:

`Character: dialogue`

Each line becomes a scene.

### 5. Generate

Characters have:

- Body movement
- Head movement
- Arm gestures
- Facial expressions
- Eye movement
- Animated mouth movement
- Character name tags
- Scene backgrounds
- Dialogue timing

### 6. Join episodes

Use **Join Videos** to combine multiple short
cartoons into a longer episode.

### Next upgrade: V2.1

The next stage is the voice engine:

`Script → AI voice → audio timing → lip-sync → final MP4`

That will make characters actually speak
their dialogue instead of only animating their mouths.
"""
    )

st.caption(
    "Cartoon Studio V2.0 • Original characters • Animated 2D scenes"
)
