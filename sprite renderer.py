"""
Sprite-based character rendering, using the AI-generated portrait
crops (head.png per character) as the primary on-screen sprite.

Why portraits and not full body: the source sheets give a
straight-on torso view and a 3/4-angle portrait from two different
"camera angles" in the original generation. Stitching those into one
full-body figure produces a visible mismatch at the neck. The
portrait alone is high quality, includes the full face, and
head-and-shoulders framing is a normal, deliberate choice for a
dialogue-driven show — not a compromise.

Eye/mouth positions below are calibrated against the actual
generated art (checked across multiple characters), not guessed —
see the calibration grid images if you need to re-check after
generating new characters in a different framing.
"""

from pathlib import Path
from functools import lru_cache
import math

from PIL import Image, ImageDraw


ASSET_DIR = Path("char_assets")

CHARACTER_SLUGS = {
    "Zuri Spark": "zuri_spark",
    "Milo Quirk": "milo_quirk",
    "Kemi Bolt": "kemi_bolt",
    "Tari Reed": "tari_reed",
    "Biko Bean": "biko_bean",
    "Nala Vee": "nala_vee",
    "Dex Orbit": "dex_orbit",
    "Ayo Finch": "ayo_finch",
    "Rhea Moss": "rhea_moss",
    "Professor Pogo": "professor_pogo",
    "Jax Noon": "jax_noon",
    "Simi Ray": "simi_ray",
}

# Calibrated against the actual generated portraits. If you
# regenerate characters with a noticeably different zoom/framing,
# recheck these against a couple of samples (see process_sheets.py
# for a quick grid-overlay snippet).
EYE_Y_FRAC = 0.415
MOUTH_Y_FRAC = 0.48
EYE_L_X_FRAC = 0.22
EYE_R_X_FRAC = 0.44
EYE_RADIUS_FRAC = 0.06


@lru_cache(maxsize=32)
def load_portrait(character_name):

    slug = CHARACTER_SLUGS.get(character_name)

    if not slug:
        raise ValueError(f"No sprite mapping for {character_name!r}")

    path = ASSET_DIR / slug / "head.png"

    if not path.exists():
        raise FileNotFoundError(
            f"Missing portrait for {character_name}: expected {path}"
        )

    return Image.open(path).convert("RGBA")


def has_sprite(character_name):

    slug = CHARACTER_SLUGS.get(character_name)

    if not slug:
        return False

    return (ASSET_DIR / slug / "head.png").exists()


def make_blink_mask(size, closed_amount):

    if closed_amount <= 0.02:
        return None

    w, h = size
    mask_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(mask_img)

    eye_r_px = max(3, int(w * EYE_RADIUS_FRAC))
    eye_y = int(h * EYE_Y_FRAC)

    for eye_x_frac in (EYE_L_X_FRAC, EYE_R_X_FRAC):

        ex = int(w * eye_x_frac)
        lid_h = eye_r_px * closed_amount

        d.ellipse(
            [
                ex - eye_r_px, eye_y - lid_h,
                ex + eye_r_px, eye_y + lid_h
            ],
            fill=(50, 38, 34, int(235 * closed_amount))
        )

    return mask_img


def blink_amount(global_frame, seed):

    blink_period = 79 + int(
        14 * math.sin(global_frame / 260.0 + seed)
    )
    phase = (global_frame + seed * 13) % blink_period

    if phase in (0, 1, 2, 3):
        return 1.0
    if phase in (4, 5):
        return 0.5

    return 0.0


def compose_character_frame(
    character_name,
    global_frame,
    talking,
    seed,
    scale=1.0
):
    """Returns (image, x_offset, y_offset) — the composited sprite
    for this frame plus the idle-motion offsets to paste it with."""

    portrait = load_portrait(character_name)

    frame_img = portrait.copy()

    closed_amount = blink_amount(global_frame, seed)
    mask = make_blink_mask(portrait.size, closed_amount)

    if mask is not None:
        frame_img = Image.alpha_composite(frame_img, mask)

    breath_y = 2.5 * math.sin(global_frame / 11.0 + seed)
    sway_x = 3.0 * math.sin(global_frame / 18.0 + seed * 0.7)

    talk_y = 0.0

    if talking:

        viseme_hold = 4
        step = global_frame // viseme_hold

        if step % 6 != 5:
            talk_y = -3.5 * abs(
                math.sin(global_frame / (viseme_hold * 1.6))
            )

    if scale != 1.0:

        new_size = (
            max(1, int(frame_img.width * scale)),
            max(1, int(frame_img.height * scale))
        )
        frame_img = frame_img.resize(new_size, Image.LANCZOS)

    return frame_img, int(sway_x), int(breath_y + talk_y)


def paste_character(
    canvas,
    character_name,
    anchor_xy,
    global_frame,
    talking,
    seed,
    scale=1.0
):
    """anchor_xy: (x, y) on the canvas where the sprite's
    bottom-center should land (e.g. where shoulders meet the
    dialogue framing)."""

    sprite_img, x_off, y_off = compose_character_frame(
        character_name, global_frame, talking, seed, scale
    )

    anchor_x, anchor_y = anchor_xy

    paste_x = int(anchor_x - sprite_img.width / 2 + x_off)
    paste_y = int(anchor_y - sprite_img.height + y_off)

    canvas.alpha_composite(sprite_img, (paste_x, paste_y))
