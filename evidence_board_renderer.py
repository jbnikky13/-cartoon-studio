"""
Evidence Board renderer — the "detective board" style: photos/
documents pinned to a corkboard, connected by animated red string
as the narration reveals each one, with a big bold stamp caption
available at the end.

Built from the same proven pieces as the rest of the app:
  - photo-background compositing (same idea as RealityBlend)
  - per-beat TTS + per-scene-encode-then-concat (same pattern as
    render_video / render_explainer_video / render_timeline_video)
  - stamp-style bold text (same look as the Explainer stat cards)

The one genuinely new piece is the animated string between pins.
"""

import asyncio
import math
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False


W = 1280
H = 720
FPS = 24


# ============================================================
# TTS (same proven pattern used elsewhere in the app)
# ============================================================

def synthesize_line(text, voice_id, out_path):

    if not EDGE_TTS_AVAILABLE or not text or not text.strip():
        return False

    async def _run():
        communicate = edge_tts.Communicate(text, voice_id)
        await communicate.save(str(out_path))

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_run())
        loop.close()
        return Path(out_path).exists() and Path(out_path).stat().st_size > 0
    except Exception:
        return False


def get_media_duration(path):

    if imageio_ffmpeg is None:
        return None

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    result = subprocess.run(
        [ffmpeg, "-i", str(path)],
        capture_output=True, text=True
    )

    match = re.search(
        r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", result.stderr
    )

    if not match:
        return None

    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def get_safe_font(size=32, bold=True):

    candidates = [
        (
            "/usr/share/fonts/truetype/dejavu/"
            + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")
        ),
        (
            "/usr/share/fonts/truetype/liberation2/"
            + (
                "LiberationSans-Bold.ttf" if bold
                else "LiberationSans-Regular.ttf"
            )
        ),
    ]

    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


# ============================================================
# BOARD ITEMS
# ============================================================

@dataclass
class BoardItem:
    name: str
    image: Image.Image          # RGBA
    x: float                    # 0-1 fraction of board width
    y: float                    # 0-1 fraction of board height
    scale: float = 0.28
    rotation: float = 0.0       # degrees, fixed per-item tilt


@dataclass
class Beat:
    """One narrated step: reveal an item, optionally string it
    back to a previous item."""
    text: str
    item_index: int              # index into the items list
    connect_from_index: Optional[int] = None


def generate_default_corkboard(width=W, height=H):
    """A procedural placeholder board texture, so this works
    without requiring a background upload."""

    base = Image.new("RGB", (width, height), (120, 88, 58))
    draw = ImageDraw.Draw(base)

    # subtle vertical wood-grain-ish streaks
    import random
    rng = random.Random(7)

    for _ in range(140):

        x = rng.randint(0, width)
        streak_w = rng.randint(1, 3)
        shade = rng.randint(-14, 10)

        color = tuple(
            max(0, min(255, c + shade)) for c in (120, 88, 58)
        )

        draw.line(
            [(x, 0), (x + rng.randint(-20, 20), height)],
            fill=color, width=streak_w
        )

    # vignette
    vignette = Image.new("L", (width, height), 0)
    vdraw = ImageDraw.Draw(vignette)
    vdraw.ellipse(
        [-width * 0.2, -height * 0.2, width * 1.2, height * 1.2],
        fill=255
    )
    vignette = vignette.filter(ImageFilter.GaussianBlur(120))

    dark = Image.new("RGB", (width, height), (40, 28, 18))
    base = Image.composite(base, dark, vignette)

    return base


# ============================================================
# PINNED ITEM RENDERING
# ============================================================

def pin_anchor_point(item: BoardItem, board_size):
    """Where the string visually connects — top-center of the
    item, where the pin sits, in absolute board pixel coords."""

    bw, bh = board_size

    cx = item.x * bw
    cy = item.y * bh

    target = bw * item.scale
    img_w, img_h = item.image.size

    fit_scale = target / max(img_w, img_h)
    disp_w = img_w * fit_scale
    disp_h = img_h * fit_scale

    return (cx, cy - disp_h / 2 + 14)


def paste_pinned_item(canvas, item: BoardItem, reveal_progress):
    """reveal_progress: 0 (not yet appeared) -> 1 (fully settled).
    Pops in with a small overshoot for a satisfying "pinned down"
    feel rather than a flat fade."""

    if reveal_progress <= 0.001:
        return

    bw, bh = canvas.size

    target = bw * item.scale
    img_w, img_h = item.image.size

    fit_scale = target / max(img_w, img_h)
    thumb_w = max(1, int(img_w * fit_scale))
    thumb_h = max(1, int(img_h * fit_scale))

    thumb = item.image.resize((thumb_w, thumb_h), Image.LANCZOS)

    # overshoot pop-in: scale bounces slightly past 1.0 then settles
    if reveal_progress < 1.0:
        ease = 1 - (1 - reveal_progress) ** 3
        bounce = 1.0 + 0.08 * math.sin(reveal_progress * math.pi)
        draw_scale = ease * bounce
    else:
        draw_scale = 1.0

    draw_scale = max(0.01, draw_scale)

    dw = max(1, int(thumb_w * draw_scale))
    dh = max(1, int(thumb_h * draw_scale))
    thumb_scaled = thumb.resize((dw, dh), Image.LANCZOS)

    rotated = thumb_scaled.rotate(
        item.rotation, resample=Image.BICUBIC, expand=True
    )

    cx = int(item.x * bw)
    cy = int(item.y * bh)

    # drop shadow
    shadow = Image.new("RGBA", rotated.size, (0, 0, 0, 0))
    alpha = rotated.split()[-1]
    shadow.paste((0, 0, 0, 90), (0, 0), alpha)
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))

    shadow_offset = (
        cx - rotated.width // 2 + 6,
        cy - rotated.height // 2 + 8
    )
    canvas.alpha_composite(shadow, shadow_offset)

    paste_pos = (
        cx - rotated.width // 2,
        cy - rotated.height // 2
    )
    canvas.alpha_composite(rotated, paste_pos)

    if reveal_progress >= 0.4:

        pin_x, pin_y = pin_anchor_point(item, canvas.size)
        pin_alpha = min(1.0, (reveal_progress - 0.4) / 0.3)

        pin_r = 7
        pin_overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        pdraw = ImageDraw.Draw(pin_overlay)

        pdraw.ellipse(
            [pin_x - pin_r, pin_y - pin_r, pin_x + pin_r, pin_y + pin_r],
            fill=(180, 20, 20, int(255 * pin_alpha)),
            outline=(90, 5, 5, int(255 * pin_alpha)),
            width=2
        )
        pdraw.ellipse(
            [pin_x - 2, pin_y - 2, pin_x + 2, pin_y + 2],
            fill=(255, 180, 180, int(220 * pin_alpha))
        )

        canvas.alpha_composite(pin_overlay)


# ============================================================
# STRING
# ============================================================

def draw_string(canvas, p1, p2, progress, sag=22, color=(176, 24, 24)):
    """A slightly sagging red string growing from p1 toward p2.
    progress 0 -> nothing drawn, 1 -> fully connected."""

    if progress <= 0.001:
        return

    x1, y1 = p1
    x2, y2 = p2

    end_x = x1 + (x2 - x1) * progress
    end_y = y1 + (y2 - y1) * progress

    # midpoint sag via a simple quadratic curve, approximated with
    # a handful of straight segments
    segments = 14
    points = []

    mid_x = (x1 + end_x) / 2
    mid_y = (y1 + end_y) / 2 + sag * progress

    for i in range(segments + 1):

        t = i / segments

        # quadratic bezier: p1 -> mid -> end
        bx = (
            (1 - t) ** 2 * x1
            + 2 * (1 - t) * t * mid_x
            + t ** 2 * end_x
        )
        by = (
            (1 - t) ** 2 * y1
            + 2 * (1 - t) * t * mid_y
            + t ** 2 * end_y
        )

        points.append((bx, by))

    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    odraw.line(points, fill=color + (255,), width=3)

    # small pin dots at both existing ends
    for px, py in (points[0], points[-1]):

        odraw.ellipse(
            [px - 4, py - 4, px + 4, py + 4],
            fill=color + (255,)
        )

    canvas.alpha_composite(overlay)


# ============================================================
# STAMP CAPTION (same visual language as Explainer's stat cards)
# ============================================================

def draw_stamp(canvas, text, reveal_progress):

    if reveal_progress <= 0.001 or not text:
        return

    bw, bh = canvas.size

    ease = 1 - (1 - min(1.0, reveal_progress)) ** 3
    font_size = int(bw * 0.09 * (0.7 + 0.3 * ease))
    font = get_safe_font(size=font_size, bold=True)

    draw = ImageDraw.Draw(canvas)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    x = (bw - tw) // 2
    y = int(bh * 0.42) - th // 2

    # a rough rectangle "stamp" frame behind the text, slightly
    # rotated for that hand-stamped look
    pad_x, pad_y = 26, 16

    frame = Image.new(
        "RGBA",
        (tw + pad_x * 2, th + pad_y * 2 + 30),
        (0, 0, 0, 0)
    )
    fdraw = ImageDraw.Draw(frame)

    fdraw.rectangle(
        [0, 0, frame.width - 1, frame.height - 1],
        outline=(200, 30, 30, 230), width=6
    )
    fdraw.text(
        (pad_x, pad_y),
        text, font=font,
        fill=(200, 30, 30, 230),
        stroke_width=2, stroke_fill=(0, 0, 0, 160)
    )

    frame = frame.rotate(-4, resample=Image.BICUBIC, expand=True)

    canvas.alpha_composite(
        frame,
        (x - (frame.width - tw) // 2, y - (frame.height - th) // 2)
    )


# ============================================================
# FRAME COMPOSITING
# ============================================================

def render_board_frame(
    board_bg,
    items: List[BoardItem],
    revealed_state,
    string_state,
    zoom_progress,
    stamp_text=None,
    stamp_progress=0.0
):
    """
    revealed_state: {item_index: reveal_progress 0-1}
    string_state: list of (from_index, to_index, progress 0-1)
    """

    canvas = board_bg.convert("RGBA").copy()

    if zoom_progress > 0.001:

        zoom = 1.0 + 0.06 * zoom_progress
        new_w = int(canvas.width * zoom)
        new_h = int(canvas.height * zoom)

        canvas = canvas.resize((new_w, new_h), Image.LANCZOS)

        left = (new_w - board_bg.width) // 2
        top = (new_h - board_bg.height) // 2

        canvas = canvas.crop(
            (left, top, left + board_bg.width, top + board_bg.height)
        )

    for from_idx, to_idx, progress in string_state:

        if from_idx >= len(items) or to_idx >= len(items):
            continue

        p1 = pin_anchor_point(items[from_idx], canvas.size)
        p2 = pin_anchor_point(items[to_idx], canvas.size)

        draw_string(canvas, p1, p2, progress)

    for idx, item in enumerate(items):

        progress = revealed_state.get(idx, 0.0)
        paste_pinned_item(canvas, item, progress)

    if stamp_text:
        draw_stamp(canvas, stamp_text, stamp_progress)

    return canvas.convert("RGB")


# ============================================================
# MAIN VIDEO RENDERER
# ============================================================

def render_evidence_board_video(
    board_bg,
    items: List[BoardItem],
    beats: List[Beat],
    output_path,
    narrator_voice="en-US-JennyNeural",
    stamp_text=None,
    root_dir=None,
    progress_cb=None
):
    """
    Same per-beat encode-then-concat pattern as the rest of the
    app (render_video / render_explainer_video / render_timeline_
    video) — bounded peak memory regardless of total video length.
    """

    if imageio_ffmpeg is None:
        return None, "imageio_ffmpeg not available"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    root_dir = Path(root_dir) if root_dir else output_path.parent
    work_dir = root_dir / f"_evidence_board_{output_path.stem}"
    work_dir.mkdir(exist_ok=True, parents=True)

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    beat_clips = []
    total_beats = max(1, len(beats)) + (1 if stamp_text else 0)

    revealed_state = {}
    string_state = []

    try:

        for i, beat in enumerate(beats):

            raw_audio = work_dir / f"raw_{i:04d}.mp3"

            synth_ok = synthesize_line(
                beat.text, narrator_voice, raw_audio
            )

            real_duration = (
                get_media_duration(raw_audio) if synth_ok else None
            )
            beat_duration = (
                real_duration
                or max(1.6, len(beat.text.split()) / 2.3)
            ) + 0.35

            n_frames = max(1, int(beat_duration * FPS))

            cmd = [
                ffmpeg, "-y",
                "-f", "rawvideo", "-pix_fmt", "rgb24",
                "-s", f"{W}x{H}", "-r", str(FPS),
                "-i", "-",
                "-an",
                "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "20", "-pix_fmt", "yuv420p",
                str(work_dir / f"silent_{i:04d}.mp4")
            ]

            proc = subprocess.Popen(
                cmd, stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
            )

            reveal_start = 0.0
            reveal_end = 0.35

            string_start = 0.30
            string_end = 0.75

            for f in range(n_frames):

                t = f / max(1, n_frames - 1)

                local_revealed = dict(revealed_state)
                local_strings = list(string_state)

                item_reveal_progress = min(
                    1.0,
                    max(
                        0.0,
                        (t - reveal_start) / (reveal_end - reveal_start)
                    )
                )
                local_revealed[beat.item_index] = item_reveal_progress

                if beat.connect_from_index is not None:

                    str_progress = min(
                        1.0,
                        max(
                            0.0,
                            (t - string_start)
                            / (string_end - string_start)
                        )
                    )
                    local_strings.append(
                        (
                            beat.connect_from_index,
                            beat.item_index,
                            str_progress
                        )
                    )

                frame = render_board_frame(
                    board_bg, items, local_revealed, local_strings,
                    zoom_progress=min(1.0, t + i * 0.15)
                )

                proc.stdin.write(frame.tobytes())

                if progress_cb:
                    progress_cb((i + t) / total_beats)

            proc.stdin.close()
            stderr = proc.stderr.read().decode("utf-8", errors="ignore")
            rc = proc.wait()

            if rc != 0:
                raise RuntimeError(
                    "FFmpeg beat render failed:\n" + stderr[-4000:]
                )

            revealed_state[beat.item_index] = 1.0

            if beat.connect_from_index is not None:
                string_state.append(
                    (beat.connect_from_index, beat.item_index, 1.0)
                )

            silent_clip = work_dir / f"silent_{i:04d}.mp4"
            final_clip = work_dir / f"final_{i:04d}.mp4"

            if synth_ok:

                padded_audio = work_dir / f"padded_{i:04d}.wav"

                subprocess.run(
                    [
                        ffmpeg, "-y",
                        "-i", str(raw_audio),
                        "-af", f"apad=whole_dur={beat_duration}",
                        "-t", str(beat_duration),
                        "-ar", "16000", "-ac", "1",
                        str(padded_audio)
                    ],
                    capture_output=True
                )

                subprocess.run(
                    [
                        ffmpeg, "-y",
                        "-i", str(silent_clip),
                        "-i", str(padded_audio),
                        "-c:v", "copy", "-c:a", "aac",
                        "-shortest",
                        str(final_clip)
                    ],
                    capture_output=True
                )

                try:
                    padded_audio.unlink()
                except Exception:
                    pass

                try:
                    silent_clip.unlink()
                except Exception:
                    pass

            else:

                final_clip = silent_clip

            try:
                raw_audio.unlink()
            except Exception:
                pass

            beat_clips.append(final_clip)

        if stamp_text:

            stamp_duration = 2.2
            n_frames = int(stamp_duration * FPS)

            stamp_clip = work_dir / "stamp.mp4"

            cmd = [
                ffmpeg, "-y",
                "-f", "rawvideo", "-pix_fmt", "rgb24",
                "-s", f"{W}x{H}", "-r", str(FPS),
                "-i", "-",
                "-an",
                "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "20", "-pix_fmt", "yuv420p",
                str(stamp_clip)
            ]

            proc = subprocess.Popen(
                cmd, stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
            )

            for f in range(n_frames):

                t = f / max(1, n_frames - 1)

                frame = render_board_frame(
                    board_bg, items, revealed_state, string_state,
                    zoom_progress=1.0,
                    stamp_text=stamp_text,
                    stamp_progress=min(1.0, t / 0.4)
                )

                proc.stdin.write(frame.tobytes())

                if progress_cb:
                    progress_cb((len(beats) + t) / total_beats)

            proc.stdin.close()
            proc.stderr.read()
            proc.wait()

            beat_clips.append(stamp_clip)

        concat_list = work_dir / "concat.txt"

        with open(concat_list, "w") as f:
            for clip in beat_clips:
                escaped = str(Path(clip).resolve()).replace("'", "'\\''")
                f.write(f"file '{escaped}'\n")

        result = subprocess.run(
            [
                ffmpeg, "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(concat_list),
                "-c", "copy",
                "-movflags", "+faststart",
                str(output_path)
            ],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            return None, result.stderr[-4000:]

        return output_path, None

    finally:

        for clip in beat_clips:
            try:
                Path(clip).unlink()
            except Exception:
                pass

        try:
            (work_dir / "concat.txt").unlink()
        except Exception:
            pass

        for f in work_dir.glob("*"):
            try:
                f.unlink()
            except Exception:
                pass

        try:
            work_dir.rmdir()
        except Exception:
            pass
