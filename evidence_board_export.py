"""Final Evidence Board export pass: subtitles, labels, arrows and aspect-ratio output."""
from pathlib import Path
import re
import subprocess
import tempfile

import imageio_ffmpeg


def _esc_filter_path(path):
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _write_text(work, name, text):
    p = Path(work) / name
    p.write_text(str(text or ""), encoding="utf-8")
    return p


def _clean_text(text, limit=180):
    return re.sub(r"\s+", " ", str(text or "")).strip()[:limit]


def _duration_for_beat(text):
    # Matches the base renderer's fallback timing closely when TTS timing
    # cannot be queried during the final export pass.
    return max(1.6, len(str(text or "").split()) / 2.3) + 0.35


def finalize_discovery_export(master_path, output_path, beats, items, aspect="16:9", subtitles=True, labels=True, title="DISCOVERY STORY", progress_cb=None):
    """Re-encode the completed master so final visual controls are actually
    present in the MP4. Audio is preserved/re-encoded, not removed.

    Aspect crops the 16:9 master to 16:9, 9:16 or 1:1. Captions are burned
    into the video using FFmpeg drawtext. Evidence labels are shown while
    their corresponding beat is active. The master already contains the
    animated pins/strings/stamp from evidence_board_renderer.
    """
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    master_path = Path(master_path); output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="evidence_export_"))
    try:
        sizes = {"16:9": (1280, 720), "9:16": (720, 1280), "1:1": (900, 900)}
        ow, oh = sizes.get(aspect, sizes["16:9"])
        filters = [f"scale={ow}:{oh}:force_original_aspect_ratio=increase", f"crop={ow}:{oh}"]
        font = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if not Path(font).exists():
            font = "Sans"; bold = "Sans"

        t = 0.0
        for i, beat in enumerate(beats):
            dur = _duration_for_beat(getattr(beat, "text", ""))
            start, end = t, t + dur
            text = _clean_text(getattr(beat, "text", ""), 190)
            if subtitles and text:
                p = _write_text(work, f"subtitle_{i}.txt", text)
                filters.append(
                    "drawtext="
                    f"fontfile='{_esc_filter_path(font)}':textfile='{_esc_filter_path(p)}':"
                    "fontcolor=white:fontsize=26:borderw=3:bordercolor=black:"
                    "box=1:boxcolor=black@0.72:boxborderw=14:"
                    f"x=(w-text_w)/2:y=h-text_h-42:enable='between(t\\,{start:.3f}\\,{end:.3f})'"
                )
            if labels:
                item_index = getattr(beat, "item_index", i)
                item_name = getattr(items[item_index], "name", f"Evidence {item_index + 1}") if 0 <= item_index < len(items) else f"Evidence {item_index + 1}"
                label = _clean_text(f"EVIDENCE {item_index + 1}  •  {item_name}", 80)
                p = _write_text(work, f"label_{i}.txt", label)
                filters.append(
                    "drawtext="
                    f"fontfile='{_esc_filter_path(bold)}':textfile='{_esc_filter_path(p)}':"
                    "fontcolor=white:fontsize=22:borderw=2:bordercolor=black:"
                    "box=1:boxcolor=black@0.62:boxborderw=10:"
                    f"x=34:y=94:enable='between(t\\,{start:.3f}\\,{end:.3f})'"
                )
            t = end

        # Small persistent title, useful especially on vertical/social exports.
        if title:
            p = _write_text(work, "title.txt", _clean_text(title, 60))
            filters.append(
                "drawtext="
                f"fontfile='{_esc_filter_path(bold)}':textfile='{_esc_filter_path(p)}':"
                "fontcolor=white:fontsize=22:borderw=2:bordercolor=black:"
                "x=34:y=30"
            )

        vf = ",".join(filters)
        cmd = [
            ffmpeg, "-y", "-i", str(master_path),
            "-vf", vf,
            "-map", "0:v:0", "-map", "0:a?",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart", str(output_path)
        ]
        if progress_cb:
            progress_cb(0.96)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return None, result.stderr[-5000:]
        if progress_cb:
            progress_cb(1.0)
        return output_path, None
    finally:
        for p in work.glob("*"):
            try: p.unlink()
            except Exception: pass
        try: work.rmdir()
        except Exception: pass
