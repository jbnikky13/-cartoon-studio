"""Lightweight video audio + story layer for Cartoon Studio."""
from pathlib import Path
import re, subprocess, tempfile
import imageio_ffmpeg

def extract_audio(video_path, out_dir=None):
    out_dir=Path(out_dir or tempfile.mkdtemp(prefix="cartoon_audio_")); out_dir.mkdir(parents=True,exist_ok=True)
    out=out_dir/(Path(video_path).stem+".m4a")
    ff=imageio_ffmpeg.get_ffmpeg_exe()
    p=subprocess.run([ff,"-y","-i",str(video_path),"-vn","-ac","1","-ar","16000","-c:a","aac","-b:a","64k",str(out)],capture_output=True,text=True)
    if p.returncode!=0 or not out.exists(): raise RuntimeError("Audio extraction failed. The video may not contain an audio track.")
    return str(out)

def _clean_transcript(text): return re.sub(r"\s+"," ",(text or "")).strip()[:20000]

def transcribe_if_available(audio_path):
    try: from faster_whisper import WhisperModel
    except Exception: return "", "Transcription model is not installed; audio extraction succeeded."
    try:
        model=WhisperModel("tiny",device="cpu",compute_type="int8",cpu_threads=1,num_workers=1)
        segments,_=model.transcribe(str(audio_path),beam_size=1,vad_filter=True)
        text=_clean_transcript(" ".join(s.text.strip() for s in segments)); del model
        return text, ""
    except Exception as exc: return "", f"Transcription unavailable: {exc}"

def story_beats_from_text(text,count=6):
    sentences=[s.strip() for s in re.split(r"(?<=[.!?])\s+",_clean_transcript(text)) if len(s.strip())>=25]
    if not sentences and text: sentences=[_clean_transcript(text)]
    beats=[]
    for s in sentences:
        if s not in beats: beats.append(s)
        if len(beats)>=count: break
    while len(beats)<count: beats.append("The evidence develops as another detail comes into view.")
    return beats[:count]

def analyze_audio_story(video_path,transcript="",transcribe=False,count=6):
    audio=extract_audio(video_path); used=_clean_transcript(transcript); note=""
    if not used and transcribe: used,note=transcribe_if_available(audio)
    return {"audio_path":audio,"transcript":used,"story_beats":story_beats_from_text(used,count) if used else [],"note":note}
