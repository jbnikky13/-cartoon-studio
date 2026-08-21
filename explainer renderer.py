"""
Explainer / "faceless" video mode — bold kinetic captions over an
animated background, narrated by a single voice. No characters, no
footage dependency (deliberately, since there was no clear direction
on sourcing stock footage — this leans entirely on typography +
motion, which is how a lot of real faceless/explainer content
actually works).

Reuses the same TTS (synthesize_line) and per-scene-encode-then-
concat video pipeline as the character mode in app.py, so it
inherits the same memory-safe rendering approach rather than
re-solving that problem.
"""

import math
import random
from PIL import Image, ImageDraw, ImageFilter


W = 1280
H = 720
FPS = 24


# ============================================================
# BACKGROUND — animated gradient, not a static color, so there's
# always some motion even during a long caption
# ============================================================

PALETTES = [
    ((20, 22, 46), (76, 29, 149)),    # navy -> violet
    ((15, 32, 39), (32, 58, 67)),     # deep teal
    ((44, 20, 60), (120, 40, 90)),    # plum -> magenta
    ((10, 25, 47), (23, 74, 115)),    # navy -> blue
]


def lerp_color(c1, c2, t):

    return tuple(
        int(a + (b - a) * t)
        for a, b in zip(c1, c2)
    )


def draw_gradient_background(draw, global_frame, palette_index=0):

    c1, c2 = PALETTES[palette_index % len(PALETTES)]

    # slow diagonal drift so the gradient angle isn't static
    drift = math.sin(global_frame / 140.0) * 0.15

    for y in range(H):

        t = (y / H) + drift
        t = max(0.0, min(1.0, t))

        color = lerp_color(c1, c2, t)

        draw.line(
            [(0, y), (W, y)],
            fill=color
        )


def draw_ambient_shapes(image, global_frame, seed=0):
    """A few soft, slowly-drifting circles in the background for
    depth — subtle, not competing with the text."""

    for i in range(3):

        phase = global_frame / 90.0 + i * 2.1 + seed

        cx = W * (0.2 + 0.6 * ((i * 0.37) % 1.0))
        cx += 40 * math.sin(phase)

        cy = H * (0.25 + 0.5 * ((i * 0.61) % 1.0))
        cy += 30 * math.cos(phase * 0.8)

        radius = 90 + 30 * math.sin(phase * 0.5)

        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)

        odraw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            fill=(255, 255, 255, 14)
        )

        overlay = overlay.filter(
            ImageFilter.GaussianBlur(30)
        )

        image.paste(overlay, (0, 0), overlay)


# ============================================================
# KINETIC TEXT
# ============================================================

def split_words(text):

    return text.split()


def get_words_to_show(words, progress):
    """How many words are revealed at this point in the beat.
    Progress 0->1 across the beat's duration."""

    reveal_progress = min(1.0, progress / 0.85)

    count = int(len(words) * reveal_progress) + 1

    return min(count, len(words))


def wrap_words(words, font, draw, max_width):

    lines = []
    current = []

    for word in words:

        trial = current + [word]
        trial_text = " ".join(trial)

        bbox = draw.textbbox((0, 0), trial_text, font=font)
        trial_width = bbox[2] - bbox[0]

        if trial_width > max_width and current:
            lines.append(current)
            current = [word]
        else:
            current = trial

    if current:
        lines.append(current)

    return lines


def draw_kinetic_text(
    draw,
    image,
    text,
    progress,
    get_font_fn,
    accent_color=(255, 200, 60)
):

    words = split_words(text)
    n_visible = get_words_to_show(words, progress)
    visible_words = words[:n_visible]

    font_size = 64
    font = get_font_fn(size=font_size, bold=True)

    max_width = int(W * 0.78)

    lines = wrap_words(words, font, draw, max_width)

    # figure out which line/word index the "newest" word is on,
    # for the pop/highlight effect
    flat_index = 0
    newest_line = 0
    newest_word_in_line = 0

    for li, line in enumerate(lines):

        for wi in range(len(line)):

            if flat_index == n_visible - 1:
                newest_line = li
                newest_word_in_line = wi

            flat_index += 1

    line_height = int(font_size * 1.35)
    total_height = line_height * len(lines)
    start_y = (H - total_height) // 2

    shown_count = 0

    for li, line in enumerate(lines):

        line_words_shown = []

        for wi, word in enumerate(line):

            if shown_count >= n_visible:
                break

            line_words_shown.append((word, li == newest_line and wi == newest_word_in_line))
            shown_count += 1

        if not line_words_shown:
            continue

        line_text = " ".join(w for w, _ in line_words_shown)
        bbox = draw.textbbox((0, 0), line_text, font=font)
        line_width = bbox[2] - bbox[0]
        x = (W - line_width) // 2
        y = start_y + li * line_height

        cursor_x = x

        for word, is_newest in line_words_shown:

            color = accent_color if is_newest else (255, 255, 255)

            # newest word gets a small pop-in scale via a temp
            # larger draw then shrink isn't trivial in PIL without
            # per-word image compositing — approximate the "pop"
            # with a subtle vertical bounce offset instead
            y_off = 0

            if is_newest:

                pop_phase = (progress * 0.85 * len(words)) % 1.0
                y_off = int(-6 * max(0, 1 - pop_phase * 3))

            draw.text(
                (cursor_x, y + y_off),
                word,
                font=font,
                fill=color,
                stroke_width=2,
                stroke_fill=(0, 0, 0)
            )

            word_bbox = draw.textbbox(
                (0, 0), word + " ", font=font
            )
            cursor_x += word_bbox[2] - word_bbox[0]


def draw_stat_card(draw, stat_text, progress, get_font_fn):
    """For beats marked as a stat/number callout (wrapped in ** )
    — a big bold centered number/phrase instead of flowing text."""

    scale_in = min(1.0, progress / 0.25)
    ease = 1 - (1 - scale_in) ** 3

    font_size = int(140 * (0.7 + 0.3 * ease))
    font = get_font_fn(size=font_size, bold=True)

    bbox = draw.textbbox((0, 0), stat_text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    x = (W - tw) // 2
    y = (H - th) // 2

    alpha_fade = min(1.0, progress / 0.15)

    draw.text(
        (x, y),
        stat_text,
        font=font,
        fill=(255, 200, 60),
        stroke_width=3,
        stroke_fill=(0, 0, 0)
    )


# ============================================================
# FRAME + BEAT RENDERING
# ============================================================

def render_explainer_frame(
    beat_text,
    progress,
    global_frame,
    palette_index,
    get_font_fn,
    is_stat=False
):

    image = Image.new("RGB", (W, H), (20, 20, 30))
    draw = ImageDraw.Draw(image)

    draw_gradient_background(draw, global_frame, palette_index)
    draw_ambient_shapes(image, global_frame, seed=palette_index)

    # slow continuous zoom for a Ken-Burns-ish "always moving"
    # camera feel even with no photographic content
    zoom = 1.0 + 0.05 * min(1.0, progress)

    if zoom > 1.001:

        new_w = int(W * zoom)
        new_h = int(H * zoom)

        image = image.resize((new_w, new_h), Image.LANCZOS)

        left = (new_w - W) // 2
        top = (new_h - H) // 2

        image = image.crop((left, top, left + W, top + H))
        draw = ImageDraw.Draw(image)

    if is_stat:
        draw_stat_card(draw, beat_text, progress, get_font_fn)
    else:
        draw_kinetic_text(
            draw, image, beat_text, progress, get_font_fn
        )

    return image
