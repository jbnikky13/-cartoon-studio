from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import requests
from imageio_ffmpeg import get_ffmpeg_exe

MINIMAX_BASE = os.getenv("MINIMAX_API_BASE", "https://api.minimax.io").rstrip("/")
CREATE_URL = f"{MINIMAX_BASE}/v2/video_generation"
QUERY_URL = f"{MINIMAX_BASE}/v2/query/video_generation/{{task_id}}"

@dataclass
class CharacterReference:
    name: str
    description: str = ""
    image_url: str = ""
    image_data_url: str = ""

@dataclass
class SceneSpec:
    number: int
    title: str
    setting: str
    action: str
    dialogue: str
    characters: list[str] = field(default_factory=list)
    duration: int = 6

def image_to_data_url(uploaded_file) -> str:
    raw = uploaded_file.getvalue()
    mime = getattr(uploaded_file, "type", None) or "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"

def _headers(api_key: str) -> dict[str, str]:
    if not api_key:
        raise ValueError("MINIMAX_API_KEY is not configured.")
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

def build_scene_prompt(scene: SceneSpec, characters: Iterable[CharacterReference]) -> str:
    refs = {c.name.lower(): c for c in characters}
    identity_lines = []
    for name in scene.characters:
        c = refs.get(name.lower())
        if c and c.description:
            identity_lines.append(f"{c.name}: {c.description}")
    identity = "\n".join(identity_lines) or "Use the supplied reference subjects consistently."
    dialogue = scene.dialogue.strip()
    speech = (
        "The character physically speaks the dialogue below. Preserve every spoken word verbatim; do not paraphrase, summarize, or invent dialogue. Make mouth movement and facial expression naturally synchronized to the spoken words."
        if dialogue else
        "There is no dialogue; use natural environmental audio and restrained human performance."
    )
    return f"""Photorealistic live-action microdrama scene. Cinematic but believable human performance, real skin texture, natural eyes, realistic hair, physically plausible hands and body movement, natural lighting, realistic depth of field, subtle cinematic camera motion. No cartoon, illustration, plastic skin, warped faces, extra fingers, text overlays, or subtitles baked into the generated scene.

CHARACTER IDENTITY:
{identity}

SETTING:
{scene.setting}

ACTION / PERFORMANCE:
{scene.action}

{speech}

EXACT DIALOGUE:
{dialogue or '[No spoken dialogue]'}

Keep recurring characters visually consistent with their supplied reference images. Prioritize continuity, clear facial expressions, realistic eye lines, and a coherent beginning-to-end shot. End naturally without a sudden pose change."""

def _content_for_scene(scene: SceneSpec, characters: list[CharacterReference]) -> list[dict]:
    content = [{"type": "text", "text": build_scene_prompt(scene, characters)}]
    refs = {c.name.lower(): c for c in characters}
    for name in scene.characters:
        c = refs.get(name.lower())
        if not c:
            continue
        image = c.image_url.strip() or c.image_data_url.strip()
        if image:
            content.append({"type": "image_url", "image_url": image, "role": "reference_image"})
    return content

def create_video_task(api_key: str, scene: SceneSpec, characters: list[CharacterReference], model="MiniMax-H3", resolution="768P", ratio="9:16") -> str:
    if not 4 <= int(scene.duration) <= 15:
        raise ValueError("MiniMax H3 scene duration must be between 4 and 15 seconds.")
    content = _content_for_scene(scene, characters)
    if not any(item.get("type") == "image_url" for item in content):
        raise ValueError(f"Scene {scene.number} has no usable character reference image.")
    payload = {"model": model, "content": content, "resolution": resolution, "duration": int(scene.duration), "ratio": ratio}
    response = requests.post(CREATE_URL, headers=_headers(api_key), json=payload, timeout=90)
    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise RuntimeError(f"MiniMax create task failed ({response.status_code}): {detail}")
    task_id = response.json().get("task_id")
    if not task_id:
        raise RuntimeError(f"MiniMax did not return a task_id: {response.text}")
    return str(task_id)

def poll_video_task(api_key: str, task_id: str, poll_seconds=8, timeout_seconds=900, progress_callback=None) -> dict:
    started = time.time(); last_status = None
    while time.time() - started < timeout_seconds:
        response = requests.get(QUERY_URL.format(task_id=task_id), headers=_headers(api_key), timeout=60)
        if response.status_code >= 400:
            raise RuntimeError(f"MiniMax query failed ({response.status_code}): {response.text}")
        task = response.json().get("task", response.json())
        status = task.get("status", "unknown")
        if progress_callback and status != last_status:
            progress_callback(status, task); last_status = status
        if status == "succeeded":
            if not (task.get("content") or {}).get("url"):
                raise RuntimeError(f"MiniMax completed without a video URL: {task}")
            return task
        if status in {"failed", "cancelled"}:
            raise RuntimeError(f"MiniMax task {status}: {task}")
        time.sleep(poll_seconds)
    raise TimeoutError(f"MiniMax task {task_id} did not finish within {timeout_seconds} seconds.")

def download_video(url: str, destination: str | Path) -> Path:
    destination = Path(destination); destination.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk: handle.write(chunk)
    return destination

def _run_ffmpeg(args: list[str]) -> None:
    proc = subprocess.run([get_ffmpeg_exe(), "-y", *args], capture_output=True, text=True)
    if proc.returncode: raise RuntimeError(proc.stderr[-4000:] or "FFmpeg failed")

def stitch_clips(clip_paths: list[str | Path], output_path: str | Path) -> Path:
    if not clip_paths: raise ValueError("No clips supplied for stitching.")
    output_path = Path(output_path); output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        concat = Path(td) / "concat.txt"
        concat.write_text("\n".join("file '" + str(Path(p).resolve()).replace("'", "'\\''") + "'" for p in clip_paths), encoding="utf-8")
        _run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(output_path)])
    return output_path

def srt_for_scenes(scenes: list[SceneSpec]) -> str:
    cursor = 0.0; blocks = []
    def stamp(value: float) -> str:
        h = int(value // 3600); m = int((value % 3600) // 60); s = int(value % 60); ms = int((value - int(value)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    for scene in scenes:
        if scene.dialogue.strip():
            blocks.append(f"{len(blocks)+1}\n{stamp(cursor)} --> {stamp(cursor + scene.duration)}\n{scene.dialogue.strip()}\n")
        cursor += float(scene.duration)
    return "\n".join(blocks)

def burn_captions(video_path: str | Path, srt_text: str, output_path: str | Path) -> Path:
    output_path = Path(output_path); output_path.parent.mkdir(parents=True, exist_ok=True)
    if not srt_text.strip():
        Path(video_path).replace(output_path); return output_path
    with tempfile.TemporaryDirectory() as td:
        srt = Path(td) / "captions.srt"; srt.write_text(srt_text, encoding="utf-8")
        filt = "subtitles='" + str(srt).replace("\\", "/").replace("'", "\\'") + "'"
        _run_ffmpeg(["-i", str(video_path), "-vf", filt, "-c:a", "copy", str(output_path)])
    return output_path

def export_microdrama(api_key: str, scenes: list[SceneSpec], characters: list[CharacterReference], model="MiniMax-H3", resolution="768P", ratio="9:16", workdir="generated_microdramas", progress_callback=None):
    workdir = Path(workdir); workdir.mkdir(parents=True, exist_ok=True)
    clips = []; task_records = []
    for scene in scenes:
        task_id = create_video_task(api_key, scene, characters, model=model, resolution=resolution, ratio=ratio)
        task = poll_video_task(api_key, task_id, progress_callback=progress_callback)
        clip = workdir / f"scene_{scene.number:02d}.mp4"; download_video(task["content"]["url"], clip); clips.append(clip)
        task_records.append({"scene": scene.number, "task_id": task_id, "status": task.get("status"), "usage": task.get("usage", {})})
    raw = workdir / "microdrama_raw.mp4"; stitch_clips(clips, raw)
    final = workdir / "microdrama_final.mp4"; burn_captions(raw, srt_for_scenes(scenes), final)
    (workdir / "manifest.json").write_text(json.dumps({"scenes": [s.__dict__ for s in scenes], "tasks": task_records}, indent=2), encoding="utf-8")
    return final, task_records
