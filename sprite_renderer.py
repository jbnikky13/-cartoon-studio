"""
Sprite-based character rendering, using the AI-generated full-body
character art (full_body.png per character) as the on-screen sprite.

Earlier versions of this used head-and-shoulders portraits, because
the original source images had a body crop and a portrait crop from
two different "camera angles," which didn't stitch together cleanly.
This version uses purpose-generated full-body art instead (one clean
image per character, generated directly), so that problem doesn't
apply anymore — this is a real full body, not a stitch.

Eye/mouth positions below are calibrated against the actual full-body
art (checked via grid overlay across multiple characters).
"""

from pathlib import Path
from functools import lru_cache
import math

from PIL import Image, ImageDraw


ASSET_DIR_CANDIDATES = [
    Path("char_assets"),
    # Fallback: an earlier upload landed the full-body art in a
    # folder named this way instead of being merged into
    # char_assets/ as intended. Checking both means the renderer
    # keeps working regardless of which naming ended up in the
    # repo, rather than silently failing if they don't match.
    Path("char_assets_fullbody"),
]

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

# Calibrated against the actual generated full-body art (checked
# across multiple characters via grid overlay). If you regenerate
# characters with a different framing/crop, recheck these.
EYE_Y_FRAC = 0.145
MOUTH_Y_FRAC = 0.165
EYE_L_X_FRAC = 0.38
EYE_R_X_FRAC = 0.56
EYE_RADIUS_FRAC = 0.042


def _find_sprite_path(slug):

    for base in ASSET_DIR_CANDIDATES:

        candidate = base / slug / "full_body.png"

        if candidate.exists():
            return candidate

    return None


@lru_cache(maxsize=32)
def load_portrait(character_name):

    slug = CHARACTER_SLUGS.get(character_name)

    if not slug:
        raise ValueError(f"No sprite mapping for {character_name!r}")

    path = _find_sprite_path(slug)

    if path is None:

        checked = [
            str(base / slug / "full_body.png")
            for base in ASSET_DIR_CANDIDATES
        ]

        raise FileNotFoundError(
            f"Missing sprite for {character_name}. Checked: "
            + ", ".join(checked)
        )

    return Image.open(path).convert("RGBA")


def has_sprite(character_name):

    slug = CHARACTER_SLUGS.get(character_name)

    if not slug:
        return False

    return _find_sprite_path(slug) is not None


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
    scale=1.0,
    gesture="None"
):
    """Returns (image, x_offset, y_offset) — the composited sprite
    for this frame plus the idle-motion offsets to paste it with.

    gesture: one of the same gesture labels the app already infers
    from dialogue (Waving, Pointing, Thinking, Shrugging, Laughing,
    Nervous, Talking Hands, None). Since this is flat full-body art
    rather than a rigged character, individual limbs can't move —
    instead each gesture gets a distinct whole-body reaction (tilt,
    lean, bounce, jitter) so gestures inferred from the dialogue
    actually show up as *something* instead of being silently
    dropped, which was happening before this.
    """

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

    # ---- gesture-reactive whole-body motion ----
    extra_x = 0.0
    extra_y = 0.0
    rotation = 0.0

    if gesture == "Waving":

        # side-to-side rock, like leaning into an enthusiastic wave
        rotation = 4.0 * math.sin(global_frame / 4.5 + seed)
        extra_x = 4.0 * math.sin(global_frame / 4.5 + seed)

    elif gesture == "Pointing":

        # a held forward-ish lean, not oscillating — reads as
        # someone making a point
        lean_in = min(1.0, (global_frame % 48) / 8.0)
        rotation = 3.0 * lean_in
        extra_x = 3.0 * lean_in

    elif gesture == "Thinking":

        # slow, small head-tilt-like sway, distinctly slower than
        # idle breathing so it reads as a held pose, not fidgeting
        rotation = 2.5 * math.sin(global_frame / 22.0 + seed)

    elif gesture == "Shrugging":

        # a shoulder-raise implied via a quick upward bounce that
        # holds briefly then releases, roughly every couple seconds
        phase = global_frame % 48
        if phase < 8:
            extra_y = -6.0 * math.sin(phase / 8.0 * math.pi)

    elif gesture == "Laughing":

        # quick, loose vertical bounce — bigger and faster than
        # the idle breathing motion
        extra_y = -5.0 * abs(
            math.sin(global_frame / 3.0 + seed)
        )
        rotation = 2.0 * math.sin(global_frame / 3.0 + seed)

    elif gesture == "Nervous":

        # small fast side-to-side jitter
        extra_x = 2.5 * math.sin(global_frame / 2.0 + seed)

    elif gesture == "Talking Hands":

        # a bit more energetic than idle sway, timed to talking
        # cadence rather than the slow idle wave
        extra_x = 2.5 * math.sin(global_frame / 6.0 + seed)

    if scale != 1.0:

        new_size = (
            max(1, int(frame_img.width * scale)),
            max(1, int(frame_img.height * scale))
        )
        frame_img = frame_img.resize(new_size, Image.LANCZOS)

    if abs(rotation) > 0.05:

        frame_img = frame_img.rotate(
            rotation,
            resample=Image.BICUBIC,
            expand=False,
            center=(
                frame_img.width / 2,
                frame_img.height * 0.15
            )
        )

    total_x = sway_x + extra_x
    total_y = breath_y + talk_y + extra_y

    return frame_img, int(total_x), int(total_y)


def paste_character(
    canvas,
    character_name,
    anchor_xy,
    global_frame,
    talking,
    seed,
    scale=1.0,
    gesture="None"
):
    """anchor_xy: (x, y) on the canvas where the sprite's
    bottom-center should land (e.g. where shoulders meet the
    dialogue framing)."""

    sprite_img, x_off, y_off = compose_character_frame(
        character_name, global_frame, talking, seed, scale,
        gesture=gesture
    )

    anchor_x, anchor_y = anchor_xy

    paste_x = int(anchor_x - sprite_img.width / 2 + x_off)
    paste_y = int(anchor_y - sprite_img.height + y_off)

    canvas.alpha_composite(sprite_img, (paste_x, paste_y))
