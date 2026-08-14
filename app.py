import streamlit as st
from PIL import Image, ImageDraw, ImageFont
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

import imageio_ffmpeg


# ============================================================
# CARTOON STUDIO V5
# PROPER 2D CARTOON ANIMATION ENGINE
# ============================================================

st.set_page_config(
    page_title="Cartoon Studio V5",
    page_icon="🎬",
    layout="wide"
)

WIDTH = 1280
HEIGHT = 720
FPS = 24

ROOT = Path(tempfile.gettempdir()) / "cartoon_studio_v5"
ROOT.mkdir(parents=True, exist_ok=True)


# ============================================================
# ORIGINAL CHARACTER LIBRARY
# ============================================================

CHARACTERS = {

    "Zuri Spark": {
        "skin": (151, 94, 70),
        "hair": (38, 24, 22),
        "shirt": (239, 94, 77),
        "pants": (48, 59, 82),
        "shoes": (35, 35, 42),
        "accent": (247, 190, 65),
        "body": "athletic",
        "hair_style": "curly",
        "personality": "energetic",
        "voice": "en-US-JennyNeural"
    },

    "Milo Quirk": {
        "skin": (184, 124, 91),
        "hair": (48, 32, 25),
        "shirt": (65, 145, 185),
        "pants": (50, 56, 72),
        "shoes": (34, 34, 39),
        "accent": (235, 180, 70),
        "body": "slim",
        "hair_style": "side",
        "personality": "deadpan",
        "voice": "en-US-GuyNeural"
    },

    "Kemi Bolt": {
        "skin": (112, 70, 53),
        "hair": (28, 22, 20),
        "shirt": (239, 172, 52),
        "pants": (53, 64, 77),
        "shoes": (32, 32, 37),
        "accent": (218, 73, 80),
        "body": "athletic",
        "hair_style": "short",
        "personality": "confident",
        "voice": "en-US-AriaNeural"
    },

    "Tari Reed": {
        "skin": (162, 103, 75),
        "hair": (48, 30, 26),
        "shirt": (91, 171, 132),
        "pants": (51, 61, 75),
        "shoes": (33, 33, 38),
        "accent": (235, 200, 83),
        "body": "slim",
        "hair_style": "long",
        "personality": "relaxed",
        "voice": "en-US-SaraNeural"
    },

    "Biko Bean": {
        "skin": (129, 81, 60),
        "hair": (65, 43, 32),
        "shirt": (154, 101, 190),
        "pants": (54, 56, 72),
        "shoes": (34, 34, 39),
        "accent": (239, 172, 65),
        "body": "round",
        "hair_style": "short",
        "personality": "funny",
        "voice": "en-US-DavisNeural"
    },

    "Nala Vee": {
        "skin": (185, 123, 90),
        "hair": (31, 22, 21),
        "shirt": (71, 119, 209),
        "pants": (55, 57, 80),
        "shoes": (34, 34, 39),
        "accent": (244, 116, 157),
        "body": "slim",
        "hair_style": "long",
        "personality": "ambitious",
        "voice": "en-US-EmmaNeural"
    },

    "Dex Orbit": {
        "skin": (145, 91, 67),
        "hair": (36, 27, 23),
        "shirt": (101, 108, 123),
        "pants": (46, 50, 64),
        "shoes": (32, 32, 37),
        "accent": (85, 174, 220),
        "body": "tall",
        "hair_style": "spiky",
        "personality": "dramatic",
        "voice": "en-US-AndrewNeural"
    },

    "Ayo Finch": {
        "skin": (111, 69, 53),
        "hair": (27, 21, 19),
        "shirt": (207, 91, 137),
        "pants": (54, 58, 70),
        "shoes": (32, 32, 37),
        "accent": (92, 190, 160),
        "body": "slim",
        "hair_style": "short",
        "personality": "sarcastic",
        "voice": "en-US-BrianNeural"
    },

    "Rhea Moss": {
        "skin": (161, 104, 76),
        "hair": (83, 53, 36),
        "shirt": (86, 151, 191),
        "pants": (50, 60, 75),
        "shoes": (34, 34, 39),
        "accent": (235, 170, 75),
        "body": "athletic",
        "hair_style": "curly",
        "personality": "practical",
        "voice": "en-US-MichelleNeural"
    },

    "Professor Pogo": {
        "skin": (188, 128, 95),
        "hair": (143, 143, 143),
        "shirt": (229, 229, 224),
        "pants": (64, 75, 86),
        "shoes": (35, 35, 39),
        "accent": (207, 80, 80),
        "body": "round",
        "hair_style": "wild",
        "personality": "eccentric",
        "voice": "en-US-RogerNeural"
    },

    "Jax Noon": {
        "skin": (121, 76, 58),
        "hair": (30, 22, 20),
        "shirt": (194, 77, 71),
        "pants": (49, 53, 67),
        "shoes": (32, 32, 37),
        "accent": (74, 146, 214),
        "body": "tall",
        "hair_style": "short",
        "personality": "dramatic",
        "voice": "en-US-ChristopherNeural"
    },

    "Simi Ray": {
        "skin": (140, 88, 65),
        "hair": (43, 28, 23),
        "shirt": (76, 181, 165),
        "pants": (54, 60, 74),
        "shoes": (33, 33, 38),
        "accent": (244, 184, 76),
        "body": "athletic",
        "hair_style": "curly",
        "personality": "curious",
        "voice": "en-US-AnaNeural"
    }
}


LOCATIONS = [
    "Apartment",
    "Bedroom",
    "Kitchen",
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

EMOTIONS = [
    "Auto",
    "Neutral",
    "Happy",
    "Surprised",
    "Confused",
    "Thinking",
    "Annoyed",
    "Laughing",
    "Excited",
    "Sad",
    "Nervous",
    "Angry"
]

GESTURES = [
    "Auto",
    "Natural",
    "Point",
    "Wave",
    "Think",
    "Shrug",
    "Cross Arms",
    "Hands Up",
    "Laugh",
    "Nervous",
    "None"
]

POSTURES = [
    "Standing",
    "Sitting",
    "Leaning"
]

CAMERAS = [
    "Auto",
    "Wide",
    "Two Shot",
    "Speaker Close",
    "Listener Close",
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

def get_font(size, bold=False):

    candidates = [
        "/usr/share/fonts/truetype/dejavu/"
        + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),

        "/usr/share/fonts/truetype/liberation2/"
        + ("LiberationSans-Bold.ttf"
           if bold else
           "LiberationSans-Regular.ttf")
    ]

    for path in candidates:

        if os.path.exists(path):

            return ImageFont.truetype(
                path,
                size
            )

    return ImageFont.load_default()


# ============================================================
# SCRIPT PARSER
# ============================================================

def parse_script(text):

    scenes = []

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        match = re.match(
            r"^([^:]{1,40}):\s*(.+)$",
            line
        )

        if not match:
            continue

        scenes.append(
            {
                "speaker": match.group(1).strip(),
                "dialogue": match.group(2).strip()
            }
        )

    return scenes


# ============================================================
# PERFORMANCE ENGINE
# ============================================================

def detect_emotion(text):

    t = text.lower()

    if any(
        x in t
        for x in [
            "haha",
            "lol",
            "hilarious",
            "funny"
        ]
    ):
        return "Laughing"

    if any(
        x in t
        for x in [
            "wow",
            "amazing",
            "awesome",
            "yes!"
        ]
    ):
        return "Excited"

    if "?" in text:
        return "Confused"

    if any(
        x in t
        for x in [
            "really?",
            "seriously",
            "why",
            "how"
        ]
    ):
        return "Confused"

    if any(
        x in t
        for x in [
            "stop",
            "ridiculous",
            "annoying"
        ]
    ):
        return "Annoyed"

    if any(
        x in t
        for x in [
            "think",
            "maybe",
            "perhaps"
        ]
    ):
        return "Thinking"

    if any(
        x in t
        for x in [
            "sorry",
            "sad",
            "unfortunately"
        ]
    ):
        return "Sad"

    if any(
        x in t
        for x in [
            "worried",
            "nervous",
            "scared"
        ]
    ):
        return "Nervous"

    if any(
        x in t
        for x in [
            "great",
            "good",
            "nice",
            "love"
        ]
    ):
        return "Happy"

    return "Neutral"


def detect_gesture(text, emotion):

    t = text.lower()

    if any(
        x in t
        for x in [
            "look",
            "there",
            "that",
            "this"
        ]
    ):
        return "Point"

    if any(
        x in t
        for x in [
            "hello",
            "hi",
            "hey",
            "bye"
        ]
    ):
        return "Wave"

    if emotion == "Thinking":
        return "Think"

    if emotion == "Laughing":
        return "Laugh"

    if emotion == "Nervous":
        return "Nervous"

    if emotion == "Annoyed":
        return "Cross Arms"

    if emotion == "Excited":
        return "Hands Up"

    return "Natural"


def estimate_duration(text, pace):

    words = max(
        1,
        len(text.split())
    )

    rates = {
        "Natural": 2.6,
        "Comedic": 2.25,
        "Calm": 2.05,
        "Fast": 3.15
    }

    return max(
        1.8,
        words / rates[pace] + 0.6
    )


# ============================================================
# STAGE SYSTEM
# ============================================================

def stage_positions(cast):

    count = len(cast)

    if count == 1:
        return {
            cast[0]: 640
        }

    if count == 2:
        return {
            cast[0]: 400,
            cast[1]: 880
        }

    if count == 3:
        return {
            cast[0]: 260,
            cast[1]: 640,
            cast[2]: 1020
        }

    positions = {}

    spacing = 1000 / max(
        1,
        count - 1
    )

    for i, name in enumerate(cast):

        positions[name] = (
            140 + spacing * i
        )

    return positions


# ============================================================
# BACKGROUND ENGINE
# ============================================================

def draw_background(draw, location):

    draw.rectangle(
        [0, 0, WIDTH, HEIGHT],
        fill=(190, 218, 238)
    )

    # ground

    draw.rectangle(
        [0, 485, WIDTH, HEIGHT],
        fill=(112, 145, 105)
    )

    # indoor locations

    indoor = [
        "Apartment",
        "Bedroom",
        "Kitchen",
        "Classroom",
        "Office",
        "Pharmacy",
        "Restaurant",
        "Corner Shop"
    ]

    if location in indoor:

        draw.rectangle(
            [25, 55, WIDTH - 25, 485],
            fill=(235, 225, 210),
            outline=(55, 55, 60),
            width=5
        )

        # window

        draw.rectangle(
            [90, 100, 320, 275],
            fill=(145, 203, 230),
            outline=(65, 70, 75),
            width=4
        )

        draw.line(
            [205, 100, 205, 275],
            fill=(65, 70, 75),
            width=3
        )

        draw.line(
            [90, 188, 320, 188],
            fill=(65, 70, 75),
            width=3
        )

        if location == "Office":

            draw.rectangle(
                [370, 360, 910, 445],
                fill=(105, 74, 54)
            )

        elif location == "Classroom":

            draw.rectangle(
                [440, 170, 840, 290],
                fill=(74, 125, 160),
                outline=(50, 55, 60),
                width=4
            )

        elif location == "Restaurant":

            draw.ellipse(
                [380, 355, 900, 475],
                fill=(126, 84, 58),
                outline=(70, 48, 36),
                width=4
            )

        elif location == "Pharmacy":

            draw.rectangle(
                [430, 300, 850, 410],
                fill=(220, 225, 228),
                outline=(70, 70, 75),
                width=4
            )

            draw.text(
                [525, 332],
                "PHARMACY",
                font=get_font(32, True),
                fill=(55, 60, 65)
            )

        elif location == "Kitchen":

            draw.rectangle(
                [400, 340, 900, 460],
                fill=(155, 157, 160),
                outline=(70, 70, 75),
                width=4
            )

            draw.rectangle(
                [470, 220, 600, 340],
                fill=(180, 180, 180),
                outline=(70, 70, 75),
                width=4
            )

        elif location == "Bedroom":

            draw.rectangle(
                [420, 330, 870, 470],
                fill=(130, 100, 90),
                outline=(70, 60, 60),
                width=4
            )

        elif location == "Corner Shop":

            draw.rectangle(
                [400, 260, 880, 455],
                fill=(220, 220, 205),
                outline=(60, 60, 65),
                width=4
            )

    elif location == "Street":

        draw.rectangle(
            [0, 405, WIDTH, 490],
            fill=(72, 77, 85)
        )

        draw.line(
            [0, 447, WIDTH, 447],
            fill=(235, 205, 90),
            width=5
        )

        for x in range(50, WIDTH, 260):

            draw.rectangle(
                [x, 140, x + 150, 405],
                fill=(157, 151, 148),
                outline=(65, 65, 70),
                width=3
            )

    elif location == "Park":

        for x in [130, 1080]:

            draw.rectangle(
                [x, 220, x + 30, 490],
                fill=(104, 69, 43)
            )

            draw.ellipse(
                [x - 95, 100, x + 120, 300],
                fill=(65, 142, 72)
            )

    elif location == "Rooftop":

        draw.rectangle(
            [0, 370, WIDTH, 490],
            fill=(100, 105, 115)
        )

        draw.line(
            [0, 370, WIDTH, 370],
            fill=(45, 48, 55),
            width=8
        )

    else:

        draw.rectangle(
            [0, 420, WIDTH, 490],
            fill=(85, 88, 94)
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
    emotion,
    gesture,
    posture,
    talking=False,
    look_at=None,
    scale=1.0,
    seed=0
):

    c = CHARACTERS[name]

    # --------------------------------------------------------
    # IMPORTANT:
    # X POSITION NEVER CHANGES BECAUSE OF SPEAKING.
    # --------------------------------------------------------

    base_x = x

    # very subtle idle breathing only

    breathe = (
        math.sin(
            frame / 18 + seed
        ) * 2
    )

    ground = ground + breathe

    # subtle lean

    lean = 0

    if posture == "Leaning":

        lean = 10

    # body dimensions

    if c["body"] == "round":

        torso_w = 72
        torso_h = 145

    elif c["body"] == "tall":

        torso_w = 60
        torso_h = 170

    elif c["body"] == "athletic":

        torso_w = 70
        torso_h = 155

    else:

        torso_w = 60
        torso_h = 150

    head_r = int(
        57 * scale
    )

    if posture == "Sitting":

        head_y = ground - 275

        torso_top = head_y + 60

        torso_bottom = ground - 90

    else:

        head_y = ground - 315

        torso_top = head_y + 60

        torso_bottom = ground - 65

    # --------------------------------------------------------
    # SHADOW
    # --------------------------------------------------------

    draw.ellipse(
        [
            base_x - 80,
            ground - 2,
            base_x + 80,
            ground + 20
        ],
        fill=(70, 74, 72)
    )

    # --------------------------------------------------------
    # LEGS
    # --------------------------------------------------------

    if posture == "Sitting":

        draw.line(
            [
                base_x - 25,
                torso_bottom,
                base_x - 75,
                ground - 35
            ],
            fill=c["pants"],
            width=17
        )

        draw.line(
            [
                base_x + 25,
                torso_bottom,
                base_x + 75,
                ground - 35
            ],
            fill=c["pants"],
            width=17
        )

    else:

        draw.line(
            [
                base_x - 22,
                torso_bottom,
                base_x - 34,
                ground
            ],
            fill=c["pants"],
            width=17
        )

        draw.line(
            [
                base_x + 22,
                torso_bottom,
                base_x + 34,
                ground
            ],
            fill=c["pants"],
            width=17
        )

    # --------------------------------------------------------
    # SHOES
    # --------------------------------------------------------

    draw.ellipse(
        [
            base_x - 62,
            ground - 6,
            base_x - 2,
            ground + 18
        ],
        fill=c["shoes"]
    )

    draw.ellipse(
        [
            base_x + 2,
            ground - 6,
            base_x + 62,
            ground + 18
        ],
        fill=c["shoes"]
    )

    # --------------------------------------------------------
    # TORSO
    # --------------------------------------------------------

    draw.rounded_rectangle(
        [
            base_x - torso_w,
            torso_top,
            base_x + torso_w,
            torso_bottom
        ],
        radius=28,
        fill=c["shirt"],
        outline=(45, 45, 50),
        width=4
    )

    # accent

    draw.line(
        [
            base_x - torso_w + 12,
            torso_top + 45,
            base_x + torso_w - 12,
            torso_top + 45
        ],
        fill=c["accent"],
        width=6
    )

    # --------------------------------------------------------
    # NECK
    # --------------------------------------------------------

    draw.rectangle(
        [
            base_x - 17,
            head_y + 42,
            base_x + 17,
            head_y + 78
        ],
        fill=c["skin"]
    )

    # --------------------------------------------------------
    # ARM POSE
    # --------------------------------------------------------

    arm_y = torso_top + 60

    left_shoulder = (
        base_x - torso_w + 5,
        arm_y
    )

    right_shoulder = (
        base_x + torso_w - 5,
        arm_y
    )

    # Natural movement

    wave = math.sin(
        frame / 7 + seed
    )

    left_hand = (
        base_x - 105,
        arm_y + int(wave * 12)
    )

    right_hand = (
        base_x + 105,
        arm_y - int(wave * 12)
    )

    if gesture == "Point":

        right_hand = (
            base_x + 135,
            arm_y - 35
        )

        left_hand = (
            base_x - 90,
            arm_y + 45
        )

    elif gesture == "Wave":

        right_hand = (
            base_x + 70,
            arm_y - 90 +
            int(wave * 15)
        )

        left_hand = (
            base_x - 90,
            arm_y + 35
        )

    elif gesture == "Think":

        right_hand = (
            base_x + 52,
            head_y + 35
        )

        left_hand = (
            base_x - 70,
            arm_y + 35
        )

    elif gesture == "Shrug":

        right_hand = (
            base_x + 105,
            arm_y - 35
        )

        left_hand = (
            base_x - 105,
            arm_y - 35
        )

    elif gesture == "Cross Arms":

        right_hand = (
            base_x - 20,
            arm_y + 55
        )

        left_hand = (
            base_x + 20,
            arm_y + 55
        )

    elif gesture == "Hands Up":

        right_hand = (
            base_x + 80,
            arm_y - 75
        )

        left_hand = (
            base_x - 80,
            arm_y - 75
        )

    elif gesture == "Laugh":

        right_hand = (
            base_x + 75,
            arm_y + 15
        )

        left_hand = (
            base_x - 75,
            arm_y + 15
        )

    elif gesture == "Nervous":

        right_hand = (
            base_x + 60,
            arm_y + 75
        )

        left_hand = (
            base_x - 60,
            arm_y + 75
        )

    elif gesture == "None":

        right_hand = (
            base_x + 50,
            torso_bottom - 5
        )

        left_hand = (
            base_x - 50,
            torso_bottom - 5
        )

    # --------------------------------------------------------
    # DRAW LEFT ARM
    # --------------------------------------------------------

    left_mid = (
        int(
            (left_shoulder[0] +
             left_hand[0]) / 2
        ),
        int(
            (left_shoulder[1] +
             left_hand[1]) / 2
        )
    )

    draw.line(
        [
            left_shoulder,
            left_mid,
            left_hand
        ],
        fill=c["shirt"],
        width=22
    )

    # --------------------------------------------------------
    # DRAW RIGHT ARM
    # --------------------------------------------------------

    right_mid = (
        int(
            (right_shoulder[0] +
             right_hand[0]) / 2
        ),
        int(
            (right_shoulder[1] +
             right_hand[1]) / 2
        )
    )

    draw.line(
        [
            right_shoulder,
            right_mid,
            right_hand
        ],
        fill=c["shirt"],
        width=22
    )

    # --------------------------------------------------------
    # HANDS
    # --------------------------------------------------------

    for hx, hy in [
        left_hand,
        right_hand
    ]:

        draw.ellipse(
            [
                hx - 14,
                hy - 14,
                hx + 14,
                hy + 14
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
            base_x - head_r + lean,
            head_y - head_r,
            base_x + head_r + lean,
            head_y + head_r
        ],
        fill=c["skin"],
        outline=(48, 40, 38),
        width=4
    )

    face_x = base_x + lean

    # --------------------------------------------------------
    # HAIR STYLES
    # --------------------------------------------------------

    style = c["hair_style"]

    if style == "curly":

        for dx, dy, r in [
            (-42, -43, 24),
            (-15, -55, 27),
            (15, -55, 27),
            (43, -40, 23),
            (-52, -12, 18),
            (52, -10, 18)
        ]:

            draw.ellipse(
                [
                    face_x + dx - r,
                    head_y + dy - r,
                    face_x + dx + r,
                    head_y + dy + r
                ],
                fill=c["hair"]
            )

    elif style == "spiky":

        points = [
            (
                face_x - 50,
                head_y - 25
            ),
            (
                face_x - 30,
                head_y - 75
            ),
            (
                face_x - 8,
                head_y - 45
            ),
            (
                face_x + 10,
                head_y - 82
            ),
            (
                face_x + 32,
                head_y - 45
            ),
            (
                face_x + 58,
                head_y - 70
            ),
            (
                face_x + 52,
                head_y - 5
            ),
            (
                face_x - 50,
                head_y - 5
            )
        ]

        draw.polygon(
            points,
            fill=c["hair"]
        )

    elif style == "wild":

        draw.ellipse(
            [
                face_x - 65,
                head_y - 70,
                face_x + 65,
                head_y + 5
            ],
            fill=c["hair"]
        )

        for dx in range(
            -50,
            60,
            25
        ):

            draw.line(
                [
                    face_x + dx,
                    head_y - 55,
                    face_x + dx - 8,
                    head_y - 90
                ],
                fill=c["hair"],
                width=12
            )

    elif style == "long":

        draw.ellipse(
            [
                face_x - 60,
                head_y - 65,
                face_x + 60,
                head_y + 5
            ],
            fill=c["hair"]
        )

        draw.rectangle(
            [
                face_x - 58,
                head_y - 10,
                face_x - 30,
                head_y + 80
            ],
            fill=c["hair"]
        )

        draw.rectangle(
            [
                face_x + 30,
                head_y - 10,
                face_x + 58,
                head_y + 80
            ],
            fill=c["hair"]
        )

    else:

        draw.ellipse(
            [
                face_x - 58,
                head_y - 65,
                face_x + 58,
                head_y - 2
            ],
            fill=c["hair"]
        )

    # side hairstyle

    if style == "side":

        draw.ellipse(
            [
                face_x - 50,
                head_y - 60,
                face_x + 62,
                head_y - 5
            ],
            fill=c["hair"]
        )

        draw.polygon(
            [
                (
                    face_x + 25,
                    head_y - 55
                ),
                (
                    face_x + 70,
                    head_y - 20
                ),
                (
                    face_x + 15,
                    head_y - 15
                )
            ],
            fill=c["hair"]
        )

    # --------------------------------------------------------
    # EYE DIRECTION
    # --------------------------------------------------------

    eye_shift = 0

    if look_at is not None:

        eye_shift = max(
            -6,
            min(
                6,
                int(
                    (look_at - base_x) / 100
                )
            )
        )

    blink = (
        (frame + seed * 19) % 100
        < 3
    )

    eye_y = head_y - 12

    if blink:

        draw.line(
            [
                face_x - 35,
                eye_y,
                face_x - 10,
                eye_y
            ],
            fill=(35, 30, 30),
            width=4
        )

        draw.line(
            [
                face_x + 10,
                eye_y,
                face_x + 35,
                eye_y
            ],
            fill=(35, 30, 30),
            width=4
        )

    else:

        for ex in [
            face_x - 24,
            face_x + 24
        ]:

            draw.ellipse(
                [
                    ex - 10 + eye_shift,
                    eye_y - 9,
                    ex + 10 + eye_shift,
                    eye_y + 9
                ],
                fill=(245, 245, 240),
                outline=(40, 40, 42),
                width=2
            )

            draw.ellipse(
                [
                    ex - 4 + eye_shift,
                    eye_y - 4,
                    ex + 4 + eye_shift,
                    eye_y + 4
                ],
                fill=(25, 25, 28)
            )

    # --------------------------------------------------------
    # EYEBROWS
    # --------------------------------------------------------

    brow_y = head_y - 38

    if emotion in [
        "Surprised",
        "Excited"
    ]:

        brow_y -= 8

    if emotion == "Annoyed":

        draw.line(
            [
                face_x - 42,
                brow_y + 7,
                face_x - 10,
                brow_y - 3
            ],
            fill=(48, 35, 30),
            width=5
        )

        draw.line(
            [
                face_x + 10,
                brow_y - 3,
                face_x + 42,
                brow_y + 7
            ],
            fill=(48, 35, 30),
            width=5
        )

    else:

        draw.line(
            [
                face_x - 40,
                brow_y,
                face_x - 10,
                brow_y - 2
            ],
            fill=(48, 35, 30),
            width=4
        )

        draw.line(
            [
                face_x + 10,
                brow_y - 2,
                face_x + 40,
                brow_y
            ],
            fill=(48, 35, 30),
            width=4
        )

    # --------------------------------------------------------
    # MOUTH / SPEECH ANIMATION
    # --------------------------------------------------------

    mouth_y = head_y + 36

    if talking:

        mouth_phase = frame % 10

        if mouth_phase < 3:

            draw.line(
                [
                    face_x - 18,
                    mouth_y + 8,
                    face_x + 18,
                    mouth_y + 8
                ],
                fill=(78, 28, 32),
                width=4
            )

        elif mouth_phase < 6:

            draw.ellipse(
                [
                    face_x - 14,
                    mouth_y,
                    face_x + 14,
                    mouth_y + 17
                ],
                fill=(78, 28, 32)
            )

        else:

            draw.ellipse(
                [
                    face_x - 18,
                    mouth_y - 2,
                    face_x + 18,
                    mouth_y + 23
                ],
                fill=(78, 28, 32)
            )

    elif emotion in [
        "Happy",
        "Excited",
        "Laughing"
    ]:

        draw.arc(
            [
                face_x - 27,
                mouth_y - 8,
                face_x + 27,
                mouth_y + 27
            ],
            0,
            180,
            fill=(78, 28, 32),
            width=5
        )

    elif emotion == "Surprised":

        draw.ellipse(
            [
                face_x - 14,
                mouth_y - 2,
                face_x + 14,
                mouth_y + 25
            ],
            fill=(78, 28, 32)
        )

    else:

        draw.line(
            [
                face_x - 17,
                mouth_y + 7,
                face_x + 17,
                mouth_y + 7
            ],
            fill=(78, 28, 32),
            width=4
        )


# ============================================================
# LISTENER PERFORMANCE
# ============================================================

def listener_emotion(speaker_emotion, frame):

    # reactions are subtle and periodic

    reaction_window = (
        frame % 144
    )

    if reaction_window > 112:

        if speaker_emotion == "Surprised":
            return "Surprised"

        if speaker_emotion == "Funny":
            return "Laughing"

        if speaker_emotion == "Annoyed":
            return "Confused"

        if speaker_emotion == "Excited":
            return "Happy"

        if speaker_emotion == "Confused":
            return "Thinking"

    return "Neutral"


# ============================================================
# SUBTITLE ENGINE
# ============================================================

def subtitle_words(text):

    words = text.split()

    return words


def draw_subtitles(
    draw,
    text,
    frame,
    total_frames,
    speaker
):

    words = subtitle_words(text)

    if not words:
        return

    progress = frame / max(
        1,
        total_frames - 1
    )

    visible = max(
        1,
        min(
            len(words),
            int(
                progress *
                (len(words) + 1)
            )
        )
    )

    current = " ".join(
        words[:visible]
    )

    # --------------------------------------------------------
    # BOTTOM SUBTITLE BAR
    # --------------------------------------------------------

    bar_top = 585
    bar_bottom = 675

    draw.rounded_rectangle(
        [
            95,
            bar_top,
            WIDTH - 95,
            bar_bottom
        ],
        radius=18,
        fill=(15, 15, 18),
        outline=(255, 255, 255),
        width=2
    )

    # speaker name

    name_width = draw.textbbox(
        (0, 0),
        speaker,
        font=get_font(20, True)
    )[2]

    draw.rounded_rectangle(
        [
            115,
            bar_top - 28,
            135 + name_width,
            bar_top + 5
        ],
        radius=8,
        fill=(235, 91, 76)
    )

    draw.text(
        [
            125,
            bar_top - 24
        ],
        speaker,
        font=get_font(18, True),
        fill=(255, 255, 255)
    )

    # subtitle wrapping

    if len(current) > 72:

        midpoint = len(
            current
        ) // 2

        space = current.rfind(
            " ",
            0,
            midpoint
        )

        if space < 1:

            space = midpoint

        lines = [
            current[:space],
            current[space + 1:]
        ]

    else:

        lines = [current]

    y = 610

    for line in lines:

        bbox = draw.textbbox(
            (0, 0),
            line,
            font=get_font(26, True)
        )

        tw = bbox[2] - bbox[0]

        x = (
            WIDTH - tw
        ) // 2

        draw.text(
            [x, y],
            line,
            font=get_font(26, True),
            fill=(255, 255, 255)
        )

        y += 31


# ============================================================
# FRAME ENGINE
# ============================================================

def render_frame(
    scene,
    project,
    frame
):

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        (220, 220, 220)
    )

    draw = ImageDraw.Draw(
        image
    )

    location = scene[
        "location"
    ]

    draw_background(
        draw,
        location
    )

    cast = project[
        "cast"
    ]

    positions = stage_positions(
        cast
    )

    speaker = scene[
        "speaker"
    ]

    listeners = [
        name
        for name in cast
        if name != speaker
    ]

    # --------------------------------------------------------
    # CAMERA
    #
    # Camera changes framing, NOT character stage positions.
    # --------------------------------------------------------

    camera = scene[
        "camera"
    ]

    camera_scale = 1.0
    camera_offset = 0

    if camera == "Speaker Close":

        camera_scale = 1.08

    elif camera == "Listener Close":

        camera_scale = 1.06

    elif camera == "Close Up":

        camera_scale = 1.12

    # --------------------------------------------------------
    # DRAW CHARACTERS
    # --------------------------------------------------------

    for index, name in enumerate(cast):

        x = positions[name]

        expression = "Neutral"
        gesture = "None"
        talking = False

        if name == speaker:

            expression = scene[
                "emotion"
            ]

            gesture = scene[
                "gesture"
            ]

            talking = True

        else:

            expression = listener_emotion(
                scene["emotion"],
                frame
            )

            # listeners mostly remain still

            if frame % 160 > 125:

                gesture = "Think"

        draw_character(
            draw=draw,
            name=name,
            x=x,
            ground=620,
            frame=frame,
            emotion=expression,
            gesture=gesture,
            posture=scene[
                "posture"
            ],
            talking=talking,
            look_at=positions[
                speaker
            ]
            if name != speaker
            else (
                positions[
                    listeners[0]
                ]
                if listeners
                else None
            ),
            scale=camera_scale,
            seed=index + 10
        )

    # --------------------------------------------------------
    # SUBTITLES AT BOTTOM
    # --------------------------------------------------------

    draw_subtitles(
        draw,
        scene["dialogue"],
        frame,
        scene["frames"],
        speaker
    )

    # --------------------------------------------------------
    # SMALL SCENE LABEL
    # --------------------------------------------------------

    draw.text(
        [25, 20],
        project["name"],
        font=get_font(20, True),
        fill=(40, 40, 45)
    )

    return image


# ============================================================
# VOICE ENGINE
# ============================================================

async def create_voice(
    text,
    voice,
    output
):

    import edge_tts

    communicator = edge_tts.Communicate(
        text,
        voice
    )

    await communicator.save(
        str(output)
    )


def generate_voice(
    text,
    character,
    output
):

    voice = CHARACTERS[
        character
    ]["voice"]

    try:

        asyncio.run(
            create_voice(
                text,
                voice,
                output
            )
        )

        if (
            output.exists()
            and
            output.stat().st_size > 1000
        ):

            return True

    except Exception:

        pass

    return False


# ============================================================
# AUDIO DURATION
# ============================================================

def get_duration(path):

    ffmpeg = (
        imageio_ffmpeg
        .get_ffmpeg_exe()
    )

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
        result.stderr or ""
    )

    match = re.search(
        r"Duration:\s*(\d+):(\d+):([\d.]+)",
        text
    )

    if not match:

        return 3.0

    return (
        int(match.group(1)) * 3600
        +
        int(match.group(2)) * 60
        +
        float(match.group(3))
    )


# ============================================================
# RENDER EPISODE
# ============================================================

def render_episode(
    scenes,
    project,
    progress
):

    job = ROOT / (
        "render_" +
        str(os.getpid())
    )

    frame_dir = job / "frames"
    audio_dir = job / "audio"

    job.mkdir(
        exist_ok=True
    )

    frame_dir.mkdir()
    audio_dir.mkdir()

    output = ROOT / (
        "cartoon_v5_" +
        str(os.getpid()) +
        ".mp4"
    )

    try:

        # ----------------------------------------------------
        # GENERATE VOICE FOR EVERY SCENE
        # ----------------------------------------------------

        voice_files = []

        for i, scene in enumerate(
            scenes
        ):

            voice_file = (
                audio_dir /
                f"voice_{i}.mp3"
            )

            ok = generate_voice(
                scene["dialogue"],
                scene["speaker"],
                voice_file
            )

            if ok:

                duration = get_duration(
                    voice_file
                )

            else:

                duration = estimate_duration(
                    scene["dialogue"],
                    project["pace"]
                )

                # Silent fallback

                voice_file = (
                    audio_dir /
                    f"silent_{i}.wav"
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

            scene["duration"] = (
                max(
                    1.8,
                    duration + 0.25
                )
            )

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

            progress(
                0.15 *
                (
                    (i + 1) /
                    len(scenes)
                ),
                "Generating voices..."
            )

        # ----------------------------------------------------
        # RENDER ANIMATION FRAMES
        # ----------------------------------------------------

        total_frames = sum(
            s["frames"]
            for s in scenes
        )

        completed = 0
        frame_number = 0

        for scene in scenes:

            for frame in range(
                scene["frames"]
            ):

                image = render_frame(
                    scene,
                    project,
                    frame
                )

                image.save(
                    frame_dir /
                    f"frame_{frame_number:07d}.png"
                )

                frame_number += 1
                completed += 1

                progress(
                    0.15 +
                    0.55 *
                    (
                        completed /
                        total_frames
                    ),
                    "Animating scenes..."
                )

        ffmpeg = (
            imageio_ffmpeg
            .get_ffmpeg_exe()
        )

        # ----------------------------------------------------
        # VIDEO
        # ----------------------------------------------------

        silent_video = (
            job /
            "video.mp4"
        )

        result = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-framerate",
                str(FPS),
                "-i",
                str(
                    frame_dir /
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

            return None, result.stderr[-3000:]

        progress(
            0.78,
            "Building audio..."
        )

        # ----------------------------------------------------
        # JOIN AUDIO
        # ----------------------------------------------------

        manifest = (
            job /
            "audio.txt"
        )

        manifest.write_text(
            "\n".join(
                [
                    f"file '{f.as_posix()}'"
                    for f in voice_files
                ]
            )
        )

        joined_audio = (
            job /
            "audio.mp3"
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
                "-vn",
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

            return None, result.stderr[-3000:]

        progress(
            0.90,
            "Combining animation and voices..."
        )

        # ----------------------------------------------------
        # FINAL MP4
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

            return None, result.stderr[-3000:]

        progress(
            1.0,
            "Finished!"
        )

        return output, None

    finally:

        shutil.rmtree(
            job,
            ignore_errors=True
        )


# ============================================================
# VIDEO JOINER
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

        ffmpeg = (
            imageio_ffmpeg
            .get_ffmpeg_exe()
        )

        clips = []

        for i, uploaded in enumerate(
            files
        ):

            source = (
                job /
                f"source_{i}.mp4"
            )

            normalized = (
                job /
                f"clip_{i}.mp4"
            )

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

        manifest = (
            job /
            "videos.txt"
        )

        manifest.write_text(
            "\n".join(
                [
                    f"file '{x.as_posix()}'"
                    for x in clips
                ]
            )
        )

        output = ROOT / (
            "cartoon_episode_" +
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
# DEFAULT PROJECT
# ============================================================

if "project" not in st.session_state:

    st.session_state.project = {
        "name": "My Cartoon Episode",
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
    "🎬 Cartoon Studio V5"
)

st.caption(
    "A 2D cartoon animation engine — "
    "characters, acting, voices, subtitles and scenes."
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header(
        "🎨 Episode"
    )

    st.session_state.project["name"] = st.text_input(
        "Episode title",
        st.session_state.project["name"]
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
        "### V5 Animation Engine"
    )

    st.write(
        "🧍 Fixed stage positions\n\n"
        "🤲 Full hands and arms\n\n"
        "👀 Eye movement\n\n"
        "😄 Expressions\n\n"
        "🫁 Idle animation\n\n"
        "🗣️ Talking animation\n\n"
        "🎭 Gestures\n\n"
        "🪑 Sitting/standing\n\n"
        "🎙️ Character voices\n\n"
        "💬 Voice-timed subtitles\n\n"
        "🎥 Cinematic framing"
    )


# ============================================================
# TABS
# ============================================================

create_tab, stage_tab, render_tab, join_tab, save_tab = st.tabs(
    [
        "✨ Create",
        "🎭 Stage & Acting",
        "🎬 Render",
        "🔗 Join Videos",
        "💾 Project"
    ]
)


# ============================================================
# CREATE TAB
# ============================================================

with create_tab:

    st.subheader(
        "Choose your cast"
    )

    selected = st.multiselect(
        "Characters",
        list(CHARACTERS.keys()),
        default=st.session_state.project["cast"],
        max_selections=4
    )

    if len(selected) < 1:

        st.warning(
            "Select at least one character."
        )

    else:

        st.session_state.project[
            "cast"
        ] = selected

        cols = st.columns(
            min(
                4,
                len(selected)
            )
        )

        for i, name in enumerate(
            selected
        ):

            with cols[i]:

                c = CHARACTERS[name]

                st.markdown(
                    f"**{name}**"
                )

                st.caption(
                    c["personality"]
                    .capitalize()
                )

    st.divider()

    st.subheader(
        "📝 Write your cartoon script"
    )

    script = st.text_area(
        "Use Character: dialogue format",
        height=300,
        placeholder=(
            "Zuri Spark: Milo, why are you "
            "staring at the microwave?\n\n"
            "Milo Quirk: I'm waiting for it "
            "to finish.\n\n"
            "Zuri Spark: It already says zero "
            "seconds.\n\n"
            "Milo Quirk: Exactly. I'm giving "
            "it time to think."
        )
    )

    if st.button(
        "🧠 Build Animation",
        type="primary",
        use_container_width=True
    ):

        parsed = parse_script(
            script
        )

        cast = (
            st.session_state.project[
                "cast"
            ]
        )

        if not parsed:

            st.error(
                "No dialogue was detected."
            )

        elif not cast:

            st.error(
                "Choose some characters."
            )

        else:

            scenes = []

            for i, row in enumerate(
                parsed
            ):

                speaker = row[
                    "speaker"
                ]

                # Unknown names automatically
                # use a selected cast member.

                if speaker not in cast:

                    speaker = cast[
                        i % len(cast)
                    ]

                dialogue = row[
                    "dialogue"
                ]

                emotion = detect_emotion(
                    dialogue
                )

                gesture = detect_gesture(
                    dialogue,
                    emotion
                )

                scenes.append(
                    {
                        "id": i + 1,
                        "speaker": speaker,
                        "dialogue": dialogue,
                        "emotion": emotion,
                        "gesture": gesture,
                        "posture": "Standing",
                        "camera": "Two Shot",
                        "location":
                            st.session_state
                            .project[
                                "location"
                            ],
                        "duration":
                            estimate_duration(
                                dialogue,
                                st.session_state
                                .project[
                                    "pace"
                                ]
                            )
                    }
                )

            st.session_state.scenes = scenes

            st.success(
                f"{len(scenes)} scenes created."
            )


# ============================================================
# STAGE / ACTING
# ============================================================

with stage_tab:

    st.subheader(
        "🎭 Direct your characters"
    )

    if not st.session_state.scenes:

        st.info(
            "Build a script first."
        )

    else:

        st.info(
            "Characters remain in their "
            "assigned stage positions. "
            "Speaking does NOT move them."
        )

        for scene in st.session_state.scenes:

            with st.expander(
                f"Scene {scene['id']} — "
                f"{scene['speaker']}"
            ):

                st.write(
                    f"**{scene['dialogue']}**"
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
                        index=POSTURES.index(
                            scene["posture"]
                        ),
                        key=f"posture_{scene['id']}"
                    )

                    scene["camera"] = st.selectbox(
                        "Camera",
                        CAMERAS,
                        index=CAMERAS.index(
                            scene["camera"]
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
                        "Minimum duration",
                        min_value=1.5,
                        max_value=20.0,
                        value=float(
                            scene["duration"]
                        ),
                        step=0.5,
                        key=f"duration_{scene['id']}"
                    )


# ============================================================
# RENDER TAB
# ============================================================

with render_tab:

    st.subheader(
        "🎬 Render V5"
    )

    if not st.session_state.scenes:

        st.info(
            "Create an animation first."
        )

    else:

        st.write(
            f"Ready to render "
            f"{len(st.session_state.scenes)} scenes."
        )

        progress_bar = st.progress(
            0
        )

        status = st.empty()

        if st.button(
            "🚀 Render Cartoon",
            type="primary",
            use_container_width=True
        ):

            def update_progress(
                value,
                message
            ):

                progress_bar.progress(
                    min(
                        1.0,
                        value
                    )
                )

                status.info(
                    message
                )

            with st.spinner(
                "Building your cartoon..."
            ):

                result, error = render_episode(
                    st.session_state.scenes,
                    st.session_state.project,
                    update_progress
                )

            if result:

                st.session_state[
                    "output"
                ] = str(result)

                status.success(
                    "🎉 Cartoon completed!"
                )

            else:

                status.error(
                    "Rendering failed."
                )

                if error:

                    st.code(
                        error
                    )

        output = st.session_state.get(
            "output"
        )

        if output and Path(
            output
        ).exists():

            st.video(
                output
            )

            st.download_button(
                "⬇️ Download Cartoon",
                Path(
                    output
                ).read_bytes(),
                "cartoon_v5.mp4",
                "video/mp4",
                use_container_width=True
            )


# ============================================================
# JOIN VIDEOS TAB
# ============================================================

with join_tab:

    st.subheader(
        "🔗 Build a long episode"
    )

    st.write(
        "Upload several short cartoon clips. "
        "They will be combined in the order shown."
    )

    uploads = st.file_uploader(
        "Upload MP4 clips",
        type=[
            "mp4",
            "mov",
            "m4v"
        ],
        accept_multiple_files=True
    )

    if uploads:

        for i, item in enumerate(
            uploads
        ):

            st.write(
                f"**{i + 1}.** {item.name}"
            )

        if st.button(
            "🔗 Join Into Full Episode",
            type="primary",
            use_container_width=True
        ):

            with st.spinner(
                "Joining clips..."
            ):

                result, error = join_videos(
                    uploads
                )

            if result:

                st.session_state[
                    "joined"
                ] = str(result)

                st.success(
                    "Full episode created!"
                )

            else:

                st.error(
                    error or
                    "Could not join the videos."
                )

    joined = st.session_state.get(
        "joined"
    )

    if joined and Path(
        joined
    ).exists():

        st.video(
            joined
        )

        st.download_button(
            "⬇️ Download Full Episode",
            Path(
                joined
            ).read_bytes(),
            "cartoon_full_episode.mp4",
            "video/mp4",
            use_container_width=True
        )


# ============================================================
# PROJECT TAB
# ============================================================

with save_tab:

    st.subheader(
        "💾 Project"
    )

    project_data = {
        "version": "5.0",
        "project":
            st.session_state.project,
        "scenes":
            st.session_state.scenes
    }

    st.json(
        {
            "version": "5.0",
            "episode":
                st.session_state.project[
                    "name"
                ],
            "characters":
                st.session_state.project[
                    "cast"
                ],
            "scenes":
                len(
                    st.session_state.scenes
                )
        }
    )

    st.download_button(
        "💾 Save Project",
        json.dumps(
            project_data,
            indent=2
        ),
        "cartoon_project_v5.json",
        "application/json",
        use_container_width=True
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Cartoon Studio V5 • "
    "Original 2D characters • "
    "Fixed stage positions • "
    "Acting • Voices • Subtitles • "
    "Video joining"
)
