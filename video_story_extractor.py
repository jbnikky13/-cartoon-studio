"""Video evidence analyzer: sample frames and score visual signals.

Scores are lightweight CV heuristics designed to run locally. They are not
identity recognition and should be treated as evidence-ranking signals.
"""
from pathlib import Path
import math, re, subprocess, tempfile
import imageio_ffmpeg
from PIL import Image, ImageStat, ImageFilter


def extract_video_frames(video_path, output_dir=None, max_frames=24):
    video_path=Path(video_path)
    if not video_path.exists(): raise FileNotFoundError(video_path)
    out=Path(output_dir or tempfile.mkdtemp(prefix="video_story_frames_")); out.mkdir(parents=True,exist_ok=True)
    ff=imageio_ffmpeg.get_ffmpeg_exe(); probe=subprocess.run([ff,"-i",str(video_path)],capture_output=True,text=True)
    m=re.search(r"Duration:\s+(\d+):(\d+):(\d+(?:\.\d+)?)",probe.stderr)
    duration=(int(m.group(1))*3600+int(m.group(2))*60+float(m.group(3))) if m else 30.0
    count=max(1,min(max_frames,int(math.ceil(duration/4)))); paths=[]
    for i in range(count):
        t=0 if count==1 else duration*i/(count-1); p=out/f"evidence_{i+1:02d}.jpg"
        subprocess.run([ff,"-y","-ss",str(t),"-i",str(video_path),"-frames:v","1","-q:v","3",str(p)],capture_output=True)
        if p.exists(): paths.append({"path":str(p),"timestamp":round(t,2)})
    return {"duration":duration,"frames":paths}


def _variance(img):
    return sum(ImageStat.Stat(img.convert("L")).var)/max(1,len(ImageStat.Stat(img.convert("L")).var))


def _edge_score(img):
    gray=img.convert("L").resize((160,90)).filter(ImageFilter.FIND_EDGES)
    return min(1.0,ImageStat.Stat(gray).mean/80.0)


def _skin_score(img):
    im=img.convert("RGB").resize((96,54)); px=list(im.getdata()); hits=0
    for r,g,b in px:
        if r>80 and r>g*1.12 and g>b*1.08 and r-g>15: hits+=1
    return min(1.0,hits/max(1,len(px))*5.0)


def _text_score(img):
    # Text/document proxy: dense horizontal/vertical edges and relatively low color variance.
    small=img.convert("L").resize((160,90)); e=small.filter(ImageFilter.FIND_EDGES)
    edge=ImageStat.Stat(e).mean/255.0; var=_variance(img)
    return max(0.0,min(1.0,edge*3.0 + (1.0-min(1.0,var/2500.0))*0.25))


def score_frame(img, previous=None):
    if not isinstance(img,Image.Image): img=Image.open(img)
    img=img.convert("RGB")
    visual=_edge_score(img); texture=min(1.0,_variance(img)/1800.0)
    people=_skin_score(img)
    text=_text_score(img)
    # Scene-change score compares compact grayscale pixels with the previous frame.
    scene=0.0
    if previous is not None:
        a=img.resize((64,36)).convert("L"); b=previous.resize((64,36)).convert("L")
        diff=sum(abs(x-y) for x,y in zip(a.getdata(),b.getdata()))/(64*36*255)
        scene=min(1.0,diff*3.2)
    distinctive=min(1.0,visual*.42+texture*.33+scene*.25)
    # Object/location are visual proxies; advanced models can replace these later.
    objects=min(1.0,visual*.55+texture*.45)
    location=min(1.0,visual*.35+(1-people)*.25+texture*.40)
    overall=(scene*.18+people*.16+text*.16+objects*.16+location*.14+distinctive*.20)
    return {"scene_change":round(scene,3),"people_faces":round(people,3),"documents_text":round(text,3),"objects":round(objects,3),"locations":round(location,3),"visually_distinctive":round(distinctive,3),"overall":round(overall,3)}


def rank_evidence_frames(frame_records, top_n=10):
    return sorted(frame_records,key=lambda x:x.get("scores",{}).get("overall",0),reverse=True)[:top_n]


def analyze_video_frames(video_path,max_frames=24,top_n=10):
    extracted=extract_video_frames(video_path,max_frames=max_frames); records=[]; previous=None
    for f in extracted["frames"]:
        img=Image.open(f["path"]).convert("RGB"); scores=score_frame(img,previous); previous=img
        records.append({**f,"scores":scores})
    return {"duration":extracted["duration"],"frames":records,"top_evidence":rank_evidence_frames(records,top_n)}


def extract_video_audio(video_path,output_path=None):
    out=Path(output_path or Path(tempfile.mkdtemp(prefix="video_story_audio_"))/"audio.wav"); ff=imageio_ffmpeg.get_ffmpeg_exe()
    r=subprocess.run([ff,"-y","-i",str(video_path),"-vn","-ac","1","-ar","16000","-c:a","pcm_s16le",str(out)],capture_output=True,text=True)
    return str(out) if r.returncode==0 and out.exists() else None


def transcribe_video(video_path,model_size="tiny"):
    try: from faster_whisper import WhisperModel
    except ImportError: return {"available":False,"text":"","segments":[]}
    audio=extract_video_audio(video_path)
    if not audio: return {"available":True,"text":"","segments":[]}
    model=WhisperModel(model_size,device="cpu",compute_type="int8"); segments,_=model.transcribe(audio,beam_size=1)
    data=[{"start":round(s.start,2),"end":round(s.end,2),"text":s.text.strip()} for s in segments]
    return {"available":True,"text":" ".join(x["text"] for x in data),"segments":data}


def build_video_story(video_path,max_frames=24,transcribe=True):
    analysis=analyze_video_frames(video_path,max_frames=max_frames); transcript=transcribe_video(video_path) if transcribe else {"available":False,"text":"","segments":[]}
    beats=[]
    for i,f in enumerate(analysis["top_evidence"]):
        text=""
        if transcript.get("segments"):
            t=f["timestamp"]; nearby=min(transcript["segments"],key=lambda s:abs(s["start"]-t))
            if abs(nearby["start"]-t)<=4: text=nearby["text"]
        scores=f["scores"]; tags=[k.replace("_"," ") for k,v in scores.items() if k!="overall" and v>=.55]
        beats.append({"frame":f["path"],"timestamp":f["timestamp"],"scores":scores,"tags":tags,"narration":text or f"Evidence moment {i+1} from the source video."})
    return {"duration":analysis["duration"],"transcript":transcript,"frames":analysis["frames"],"top_evidence":analysis["top_evidence"],"beats":beats}
