"""Build an evidence/storyboard draft from an uploaded video."""
from pathlib import Path
import math, re, subprocess, tempfile
import imageio_ffmpeg


def extract_video_frames(video_path, output_dir=None, max_frames=12):
    video_path=Path(video_path)
    if not video_path.exists(): raise FileNotFoundError(video_path)
    out=Path(output_dir or tempfile.mkdtemp(prefix="video_story_frames_")); out.mkdir(parents=True,exist_ok=True)
    ff=imageio_ffmpeg.get_ffmpeg_exe(); probe=subprocess.run([ff,"-i",str(video_path)],capture_output=True,text=True)
    m=re.search(r"Duration:\s+(\d+):(\d+):(\d+(?:\.\d+)?)",probe.stderr)
    duration=(int(m.group(1))*3600+int(m.group(2))*60+float(m.group(3))) if m else 30.0
    count=max(1,min(max_frames,int(math.ceil(duration/5)))); paths=[]
    for i in range(count):
        t=0 if count==1 else duration*i/(count-1); p=out/f"evidence_{i+1:02d}.jpg"
        subprocess.run([ff,"-y","-ss",str(t),"-i",str(video_path),"-frames:v","1","-q:v","3",str(p)],capture_output=True)
        if p.exists(): paths.append({"path":str(p),"timestamp":round(t,2)})
    return {"duration":duration,"frames":paths}


def extract_video_audio(video_path, output_path=None):
    out=Path(output_path or Path(tempfile.mkdtemp(prefix="video_story_audio_"))/"audio.wav"); ff=imageio_ffmpeg.get_ffmpeg_exe()
    r=subprocess.run([ff,"-y","-i",str(video_path),"-vn","-ac","1","-ar","16000","-c:a","pcm_s16le",str(out)],capture_output=True,text=True)
    return str(out) if r.returncode==0 and out.exists() else None


def transcribe_video(video_path, model_size="tiny"):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return {"available":False,"text":"","segments":[]}
    audio=extract_video_audio(video_path)
    if not audio: return {"available":True,"text":"","segments":[]}
    model=WhisperModel(model_size,device="cpu",compute_type="int8")
    segments,_=model.transcribe(audio,beam_size=1)
    data=[{"start":round(s.start,2),"end":round(s.end,2),"text":s.text.strip()} for s in segments]
    return {"available":True,"text":" ".join(x["text"] for x in data),"segments":data}


def build_video_story(video_path,max_frames=12,transcribe=True):
    frames=extract_video_frames(video_path,max_frames=max_frames)
    transcript=transcribe_video(video_path) if transcribe else {"available":False,"text":"","segments":[]}
    beats=[]
    for i,f in enumerate(frames["frames"]):
        text=""
        if transcript.get("segments"):
            t=f["timestamp"]; nearby=min(transcript["segments"],key=lambda s:abs(s["start"]-t))
            if abs(nearby["start"]-t)<=4: text=nearby["text"]
        beats.append({"frame":f["path"],"timestamp":f["timestamp"],"narration":text or f"Evidence frame {i+1} from the source video."})
    return {"duration":frames["duration"],"transcript":transcript,"beats":beats}
