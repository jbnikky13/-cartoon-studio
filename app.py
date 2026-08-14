import streamlit as st
from pathlib import Path
import tempfile
import subprocess
import shutil
import re
import os
import json
import math
import asyncio
import wave
import struct

from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg


# ============================================================
# CARTOON STUDIO V4.1
# Character Rig + Voices + Lip Sync + Acting + Camera
# ============================================================

st.set_page_config(
    page_title="Cartoon Studio V4.1",
    page_icon="🎬",
    layout="wide"
)

ROOT = Path(tempfile.gettempdir()) / "cartoon_studio_v41"
ROOT.mkdir(exist_ok=True)

W = 1280
H = 720
FPS = 24


# ============================================================
# ORIGINAL CHARACTERS
# ============================================================

CHARACTERS = {
    "Zuri Spark": {
        "skin": (137, 87, 65),
        "hair": (42, 27, 25),
        "shirt": (235, 91, 76),
        "pants": (46, 55, 76),
        "shoes": (35, 35, 42),
        "voice": "en-NG-EzinneNeural",
        "voice_fallback": "en-US-AriaNeural",
        "description": "Energetic, curious and optimistic"
    },

    "Milo Quirk": {
        "skin": (177, 119, 87),
        "hair": (55, 39, 29),
        "shirt": (63, 145, 183),
        "pants": (48, 55, 72),
        "shoes": (35, 35, 42),
        "voice": "en-US-GuyNeural",
        "voice_fallback": "en-US-GuyNeural",
        "description": "Calm, dry and deadpan"
    },

    "Kemi Bolt": {
        "skin": (108, 70, 54),
        "hair": (30, 23, 20),
        "shirt": (235, 168, 58),
        "pants": (55, 64, 76),
        "shoes": (35, 35, 42),
        "voice": "en-US-JennyNeural",
        "voice_fallback": "en-US-JennyNeural",
        "description": "Fast, confident and fearless"
    },

    "Tari Reed": {
        "skin": (157, 99, 73),
        "hair": (45, 29, 26),
        "shirt": (92, 171, 132),
        "pants": (50, 61, 76),
        "shoes": (35, 35, 42),
        "voice": "en-US-SaraNeural",
        "voice_fallback": "en-US-SaraNeural",
        "description": "Relaxed and observant"
    },

    "Biko Bean": {
        "skin": (126, 79, 59),
        "hair": (72, 48, 35),
        "shirt": (154, 101, 190),
        "pants": (55, 56, 72),
        "shoes": (35, 35, 42),
        "voice": "en-US-DavisNeural",
        "voice_fallback": "en-US-DavisNeural",
        "description": "Warm, funny and food obsessed"
    },

    "Nala Vee": {
        "skin": (184, 123, 90),
        "hair": (31, 24, 22),
        "shirt": (69, 116, 207),
        "pants": (55, 56, 80),
        "shoes": (35, 35, 42),
        "voice": "en-US-AnaNeural",
        "voice_fallback": "en-US-AriaNeural",
        "description": "Ambitious and expressive"
    },

    "Dex Orbit": {
        "skin": (146, 93, 68),
        "hair": (36, 27, 24),
        "shirt": (102, 107, 121),
        "pants": (46, 51, 66),
        "shoes": (35, 35, 42),
        "voice": "en-US-AndrewNeural",
        "voice_fallback": "en-US-GuyNeural",
        "description": "Dramatic and suspicious"
    },

    "Ayo Finch": {
        "skin": (112, 71, 54),
        "hair": (27, 22, 20),
        "shirt": (207, 91, 137),
        "pants": (54, 59, 71),
        "shoes": (35, 35, 42),
        "voice": "en-US-BrianNeural",
        "voice_fallback": "en-US-GuyNeural",
        "description": "Quiet and sarcastic"
    },

    "Rhea Moss": {
        "skin": (161, 105, 77),
        "hair": (84, 53, 36),
        "shirt": (86, 151, 191),
        "pants": (50, 60, 75),
        "shoes": (35, 35, 42),
        "voice": "en-US-EmmaNeural",
        "voice_fallback": "en-US-AriaNeural",
        "description": "Practical and confident"
    },

    "Professor Pogo": {
        "skin": (186, 127, 94),
        "hair": (145, 145, 145),
        "shirt": (226, 226, 220),
        "pants": (64, 75, 86),
        "shoes": (35, 35, 42),
        "voice": "en-US-RogerNeural",
        "voice_fallback": "en-US-GuyNeural",
        "description": "Eccentric and theatrical"
    },

    "Jax Noon": {
        "skin": (120, 76, 58),
        "hair": (31, 24, 21),
        "shirt": (192, 76, 70),
        "pants": (48, 53, 66),
        "shoes": (35, 35, 42),
        "voice": "en-US-ChristopherNeural",
        "voice_fallback": "en-US-GuyNeural",
        "description": "Dramatic storyteller"
    },

    "Simi Ray": {
        "skin": (139, 87, 64),
        "hair": (45, 29, 24),
        "shirt": (75, 181, 165),
        "pants": (55, 60, 75),
        "shoes": (35, 35, 42),
        "voice": "en-US-MichelleNeural",
        "voice_fallback": "en-US-AriaNeural",
        "description": "Curious and enthusiastic"
    }
}


LOCATIONS = [
    "Apartment",
    "Classroom",
    "Office",
    "Pharmacy",
    "Restaurant",
    "Park",
    "Street",
    "Bus Stop",
    "Corner Shop",
    "Rooftop"
]

STYLES = [
    "Bold 2D Comedy",
    "Clean Vector",
    "Comic Panel",
    "Storybook",
    "Retro Cartoon"
]

EMOTIONS = [
    "Auto",
    "Neutral",
    "Happy",
    "Surprised",
    "Thinking",
    "Annoyed",
    "Laughing",
    "Excited",
    "Confused",
    "Sad",
    "Nervous"
]

GESTURES = [
    "Auto",
    "Talking",
    "Pointing",
    "Waving",
    "Thinking",
    "Shrugging",
    "Crossed Arms",
    "Laughing",
    "Nervous",
    "None"
]

POSTURES = [
    "Auto",
    "Standing",
    "Sitting",
    "Leaning"
]

CAMERAS = [
    "Auto",
    "Wide",
    "Two Shot",
    "Speaker",
    "Listener",
    "Close Up"
]

PACE = [
    "Natural",
    "Comedic",
    "Calm",
    "Fast"
]


# ============================================================
# FONTS
# ============================================================

def font(size=24, bold=False):

    paths = [
        "/usr/share/fonts/truetype/dejavu/"
        + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),

        "/usr/share/fonts/truetype/liberation2/"
        + ("LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf")
    ]

    for p in paths:

        if Path(p).exists():

            return ImageFont.truetype(p, size)

    return ImageFont.load_default()


# ============================================================
# SCRIPT PARSER
# ============================================================

def parse_script(script):

    rows = []

    for line in script.splitlines():

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

            rows.append(
                {
                    "speaker": speaker,
                    "dialogue": dialogue
                }
            )

    return rows


# ============================================================
# PERFORMANCE AI
# ============================================================

def infer_emotion(text):

    t = text.lower()

    if any(x in t for x in [
        "haha", "lol", "funny",
        "hilarious"
    ]):
        return "Laughing"

    if any(x in t for x in [
        "wow", "amazing", "awesome",
        "yes!", "finally"
    ]):
        return "Excited"

    if "?" in text or any(x in t for x in [
        "really", "why", "how",
        "what", "huh"
    ]):
        return "Confused"

    if any(x in t for x in [
        "annoying", "seriously",
        "stop", "ridiculous"
    ]):
        return "Annoyed"

    if any(x in t for x in [
        "think", "maybe", "perhaps",
        "wonder"
    ]):
        return "Thinking"

    if any(x in t for x in [
        "sorry", "sad", "unfortunately"
    ]):
        return "Sad"

    if any(x in t for x in [
        "nervous", "worried",
        "scared"
    ]):
        return "Nervous"

    if any(x in t for x in [
        "great", "good", "nice",
        "love", "thank"
    ]):
        return "Happy"

    return "Neutral"


def infer_gesture(text, emotion):

    t = text.lower()

    if any(x in t for x in [
        "look", "there", "that",
        "this", "see"
    ]):
        return "Pointing"

    if any(x in t for x in [
        "hello", "hi", "hey",
        "bye"
    ]):
        return "Waving"

    if emotion == "Thinking":
        return "Thinking"

    if emotion == "Laughing":
        return "Laughing"

    if emotion == "Nervous":
        return "Nervous"

    if emotion == "Annoyed":
        return "Crossed Arms"

    if emotion == "Excited":
        return "Talking"

    return "Talking"


def infer_posture(location, text):

    t = text.lower()

    if any(x in t for x in [
        "sit", "sitting",
        "chair", "desk"
    ]):
        return "Sitting"

    if any(x in t for x in [
        "stand", "standing",
        "walk"
    ]):
        return "Standing"

    if location in [
        "Restaurant",
        "Office",
        "Classroom"
    ]:
        return "Sitting"

    return "Standing"


def infer_camera(index, total, text):

    t = text.lower()

    if any(x in t for x in [
        "wow", "really", "look",
        "listen"
    ]):
        return "Speaker"

    if "?" in text:
        return "Listener"

    if index == 0:
        return "Wide"

    if index == total - 1:
        return "Two Shot"

    return "Speaker"


def estimate_duration(text, pace):

    words = max(1, len(text.split()))

    rates = {
        "Natural": 2.65,
        "Comedic": 2.25,
        "Calm": 2.0,
        "Fast": 3.15
    }

    return max(
        2.0,
        min(
            12.0,
            words / rates[pace] + 0.8
        )
    )


# ============================================================
# BACKGROUND
# ============================================================

def draw_background(draw, location):

    draw.rectangle(
        [0, 0, W, H],
        fill=(190, 218, 238)
    )

    draw.rectangle(
        [0, 475, W, H],
        fill=(105, 145, 100)
    )

    if location == "Street":

        draw.rectangle(
            [0, 400, W, 475],
            fill=(75, 80, 88)
        )

        draw.line(
            [0, 435, W, 435],
            fill=(235, 205, 90),
            width=4
        )

        for x in range(50, W, 250):

            draw.rectangle(
                [x, 120, x + 160, 400],
                fill=(160, 153, 148),
                outline=(70, 70, 75),
                width=3
            )

            draw.rectangle(
                [x + 35, 325, x + 115, 350],
                fill=(239, 187, 65)
            )

    elif location in [
        "Apartment",
        "Office",
        "Classroom",
        "Pharmacy",
        "Restaurant",
        "Corner Shop"
    ]:

        draw.rectangle(
            [35, 70, W - 35, 475],
            fill=(235, 225, 210),
            outline=(55, 55, 60),
            width=4
        )

        draw.rectangle(
            [85, 115, 325, 270],
            fill=(150, 205, 230),
            outline=(60, 70, 75),
            width=4
        )

        draw.line(
            [205, 115, 205, 270],
            fill=(70, 75, 80),
            width=3
        )

        draw.line(
            [85, 192, 325, 192],
            fill=(70, 75, 80),
            width=3
        )

        draw.rectangle(
            [850, 115, 1090, 270],
            fill=(150, 205, 230),
            outline=(60, 70, 75),
            width=4
        )

        draw.line(
            [970, 115, 970, 270],
            fill=(70, 75, 80),
            width=3
        )

        if location == "Restaurant":

            draw.ellipse(
                [390, 350, 890, 470],
                fill=(125, 84, 58),
                outline=(65, 45, 35),
                width=4
            )

        elif location == "Classroom":

            draw.rectangle(
                [390, 320, 890, 365],
                fill=(125, 91, 61)
            )

            draw.rectangle(
                [530, 165, 750, 285],
                fill=(70, 125, 165),
                outline=(55, 60, 65),
                width=4
            )

        elif location == "Pharmacy":

            draw.rectangle(
                [430, 300, 850, 400],
                fill=(220, 225, 228),
                outline=(70, 70, 75),
                width=4
            )

            draw.text(
                [510, 330],
                "PHARMACY",
                font=font(34, True),
                fill=(55, 60, 65)
            )

        elif location == "Office":

            draw.rectangle(
                [390, 360, 890, 435],
                fill=(105, 75, 55)
            )

    elif location == "Park":

        for x in [130, 1060]:

            draw.rectangle(
                [x, 220, x + 28, 475],
                fill=(105, 70, 45)
            )

            draw.ellipse(
                [x - 90, 100, x + 115, 300],
                fill=(60, 140, 70)
            )

    elif location == "Rooftop":

        draw.rectangle(
            [0, 360, W, 475],
            fill=(100, 105, 115)
        )

        draw.line(
            [0, 360, W, 360],
            fill=(45, 48, 55),
            width=8
        )

    else:

        draw.rectangle(
            [0, 410, W, 475],
            fill=(80, 82, 88)
        )


# ============================================================
# CHARACTER RIG
# ============================================================

def draw_character(
    draw,
    name,
    x,
    ground,
    frame,
    expression,
    gesture,
    posture,
    talking,
    look_x=None,
    scale=1.0,
    seed=1
):

    c = CHARACTERS[name]

    # --------------------------------------------------------
    # GLOBAL MOTION
    # --------------------------------------------------------

    breathing = 2.5 * math.sin(
        frame / 12 + seed
    )

    sway = 3.0 * math.sin(
        frame / 18 + seed
    )

    x += sway

    if posture == "Leaning":
        x += 15 * math.sin(
            frame / 25
        )

    ground += breathing

    # --------------------------------------------------------
    # DIMENSIONS
    # --------------------------------------------------------

    head_r = int(61 * scale)

    if posture == "Sitting":

        head_y = ground - 285
        body_bottom = ground - 75

    else:

        head_y = ground - 315
        body_bottom = ground - 70

    body_top = head_y + 75

    # --------------------------------------------------------
    # SHADOW
    # --------------------------------------------------------

    draw.ellipse(
        [
            x - 80,
            ground + 5,
            x + 80,
            ground + 25
        ],
        fill=(65, 70, 67)
    )

    # --------------------------------------------------------
    # LEGS
    # --------------------------------------------------------

    if posture == "Sitting":

        draw.line(
            [
                x - 22,
                body_bottom,
                x - 75,
                ground - 30
            ],
            fill=c["pants"],
            width=15
        )

        draw.line(
            [
                x + 22,
                body_bottom,
                x + 75,
                ground - 30
            ],
            fill=c["pants"],
            width=15
        )

    else:

        leg_wave = math.sin(
            frame / 15 + seed
        )

        draw.line(
            [
                x - 22,
                body_bottom,
                x - 38 + int(leg_wave * 4),
                ground
            ],
            fill=c["pants"],
            width=15
        )

        draw.line(
            [
                x + 22,
                body_bottom,
                x + 38 - int(leg_wave * 4),
                ground
            ],
            fill=c["pants"],
            width=15
        )

    # --------------------------------------------------------
    # SHOES
    # --------------------------------------------------------

    draw.ellipse(
        [
            x - 65,
            ground - 5,
            x - 5,
            ground + 17
        ],
        fill=c["shoes"]
    )

    draw.ellipse(
        [
            x + 5,
            ground - 5,
            x + 65,
            ground + 17
        ],
        fill=c["shoes"]
    )

    # --------------------------------------------------------
    # TORSO
    # --------------------------------------------------------

    draw.rounded_rectangle(
        [
            x - 62,
            body_top,
            x + 62,
            body_bottom
        ],
        radius=25,
        fill=c["shirt"],
        outline=(45, 45, 50),
        width=4
    )

    # --------------------------------------------------------
    # NECK
    # --------------------------------------------------------

    draw.rectangle(
        [
            x - 18,
            head_y + 42,
            x + 18,
            head_y + 82
        ],
        fill=c["skin"]
    )

    # --------------------------------------------------------
    # ARMS - ALWAYS DRAW BOTH
    # --------------------------------------------------------

    arm_y = body_top + 62

    motion = math.sin(
        frame / 4.0 + seed
    )

    left_end = (
        x - 105,
        arm_y + 35
    )

    right_end = (
        x + 105,
        arm_y + 35
    )

    if gesture == "Pointing":

        right_end = (
            x + 145,
            arm_y - 25
        )

        left_end = (
            x - 90,
            arm_y + 55
        )

    elif gesture == "Waving":

        right_end = (
            x + 82,
            arm_y - 85 + int(
                motion * 15
            )
        )

        left_end = (
            x - 90,
            arm_y + 45
        )

    elif gesture == "Thinking":

        right_end = (
            x + 62,
            head_y + 38
        )

        left_end = (
            x - 70,
            arm_y + 35
        )

    elif gesture == "Shrugging":

        right_end = (
            x + 100,
            arm_y - 35
        )

        left_end = (
            x - 100,
            arm_y - 35
        )

    elif gesture == "Crossed Arms":

        right_end = (
            x - 25,
            arm_y + 48
        )

        left_end = (
            x + 25,
            arm_y + 48
        )

    elif gesture == "Laughing":

        right_end = (
            x + 75,
            arm_y + 20
        )

        left_end = (
            x - 75,
            arm_y + 20
        )

    elif gesture == "Nervous":

        right_end = (
            x + 65,
            arm_y + 75
        )

        left_end = (
            x - 65,
            arm_y + 75
        )

    elif gesture == "None":

        right_end = (
            x + 45,
            body_bottom - 5
        )

        left_end = (
            x - 45,
            body_bottom - 5
        )

    else:

        # Natural talking hands

        right_end = (
            x + 88,
            arm_y + int(
                18 * math.sin(
                    frame / 5 + seed
                )
            )
        )

        left_end = (
            x - 88,
            arm_y + int(
                18 * math.sin(
                    frame / 5 + seed + 2
                )
            )
        )

    # LEFT ARM

    left_joint = (
        x - 50,
        arm_y
    )

    draw.line(
        [
            left_joint,
            (
                (left_joint[0] + left_end[0]) // 2,
                (left_joint[1] + left_end[1]) // 2
            ),
            left_end
        ],
        fill=c["shirt"],
        width=22
    )

    # RIGHT ARM

    right_joint = (
        x + 50,
        arm_y
    )

    draw.line(
        [
            right_joint,
            (
                (right_joint[0] + right_end[0]) // 2,
                (right_joint[1] + right_end[1]) // 2
            ),
            right_end
        ],
        fill=c["shirt"],
        width=22
    )

    # --------------------------------------------------------
    # HANDS - ALWAYS VISIBLE
    # --------------------------------------------------------

    for hand_x, hand_y in [
        left_end,
        right_end
    ]:

        draw.ellipse(
            [
                hand_x - 13,
                hand_y - 13,
                hand_x + 13,
                hand_y + 13
            ],
            fill=c["skin"],
            outline=(55, 45, 42),
            width=3
        )

    # --------------------------------------------------------
    # HEAD
    # --------------------------------------------------------

    draw.ellipse(
        [
            x - head_r,
            head_y - head_r,
            x + head_r,
            head_y + head_r
        ],
        fill=c["skin"],
        outline=(55, 45, 40),
        width=4
    )

    # --------------------------------------------------------
    # HAIR
    # --------------------------------------------------------

    draw.arc(
        [
            x - head_r - 5,
            head_y - head_r - 12,
            x + head_r + 5,
            head_y + 25
        ],
        180,
        360,
        fill=c["hair"],
        width=19
    )

    # --------------------------------------------------------
    # EYES
    # --------------------------------------------------------

    eye_offset = 0

    if look_x is not None:

        eye_offset = max(
            -7,
            min(
                7,
                int(
                    (look_x - x) / 90
                )
            )
        )

    blinking = (
        (frame + seed * 17) % 91
        in [0, 1, 2]
    )

    eye_h = 2 if blinking else 9

    eye_y = head_y - 12

    for ex in [
        x - 23,
        x + 23
    ]:

        draw.ellipse(
            [
                ex - 10 + eye_offset,
                eye_y - eye_h,
                ex + 10 + eye_offset,
                eye_y + eye_h
            ],
            fill=(25, 25, 28)
        )

    # --------------------------------------------------------
    # EYEBROWS
    # --------------------------------------------------------

    brow_y = head_y - 35

    if expression == "Annoyed":

        draw.line(
            [
                x - 40,
                brow_y + 5,
                x - 12,
                brow_y - 5
            ],
            fill=(45, 32, 30),
            width=5
        )

        draw.line(
            [
                x + 12,
                brow_y - 5,
                x + 40,
                brow_y + 5
            ],
            fill=(45, 32, 30),
            width=5
        )

    elif expression in [
        "Surprised",
        "Excited"
    ]:

        draw.line(
            [
                x - 40,
                brow_y - 8,
                x - 12,
                brow_y - 11
            ],
            fill=(45, 32, 30),
            width=5
        )

        draw.line(
            [
                x + 12,
                brow_y - 11,
                x + 40,
                brow_y - 8
            ],
            fill=(45, 32, 30),
            width=5
        )

    else:

        draw.line(
            [
                x - 38,
                brow_y,
                x - 12,
                brow_y - 2
            ],
            fill=(45, 32, 30),
            width=4
        )

        draw.line(
            [
                x + 12,
                brow_y - 2,
                x + 38,
                brow_y
            ],
            fill=(45, 32, 30),
            width=4
        )

    # --------------------------------------------------------
    # MOUTH / LIP SYNC
    # --------------------------------------------------------

    mouth_y = head_y + 38

    if talking:

        # Procedural phoneme-like mouth cycle
        phase = frame % 12

        if phase in [0, 1, 2]:

            draw.line(
                [
                    x - 20,
                    mouth_y + 8,
                    x + 20,
                    mouth_y + 8
                ],
                fill=(80, 30, 32),
                width=4
            )

        elif phase in [3, 4, 5]:

            draw.ellipse(
                [
                    x - 15,
                    mouth_y,
                    x + 15,
                    mouth_y + 17
                ],
                fill=(80, 27, 32)
            )

        elif phase in [6, 7, 8]:

            draw.ellipse(
                [
                    x - 20,
                    mouth_y - 1,
                    x + 20,
                    mouth_y + 23
                ],
                fill=(80, 27, 32)
            )

        else:

            draw.arc(
                [
                    x - 25,
                    mouth_y - 8,
                    x + 25,
                    mouth_y + 28
                ],
                0,
                180,
                fill=(80, 27, 32),
                width=5
            )

    elif expression == "Surprised":

        draw.ellipse(
            [
                x - 15,
                mouth_y,
                x + 15,
                mouth_y + 27
            ],
            fill=(80, 27, 32)
        )

    elif expression in [
        "Happy",
        "Excited",
        "Laughing"
    ]:

        draw.arc(
            [
                x - 28,
                mouth_y - 10,
                x + 28,
                mouth_y + 27
            ],
            0,
            180,
            fill=(80, 27, 32),
            width=5
        )

    elif expression == "Sad":

        draw.arc(
            [
                x - 25,
                mouth_y - 3,
                x + 25,
                mouth_y + 23
            ],
            180,
            360,
            fill=(80, 27, 32),
            width=5
        )

    else:

        draw.line(
            [
                x - 18,
                mouth_y + 8,
                x + 18,
                mouth_y + 8
            ],
            fill=(80, 30, 32),
            width=4
        )


# ============================================================
# DIALOGUE BOX
# ============================================================

def draw_dialogue(
    draw,
    speaker,
    text,
    emotion
):

    draw.rounded_rectangle(
        [
            35,
            52,
            1245,
            175
        ],
        radius=25,
        fill=(255, 255, 255),
        outline=(35, 37, 42),
        width=4
    )

    draw.text(
        (65, 68),
        speaker,
        font=font(27, True),
        fill=(30, 30, 34)
    )

    words = text.split()

    lines = []
    current = ""

    for word in words:

        trial = (
            current + " " + word
        ).strip()

        if len(trial) <= 78:

            current = trial

        else:

            lines.append(current)
            current = word

    if current:
        lines.append(current)

    y = 108

    for line in lines[:2]:

        draw.text(
            (65, y),
            line,
            font=font(23),
            fill=(45, 45, 50)
        )

        y += 30

    draw.rounded_rectangle(
        [
            1060,
            18,
            1230,
            46
        ],
        radius=12,
        fill=(32, 35, 40)
    )

    draw.text(
        (1080, 23),
        emotion.upper(),
        font=font(14, True),
        fill=(245, 245, 245)
    )


# ============================================================
# FRAME RENDERING
# ============================================================

def render_frame(
    scene,
    project,
    frame
):

    img = Image.new(
        "RGB",
        (W, H),
        (220, 220, 220)
    )

    draw = ImageDraw.Draw(img)

    draw_background(
        draw,
        scene["location"]
    )

    cast = project["cast"]

    speaker = scene["speaker"]

    listener = next(
        (
            c for c in cast
            if c != speaker
        ),
        None
    )

    total_frames = scene["frames"]

    progress = frame / max(
        1,
        total_frames - 1
    )

    camera = scene["camera"]

    if camera == "Auto":

        camera = infer_camera(
            scene["index"],
            scene["total"],
            scene["dialogue"]
        )

    if camera == "Wide":

        left_x = 340
        right_x = 930
        scale = 0.88

    elif camera == "Close Up":

        left_x = 460
        right_x = 820
        scale = 1.12

    elif camera == "Speaker":

        if speaker == cast[0]:

            left_x = 460
            right_x = 930

        else:

            left_x = 350
            right_x = 820

        scale = 1.08

    elif camera == "Listener":

        if listener == cast[0]:

            left_x = 460
            right_x = 930

        else:

            left_x = 350
            right_x = 820

        scale = 1.05

    else:

        left_x = 380
        right_x = 900
        scale = 1.0

    # --------------------------------------------------------
    # CINEMATIC MICRO CAMERA MOVEMENT
    # --------------------------------------------------------

    camera_move = int(
        10 *
        math.sin(
            progress * math.pi
        )
    )

    left_x += camera_move
    right_x -= camera_move

    # --------------------------------------------------------
    # SPEAKER
    # --------------------------------------------------------

    draw_character(
        draw,
        speaker,
        left_x,
        655,
        frame,
        scene["emotion"],
        scene["gesture"],
        scene["posture"],
        True,
        look_x=right_x,
        scale=scale,
        seed=3
    )

    # --------------------------------------------------------
    # LISTENER
    # --------------------------------------------------------

    if listener:

        listener_expression = "Neutral"
        listener_gesture = "None"

        if scene["emotion"] == "Surprised":

            listener_expression = "Surprised"

        elif scene["emotion"] == "Excited":

            listener_expression = "Happy"

        elif scene["emotion"] == "Annoyed":

            listener_expression = "Confused"

        elif scene["emotion"] == "Laughing":

            listener_expression = "Laughing"

        elif scene["emotion"] == "Confused":

            listener_expression = "Thinking"

        # occasional listener reactions

        if frame % 130 > 105:

            listener_gesture = "Thinking"

        draw_character(
            draw,
            listener,
            right_x,
            655,
            frame + 5,
            listener_expression,
            listener_gesture,
            scene["posture"],
            False,
            look_x=left_x,
            scale=scale,
            seed=8
        )

    # --------------------------------------------------------
    # DIALOGUE
    # --------------------------------------------------------

    draw_dialogue(
        draw,
        speaker,
        scene["dialogue"],
        scene["emotion"]
    )

    # --------------------------------------------------------
    # TIMELINE
    # --------------------------------------------------------

    draw.rectangle(
        [
            35,
            694,
            1245,
            702
        ],
        fill=(40, 43, 48)
    )

    draw.rectangle(
        [
            35,
            694,
            35 + int(
                1210 * progress
            ),
            702
        ],
        fill=(235, 91, 76)
    )

    return img


# ============================================================
# AUDIO
# ============================================================

async def generate_edge_voice(
    text,
    voice,
    output
):

    import edge_tts

    communicate = edge_tts.Communicate(
        text,
        voice
    )

    await communicate.save(
        str(output)
    )


def generate_voice(
    text,
    character,
    output
):

    c = CHARACTERS[character]

    try:

        asyncio.run(
            generate_edge_voice(
                text,
                c["voice"],
                output
            )
        )

        if output.exists() and output.stat().st_size > 1000:

            return True

    except Exception:

        pass

    # fallback voice

    try:

        asyncio.run(
            generate_edge_voice(
                text,
                c["voice_fallback"],
                output
            )
        )

        if output.exists() and output.stat().st_size > 1000:

            return True

    except Exception:

        pass

    return False


# ============================================================
# AUDIO DURATION
# ============================================================

def audio_duration(path):

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    result = subprocess.run(
        [
            ffmpeg,
            "-i",
            str(path)
        ],
        capture_output=True,
        text=True
    )

    text = (
        result.stderr or
        result.stdout or
        ""
    )

    match = re.search(
        r"Duration:\s*(\d+):(\d+):([\d.]+)",
        text
    )

    if not match:

        return 3.0

    h = int(match.group(1))
    m = int(match.group(2))
    s = float(match.group(3))

    return (
        h * 3600 +
        m * 60 +
        s
    )


# ============================================================
# RENDER FULL VIDEO
# ============================================================

def render_video(
    scenes,
    project,
    progress_callback=None
):

    job = ROOT / (
        "job_" +
        str(os.getpid())
    )

    frames = job / "frames"
    audio = job / "audio"

    job.mkdir(
        exist_ok=True
    )

    frames.mkdir()
    audio.mkdir()

    output = ROOT / (
        "cartoon_v41_" +
        str(os.getpid()) +
        ".mp4"
    )

    try:

        # ----------------------------------------------------
        # GENERATE VOICES FIRST
        # ----------------------------------------------------

        voice_files = []

        for i, scene in enumerate(scenes):

            voice_file = audio / (
                f"voice_{i}.mp3"
            )

            ok = generate_voice(
                scene["dialogue"],
                scene["speaker"],
                voice_file
            )

            if not ok:

                voice_file = audio / (
                    f"voice_{i}.wav"
                )

                duration = estimate_duration(
                    scene["dialogue"],
                    project["pace"]
                )

                sample_rate = 16000

                samples = int(
                    duration *
                    sample_rate
                )

                with wave.open(
                    str(voice_file),
                    "wb"
                ) as wf:

                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(
                        sample_rate
                    )

                    wf.writeframes(
                        struct.pack(
                            "<h",
                            0
                        ) * samples
                    )

            scene["audio"] = str(
                voice_file
            )

            # Use actual voice duration

            try:

                duration = audio_duration(
                    voice_file
                )

                scene["duration"] = max(
                    1.8,
                    duration + 0.35
                )

            except Exception:

                pass

            scene["frames"] = max(
                1,
                int(
                    scene["duration"] *
                    FPS
                )
            )

            voice_files.append(
                voice_file
            )

            if progress_callback:

                progress_callback(
                    0.15 *
                    (
                        (i + 1) /
                        len(scenes)
                    )
                )

        # ----------------------------------------------------
        # RENDER FRAMES
        # ----------------------------------------------------

        total_frames = sum(
            scene["frames"]
            for scene in scenes
        )

        completed = 0
        frame_number = 0

        for scene in scenes:

            for frame in range(
                scene["frames"]
            ):

                img = render_frame(
                    scene,
                    project,
                    frame
                )

                img.save(
                    frames /
                    f"frame_{frame_number:07d}.png"
                )

                frame_number += 1
                completed += 1

                if progress_callback:

                    progress_callback(
                        0.15 +
                        0.55 *
                        (
                            completed /
                            total_frames
                        )
                    )

        # ----------------------------------------------------
        # CREATE VIDEO WITHOUT AUDIO
        # ----------------------------------------------------

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

        silent_video = job / "silent.mp4"

        result = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-framerate",
                str(FPS),
                "-i",
                str(
                    frames /
                    "frame_%07d.png"
                ),
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(silent_video)
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:

            return None, result.stderr[-4000:]

        if progress_callback:

            progress_callback(0.78)

        # ----------------------------------------------------
        # BUILD AUDIO TRACK
        # ----------------------------------------------------

        concat_audio = job / "audio_concat.txt"

        concat_audio.write_text(
            "\n".join(
                [
                    f"file '{Path(f).as_posix()}'"
                    for f in voice_files
                ]
            )
        )

        joined_audio = job / "joined_audio.mp3"

        result = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_audio),
                "-c:a",
                "libmp3lame",
                "-b:a",
                "128k",
                str(joined_audio)
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:

            # If MP3 concat fails, render each voice
            # into WAV-compatible PCM through ffmpeg.

            wav_files = []

            for i, f in enumerate(
                voice_files
            ):

                wav = job / (
                    f"voice_{i}.wav"
                )

                r = subprocess.run(
                    [
                        ffmpeg,
                        "-y",
                        "-i",
                        str(f),
                        "-ar",
                        "44100",
                        "-ac",
                        "2",
                        str(wav)
                    ],
                    capture_output=True,
                    text=True
                )

                if r.returncode == 0:

                    wav_files.append(wav)

            if not wav_files:

                return None, (
                    "Could not create the voice track."
                )

            concat_audio.write_text(
                "\n".join(
                    [
                        f"file '{f.as_posix()}'"
                        for f in wav_files
                    ]
                )
            )

            joined_audio = job / "joined_audio.wav"

            result = subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(concat_audio),
                    "-c:a",
                    "pcm_s16le",
                    str(joined_audio)
                ],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:

                return None, result.stderr[-4000:]

        if progress_callback:

            progress_callback(0.90)

        # ----------------------------------------------------
        # COMBINE VIDEO + VOICE
        # ----------------------------------------------------

        result = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(silent_video),
                "-i",
                str(joined_audio),
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-shortest",
                "-movflags",
                "+faststart",
                str(output)
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:

            return None, result.stderr[-4000:]

        if progress_callback:

            progress_callback(1.0)

        return output, None

    finally:

        shutil.rmtree(
            job,
            ignore_errors=True
        )


# ============================================================
# JOIN VIDEOS
# ============================================================

def join_videos(files):

    job = ROOT / (
        "join_" +
        str(os.getpid())
    )

    job.mkdir(
        exist_ok=True
    )

    try:

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

        clips = []

        for i, file in enumerate(files):

            src = job / (
                f"source_{i}.mp4"
            )

            normalized = job / (
                f"clip_{i}.mp4"
            )

            src.write_bytes(
                file.getvalue()
            )

            result = subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-i",
                    str(src),
                    "-vf",
                    (
                        "scale=1280:720:"
                        "force_original_aspect_ratio=decrease,"
                        "pad=1280:720:"
                        "(ow-iw)/2:"
                        "(oh-ih)/2,"
                        "format=yuv420p"
                    ),
                    "-r",
                    "24",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-c:a",
                    "aac",
                    str(normalized)
                ],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:

                return None, result.stderr[-3000:]

            clips.append(
                normalized
            )

        manifest = job / "concat.txt"

        manifest.write_text(
            "\n".join(
                [
                    f"file '{x.as_posix()}'"
                    for x in clips
                ]
            )
        )

        output = ROOT / (
            "full_episode_" +
            str(os.getpid()) +
            ".mp4"
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

        if result.returncode != 0:

            return None, result.stderr[-3000:]

        return output, None

    finally:

        shutil.rmtree(
            job,
            ignore_errors=True
        )


# ============================================================
# SESSION STATE
# ============================================================

if "project" not in st.session_state:

    st.session_state.project = {
        "name": "My Cartoon Episode",
        "style": "Bold 2D Comedy",
        "location": "Apartment",
        "pace": "Natural",
        "cast": [
            "Zuri Spark",
            "Milo Quirk"
        ]
    }

if "scenes" not in st.session_state:

    st.session_state.scenes = []


# ============================================================
# HEADER
# ============================================================

st.title(
    "🎬 Cartoon Studio V4.1"
)

st.caption(
    "Create animated 2D cartoon scenes with "
    "original characters, acting, voices and reactions."
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("🎨 Episode Settings")

    st.session_state.project["name"] = st.text_input(
        "Episode name",
        st.session_state.project["name"]
    )

    st.session_state.project["style"] = st.selectbox(
        "Animation style",
        STYLES
    )

    st.session_state.project["location"] = st.selectbox(
        "Default location",
        LOCATIONS
    )

    st.session_state.project["pace"] = st.selectbox(
        "Dialogue pace",
        PACE
    )

    st.divider()

    st.markdown(
        "### V4.1 Performance"
    )

    st.write(
        "✓ Full arms and hands\n\n"
        "✓ Facial expressions\n\n"
        "✓ Blinking\n\n"
        "✓ Breathing\n\n"
        "✓ Gestures\n\n"
        "✓ Listener reactions\n\n"
        "✓ Character voices\n\n"
        "✓ Lip movement\n\n"
        "✓ Cinematic camera"
    )


# ============================================================
# TABS
# ============================================================

create_tab, acting_tab, render_tab, join_tab, project_tab = st.tabs(
    [
        "✨ Create",
        "🎭 Acting",
        "🎬 Render",
        "🔗 Join Videos",
        "💾 Project"
    ]
)


# ============================================================
# CREATE
# ============================================================

with create_tab:

    st.subheader(
        "Choose your characters"
    )

    st.session_state.project["cast"] = st.multiselect(
        "Characters",
        list(CHARACTERS.keys()),
        default=st.session_state.project["cast"],
        max_selections=4
    )

    if not st.session_state.project["cast"]:

        st.warning(
            "Choose at least two characters."
        )

    else:

        cols = st.columns(
            min(
                4,
                len(
                    st.session_state.project["cast"]
                )
            )
        )

        for i, name in enumerate(
            st.session_state.project["cast"]
        ):

            with cols[i]:

                c = CHARACTERS[name]

                st.markdown(
                    f"### {name}"
                )

                st.caption(
                    c["description"]
                )

    st.divider()

    st.subheader(
        "Paste your script"
    )

    script = st.text_area(
        "Character: dialogue",
        height=280,
        placeholder=(
            "Zuri Spark: Milo, why are you "
            "staring at the microwave?\n\n"
            "Milo Quirk: I'm waiting for it "
            "to finish.\n\n"
            "Zuri Spark: It says zero seconds.\n\n"
            "Milo Quirk: Exactly. I'm giving "
            "it a moment to think."
        )
    )

    if st.button(
        "🧠 Analyze & Build Scenes",
        type="primary",
        use_container_width=True
    ):

        rows = parse_script(
            script
        )

        cast = (
            st.session_state.project["cast"]
        )

        if len(cast) < 2:

            st.error(
                "Choose at least two characters."
            )

        elif not rows:

            st.error(
                "Enter a script first."
            )

        else:

            scenes = []

            for i, row in enumerate(rows):

                speaker = row["speaker"]

                if speaker not in cast:

                    speaker = cast[
                        i % len(cast)
                    ]

                dialogue = row["dialogue"]

                emotion = infer_emotion(
                    dialogue
                )

                gesture = infer_gesture(
                    dialogue,
                    emotion
                )

                posture = infer_posture(
                    st.session_state
                    .project["location"],
                    dialogue
                )

                camera = infer_camera(
                    i,
                    len(rows),
                    dialogue
                )

                scenes.append(
                    {
                        "id": i + 1,
                        "index": i,
                        "total": len(rows),
                        "speaker": speaker,
                        "dialogue": dialogue,
                        "emotion": emotion,
                        "gesture": gesture,
                        "posture": posture,
                        "camera": camera,
                        "location":
                            st.session_state
                            .project["location"],
                        "duration":
                            estimate_duration(
                                dialogue,
                                st.session_state
                                .project["pace"]
                            )
                    }
                )

            st.session_state.scenes = scenes

            st.success(
                f"Created {len(scenes)} animated shots."
            )


# ============================================================
# ACTING
# ============================================================

with acting_tab:

    st.subheader(
        "🎭 Direct the performance"
    )

    if not st.session_state.scenes:

        st.info(
            "Create a script first."
        )

    else:

        for scene in st.session_state.scenes:

            with st.expander(
                f"Shot {scene['id']} — "
                f"{scene['speaker']} — "
                f"{scene['emotion']}"
            ):

                st.write(
                    f"**Dialogue:** "
                    f"{scene['dialogue']}"
                )

                c1, c2, c3 = st.columns(3)

                with c1:

                    scene["emotion"] = st.selectbox(
                        "Emotion",
                        EMOTIONS,
                        index=(
                            EMOTIONS.index(
                                scene["emotion"]
                            )
                            if scene["emotion"]
                            in EMOTIONS
                            else 0
                        ),
                        key=f"emotion_{scene['id']}"
                    )

                    scene["gesture"] = st.selectbox(
                        "Gesture",
                        GESTURES,
                        index=(
                            GESTURES.index(
                                scene["gesture"]
                            )
                            if scene["gesture"]
                            in GESTURES
                            else 0
                        ),
                        key=f"gesture_{scene['id']}"
                    )

                with c2:

                    scene["posture"] = st.selectbox(
                        "Posture",
                        POSTURES,
                        index=(
                            POSTURES.index(
                                scene["posture"]
                            )
                            if scene["posture"]
                            in POSTURES
                            else 0
                        ),
                        key=f"posture_{scene['id']}"
                    )

                    scene["camera"] = st.selectbox(
                        "Camera",
                        CAMERAS,
                        index=(
                            CAMERAS.index(
                                scene["camera"]
                            )
                            if scene["camera"]
                            in CAMERAS
                            else 0
                        ),
                        key=f"camera_{scene['id']}"
                    )

                with c3:

                    scene["location"] = st.selectbox(
                        "Location",
                        LOCATIONS,
                        index=LOCATIONS.index(
                            scene["location"]
                        ),
                        key=f"location_{scene['id']}"
                    )

                    scene["duration"] = st.number_input(
                        "Minimum seconds",
                        min_value=1.5,
                        max_value=20.0,
                        value=float(
                            scene["duration"]
                        ),
                        step=0.5,
                        key=f"duration_{scene['id']}"
                    )


# ============================================================
# RENDER
# ============================================================

with render_tab:

    st.subheader(
        "🎬 Render your cartoon"
    )

    if not st.session_state.scenes:

        st.info(
            "Create an episode first."
        )

    else:

        st.write(
            f"{len(st.session_state.scenes)} "
            "shots ready."
        )

        progress = st.progress(0)

        status = st.empty()

        if st.button(
            "🚀 Render Cartoon Studio V4.1",
            type="primary",
            use_container_width=True
        ):

            def update_progress(value):

                progress.progress(
                    min(
                        1.0,
                        value
                    )
                )

                status.info(
                    f"Creating episode… "
                    f"{int(value * 100)}%"
                )

            with st.spinner(
                "Generating voices, animation and lip-sync…"
            ):

                output, error = render_video(
                    st.session_state.scenes,
                    st.session_state.project,
                    update_progress
                )

            if output:

                st.session_state.output = str(
                    output
                )

                progress.progress(1.0)

                status.success(
                    "🎉 Episode finished!"
                )

            else:

                status.error(
                    "Rendering failed."
                )

                st.code(
                    error or
                    "Unknown rendering error."
                )

        if (
            st.session_state.get("output")
            and Path(
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
                "cartoon_studio_v41.mp4",
                "video/mp4",
                use_container_width=True
            )


# ============================================================
# JOIN
# ============================================================

with join_tab:

    st.subheader(
        "🔗 Join short videos into a long episode"
    )

    st.write(
        "Upload your generated clips in the order "
        "you want them to appear."
    )

    files = st.file_uploader(
        "Cartoon clips",
        type=["mp4", "mov", "m4v"],
        accept_multiple_files=True
    )

    if files:

        for i, f in enumerate(
            files,
            1
        ):

            st.write(
                f"{i}. {f.name}"
            )

        if st.button(
            "🔗 Create Full Episode",
            type="primary",
            use_container_width=True
        ):

            with st.spinner(
                "Joining videos..."
            ):

                output, error = join_videos(
                    files
                )

            if output:

                st.session_state.joined = str(
                    output
                )

                st.success(
                    "Full episode created!"
                )

            else:

                st.error(
                    error or
                    "Could not join videos."
                )

    if (
        st.session_state.get("joined")
        and Path(
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
            "cartoon_full_episode.mp4",
            "video/mp4",
            use_container_width=True
        )


# ============================================================
# PROJECT
# ============================================================

with project_tab:

    st.subheader(
        "💾 Save your project"
    )

    data = {
        "version": "4.1",
        "project": st.session_state.project,
        "scenes": st.session_state.scenes
    }

    st.json(
        {
            "version": "4.1",
            "episode":
                st.session_state.project["name"],
            "characters":
                st.session_state.project["cast"],
            "shots":
                len(st.session_state.scenes)
        }
    )

    st.download_button(
        "💾 Download Project JSON",
        json.dumps(
            data,
            indent=2
        ),
        "cartoon_studio_v41_project.json",
        "application/json",
        use_container_width=True
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Cartoon Studio V4.1 — "
    "original characters, procedural 2D performance, "
    "character voices and video editing."
)
