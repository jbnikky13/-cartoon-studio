"""Memory-conscious video evidence analyzer for small hosting instances."""
from pathlib import Path
import math,re,subprocess,tempfile
import imageio_ffmpeg
from PIL import Image,ImageStat,ImageFilter
MAX_MB=200
FRAME_WIDTH=480
DEFAULT_MAX_FRAMES=8
DEFAULT_TOP_N=6

def extract_video_frames(video_path,output_dir=None,max_frames=DEFAULT_MAX_FRAMES):
    video_path=Path(video_path)
    if not video_path.exists(): raise FileNotFoundError(video_path)
    if video_path.stat().st_size>MAX_MB*1024*1024: raise ValueError(f"Video exceeds the {MAX_MB} MB limit.")
    out=Path(output_dir or tempfile.mkdtemp(prefix="video_story_frames_")); out.mkdir(parents=True,exist_ok=True)
    ff=imageio_ffmpeg.get_ffmpeg_exe(); probe=subprocess.run([ff,"-hide_banner","-i",str(video_path)],capture_output=True,text=True)
    m=re.search(r"Duration:\s+(\d+):(\d+):(\d+(?:\.\d+)?)",probe.stderr)
    duration=(int(m.group(1))*3600+int(m.group(2))*60+float(m.group(3))) if m else 30.0
    if duration<=0: duration=30.0
    count=max(1,min(max_frames,int(math.ceil(duration/6))))
    paths=[]
    for i in range(count):
        t=0 if count==1 else duration*i/(count-1); p=out/f"evidence_{i+1:02d}.jpg"
        r=subprocess.run([ff,"-hide_banner","-loglevel","error","-y","-ss",str(t),"-i",str(video_path),"-frames:v","1","-vf",f"scale={FRAME_WIDTH}:-2","-q:v","6",str(p)],capture_output=True,text=True)
        if r.returncode==0 and p.exists() and p.stat().st_size>0: paths.append({"path":str(p),"timestamp":round(t,2)})
    if not paths:
        detail=probe.stderr.strip().splitlines()[-1] if probe.stderr else "unknown FFmpeg error"
        raise RuntimeError(f"FFmpeg could not decode any frames. Try MP4/H.264. Details: {detail}")
    return {"duration":duration,"frames":paths}

def _variance(img):
    stat=ImageStat.Stat(img.convert("L")); return float(sum(stat.var)/max(1,len(stat.var)))
def _edge_score(img):
    gray=img.convert("L").resize((128,72)).filter(ImageFilter.FIND_EDGES); return min(1.0,float(ImageStat.Stat(gray).mean[0])/80.0)
def _skin_score(img):
    im=img.convert("RGB").resize((72,40)); hits=0
    for r,g,b in im.getdata():
        if r>80 and r>g*1.12 and g>b*1.08 and r-g>15: hits+=1
    return min(1.0,hits/max(1,72*40)*5.0)
def _text_score(img):
    small=img.convert("L").resize((128,72)); edge=float(ImageStat.Stat(small.filter(ImageFilter.FIND_EDGES)).mean[0])/255.0; var=_variance(img)
    return max(0.0,min(1.0,edge*3.0+(1.0-min(1.0,var/2500.0))*0.25))
def score_frame(img,previous=None):
    if not isinstance(img,Image.Image): img=Image.open(img)
    img=img.convert("RGB"); visual=_edge_score(img); texture=min(1.0,_variance(img)/1800.0); people=_skin_score(img); text=_text_score(img); scene=0.0
    if previous is not None:
        a=img.resize((48,27)).convert("L"); b=previous.resize((48,27)).convert("L"); diff=sum(abs(x-y) for x,y in zip(a.getdata(),b.getdata()))/(48*27*255); scene=min(1.0,diff*3.2)
    distinctive=min(1.0,visual*.42+texture*.33+scene*.25); objects=min(1.0,visual*.55+texture*.45); location=min(1.0,visual*.35+(1-people)*.25+texture*.40); overall=scene*.18+people*.16+text*.16+objects*.16+location*.14+distinctive*.20
    return {"scene_change":round(scene,3),"people_faces":round(people,3),"documents_text":round(text,3),"objects":round(objects,3),"locations":round(location,3),"visually_distinctive":round(distinctive,3),"overall":round(overall,3)}
def rank_evidence_frames(frame_records,top_n=DEFAULT_TOP_N): return sorted(frame_records,key=lambda x:x.get("scores",{}).get("overall",0),reverse=True)[:top_n]
def analyze_video_frames(video_path,max_frames=DEFAULT_MAX_FRAMES,top_n=DEFAULT_TOP_N):
    extracted=extract_video_frames(video_path,max_frames=max_frames); records=[]; previous=None
    for f in extracted["frames"]:
        with Image.open(f["path"]) as source: img=source.convert("RGB").copy()
        scores=score_frame(img,previous); records.append({**f,"scores":scores}); previous=img
    top=rank_evidence_frames(records,top_n)
    keep={r["path"] for r in top}
    for r in records:
        if r["path"] not in keep:
            try: Path(r["path"]).unlink(missing_ok=True)
            except Exception: pass
    return {"duration":extracted["duration"],"frames":top,"top_evidence":top}
def extract_video_audio(video_path,output_path=None):
    out=Path(output_path or Path(tempfile.mkdtemp(prefix="video_story_audio_"))/"audio.wav"); ff=imageio_ffmpeg.get_ffmpeg_exe(); r=subprocess.run([ff,"-hide_banner","-loglevel","error","-y","-i",str(video_path),"-vn","-ac","1","-ar","16000","-c:a","pcm_s16le",str(out)],capture_output=True,text=True); return str(out) if r.returncode==0 and out.exists() else None
def transcribe_video(video_path,model_size="tiny"):
    try: from faster_whisper import WhisperModel
    except ImportError: return {"available":False,"text":"","segments":[]}
    audio=extract_video_audio(video_path)
    if not audio:return {"available":True,"text":"","segments":[]}
    model=WhisperModel(model_size,device="cpu",compute_type="int8"); segments,_=model.transcribe(audio,beam_size=1); data=[{"start":round(s.start,2),"end":round(s.end,2),"text":s.text.strip()} for s in segments]; return {"available":True,"text":" ".join(x["text"] for x in data),"segments":data}
def build_video_story(video_path,max_frames=DEFAULT_MAX_FRAMES,transcribe=True):
    analysis=analyze_video_frames(video_path,max_frames=max_frames); transcript=transcribe_video(video_path) if transcribe else {"available":False,"text":"","segments":[]}; beats=[]
    for i,f in enumerate(analysis["top_evidence"]):
        text=""
        if transcript.get("segments"):
            t=f["timestamp"]; nearby=min(transcript["segments"],key=lambda s:abs(s["start"]-t))
            if abs(nearby["start"]-t)<=4:text=nearby["text"]
        scores=f["scores"]; tags=[k.replace("_"," ") for k,v in scores.items() if k!="overall" and v>=.55]; beats.append({"frame":f["path"],"timestamp":f["timestamp"],"scores":scores,"tags":tags,"narration":text or f"Evidence moment {i+1} from the source video."})
    return {"duration":analysis["duration"],"transcript":transcript,"frames":analysis["frames"],"top_evidence":analysis["top_evidence"],"beats":beats}
