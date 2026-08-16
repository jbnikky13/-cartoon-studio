import streamlit as st
from pathlib import Path
import tempfile
import subprocess
import shutil
import re
import os
import json
import math
import random
import wave
import struct
import asyncio
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

try:
    import sprite_renderer as SPRITE
    SPRITE_AVAILABLE = True
except Exception:
    SPRITE_AVAILABLE = False

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False


# ============================================================
# CARTOON STUDIO V4
# Performance-first 2D Cartoon Video Maker
# ============================================================

st.set_page_config(
    page_title="Cartoon Studio V4",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

ROOT = Path(tempfile.gettempdir()) / "cartoon_studio_v4"
ROOT.mkdir(exist_ok=True)

FPS = 24
W = 1280
H = 720


# ============================================================
# COLOR SHADING HELPERS
# (cheap cel-shading: precompute a darker/lighter flat
# tone instead of alpha blending, so it works directly
# with PIL's solid-fill draw calls)
# ============================================================

def shade(color, amount):
    """amount < 0 darkens, amount > 0 lightens."""

    r, g, b = color

    if amount >= 0:
        r = r + (255 - r) * amount
        g = g + (255 - g) * amount
        b = b + (255 - b) * amount
    else:
        r = r * (1 + amount)
        g = g * (1 + amount)
        b = b * (1 + amount)

    return (
        int(max(0, min(255, r))),
        int(max(0, min(255, g))),
        int(max(0, min(255, b)))
    )


def blend(color_a, color_b, t):
    """Mix two RGB colors, t=0 -> color_a, t=1 -> color_b."""

    return tuple(
        int(a + (b - a) * t)
        for a, b in zip(color_a, color_b)
    )


# ============================================================
# ORIGINAL CHARACTERS
# ============================================================

CHARACTERS = {
    "Zuri Spark": {
        "tag": "Fast-talking optimist",
        "skin": (137, 87, 65),
        "hair": (42, 27, 25),
        "shirt": (235, 91, 76),
        "pants": (46, 55, 76),
        "outfit": "hoodie",
        "hair_style": "afro",
        "accent": "★",
        "tts_voice": "en-US-AriaNeural",
        "voice": "bright"
    },

    "Milo Quirk": {
        "tag": "Deadpan problem-solver",
        "skin": (177, 119, 87),
        "hair": (55, 39, 29),
        "shirt": (63, 145, 183),
        "pants": (48, 55, 72),
        "outfit": "collar_shirt",
        "hair_style": "short",
        "accent": "◇",
        "tts_voice": "en-US-DavisNeural",
        "voice": "calm"
    },

    "Kemi Bolt": {
        "tag": "Fearless tinkerer",
        "skin": (108, 70, 54),
        "hair": (30, 23, 20),
        "shirt": (235, 168, 58),
        "pants": (55, 64, 76),
        "outfit": "jacket",
        "hair_style": "ponytail",
        "accent": "⚡",
        "tts_voice": "en-US-JennyNeural",
        "voice": "energetic"
    },

    "Tari Reed": {
        "tag": "Calm observer",
        "skin": (157, 99, 73),
        "hair": (45, 29, 26),
        "shirt": (92, 171, 132),
        "pants": (50, 61, 76),
        "outfit": "vneck",
        "hair_style": "bun",
        "accent": "○",
        "tts_voice": "en-US-EricNeural",
        "voice": "calm"
    },

    "Biko Bean": {
        "tag": "Snack philosopher",
        "skin": (126, 79, 59),
        "hair": (72, 48, 35),
        "shirt": (154, 101, 190),
        "pants": (55, 56, 72),
        "outfit": "turtleneck",
        "hair_style": "curly",
        "accent": "●",
        "tts_voice": "en-US-SaraNeural",
        "voice": "warm"
    },

    "Nala Vee": {
        "tag": "Ambitious overachiever",
        "skin": (184, 123, 90),
        "hair": (31, 24, 22),
        "shirt": (69, 116, 207),
        "pants": (55, 56, 80),
        "outfit": "dress",
        "hair_style": "long",
        "accent": "▲",
        "tts_voice": "en-US-MichelleNeural",
        "voice": "bright"
    },

    "Dex Orbit": {
        "tag": "Conspiracy-minded friend",
        "skin": (146, 93, 68),
        "hair": (36, 27, 24),
        "shirt": (102, 107, 121),
        "pants": (46, 51, 66),
        "outfit": "jacket",
        "hair_style": "short",
        "accent": "◎",
        "tts_voice": "en-US-ChristopherNeural",
        "voice": "dramatic"
    },

    "Ayo Finch": {
        "tag": "Quiet comedian",
        "skin": (112, 71, 54),
        "hair": (27, 22, 20),
        "shirt": (207, 91, 137),
        "pants": (54, 59, 71),
        "outfit": "crew_neck",
        "hair_style": "spiky",
        "accent": "~",
        "tts_voice": "en-US-BrianNeural",
        "voice": "dry"
    },

    "Rhea Moss": {
        "tag": "Practical realist",
        "skin": (161, 105, 77),
        "hair": (84, 53, 36),
        "shirt": (86, 151, 191),
        "pants": (50, 60, 75),
        "outfit": "collar_shirt",
        "hair_style": "bob",
        "accent": "+",
        "tts_voice": "en-US-NancyNeural",
        "voice": "firm"
    },

    "Professor Pogo": {
        "tag": "Eccentric explainer",
        "skin": (186, 127, 94),
        "hair": (145, 145, 145),
        "shirt": (226, 226, 220),
        "pants": (64, 75, 86),
        "outfit": "vneck",
        "hair_style": "bald",
        "accent": "!",
        "tts_voice": "en-US-TonyNeural",
        "voice": "dramatic"
    },

    "Jax Noon": {
        "tag": "Dramatic storyteller",
        "skin": (120, 76, 58),
        "hair": (31, 24, 21),
        "shirt": (192, 76, 70),
        "pants": (48, 53, 66),
        "outfit": "turtleneck",
        "hair_style": "wavy",
        "accent": "◆",
        "tts_voice": "en-US-JasonNeural",
        "voice": "dramatic"
    },

    "Simi Ray": {
        "tag": "Curious newcomer",
        "skin": (139, 87, 64),
        "hair": (45, 29, 24),
        "shirt": (75, 181, 165),
        "pants": (55, 60, 75),
        "outfit": "hoodie",
        "hair_style": "pigtails",
        "accent": "?",
        "tts_voice": "en-US-AshleyNeural",
        "voice": "bright"
    }
}


# ============================================================
# OPTIONS
# ============================================================

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

STYLES = [
    "Bold 2D Comedy",
    "Clean Vector",
    "Comic Panel",
    "Storybook",
    "Retro Cartoon",
    "Sketch Motion",
    "Anime-Inspired",
    "Noir Cartoon"
]

POSTURES = [
    "Auto",
    "Standing",
    "Sitting",
    "Leaning"
]

EMOTIONS = [
    "Auto",
    "Neutral",
    "Happy",
    "Surprised",
    "Thinking",
    "Annoyed",
    "Laughing",
    "Confused",
    "Excited",
    "Sad"
]

GESTURES = [
    "Auto",
    "Talking Hands",
    "Pointing",
    "Waving",
    "Thinking",
    "Shrugging",
    "Laughing",
    "Nervous",
    "None"
]

CAMERAS = [
    "Auto",
    "Wide",
    "Medium",
    "Close-up",
    "Over-the-shoulder"
]

PACE = [
    "Natural",
    "Comedic",
    "Calm",
    "Fast"
]


# ============================================================
# FONT
# ============================================================

def get_font(size=26, bold=False):

    candidates = [
        (
            "/usr/share/fonts/truetype/dejavu/"
            + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")
        ),
        (
            "/usr/share/fonts/truetype/liberation2/"
            + (
                "LiberationSans-Bold.ttf"
                if bold
                else "LiberationSans-Regular.ttf"
            )
        )
    ]

    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


# ============================================================
# TEXT WRAPPING
# ============================================================

def wrap_text(text, width=64):

    words = text.split()

    lines = []
    current = ""

    for word in words:

        trial = (current + " " + word).strip()

        if len(trial) <= width:
            current = trial
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

    for raw in text.splitlines():

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
# EMOTION AI
# ============================================================

def infer_emotion(text):

    t = text.lower()

    if any(
        word in t
        for word in [
            "haha",
            "lol",
            "hilarious",
            "funny"
        ]
    ):
        return "Laughing"

    if any(
        word in t
        for word in [
            "wow",
            "amazing",
            "yes!",
            "finally",
            "awesome"
        ]
    ):
        return "Excited"

    if "?" in text or any(
        word in t
        for word in [
            "really",
            "why",
            "how",
            "what",
            "huh"
        ]
    ):
        return "Confused"

    if any(
        word in t
        for word in [
            "no",
            "never",
            "stop",
            "seriously",
            "annoying"
        ]
    ):
        return "Annoyed"

    if any(
        word in t
        for word in [
            "maybe",
            "think",
            "perhaps",
            "wonder"
        ]
    ):
        return "Thinking"

    if any(
        word in t
        for word in [
            "sorry",
            "unfortunately",
            "sad"
        ]
    ):
        return "Sad"

    if any(
        word in t
        for word in [
            "great",
            "good",
            "nice",
            "love",
            "thank"
        ]
    ):
        return "Happy"

    return "Neutral"


# ============================================================
# GESTURE AI
# ============================================================

def infer_gesture(text, emotion):

    t = text.lower()

    if any(
        word in t
        for word in [
            "look",
            "there",
            "that",
            "this"
        ]
    ):
        return "Pointing"

    if any(
        word in t
        for word in [
            "hello",
            "hi",
            "hey",
            "bye"
        ]
    ):
        return "Waving"

    if emotion == "Thinking":
        return "Thinking"

    if emotion == "Laughing":
        return "Laughing"

    if any(
        phrase in t
        for phrase in [
            "maybe",
            "i guess",
            "not sure"
        ]
    ):
        return "Nervous"

    if emotion == "Excited":
        return "Talking Hands"

    return "Talking Hands"


# ============================================================
# POSTURE AI
# ============================================================

def infer_posture(location, text):

    if location in [
        "Apartment",
        "Restaurant",
        "Office",
        "Classroom",
        "Pharmacy"
    ]:

        if any(
            word in text.lower()
            for word in [
                "stand",
                "standing",
                "come",
                "walk"
            ]
        ):
            return "Standing"

        return "Sitting"

    return "Standing"


# ============================================================
# DURATION
# ============================================================

def estimate_duration(text, pace="Natural"):

    words = max(
        1,
        len(text.split())
    )

    rates = {
        "Natural": 2.7,
        "Comedic": 2.25,
        "Calm": 2.0,
        "Fast": 3.25
    }

    base = words / rates[pace]

    return max(
        2.0,
        min(
            12.0,
            base + 0.7
        )
    )


# ============================================================
# AUDIO PLACEHOLDER
# ============================================================

def make_silent_audio(
    duration,
    path,
    sample_rate=16000
):

    samples = int(
        duration * sample_rate
    )

    with wave.open(
        str(path),
        "wb"
    ) as wf:

        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        silence = struct.pack(
            "<h",
            0
        )

        wf.writeframes(
            silence * samples
        )


# ============================================================
# TEXT-TO-SPEECH (edge-tts)
# ============================================================

def get_media_duration(path):
    """Read a media file's duration in seconds via ffmpeg's
    stderr output (avoids needing a separate ffprobe binary)."""

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    result = subprocess.run(
        [ffmpeg, "-i", str(path)],
        capture_output=True,
        text=True
    )

    match = re.search(
        r"Duration:\s*(\d+):(\d+):(\d+\.\d+)",
        result.stderr
    )

    if not match:
        return None

    hours, minutes, seconds = match.groups()

    return (
        int(hours) * 3600 +
        int(minutes) * 60 +
        float(seconds)
    )


def synthesize_line(text, voice_id, out_path):
    """Generate a spoken audio clip for one line of dialogue
    using edge-tts. Returns True on success, False if TTS is
    unavailable or generation failed (caller should fall back
    to a silent/estimated-duration segment in that case)."""

    if not EDGE_TTS_AVAILABLE:
        return False

    if not text or not text.strip():
        return False

    async def _run():
        communicate = edge_tts.Communicate(text, voice_id)
        await communicate.save(str(out_path))

    try:

        loop = asyncio.new_event_loop()

        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_run())
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        return (
            Path(out_path).exists() and
            Path(out_path).stat().st_size > 0
        )

    except Exception:
        return False


def pad_audio_to_duration(src_path, target_seconds, out_path):
    """Pad (or trim) an audio clip so it exactly matches the
    video duration it needs to sync against."""

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    subprocess.run(
        [
            ffmpeg,
            "-y",

            "-i",
            str(src_path),

            "-af",
            (
                "apad=whole_dur=" +
                f"{target_seconds}"
            ),

            "-t",
            str(target_seconds),

            "-ar",
            "16000",

            "-ac",
            "1",

            str(out_path)
        ],
        capture_output=True,
        text=True
    )


def concat_audio_clips(clip_paths, out_path):
    """Stitch per-scene audio clips into one continuous track,
    in order, using ffmpeg's concat demuxer."""

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    list_path = Path(str(out_path) + ".txt")

    with open(list_path, "w") as f:

        for p in clip_paths:

            escaped = str(Path(p).resolve()).replace(
                "'", "'\\''"
            )

            f.write(f"file '{escaped}'\n")

    subprocess.run(
        [
            ffmpeg,
            "-y",

            "-f",
            "concat",

            "-safe",
            "0",

            "-i",
            str(list_path),

            "-c",
            "copy",

            str(out_path)
        ],
        capture_output=True,
        text=True
    )

    try:
        list_path.unlink()
    except Exception:
        pass


# ============================================================
# BACKGROUND
# ============================================================

def draw_background(draw, location):

    draw.rectangle(
        [0, 0, W, H],
        fill=(194, 222, 240)
    )

    draw.rectangle(
        [0, 510, W, H],
        fill=(112, 151, 105)
    )

    draw.rectangle(
        [0, 0, W, 58],
        fill=(24, 28, 35)
    )

    draw.text(
        (40, 16),
        location.upper(),
        font=get_font(25, True),
        fill=(245, 245, 245)
    )

    if location in [
        "Apartment",
        "Office",
        "Classroom",
        "Pharmacy",
        "Restaurant",
        "Corner Shop"
    ]:

        wall = (235, 226, 210)

        draw.rectangle(
            [40, 70, W - 40, 510],
            fill=wall,
            outline=(55, 55, 58),
            width=4
        )

        # Windows

        for x in (115, 910):

            draw.rectangle(
                [
                    x,
                    130,
                    x + 210,
                    285
                ],
                fill=(154, 205, 229),
                outline=(60, 70, 75),
                width=4
            )

            draw.line(
                [
                    x + 105,
                    130,
                    x + 105,
                    285
                ],
                fill=(70, 75, 80),
                width=3
            )

            draw.line(
                [
                    x,
                    207,
                    x + 210,
                    207
                ],
                fill=(70, 75, 80),
                width=3
            )

        if location == "Classroom":

            draw.rectangle(
                [150, 410, 1130, 455],
                fill=(125, 91, 61)
            )

            for x in (
                200,
                480,
                760,
                1040
            ):

                draw.line(
                    [
                        x,
                        455,
                        x - 10,
                        510
                    ],
                    fill=(65, 65, 65),
                    width=8
                )

                draw.line(
                    [
                        x + 90,
                        455,
                        x + 100,
                        510
                    ],
                    fill=(65, 65, 65),
                    width=8
                )

        elif location == "Restaurant":

            draw.ellipse(
                [370, 400, 910, 525],
                fill=(125, 82, 55),
                outline=(65, 45, 35),
                width=4
            )

        elif location == "Pharmacy":

            draw.rectangle(
                [430, 315, 850, 420],
                fill=(215, 220, 225),
                outline=(70, 70, 75),
                width=4
            )

            draw.text(
                (515, 350),
                "PHARMACY",
                font=get_font(32, True),
                fill=(60, 65, 70)
            )

        else:

            draw.rounded_rectangle(
                [380, 400, 900, 500],
                radius=25,
                fill=(115, 91, 80),
                outline=(60, 55, 55),
                width=4
            )

    elif location in [
        "Park",
        "Rooftop"
    ]:

        draw.rectangle(
            [0, 430, W, H],
            fill=(94, 155, 88)
        )

        for x in (150, 1050):

            draw.rectangle(
                [x, 230, x + 28, 510],
                fill=(105, 70, 45)
            )

            draw.ellipse(
                [
                    x - 80,
                    130,
                    x + 105,
                    310
                ],
                fill=(58, 137, 72)
            )

    else:

        draw.rectangle(
            [0, 440, W, H],
            fill=(78, 83, 91)
        )

        for x in range(
            40,
            W,
            230
        ):

            draw.rectangle(
                [
                    x,
                    170,
                    x + 145,
                    440
                ],
                fill=(165, 155, 150),
                outline=(70, 68, 68),
                width=3
            )

        for x in range(
            80,
            W,
            230
        ):

            draw.rectangle(
                [
                    x,
                    370,
                    x + 75,
                    400
                ],
                fill=(235, 190, 70)
            )


# ============================================================
# RIGGED 2D CHARACTER
# ============================================================

def draw_rigged_character(
    draw,
    name,
    cx,
    ground,
    frame,
    seed,
    expression="Neutral",
    posture="Standing",
    gesture="Talking Hands",
    talking=False,
    look_x=None,
    scale=1.0,
    style="Bold 2D Comedy",
    mouth_frame=None
):

    if mouth_frame is None:
        mouth_frame = frame

    character = CHARACTERS[name]

    # Breathing
    breath = (
        3.6 *
        math.sin(
            frame / 11.0 + seed
        )
    )

    # Body sway
    sway = (
        4.5 *
        math.sin(
            frame / 18.0 +
            seed * 0.7
        )
    )

    # Speech bounce
    talk = 0

    if talking:

        talk = (
            3.5 *
            math.sin(
                frame / 3.8 + seed
            )
        )

    cx += sway
    ground += breath + talk

    seated = posture == "Sitting"
    leaning = posture == "Leaning"

    torso_shift = -8 if leaning else 0

    head_y = ground - (
        285 if seated else 300
    )

    # ========================================================
    # CHAIR / LEGS
    # ========================================================

    if seated:

        # Seat cushion
        draw.rounded_rectangle(
            [
                cx - 110,
                ground - 185,
                cx + 110,
                ground - 150
            ],
            radius=12,
            fill=(88, 91, 101),
            outline=(48, 49, 55),
            width=4
        )

        # Chair legs (front pair only — back pair would be
        # hidden by the seated character anyway). Thicker
        # and rounded-off so it doesn't read as a spindly
        # stool.
        for leg_x_top, leg_x_bottom in (
            (cx - 78, cx - 100),
            (cx + 78, cx + 100)
        ):

            draw.line(
                [
                    leg_x_top,
                    ground - 150,
                    leg_x_bottom,
                    ground
                ],
                fill=(58, 60, 68),
                width=14
            )

            draw.ellipse(
                [
                    leg_x_top - 8,
                    ground - 158,
                    leg_x_top + 8,
                    ground - 142
                ],
                fill=(58, 60, 68)
            )

            # Floor foot cap
            draw.ellipse(
                [
                    leg_x_bottom - 10,
                    ground - 6,
                    leg_x_bottom + 10,
                    ground + 6
                ],
                fill=(40, 41, 47)
            )

        # Character's own legs, bent at the knee — without
        # these the character looked like a legless torso
        # perched on the stool.
        knee_y = ground - 55

        for hip_x, foot_x in (
            (cx - 26, cx - 34),
            (cx + 26, cx + 34)
        ):

            hip_y = ground - 145

            # Thigh
            draw.line(
                [
                    hip_x,
                    hip_y,
                    hip_x * 0.4 + foot_x * 0.6,
                    knee_y
                ],
                fill=character["pants"],
                width=15
            )

            # Shin
            draw.line(
                [
                    hip_x * 0.4 + foot_x * 0.6,
                    knee_y,
                    foot_x,
                    ground
                ],
                fill=character["pants"],
                width=13
            )

            # Knee joint
            draw.ellipse(
                [
                    hip_x * 0.4 + foot_x * 0.6 - 7,
                    knee_y - 7,
                    hip_x * 0.4 + foot_x * 0.6 + 7,
                    knee_y + 7
                ],
                fill=character["pants"]
            )

            # Hip joint
            draw.ellipse(
                [
                    hip_x - 7,
                    hip_y - 7,
                    hip_x + 7,
                    hip_y + 7
                ],
                fill=character["pants"]
            )

            # Shoe
            draw.ellipse(
                [
                    foot_x - 13,
                    ground - 8,
                    foot_x + 15,
                    ground + 9
                ],
                fill=shade(character["pants"], -0.5),
                outline=shade(character["pants"], -0.65),
                width=2
            )

    else:

        for hip_x, foot_x in (
            (cx - 20, cx - 35),
            (cx + 20, cx + 35)
        ):

            hip_y = ground - 80

            draw.line(
                [
                    hip_x,
                    hip_y,
                    foot_x,
                    ground
                ],
                fill=character["pants"],
                width=12
            )

            draw.ellipse(
                [
                    hip_x - 6,
                    hip_y - 6,
                    hip_x + 6,
                    hip_y + 6
                ],
                fill=character["pants"]
            )

            # Shoe
            draw.ellipse(
                [
                    foot_x - 12,
                    ground - 8,
                    foot_x + 14,
                    ground + 8
                ],
                fill=shade(character["pants"], -0.5)
            )

    # ========================================================
    # TORSO
    # ========================================================

    body_top = ground - (
        220 if seated else 235
    )

    outfit = character.get("outfit", "crew_neck")

    torso_top = body_top
    torso_bottom = ground - 70
    torso_left = cx - 53 + torso_shift
    torso_right = cx + 53 + torso_shift

    if outfit == "dress":

        # Flared trapezoid silhouette instead of a
        # straight rectangle
        flare = 22

        draw.polygon(
            [
                (torso_left + 10, torso_top),
                (torso_right - 10, torso_top),
                (torso_right + flare, torso_bottom),
                (torso_left - flare, torso_bottom)
            ],
            fill=character["shirt"],
            outline=shade(character["shirt"], -0.45)
        )

        torso_box = [
            torso_left - flare,
            torso_top,
            torso_right + flare,
            torso_bottom
        ]

    else:

        torso_box = [
            torso_left,
            torso_top,
            torso_right,
            torso_bottom
        ]

        draw.rounded_rectangle(
            torso_box,
            radius=22,
            fill=character["shirt"],
            outline=shade(character["shirt"], -0.45),
            width=4
        )

    # Shadow panel (implied light from upper-left)
    draw.rounded_rectangle(
        [
            cx + 14 + torso_shift,
            body_top + 6,
            torso_box[2] - 4,
            ground - 76
        ],
        radius=16,
        fill=shade(character["shirt"], -0.16)
    )

    # Highlight streak
    draw.rounded_rectangle(
        [
            cx - 44 + torso_shift,
            body_top + 10,
            cx - 30 + torso_shift,
            ground - 110
        ],
        radius=8,
        fill=shade(character["shirt"], 0.18)
    )

    # ========================================================
    # OUTFIT DETAILS
    # (silhouette accents so characters read as distinct
    # people, not recolored copies of the same shape)
    # ========================================================

    if outfit == "collar_shirt":

        collar_color = shade(character["shirt"], 0.3)

        draw.polygon(
            [
                (cx - 4 + torso_shift, torso_top),
                (cx - 22 + torso_shift, torso_top + 26),
                (cx + torso_shift, torso_top + 12)
            ],
            fill=collar_color
        )

        draw.polygon(
            [
                (cx + 4 + torso_shift, torso_top),
                (cx + 22 + torso_shift, torso_top + 26),
                (cx + torso_shift, torso_top + 12)
            ],
            fill=collar_color
        )

        for by in range(
            int(torso_top) + 40,
            int(ground) - 90,
            24
        ):

            draw.ellipse(
                [
                    cx - 3 + torso_shift,
                    by - 3,
                    cx + 3 + torso_shift,
                    by + 3
                ],
                fill=shade(character["shirt"], -0.5)
            )

    elif outfit == "vneck":

        draw.polygon(
            [
                (cx - 16 + torso_shift, torso_top),
                (cx + 16 + torso_shift, torso_top),
                (cx + torso_shift, torso_top + 34)
            ],
            fill=shade(character["skin"], -0.05)
        )

    elif outfit == "turtleneck":

        draw.rounded_rectangle(
            [
                cx - 22 + torso_shift,
                torso_top - 6,
                cx + 22 + torso_shift,
                torso_top + 22
            ],
            radius=10,
            fill=shade(character["shirt"], 0.12),
            outline=shade(character["shirt"], -0.3),
            width=2
        )

    elif outfit == "hoodie":

        hood_color = shade(character["shirt"], -0.12)

        draw.arc(
            [
                cx - 44 + torso_shift,
                torso_top - 30,
                cx + 44 + torso_shift,
                torso_top + 40
            ],
            160,
            380,
            fill=hood_color,
            width=16
        )

        # drawstrings
        for dx in (-8, 8):

            draw.line(
                [
                    cx + dx + torso_shift,
                    torso_top + 18,
                    cx + dx + torso_shift,
                    torso_top + 48
                ],
                fill=shade(character["shirt"], -0.5),
                width=3
            )

    elif outfit == "jacket":

        lapel_color = shade(character["shirt"], -0.22)

        draw.polygon(
            [
                (cx - 6 + torso_shift, torso_top),
                (cx - 30 + torso_shift, torso_top + 55),
                (cx - 14 + torso_shift, torso_top + 55),
                (cx + torso_shift, torso_top + 16)
            ],
            fill=lapel_color
        )

        draw.polygon(
            [
                (cx + 6 + torso_shift, torso_top),
                (cx + 30 + torso_shift, torso_top + 55),
                (cx + 14 + torso_shift, torso_top + 55),
                (cx + torso_shift, torso_top + 16)
            ],
            fill=lapel_color
        )

    else:

        # crew_neck: simple ribbed neckline
        draw.arc(
            [
                cx - 20 + torso_shift,
                torso_top - 8,
                cx + 20 + torso_shift,
                torso_top + 14
            ],
            0,
            180,
            fill=shade(character["shirt"], -0.35),
            width=4
        )

    # ========================================================
    # HEAD TILT
    # ========================================================

    if expression == "Thinking":

        tilt = -4

    elif expression == "Annoyed":

        tilt = 4

    else:

        tilt = (
            2 *
            math.sin(frame / 7)
            if expression in [
                "Excited",
                "Laughing"
            ]
            else 0
        )

    # ========================================================
    # ARMS
    # ========================================================

    wave = math.sin(
        frame / 3.2
    )

    if gesture == "Pointing":

        arms = [
            (-88, body_top + 60),
            (100, body_top + 12)
        ]

    elif gesture == "Waving":

        arms = [
            (
                -82,
                body_top +
                35 +
                int(22 * wave)
            ),
            (
                65,
                body_top -
                10 +
                int(18 * wave)
            )
        ]

    elif gesture == "Thinking":

        arms = [
            (-65, body_top + 20),
            (30, body_top + 20)
        ]

    elif gesture == "Shrugging":

        arms = [
            (-78, body_top + 5),
            (78, body_top + 5)
        ]

    elif gesture == "Laughing":

        arms = [
            (-72, body_top + 25),
            (72, body_top + 25)
        ]

    elif gesture == "Nervous":

        arms = [
            (-55, body_top + 65),
            (55, body_top + 65)
        ]

    elif gesture == "None":

        arms = [
            (-35, body_top + 100),
            (35, body_top + 100)
        ]

    else:

        arms = [
            (
                -78,
                body_top +
                65 +
                int(
                    12 *
                    math.sin(
                        frame / 5 +
                        seed
                    )
                )
            ),
            (
                78,
                body_top +
                65 +
                int(
                    12 *
                    math.sin(
                        frame / 5 +
                        seed + 1
                    )
                )
            )
        ]

    shoulder_x = cx
    shoulder_y = body_top + 58

    for ex, ey in arms:

        arm_end_x = cx + ex
        arm_end_y = ey

        draw.line(
            [
                shoulder_x,
                shoulder_y,
                arm_end_x,
                arm_end_y
            ],
            fill=character["shirt"],
            width=22
        )

        # Round the joints so limbs don't look like
        # blunt-cut rods
        for jx, jy in (
            (shoulder_x, shoulder_y),
            (arm_end_x, arm_end_y)
        ):

            draw.ellipse(
                [
                    jx - 11,
                    jy - 11,
                    jx + 11,
                    jy + 11
                ],
                fill=character["shirt"]
            )

        # Hand (skin-toned cap at the end of each arm)
        draw.ellipse(
            [
                arm_end_x - 10,
                arm_end_y - 10,
                arm_end_x + 10,
                arm_end_y + 10
            ],
            fill=character["skin"],
            outline=shade(character["skin"], -0.4),
            width=2
        )

    # ========================================================
    # NECK
    # ========================================================

    draw.rectangle(
        [
            cx - 18,
            head_y + 45,
            cx + 18,
            head_y + 70
        ],
        fill=character["skin"]
    )

    # Neck shadow (soft contact shadow where it meets torso)
    draw.rectangle(
        [
            cx - 18,
            head_y + 60,
            cx + 18,
            head_y + 70
        ],
        fill=shade(character["skin"], -0.25)
    )

    # ========================================================
    # HEAD
    # ========================================================

    hs = int(
        66 * scale
    )

    head_box = [
        cx - hs,
        head_y - hs,
        cx + hs,
        head_y + hs
    ]

    draw.ellipse(
        head_box,
        fill=character["skin"],
        outline=shade(character["skin"], -0.55),
        width=4
    )

    # Cel-shading crescent (light from upper-left, so
    # shadow falls on the lower-right of the face)
    draw.pieslice(
        head_box,
        20,
        160,
        fill=shade(character["skin"], -0.14)
    )

    # Soft cheek highlight (upper-left)
    draw.ellipse(
        [
            cx - hs * 0.55,
            head_y - hs * 0.35,
            cx - hs * 0.05,
            head_y + hs * 0.15
        ],
        fill=shade(character["skin"], 0.14)
    )

    # Cheek blush (adds warmth / life to the face)
    blush_color = blend(
        character["skin"],
        (214, 84, 90),
        0.28
    )

    for bx in (cx - hs * 0.62, cx + hs * 0.62):

        draw.ellipse(
            [
                bx - 14,
                head_y + 6,
                bx + 14,
                head_y + 22
            ],
            fill=blush_color
        )

    # ========================================================
    # HAIR
    # ========================================================

    hair_box = [
        cx - hs - 4,
        head_y - hs - 10,
        cx + hs + 4,
        head_y + 18
    ]

    hair_style = character.get("hair_style", "short")
    hair_color = character["hair"]

    if hair_style == "bald":

        # Just a faint fringe above the ears, no crown hair
        draw.arc(
            hair_box,
            250,
            290,
            fill=hair_color,
            width=14
        )

    elif hair_style == "afro":

        draw.ellipse(
            [
                cx - hs - 14,
                head_y - hs - 26,
                cx + hs + 14,
                head_y + hs - 24
            ],
            fill=hair_color,
            outline=shade(hair_color, -0.3),
            width=3
        )

        draw.ellipse(
            [
                cx - hs - 22,
                head_y - hs + 10,
                cx - hs + 6,
                head_y + hs + 6
            ],
            fill=hair_color
        )

        draw.ellipse(
            [
                cx + hs - 6,
                head_y - hs + 10,
                cx + hs + 22,
                head_y + hs + 6
            ],
            fill=hair_color
        )

    elif hair_style == "curly":

        draw.arc(
            hair_box,
            180,
            360,
            fill=hair_color,
            width=22
        )

        # Curl bumps along the top edge
        for t in range(6):

            ang = math.radians(180 + t * 30)

            bx = cx + math.cos(ang) * (hs + 2)
            by = head_y + math.sin(ang) * (hs + 2)

            draw.ellipse(
                [bx - 9, by - 9, bx + 9, by + 9],
                fill=hair_color
            )

    elif hair_style == "long":

        draw.arc(
            hair_box,
            180,
            360,
            fill=hair_color,
            width=18
        )

        for sx in (cx - hs - 2, cx + hs - 6):

            draw.rounded_rectangle(
                [
                    sx,
                    head_y - 10,
                    sx + 16,
                    head_y + 95
                ],
                radius=8,
                fill=hair_color
            )

    elif hair_style == "ponytail":

        draw.arc(
            hair_box,
            180,
            360,
            fill=hair_color,
            width=18
        )

        draw.rounded_rectangle(
            [
                cx + hs - 10,
                head_y - hs + 10,
                cx + hs + 14,
                head_y + 70
            ],
            radius=10,
            fill=hair_color
        )

    elif hair_style == "pigtails":

        draw.arc(
            hair_box,
            180,
            360,
            fill=hair_color,
            width=18
        )

        for sx in (cx - hs - 6, cx + hs - 10):

            draw.ellipse(
                [
                    sx,
                    head_y - hs + 20,
                    sx + 16,
                    head_y + 60
                ],
                fill=hair_color
            )

    elif hair_style == "bun":

        draw.arc(
            hair_box,
            180,
            360,
            fill=hair_color,
            width=18
        )

        draw.ellipse(
            [
                cx - 18,
                head_y - hs - 30,
                cx + 18,
                head_y - hs + 2
            ],
            fill=hair_color
        )

    elif hair_style == "bob":

        draw.arc(
            hair_box,
            180,
            360,
            fill=hair_color,
            width=18
        )

        for sx in (cx - hs - 2, cx + hs - 14):

            draw.rounded_rectangle(
                [
                    sx,
                    head_y - 10,
                    sx + 16,
                    head_y + 38
                ],
                radius=8,
                fill=hair_color
            )

    elif hair_style == "spiky":

        draw.arc(
            hair_box,
            180,
            360,
            fill=hair_color,
            width=16
        )

        for t in range(5):

            ang = math.radians(200 + t * 35)

            bx = cx + math.cos(ang) * hs
            by = head_y + math.sin(ang) * hs

            tip_x = cx + math.cos(ang) * (hs + 24)
            tip_y = head_y + math.sin(ang) * (hs + 24)

            draw.polygon(
                [
                    (bx - 8, by),
                    (bx + 8, by),
                    (tip_x, tip_y)
                ],
                fill=hair_color
            )

    elif hair_style == "wavy":

        draw.arc(
            hair_box,
            180,
            360,
            fill=hair_color,
            width=18
        )

        for t in range(4):

            wx = cx - hs + 20 + t * (hs * 2 - 40) / 3

            draw.arc(
                [
                    wx - 14,
                    head_y + 4,
                    wx + 14,
                    head_y + 32
                ],
                0,
                180,
                fill=hair_color,
                width=8
            )

    else:

        # short (default)
        draw.arc(
            hair_box,
            180,
            360,
            fill=hair_color,
            width=18
        )

    # Hair highlight (gives it a glossy, less flat look)
    if hair_style != "bald":

        draw.arc(
            hair_box,
            200,
            260,
            fill=shade(hair_color, 0.35),
            width=6
        )

    # ========================================================
    # EYE TRACKING
    # ========================================================

    eye_dx = 0

    if look_x is not None:

        eye_dx = max(
            -7,
            min(
                7,
                int(
                    (look_x - cx) /
                    80
                )
            )
        )

    # Slightly irregular blink interval per character
    # (varies with a slow secondary wave so it doesn't
    # feel like a metronome over a long video)
    blink_period = 79 + int(
        14 * math.sin(frame / 260.0 + seed)
    )

    blink_phase = (
        (frame + seed * 13) % blink_period
    )

    blink = blink_phase in (0, 1, 2, 3)
    half_blink = blink_phase in (4, 5)

    eye_y = head_y - 12

    base_height = (
        12
        if expression == "Surprised"
        else 8
    )

    if blink:
        eye_height = 1
    elif half_blink:
        eye_height = int(base_height * 0.5)
    else:
        eye_height = base_height

    for eye_x in (
        cx - 22,
        cx + 22
    ):

        ex = eye_x + eye_dx

        # Eye white (sclera) — without this the pupil was
        # just a dark dot floating on skin, which read as
        # flat/lifeless. This alone does a lot of the work
        # for making the face feel more alive.
        if not blink:

            draw.ellipse(
                [
                    ex - 12,
                    eye_y - max(eye_height, 3) - 2,
                    ex + 12,
                    eye_y + max(eye_height, 3) + 2
                ],
                fill=(250, 250, 248),
                outline=shade(character["skin"], -0.35),
                width=1
            )

        draw.ellipse(
            [
                ex - 9,
                eye_y - eye_height,
                ex + 9,
                eye_y + eye_height
            ],
            fill=(35, 28, 26)
        )

        # Catchlight — small highlight dot so eyes don't
        # look dead/glassy. Skipped during blinks.
        if not blink and not half_blink:

            draw.ellipse(
                [
                    ex - 5,
                    eye_y - eye_height + 1,
                    ex - 1,
                    eye_y - eye_height + 5
                ],
                fill=(255, 255, 255)
            )

    # ========================================================
    # EYEBROWS
    # ========================================================

    brow_y = head_y - 34

    if expression == "Annoyed":

        draw.line(
            [
                cx - 35,
                brow_y + 6,
                cx - 10,
                brow_y - 5
            ],
            fill=(48, 35, 35),
            width=5
        )

        draw.line(
            [
                cx + 10,
                brow_y - 5,
                cx + 35,
                brow_y + 6
            ],
            fill=(48, 35, 35),
            width=5
        )

    elif expression in [
        "Surprised",
        "Excited"
    ]:

        draw.line(
            [
                cx - 35,
                brow_y - 7,
                cx - 10,
                brow_y - 10
            ],
            fill=(48, 35, 35),
            width=5
        )

        draw.line(
            [
                cx + 10,
                brow_y - 10,
                cx + 35,
                brow_y - 7
            ],
            fill=(48, 35, 35),
            width=5
        )

    else:

        draw.line(
            [
                cx - 34,
                brow_y,
                cx - 12,
                brow_y - 2
            ],
            fill=(48, 35, 35),
            width=4
        )

        draw.line(
            [
                cx + 12,
                brow_y - 2,
                cx + 34,
                brow_y
            ],
            fill=(48, 35, 35),
            width=4
        )

    # ========================================================
    # MOUTH / VISemes
    # ========================================================

    mouth_y = head_y + 35

    if talking:

        # Hold each viseme for a few frames instead of
        # flipping every single frame (~24/sec was too
        # fast for a natural talking cadence).
        viseme_hold = 4

        shapes = [
            0, 2, 1, 3, 2, 4,
            1, 3, 0, 2, 4, 1
        ]

        step = mouth_frame // viseme_hold

        # Every ~6th viseme, hold a closed mouth a beat
        # longer to simulate a natural word/breath gap.
        if step % 6 == 5:
            shape = 0
        else:
            shape = shapes[
                step % len(shapes)
            ]

        if shape == 0:

            draw.line(
                [
                    cx - 18,
                    mouth_y + 8,
                    cx + 18,
                    mouth_y + 8
                ],
                fill=(126, 54, 54),
                width=4
            )

        elif shape == 1:

            draw.ellipse(
                [
                    cx - 17,
                    mouth_y,
                    cx + 17,
                    mouth_y + 12
                ],
                fill=(158, 68, 66)
            )

        elif shape == 2:

            draw.ellipse(
                [
                    cx - 19,
                    mouth_y,
                    cx + 19,
                    mouth_y + 22
                ],
                fill=(158, 68, 66)
            )

        elif shape == 3:

            draw.ellipse(
                [
                    cx - 13,
                    mouth_y,
                    cx + 13,
                    mouth_y + 28
                ],
                fill=(158, 68, 66)
            )

        else:

            draw.arc(
                [
                    cx - 28,
                    mouth_y - 10,
                    cx + 28,
                    mouth_y + 27
                ],
                0,
                180,
                fill=(158, 68, 66),
                width=5
            )

    elif expression == "Laughing":

        draw.arc(
            [
                cx - 30,
                mouth_y - 12,
                cx + 30,
                mouth_y + 30
            ],
            0,
            180,
            fill=(158, 68, 66),
            width=6
        )

    elif expression == "Surprised":

        draw.ellipse(
            [
                cx - 14,
                mouth_y,
                cx + 14,
                mouth_y + 27
            ],
            fill=(158, 68, 66)
        )

    elif expression in [
        "Happy",
        "Excited"
    ]:

        draw.arc(
            [
                cx - 28,
                mouth_y - 12,
                cx + 28,
                mouth_y + 25
            ],
            0,
            180,
            fill=(158, 68, 66),
            width=5
        )

    elif expression == "Sad":

        draw.arc(
            [
                cx - 25,
                mouth_y - 4,
                cx + 25,
                mouth_y + 20
            ],
            180,
            360,
            fill=(158, 68, 66),
            width=5
        )

    else:

        draw.line(
            [
                cx - 18,
                mouth_y + 8,
                cx + 18,
                mouth_y + 8
            ],
            fill=(82, 35, 35),
            width=4
        )

    # ========================================================
    # SHADOW
    # ========================================================

    draw.ellipse(
        [
            cx - 75,
            ground + 8,
            cx + 75,
            ground + 25
        ],
        fill=(60, 70, 65)
    )


# ============================================================
# DIALOGUE CARD
# ============================================================

def draw_dialogue_card(
    draw,
    speaker,
    text,
    emotion,
    progress
):

    draw.rounded_rectangle(
        [
            38,
            48,
            1242,
            178
        ],
        radius=24,
        fill=(255, 255, 255),
        outline=(38, 40, 44),
        width=4
    )

    draw.text(
        (65, 67),
        speaker,
        font=get_font(28, True),
        fill=(30, 30, 35)
    )

    lines = wrap_text(
        text,
        78
    )[:2]

    y = 108

    for line in lines:

        draw.text(
            (65, y),
            line,
            font=get_font(25),
            fill=(48, 48, 53)
        )

        y += 32

    # Emotion indicator

    draw.rounded_rectangle(
        [
            1030,
            15,
            1242,
            46
        ],
        radius=14,
        fill=(25, 29, 35)
    )

    draw.text(
        (1050, 21),
        emotion.upper(),
        font=get_font(15, True),
        fill=(245, 245, 245)
    )


# ============================================================
# FRAME RENDERER
# ============================================================

def render_frame(
    scene,
    project,
    frame,
    global_frame=None
):

    if global_frame is None:
        global_frame = frame

    image = Image.new(
        "RGB",
        (W, H),
        (235, 235, 235)
    )

    draw = ImageDraw.Draw(
        image
    )

    draw_background(
        draw,
        scene["location"]
    )

    cast = project["cast"]

    speaker = scene["speaker"]

    listener = next(
        (
            character
            for character in cast
            if character != speaker
        ),
        None
    )

    progress = (
        frame /
        max(
            1,
            scene["frames"] - 1
        )
    )

    camera = scene["camera"]

    if camera == "Auto":

        if len(
            scene["dialogue"].split()
        ) > 12:

            camera = "Close-up"

        else:

            camera = "Medium"

    if camera == "Wide":

        zoom = 0.88

    elif camera == "Close-up":

        zoom = 1.10

    else:

        zoom = 1.0

    drift = int(
        18 *
        math.sin(
            progress * math.pi
        )
    )

    center_shift = int(
        (zoom - 1) * 90
    )

    left_x = (
        345
        - center_shift
        + drift
    )

    right_x = (
        900
        + center_shift
        - drift
    )

    posture = scene["posture"]

    if posture == "Auto":

        posture = infer_posture(
            scene["location"],
            scene["dialogue"]
        )

    emotion = scene["emotion"]

    if emotion == "Auto":

        emotion = infer_emotion(
            scene["dialogue"]
        )

    gesture = scene["gesture"]

    if gesture == "Auto":

        gesture = infer_gesture(
            scene["dialogue"],
            emotion
        )

    # ========================================================
    # SPEAKER
    # ========================================================

    # Switch to RGBA here since sprite compositing needs an alpha
    # channel — converted back to RGB right before the frame is
    # returned/saved. Procedural drawing (draw_rigged_character,
    # draw_dialogue_card, etc.) works fine on an RGBA image too, so
    # this doesn't disturb anything for characters without sprites.
    image = image.convert("RGBA")
    draw = ImageDraw.Draw(image)

    SPRITE_BASE_SCALE = 0.62

    if SPRITE_AVAILABLE and SPRITE.has_sprite(speaker):

        SPRITE.paste_character(
            image,
            speaker,
            (left_x, H - 20),
            global_frame=global_frame,
            talking=True,
            seed=11,
            scale=SPRITE_BASE_SCALE * zoom
        )

    else:

        draw_rigged_character(
            draw,
            speaker,
            left_x,
            650,
            global_frame,
            11,
            expression=emotion,
            posture=posture,
            gesture=gesture,
            talking=True,
            look_x=right_x,
            scale=zoom,
            style=project["style"],
            mouth_frame=frame
        )

    # ========================================================
    # LISTENER
    # ========================================================

    if listener:

        if (
            emotion == "Surprised"
            and progress < 0.35
        ):

            listener_emotion = "Surprised"

        else:

            listener_emotion = "Neutral"

        if (
            emotion == "Annoyed"
            and progress < 0.25
        ):

            listener_gesture = "Nervous"

        else:

            listener_gesture = "None"

        listener_frame = (
            global_frame +
            (
                10
                if frame % 90 > 55
                else 0
            )
        )

        if SPRITE_AVAILABLE and SPRITE.has_sprite(listener):

            SPRITE.paste_character(
                image,
                listener,
                (right_x, H - 20),
                global_frame=listener_frame,
                talking=False,
                seed=23,
                scale=SPRITE_BASE_SCALE * zoom
            )

        else:

            draw_rigged_character(
                draw,
                listener,
                right_x,
                650,
                listener_frame,
                23,
                expression=listener_emotion,
                posture=posture,
                gesture=listener_gesture,
                talking=False,
                look_x=left_x,
                scale=zoom,
                style=project["style"],
                mouth_frame=frame
            )

    # ========================================================
    # DIALOGUE
    # ========================================================

    draw_dialogue_card(
        draw,
        speaker,
        scene["dialogue"],
        emotion,
        progress
    )

    # ========================================================
    # PROGRESS BAR
    # ========================================================

    draw.rectangle(
        [
            40,
            H - 26,
            W - 40,
            H - 18
        ],
        fill=(45, 48, 52)
    )

    draw.rectangle(
        [
            40,
            H - 26,
            40 +
            int(
                (W - 80) *
                progress
            ),
            H - 18
        ],
        fill=(235, 95, 78)
    )

    return image.convert("RGB")


# ============================================================
# VIDEO RENDERER
# ============================================================

def render_video(
    scenes,
    project,
    progress_cb=None
):

    frames_dir = (
        ROOT /
        f"frames_{os.getpid()}"
    )

    frames_dir.mkdir(
        exist_ok=True
    )

    audio_dir = (
        ROOT /
        f"audio_{os.getpid()}"
    )

    audio_dir.mkdir(
        exist_ok=True
    )

    output = (
        ROOT /
        f"cartoon_v4_{os.getpid()}.mp4"
    )

    master_audio = (
        ROOT /
        f"master_audio_{os.getpid()}.wav"
    )

    # ========================================================
    # PASS 1: synthesize real speech for each line, then size
    # each scene's frame count to match how long the line
    # actually takes to speak (falls back to the text-length
    # heuristic if TTS is unavailable or a line fails).
    # ========================================================

    scene_audio_paths = []

    for i, scene in enumerate(scenes):

        raw_clip = (
            audio_dir /
            f"raw_{i:04d}.mp3"
        )

        character = CHARACTERS.get(
            scene["speaker"], {}
        )

        voice_id = character.get(
            "tts_voice",
            "en-US-JennyNeural"
        )

        synth_ok = synthesize_line(
            scene["dialogue"],
            voice_id,
            raw_clip
        )

        spoken_seconds = None

        if synth_ok:

            spoken_seconds = get_media_duration(
                raw_clip
            )

        if spoken_seconds:

            # small pad so the mouth doesn't cut off the
            # instant audio ends, and so very short lines
            # still get a readable amount of screen time
            scene_seconds = max(
                spoken_seconds + 0.35,
                1.2
            )

        else:

            scene_seconds = float(
                scene["duration"]
            )

        scene["duration"] = scene_seconds

        scene["frames"] = max(
            1,
            int(scene_seconds * FPS)
        )

        padded_clip = (
            audio_dir /
            f"padded_{i:04d}.wav"
        )

        if synth_ok:

            pad_audio_to_duration(
                raw_clip,
                scene_seconds,
                padded_clip
            )

        else:

            make_silent_audio(
                scene_seconds,
                padded_clip
            )

        scene_audio_paths.append(
            padded_clip
        )

    # ========================================================
    # PASS 2: render frames now that every scene's true
    # duration (and therefore global_frame timeline) is known
    # ========================================================

    total = sum(
        scene["frames"]
        for scene in scenes
    )

    done = 0
    index = 0

    try:

        for scene in scenes:

            for frame in range(
                scene["frames"]
            ):

                render_frame(
                    scene,
                    project,
                    frame,
                    global_frame=index
                ).save(
                    frames_dir /
                    f"frame_{index:07d}.png"
                )

                index += 1
                done += 1

                if (
                    progress_cb
                    and done % 12 == 0
                ):

                    progress_cb(
                        done / total
                    )

        concat_audio_clips(
            scene_audio_paths,
            master_audio
        )

        ffmpeg = (
            imageio_ffmpeg
            .get_ffmpeg_exe()
        )

        result = subprocess.run(
            [
                ffmpeg,
                "-y",

                "-framerate",
                str(FPS),

                "-i",
                str(
                    frames_dir /
                    "frame_%07d.png"
                ),

                "-i",
                str(master_audio),

                "-c:v",
                "libx264",

                "-preset",
                "fast",

                "-crf",
                "18",

                "-pix_fmt",
                "yuv420p",

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

        if result.returncode == 0:

            return output, None

        return (
            None,
            result.stderr[-4000:]
        )

    finally:

        shutil.rmtree(
            frames_dir,
            ignore_errors=True
        )

        shutil.rmtree(
            audio_dir,
            ignore_errors=True
        )

        try:
            master_audio.unlink()
        except Exception:
            pass


# ============================================================
# JOIN VIDEOS
# ============================================================

def join_videos(files):

    work = (
        ROOT /
        f"join_{os.getpid()}"
    )

    work.mkdir(
        exist_ok=True
    )

    clips = []

    try:

        ffmpeg = (
            imageio_ffmpeg
            .get_ffmpeg_exe()
        )

        for i, file in enumerate(files):

            source = (
                work /
                f"src_{i}.mp4"
            )

            clip = (
                work /
                f"clip_{i}.mp4"
            )

            source.write_bytes(
                file.getvalue()
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

                    "-c:a",
                    "aac",

                    str(clip)
                ],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:

                return (
                    None,
                    result.stderr[-3000:]
                )

            clips.append(
                clip
            )

        manifest = (
            work /
            "concat.txt"
        )

        manifest.write_text(
            "\n".join(
                f"file '{clip.as_posix()}'"
                for clip in clips
            )
        )

        output = (
            ROOT /
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

        return (
            None,
            result.stderr[-3000:]
        )

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
        "name": "My Cartoon Episode",
        "style": "Bold 2D Comedy",
        "location": "Apartment",
        "cast": [
            "Zuri Spark",
            "Milo Quirk"
        ],
        "pace": "Natural"
    }


if "scenes" not in st.session_state:

    st.session_state.scenes = []


# ============================================================
# HEADER
# ============================================================

st.title(
    "🎬 Cartoon Studio V4"
)

st.caption(
    "Turn a script into a performed 2D cartoon — "
    "characters act, react, move and talk."
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header(
        "🎨 Episode"
    )

    st.session_state.project["name"] = st.text_input(
        "Project name",
        st.session_state.project["name"]
    )

    st.session_state.project["style"] = st.selectbox(
        "Visual style",
        STYLES,
        index=STYLES.index(
            st.session_state.project["style"]
        )
    )

    st.session_state.project["location"] = st.selectbox(
        "Default location",
        LOCATIONS,
        index=LOCATIONS.index(
            st.session_state.project["location"]
        )
    )

    st.session_state.project["pace"] = st.selectbox(
        "Dialogue pace",
        PACE,
        index=PACE.index(
            st.session_state.project["pace"]
        )
    )


# ============================================================
# TABS
# ============================================================

tabs = st.tabs(
    [
        "✨ Create",
        "🎭 Acting",
        "🎬 Storyboard",
        "🎞️ Join",
        "💾 Project"
    ]
)


# ============================================================
# CREATE TAB
# ============================================================

with tabs[0]:

    st.subheader(
        "1. Choose your cast"
    )

    st.session_state.project["cast"] = st.multiselect(
        "Original characters",
        list(CHARACTERS),
        default=st.session_state.project["cast"],
        max_selections=4
    )

    if not st.session_state.project["cast"]:

        st.session_state.project["cast"] = [
            "Zuri Spark",
            "Milo Quirk"
        ]

    selected = (
        st.session_state.project["cast"]
    )

    columns = st.columns(
        min(
            4,
            len(selected)
        )
    )

    for i, name in enumerate(
        selected
    ):

        with columns[i]:

            character = CHARACTERS[name]

            st.markdown(
                f"**{character['accent']} {name}**"
            )

            st.caption(
                character["tag"]
            )

    st.subheader(
        "2. Paste your script"
    )

    script = st.text_area(
        "Use Character: dialogue",
        height=260,
        placeholder=(
            "Zuri Spark: Why does the fridge light "
            "disappear when I close the door?\n"
            "Milo Quirk: It doesn't disappear. "
            "You just can't see it.\n"
            "Zuri Spark: So the fridge is hiding "
            "things from me?\n"
            "Milo Quirk: That is a surprisingly "
            "accurate description."
        )
    )

    if st.button(
        "🧠 Build Episode Automatically",
        type="primary",
        use_container_width=True
    ):

        rows = parse_script(
            script
        )

        scenes = []

        if not rows:

            st.warning(
                "Add a script first."
            )

        else:

            for i, (
                speaker,
                dialogue
            ) in enumerate(rows):

                if speaker not in selected:

                    speaker = selected[0]

                emotion = infer_emotion(
                    dialogue
                )

                gesture = infer_gesture(
                    dialogue,
                    emotion
                )

                scenes.append(
                    {
                        "id": i + 1,
                        "speaker": speaker,
                        "dialogue": dialogue,
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
                            ),
                        "posture":
                            infer_posture(
                                st.session_state
                                .project[
                                    "location"
                                ],
                                dialogue
                            ),
                        "emotion": emotion,
                        "gesture": gesture,
                        "camera": "Auto"
                    }
                )

            st.session_state.scenes = scenes

            st.success(
                f"Built {len(scenes)} acted shots."
            )


# ============================================================
# ACTING TAB
# ============================================================

with tabs[1]:

    st.subheader(
        "🎭 Acting Director"
    )

    st.write(
        "V4 automatically interprets the script, "
        "but you can override any performance."
    )

    if not st.session_state.scenes:

        st.info(
            "Build an episode from the Create tab first."
        )

    else:

        for scene in st.session_state.scenes:

            with st.expander(
                (
                    f"Shot {scene['id']} · "
                    f"{scene['speaker']} · "
                    f"{scene['emotion']} · "
                    f"{scene['gesture']}"
                ),
                expanded=False
            ):

                col1, col2, col3, col4, col5 = st.columns(5)

                with col1:

                    options = POSTURES

                    scene["posture"] = st.selectbox(
                        "Posture",
                        options,
                        index=(
                            options.index(
                                scene["posture"]
                            )
                            if scene["posture"]
                            in options
                            else 0
                        ),
                        key=f"posture_{scene['id']}"
                    )

                with col2:

                    options = EMOTIONS

                    scene["emotion"] = st.selectbox(
                        "Emotion",
                        options,
                        index=(
                            options.index(
                                scene["emotion"]
                            )
                            if scene["emotion"]
                            in options
                            else 0
                        ),
                        key=f"emotion_{scene['id']}"
                    )

                with col3:

                    options = GESTURES

                    scene["gesture"] = st.selectbox(
                        "Gesture",
                        options,
                        index=(
                            options.index(
                                scene["gesture"]
                            )
                            if scene["gesture"]
                            in options
                            else 0
                        ),
                        key=f"gesture_{scene['id']}"
                    )

                with col4:

                    options = CAMERAS

                    scene["camera"] = st.selectbox(
                        "Camera",
                        options,
                        index=(
                            options.index(
                                scene["camera"]
                            )
                            if scene["camera"]
                            in options
                            else 0
                        ),
                        key=f"camera_{scene['id']}"
                    )

                with col5:

                    scene["duration"] = st.number_input(
                        "Seconds",
                        1.5,
                        15.0,
                        float(
                            scene["duration"]
                        ),
                        0.5,
                        key=f"duration_{scene['id']}"
                    )

                st.caption(
                    "Performance layers: "
                    "blinking · breathing · head movement · "
                    "eye tracking · mouth-shape cycling · "
                    "gesture animation · listener reaction"
                )


# ============================================================
# STORYBOARD TAB
# ============================================================

with tabs[2]:

    st.subheader(
        "🎬 Storyboard & Render"
    )

    if not st.session_state.scenes:

        st.info(
            "Build an episode first."
        )

    else:

        for scene in st.session_state.scenes:

            st.markdown(
                f"""
                **SHOT {scene['id']} — {scene['speaker']}**

                {scene['dialogue']}
                """
            )

        st.divider()

        progress = st.progress(
            0
        )

        status = st.empty()

        if st.button(
            "🚀 Render V4 Cartoon",
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

                status.write(
                    f"Animating… "
                    f"{int(value * 100)}%"
                )

            with st.spinner(
                "Building performed animation…"
            ):

                output, error = render_video(
                    st.session_state.scenes,
                    st.session_state.project,
                    update_progress
                )

            if output:

                progress.progress(
                    1.0
                )

                status.success(
                    "Finished."
                )

                st.session_state.output = str(
                    output
                )

            else:

                status.error(
                    "Render failed."
                )

                st.code(
                    error or
                    "Unknown FFmpeg error"
                )

        if (
            st.session_state.get(
                "output"
            )
            and Path(
                st.session_state.output
            ).exists()
        ):

            st.video(
                st.session_state.output
            )

            st.download_button(
                "⬇️ Download V4 MP4",
                Path(
                    st.session_state.output
                ).read_bytes(),
                "cartoon_studio_v4.mp4",
                "video/mp4",
                use_container_width=True
            )


# ============================================================
# JOIN TAB
# ============================================================

with tabs[3]:

    st.subheader(
        "🎞️ Make a long episode from short videos"
    )

    files = st.file_uploader(
        "Upload clips in the order they should play",
        type=[
            "mp4",
            "mov",
            "m4v"
        ],
        accept_multiple_files=True
    )

    if files:

        for i, file in enumerate(
            files,
            1
        ):

            st.write(
                f"{i}. **{file.name}**"
            )

        if st.button(
            "🔗 Join Clips",
            type="primary",
            use_container_width=True
        ):

            with st.spinner(
                "Joining clips…"
            ):

                output, error = join_videos(
                    files
                )

            if output:

                st.session_state.joined = str(
                    output
                )

                st.success(
                    "Full episode created."
                )

            else:

                st.error(
                    error or
                    "Join failed."
                )

    if (
        st.session_state.get(
            "joined"
        )
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
            "cartoon_episode.mp4",
            "video/mp4",
            use_container_width=True
        )


# ============================================================
# PROJECT TAB
# ============================================================

with tabs[4]:

    st.subheader(
        "💾 Project"
    )

    project_data = {
        "project":
            st.session_state.project,

        "scenes":
            st.session_state.scenes,

        "version":
            "4.0"
    }

    st.json(
        {
            "name":
                st.session_state
                .project[
                    "name"
                ],

            "characters":
                st.session_state
                .project[
                    "cast"
                ],

            "style":
                st.session_state
                .project[
                    "style"
                ],

            "shots":
                len(
                    st.session_state.scenes
                )
        }
    )

    st.download_button(
        "💾 Save Project JSON",
        json.dumps(
            project_data,
            indent=2
        ),
        "cartoon_studio_v4_project.json",
        "application/json",
        use_container_width=True
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Cartoon Studio V4 · "
    "Original character performance engine · "
    "No copyrighted character assets included"
)
