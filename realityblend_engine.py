"""
Cartoon Studio V6 - RealityBlend Engine
Lightweight 2D compositor designed for small-memory hosts.

It deliberately avoids Blender/OpenGL. Frames are rendered one at a time
and streamed to FFmpeg through stdin.
"""
from __future__ import annotations

import math
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None


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


def render_frame(scene: Scene, characters: Iterable[Character], t: float) -> Image.Image:
    bg = camera_background(scene, t).convert("RGBA")
    for char in sorted(characters, key=lambda c: c.z):
        paste_character(bg, char, t)
    return bg.convert("RGB")


def ffmpeg_exe() -> str:
    if imageio_ffmpeg is None:
        raise RuntimeError("imageio-ffmpeg is required")
    return imageio_ffmpeg.get_ffmpeg_exe()


def render_video(scene: Scene, characters: Iterable[Character], output_path, audio_path=None,
                 progress=None) -> Path:
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
            frame = render_frame(scene, chars, t)
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
