"""
Cartoon Studio V6 - RealityBlend Engine
Lightweight 2D compositor designed for small-memory hosts.

It deliberately avoids Blender/OpenGL. Frames are rendered one at a time
and streamed to FFmpeg through stdin.
"""
from __future__ import annotations

import asyncio
import math
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False


# ============================================================
# TTS (self-contained — this package deliberately doesn't import
# from app.py, so a copy of the same proven pattern lives here)
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


# ============================================================
# CAPTIONS
# ============================================================

def get_safe_font(size=32, bold=True):
    """Same fallback chain as the main app's get_font — DejaVu,
    then Liberation, then PIL's built-in default. Don't rely on a
    font that might not exist on the deployment host."""

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


def wrap_caption(text, font, draw, max_width):

    words = text.split()
    lines = []
    current = []

    for word in words:

        trial = " ".join(current + [word])
        bbox = draw.textbbox((0, 0), trial, font=font)

        if bbox[2] - bbox[0] > max_width and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)

    if current:
        lines.append(" ".join(current))

    return lines


def draw_caption(frame, text, speaker=None):
    """Bottom-aligned subtitle bar — semi-transparent dark
    background, bold white text with a stroke for legibility
    against any background photo."""

    if not text:
        return frame

    frame = frame.convert("RGBA")
    W, H = frame.size

    font_size = max(18, int(W * 0.045))
    font = get_safe_font(size=font_size, bold=True)

    draw = ImageDraw.Draw(frame)
    max_width = int(W * 0.86)

    lines = wrap_caption(text, font, draw, max_width)

    line_height = int(font_size * 1.3)
    block_height = line_height * len(lines) + int(font_size * 0.8)

    bar_top = H - block_height - int(H * 0.04)

    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    odraw.rectangle(
        [0, bar_top, W, H],
        fill=(0, 0, 0, 130)
    )

    frame = Image.alpha_composite(frame, overlay)
    draw = ImageDraw.Draw(frame)

    y = bar_top + int(font_size * 0.4)

    if speaker:

        speaker_font = get_safe_font(
            size=int(font_size * 0.8), bold=True
        )

        draw.text(
            (int(W * 0.07), y),
            speaker.upper(),
            font=speaker_font,
            fill=(255, 210, 90),
            stroke_width=2,
            stroke_fill=(0, 0, 0)
        )

        y += int(font_size * 1.0)

    for line in lines:

        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x = (W - line_w) // 2

        draw.text(
            (x, y),
            line,
            font=font,
            fill=(255, 255, 255),
            stroke_width=2,
            stroke_fill=(0, 0, 0)
        )

        y += line_height

    return frame.convert("RGB")


@dataclass
class Character:
    name: str
    image: Image.Image
    x: float = 0.5          # normalized center position
    y: float = 0.78         # normalized feet/base position
    scale: float = 0.55     # fraction of canvas height
    z: int = 10
    opacity: float = 1.0
    flip: bool = False
    shadow: bool = True
    motion: str = "idle"


@dataclass
class Scene:
    background: Image.Image
    duration: float = 5.0
    fps: int = 12
    width: int = 540
    height: int = 960
    camera_zoom: float = 1.0
    camera_x: float = 0.5
    camera_y: float = 0.5
    brightness: float = 1.0
    contrast: float = 1.0
    saturation: float = 1.0


def load_rgba(source) -> Image.Image:
    if isinstance(source, Image.Image):
        return source.convert("RGBA")
    return Image.open(source).convert("RGBA")


def remove_simple_background(img: Image.Image, key="auto", tolerance=32) -> Image.Image:
    """
    Lightweight background remover for flat/near-uniform backgrounds.
    For best results upload a transparent PNG. This function is deliberately
    conservative so it does not destroy hair/clothing edges.
    """
    im = img.convert("RGBA")
    pix = im.load()
    w, h = im.size

    samples = [
        pix[0, 0][:3], pix[w - 1, 0][:3],
        pix[0, h - 1][:3], pix[w - 1, h - 1][:3],
    ]
    bg = tuple(sum(p[i] for p in samples) // len(samples) for i in range(3))

    for y in range(h):
        for x in range(w):
            r, g, b, a = pix[x, y]
            d = math.sqrt(sum((c - bg[i]) ** 2 for i, c in enumerate((r, g, b))))
            if d <= tolerance:
                pix[x, y] = (r, g, b, 0)
    return im


def chroma_key(img: Image.Image, rgb=(0, 255, 0), similarity=70, blend=20) -> Image.Image:
    im = img.convert("RGBA")
    px = im.load()
    w, h = im.size
    sr, sg, sb = rgb
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            d = math.sqrt((r-sr)**2 + (g-sg)**2 + (b-sb)**2)
            if d <= similarity:
                px[x, y] = (r, g, b, 0)
            elif d <= similarity + blend:
                alpha = int(255 * (d - similarity) / max(1, blend))
                px[x, y] = (r, g, b, min(a, alpha))
    return im


def fit_cover(img: Image.Image, size) -> Image.Image:
    return ImageOps.fit(img.convert("RGB"), size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def camera_background(scene: Scene, t: float) -> Image.Image:
    bg = scene.background.convert("RGB")
    W, H = scene.width, scene.height

    # Slight procedural camera drift creates a 2.5D feel without storing frames.
    drift_x = math.sin(t * 0.55) * 0.006
    drift_y = math.sin(t * 0.41 + 1.7) * 0.004
    cx = min(1.0, max(0.0, scene.camera_x + drift_x))
    cy = min(1.0, max(0.0, scene.camera_y + drift_y))

    scale = max(1.0, scene.camera_zoom)
    if scale <= 1.001:
        out = fit_cover(bg, (W, H))
    else:
        # Work on a modest intermediate image to keep memory low.
        base = fit_cover(bg, (int(W * scale), int(H * scale)))
        left = int((base.width - W) * cx)
        top = int((base.height - H) * cy)
        left = max(0, min(left, base.width - W))
        top = max(0, min(top, base.height - H))
        out = base.crop((left, top, left + W, top + H))

    out = ImageEnhance.Brightness(out).enhance(scene.brightness)
    out = ImageEnhance.Contrast(out).enhance(scene.contrast)
    out = ImageEnhance.Color(out).enhance(scene.saturation)
    return out


def _motion_values(motion: str, t: float):
    m = (motion or "idle").lower()
    bob = 0.0
    dx = 0.0
    angle = 0.0
    if m in ("idle", "talk", "talking"):
        bob = math.sin(t * 4.0) * 0.008
    if m in ("talk", "talking"):
        bob += math.sin(t * 9.0) * 0.004
    if m in ("bounce", "laugh"):
        bob = abs(math.sin(t * 5.0)) * 0.025
    if m in ("nervous", "shake"):
        dx = math.sin(t * 25.0) * 0.008
        angle = math.sin(t * 22.0) * 1.5
    if m in ("nod",):
        angle = math.sin(t * 5.0) * 4.0
    if m in ("wave", "point", "gesture"):
        bob = math.sin(t * 4.5) * 0.012
    return dx, bob, angle


def paste_character(canvas: Image.Image, char: Character, t: float):
    img = char.image.convert("RGBA")
    if char.flip:
        img = ImageOps.mirror(img)

    target_h = max(16, int(canvas.height * char.scale))
    ratio = target_h / max(1, img.height)
    target_w = max(16, int(img.width * ratio))
    img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)

    dx, bob, angle = _motion_values(char.motion, t)
    if angle:
        img = img.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)

    alpha = img.getchannel("A")
    if char.opacity < 0.999:
        alpha = alpha.point(lambda a: int(a * max(0.0, min(1.0, char.opacity))))
        img.putalpha(alpha)

    x = int(char.x * canvas.width + dx * canvas.width - img.width / 2)
    y = int(char.y * canvas.height + bob * canvas.height - img.height)

    if char.shadow:
        # Soft, cheap contact shadow.
        shadow_w = max(12, int(img.width * 0.34))
        shadow_h = max(4, int(shadow_w * 0.18))
        shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        sx = x + img.width // 2 - shadow_w // 2
        sy = int(char.y * canvas.height) - shadow_h // 2
        sd.ellipse((sx, sy, sx + shadow_w, sy + shadow_h), fill=(0, 0, 0, 80))
        shadow = shadow.filter(ImageFilter.GaussianBlur(max(1, shadow_w // 14)))
        canvas.alpha_composite(shadow)

    canvas.alpha_composite(img, (x, y))


def render_frame(scene: Scene, characters: Iterable[Character], t: float,
                  caption_text: str = None, caption_speaker: str = None) -> Image.Image:
    bg = camera_background(scene, t).convert("RGBA")
    for char in sorted(characters, key=lambda c: c.z):
        paste_character(bg, char, t)
    frame = bg.convert("RGB")
    if caption_text:
        frame = draw_caption(frame, caption_text, caption_speaker)
    return frame


def ffmpeg_exe() -> str:
    if imageio_ffmpeg is None:
        raise RuntimeError("imageio-ffmpeg is required")
    return imageio_ffmpeg.get_ffmpeg_exe()


def render_video(scene: Scene, characters: Iterable[Character], output_path, audio_path=None,
                 progress=None, caption_text: str = None, caption_speaker: str = None) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fps = max(6, min(24, int(scene.fps)))
    total = max(1, int(round(scene.duration * fps)))

    cmd = [
        ffmpeg_exe(), "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{scene.width}x{scene.height}", "-r", str(fps),
        "-i", "-",
    ]
    if audio_path:
        cmd += ["-i", str(audio_path), "-shortest"]
    else:
        cmd += ["-an"]

    cmd += [
        "-c:v", "libx264", "-preset", "ultrafast",
        "-crf", "28", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path),
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE)
    try:
        chars = list(characters)
        for i in range(total):
            t = i / fps
            frame = render_frame(
                scene, chars, t,
                caption_text=caption_text,
                caption_speaker=caption_speaker
            )
            proc.stdin.write(frame.tobytes())
            if progress:
                progress((i + 1) / total)
        proc.stdin.close()
        stderr = proc.stderr.read().decode("utf-8", errors="ignore")
        rc = proc.wait()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
        raise

    if rc != 0:
        raise RuntimeError("FFmpeg render failed:\n" + stderr[-4000:])
    return output_path


def render_timeline_video(
    scene_template: Scene,
    characters_by_name: dict,
    rows,
    voices_by_name: dict,
    output_path,
    default_voice: str = "en-US-JennyNeural",
    progress=None,
):
    """
    Renders one beat per DialogueLine in `rows` (from
    realityblend_models.build_timeline): synthesizes that line's
    audio in the speaking character's voice, gets its REAL duration
    (not just the word-count estimate), renders that beat's frames
    with the speaking character on "talk" motion and everyone else
    on "idle", draws the caption, muxes audio in, then concatenates
    all beats into the final video.

    characters_by_name: {name: Character}
    voices_by_name: {name: edge-tts voice id}
    """

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    work_dir = output_path.parent / f"_rb_beats_{output_path.stem}"
    work_dir.mkdir(exist_ok=True)

    beat_clips = []
    total_beats = max(1, len(rows))

    try:

        for i, row in enumerate(rows):

            raw_audio = work_dir / f"raw_{i:04d}.mp3"

            speaker_key = row.speaker.strip().lower()
            matched_name = None

            for cname in characters_by_name:
                if cname.strip().lower() == speaker_key:
                    matched_name = cname
                    break

            voice_id = voices_by_name.get(
                matched_name, default_voice
            ) if matched_name else default_voice

            synth_ok = synthesize_line(row.text, voice_id, raw_audio)

            real_duration = (
                get_media_duration(raw_audio) if synth_ok else None
            )
            beat_duration = (real_duration or row.duration) + 0.3

            beat_chars = []

            for cname, char in characters_by_name.items():

                motion = "talk" if cname == matched_name else "idle"

                beat_chars.append(Character(
                    name=char.name, image=char.image,
                    x=char.x, y=char.y, scale=char.scale,
                    z=char.z, opacity=char.opacity, flip=char.flip,
                    shadow=char.shadow, motion=motion
                ))

            beat_scene = Scene(
                background=scene_template.background,
                duration=beat_duration,
                fps=scene_template.fps,
                width=scene_template.width,
                height=scene_template.height,
                camera_zoom=scene_template.camera_zoom,
                camera_x=scene_template.camera_x,
                camera_y=scene_template.camera_y,
                brightness=scene_template.brightness,
                contrast=scene_template.contrast,
                saturation=scene_template.saturation,
            )

            silent_clip = work_dir / f"silent_{i:04d}.mp4"

            def _beat_progress(p, i=i):
                if progress:
                    progress((i + p) / total_beats)

            render_video(
                beat_scene, beat_chars, silent_clip,
                progress=_beat_progress,
                caption_text=row.text,
                caption_speaker=row.speaker if row.speaker != "Narrator" else None
            )

            final_clip = work_dir / f"final_{i:04d}.mp4"
            ffmpeg = ffmpeg_exe()

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
                        "-c:v", "copy",
                        "-c:a", "aac",
                        "-shortest",
                        str(final_clip)
                    ],
                    capture_output=True
                )

                try:
                    padded_audio.unlink()
                except Exception:
                    pass

            else:

                final_clip = silent_clip

            try:
                if final_clip != silent_clip:
                    silent_clip.unlink()
            except Exception:
                pass

            try:
                raw_audio.unlink()
            except Exception:
                pass

            beat_clips.append(final_clip)

        concat_list = work_dir / "concat.txt"

        with open(concat_list, "w") as f:
            for clip in beat_clips:
                escaped = str(clip.resolve()).replace("'", "'\\''")
                f.write(f"file '{escaped}'\n")

        ffmpeg = ffmpeg_exe()

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
            raise RuntimeError(
                "FFmpeg concat failed:\n" + result.stderr[-4000:]
            )

        return output_path

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

        try:
            work_dir.rmdir()
        except Exception:
            pass
