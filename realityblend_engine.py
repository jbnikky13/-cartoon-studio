"""Lightweight RealityBlend compositor with animated backgrounds, motion and action timelines."""
from __future__ import annotations
import asyncio, math, re, subprocess
from dataclasses import dataclass
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg=None
try:
    import edge_tts
    EDGE_TTS_AVAILABLE=True
except ImportError:
    EDGE_TTS_AVAILABLE=False

def synthesize_line(text,voice_id,out_path):
    if not EDGE_TTS_AVAILABLE or not text.strip(): return False
    async def run(): await edge_tts.Communicate(text,voice_id).save(str(out_path))
    try:
        loop=asyncio.new_event_loop(); loop.run_until_complete(run()); loop.close()
        return Path(out_path).exists() and Path(out_path).stat().st_size>0
    except Exception: return False

def get_media_duration(path):
    if imageio_ffmpeg is None: return None
    r=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-i',str(path)],capture_output=True,text=True)
    m=re.search(r'Duration:\s*(\d+):(\d+):(\d+\.\d+)',r.stderr)
    return int(m.group(1))*3600+int(m.group(2))*60+float(m.group(3)) if m else None

def get_safe_font(size=32,bold=True):
    names=['DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf','LiberationSans-Bold.ttf' if bold else 'LiberationSans-Regular.ttf']
    dirs=['/usr/share/fonts/truetype/dejavu','/usr/share/fonts/truetype/liberation2']
    for d,n in zip(dirs,names):
        p=Path(d)/n
        if p.exists(): return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def wrap_caption(text,font,draw,max_width):
    lines=[]; cur=[]
    for word in text.split():
        trial=' '.join(cur+[word])
        if draw.textbbox((0,0),trial,font=font)[2]>max_width and cur: lines.append(' '.join(cur)); cur=[word]
        else: cur.append(word)
    if cur: lines.append(' '.join(cur))
    return lines

def draw_caption(frame,text,speaker=None):
    if not text: return frame
    frame=frame.convert('RGBA'); w,h=frame.size; fs=max(18,int(w*.045)); font=get_safe_font(fs,True); d=ImageDraw.Draw(frame); lines=wrap_caption(text,font,d,int(w*.86)); lh=int(fs*1.3); top=h-(lh*len(lines)+int(fs*.8))-int(h*.04)
    ov=Image.new('RGBA',frame.size,(0,0,0,0)); ImageDraw.Draw(ov).rectangle([0,top,w,h],fill=(0,0,0,130)); frame=Image.alpha_composite(frame,ov); d=ImageDraw.Draw(frame); y=top+int(fs*.4)
    if speaker: d.text((int(w*.07),y),speaker.upper(),font=get_safe_font(int(fs*.8),True),fill=(255,210,90),stroke_width=2,stroke_fill=(0,0,0)); y+=fs
    for line in lines:
        bw=d.textbbox((0,0),line,font=font)[2]; d.text(((w-bw)//2,y),line,font=font,fill='white',stroke_width=2,stroke_fill='black'); y+=lh
    return frame.convert('RGB')

@dataclass
class Character:
    name:str
    image:Image.Image
    x:float=.5
    y:float=.78
    scale:float=.55
    z:int=10
    opacity:float=1.0
    flip:bool=False
    shadow:bool=True
    motion:str='idle'
    action_timeline:str=''
    timeline_offset:float=0.0

@dataclass
class Scene:
    background:Image.Image
    duration:float=5.0
    fps:int=12
    width:int=540
    height:int=960
    camera_zoom:float=1.0
    camera_x:float=.5
    camera_y:float=.5
    brightness:float=1.0
    contrast:float=1.0
    saturation:float=1.0

def load_rgba(source): return source.convert('RGBA') if isinstance(source,Image.Image) else Image.open(source).convert('RGBA')

def remove_simple_background(img,key='auto',tolerance=32):
    im=img.convert('RGBA'); p=im.load(); w,h=im.size; samples=[p[0,0][:3],p[w-1,0][:3],p[0,h-1][:3],p[w-1,h-1][:3]]; bg=tuple(sum(s[i] for s in samples)//4 for i in range(3))
    for y in range(h):
        for x in range(w):
            r,g,b,a=p[x,y]
            if math.dist((r,g,b),bg)<=tolerance: p[x,y]=(r,g,b,0)
    return im

def chroma_key(img,rgb=(0,255,0),similarity=70,blend=20):
    im=img.convert('RGBA'); p=im.load(); w,h=im.size
    for y in range(h):
        for x in range(w):
            r,g,b,a=p[x,y]; d=math.dist((r,g,b),rgb)
            if d<=similarity: p[x,y]=(r,g,b,0)
            elif d<=similarity+blend: p[x,y]=(r,g,b,int(255*(d-similarity)/blend))
    return im

def fit_cover(img,size): return ImageOps.fit(img.convert('RGB'),size,method=Image.Resampling.LANCZOS)

def camera_background(scene,t):
    bg=scene.background.convert('RGB'); w,h=scene.width,scene.height; scale=max(1.0,scene.camera_zoom); base=fit_cover(bg,(max(w,int(w*scale)),max(h,int(h*scale)))); driftx=math.sin(t*.55)*.006; drifty=math.sin(t*.41)*.004; cx=min(1,max(0,scene.camera_x+driftx)); cy=min(1,max(0,scene.camera_y+drifty)); left=int((base.width-w)*cx); top=int((base.height-h)*cy); out=base.crop((left,top,left+w,top+h)); out=ImageEnhance.Brightness(out).enhance(scene.brightness); out=ImageEnhance.Contrast(out).enhance(scene.contrast); return ImageEnhance.Color(out).enhance(scene.saturation)

def _motion_values(motion,t):
    m=(motion or 'idle').lower(); dx=bob=angle=0.0
    if m in ('idle','talk','talking'): bob=math.sin(t*4)*.008
    if m in ('talk','talking'): bob+=math.sin(t*9)*.004
    if m in ('bounce','laugh','celebrate'): bob=abs(math.sin(t*5))*.025
    if m in ('nervous','shake'): dx=math.sin(t*25)*.008; angle=math.sin(t*22)*1.5
    if m=='nod': angle=math.sin(t*5)*4
    if m in ('wave','point','gesture'): bob=math.sin(t*4.5)*.012
    if m=='walk': dx=.08*t; bob=abs(math.sin(t*8))*.012; angle=math.sin(t*8)*2
    if m=='run': dx=.16*t; bob=abs(math.sin(t*13))*.025; angle=math.sin(t*13)*4
    if m=='jump': p=(t*1.1)%1; bob=-(4*p*(1-p))*.16; angle=math.sin(p*math.pi)*3
    if m=='dance': dx=math.sin(t*5.5)*.035; bob=-abs(math.sin(t*5.5))*.018; angle=math.sin(t*5.5)*7
    if m=='slide left': dx=-.16*min(1,t/1.2)
    if m=='slide right': dx=.16*min(1,t/1.2)
    return dx,bob,angle

def paste_character(canvas,char,t):
    img=char.image.convert('RGBA'); img=ImageOps.mirror(img) if char.flip else img; local=max(0,t-char.timeline_offset); motion=char.motion
    if char.action_timeline:
        try:
            from timeline_actions import active_action
            motion,_=active_action(char.action_timeline,local,motion or 'idle')
        except Exception: pass
    target_h=max(16,int(canvas.height*char.scale)); ratio=target_h/max(1,img.height); img=img.resize((max(16,int(img.width*ratio)),target_h),Image.Resampling.LANCZOS); dx,bob,angle=_motion_values(motion,local)
    if angle: img=img.rotate(angle,resample=Image.Resampling.BICUBIC,expand=True)
    if char.opacity<.999: img.putalpha(img.getchannel('A').point(lambda a:int(a*max(0,min(1,char.opacity)))))
    x=int(char.x*canvas.width+dx*canvas.width-img.width/2); y=int(char.y*canvas.height+bob*canvas.height-img.height)
    if char.shadow:
        sw=max(12,int(img.width*.34)); sh=max(4,int(sw*.18)); shad=Image.new('RGBA',canvas.size,(0,0,0,0)); ImageDraw.Draw(shad).ellipse((x+img.width//2-sw//2,int(char.y*canvas.height)-sh//2,x+img.width//2+sw//2,int(char.y*canvas.height)+sh//2),fill=(0,0,0,80)); canvas.alpha_composite(shad.filter(ImageFilter.GaussianBlur(max(1,sw//14))))
    canvas.alpha_composite(img,(x,y))

def render_frame(scene,characters,t,caption_text=None,caption_speaker=None):
    bg=camera_background(scene,t).convert('RGBA')
    for c in sorted(characters,key=lambda c:c.z): paste_character(bg,c,t)
    return draw_caption(bg.convert('RGB'),caption_text,caption_speaker) if caption_text else bg.convert('RGB')

def ffmpeg_exe():
    if imageio_ffmpeg is None: raise RuntimeError('imageio-ffmpeg is required')
    return imageio_ffmpeg.get_ffmpeg_exe()

def render_video(scene,characters,output_path,audio_path=None,progress=None,caption_text=None,caption_speaker=None):
    output_path=Path(output_path); output_path.parent.mkdir(parents=True,exist_ok=True); fps=max(6,min(24,int(scene.fps))); total=max(1,int(round(scene.duration*fps))); cmd=[ffmpeg_exe(),'-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{scene.width}x{scene.height}','-r',str(fps),'-i','-']
    cmd += ['-i',str(audio_path),'-shortest'] if audio_path else ['-an']; cmd += ['-c:v','libx264','-preset','ultrafast','-crf','28','-pix_fmt','yuv420p','-movflags','+faststart',str(output_path)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        chars=list(characters)
        for i in range(total):
            proc.stdin.write(render_frame(scene,chars,i/fps,caption_text,caption_speaker).tobytes())
            if progress: progress((i+1)/total)
        proc.stdin.close(); err=proc.stderr.read().decode('utf-8',errors='ignore'); rc=proc.wait()
    except Exception:
        try: proc.kill()
        except Exception: pass
        raise
    if rc!=0: raise RuntimeError('FFmpeg render failed:\n'+err[-4000:])
    return output_path

def render_timeline_video(scene_template,characters_by_name,rows,voices_by_name,output_path,default_voice='en-US-JennyNeural',progress=None,action_timelines=None):
    output_path=Path(output_path); work=output_path.parent/f'_rb_beats_{output_path.stem}'; work.mkdir(exist_ok=True); clips=[]; elapsed=0.0; action_timelines=action_timelines or {}
    try:
        for i,row in enumerate(rows):
            raw=work/f'raw_{i:04d}.mp3'; speaker=row.speaker.strip().lower(); matched=next((n for n in characters_by_name if n.strip().lower()==speaker),None); voice=voices_by_name.get(matched,default_voice) if matched else default_voice; ok=synthesize_line(row.text,voice,raw); real=get_media_duration(raw) if ok else None; duration=(real or row.duration)+.3; beat=[]
            for name,c in characters_by_name.items(): beat.append(Character(c.name,c.image,c.x,c.y,c.scale,c.z,c.opacity,c.flip,c.shadow,'talk' if name==matched else c.motion,action_timelines.get(name,''),elapsed))
            scene=Scene(scene_template.background,duration,scene_template.fps,scene_template.width,scene_template.height,scene_template.camera_zoom,scene_template.camera_x,scene_template.camera_y,scene_template.brightness,scene_template.contrast,scene_template.saturation); silent=work/f'silent_{i:04d}.mp4'; render_video(scene,beat,silent,progress=lambda p,i=i: progress((i+p)/max(1,len(rows))) if progress else None,caption_text=row.text,caption_speaker=row.speaker if row.speaker!='Narrator' else None); final=work/f'final_{i:04d}.mp4'
            if ok:
                ff=ffmpeg_exe(); wav=work/f'padded_{i:04d}.wav'; subprocess.run([ff,'-y','-i',str(raw),'-af',f'apad=whole_dur={duration}','-t',str(duration),'-ar','16000','-ac','1',str(wav)],capture_output=True); subprocess.run([ff,'-y','-i',str(silent),'-i',str(wav),'-c:v','copy','-c:a','aac','-shortest',str(final)],capture_output=True); wav.unlink(missing_ok=True); silent.unlink(missing_ok=True)
            else: final=silent
            raw.unlink(missing_ok=True); clips.append(final); elapsed+=duration
        concat=work/'concat.txt'
        concat.write_text(''.join(f"file '{c.resolve()}'\n" for c in clips)); result=subprocess.run([ffmpeg_exe(),'-y','-f','concat','-safe','0','-i',str(concat),'-c','copy','-movflags','+faststart',str(output_path)],capture_output=True,text=True)
        if result.returncode!=0: raise RuntimeError('FFmpeg concat failed:\n'+result.stderr[-4000:])
        return output_path
    finally:
        for c in clips:
            try: Path(c).unlink()
            except Exception: pass
        try: (work/'concat.txt').unlink()
        except Exception: pass
        try: work.rmdir()
        except Exception: pass
