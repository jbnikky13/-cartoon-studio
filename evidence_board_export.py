"""Reliable final Evidence Board export pass."""
from pathlib import Path
import re,subprocess,tempfile
import imageio_ffmpeg

def _esc_filter_path(path): return str(path).replace("\\","\\\\").replace(":","\\:").replace("'","\\'")
def _write_text(work,name,text):
 p=Path(work)/name; p.write_text(str(text or ""),encoding="utf-8"); return p
def _clean_text(text,limit=180): return re.sub(r"\s+"," ",str(text or "")).strip()[:limit]
def _duration_for_beat(text): return max(1.6,len(str(text or "").split())/2.3)+0.35

def _run(cmd):
 return subprocess.run(cmd,capture_output=True,text=True)

def finalize_discovery_export(master_path,output_path,beats,items,aspect="16:9",subtitles=True,labels=True,title="DISCOVERY STORY",progress_cb=None):
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe(); master_path=Path(master_path); output_path=Path(output_path); output_path.parent.mkdir(parents=True,exist_ok=True); work=Path(tempfile.mkdtemp(prefix="evidence_export_"))
    try:
        if not master_path.exists() or master_path.stat().st_size==0:return None,"Master video was not created."
        sizes={"16:9":(1280,720),"9:16":(720,1280),"1:1":(900,900)}; ow,oh=sizes.get(aspect,sizes["16:9"])
        filters=[f"scale={ow}:{oh}:force_original_aspect_ratio=increase",f"crop={ow}:{oh}"]; t=0.0
        font="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"; bold="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if not Path(font).exists(): font=bold="Sans"
        for i,beat in enumerate(beats):
            text=_clean_text(getattr(beat,"text","") if hasattr(beat,"text") else "",190); dur=_duration_for_beat(text); start,end=t,t+dur
            if subtitles and text:
                p=_write_text(work,f"subtitle_{i}.txt",text)
                filters.append(f"drawtext=fontfile='{_esc_filter_path(font)}':textfile='{_esc_filter_path(p)}':fontcolor=white:fontsize=26:borderw=3:bordercolor=black:box=1:boxcolor=black@0.72:boxborderw=14:x=(w-text_w)/2:y=h-text_h-42:enable='between(t\\,{start:.3f}\\,{end:.3f})'")
            if labels:
                idx=getattr(beat,"item_index",i) if hasattr(beat,"item_index") else i; name=getattr(items[idx],"name",f"Evidence {idx+1}") if 0<=idx<len(items) else f"Evidence {idx+1}"; p=_write_text(work,f"label_{i}.txt",_clean_text(f"EVIDENCE {idx+1}  •  {name}",80))
                filters.append(f"drawtext=fontfile='{_esc_filter_path(bold)}':textfile='{_esc_filter_path(p)}':fontcolor=white:fontsize=22:borderw=2:bordercolor=black:box=1:boxcolor=black@0.62:boxborderw=10:x=34:y=94:enable='between(t\\,{start:.3f}\\,{end:.3f})'")
            t=end
        if title:
            p=_write_text(work,"title.txt",_clean_text(title,60)); filters.append(f"drawtext=fontfile='{_esc_filter_path(bold)}':textfile='{_esc_filter_path(p)}':fontcolor=white:fontsize=22:borderw=2:bordercolor=black:x=34:y=30")
        vf=",".join(filters); base=[ffmpeg,"-hide_banner","-loglevel","error","-y","-i",str(master_path),"-map","0:v:0","-map","0:a?","-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k","-movflags","+faststart"]
        if progress_cb: progress_cb(.96)
        result=_run(base[:4]+["-vf",vf]+base[4:-2]+[str(output_path)])
        if result.returncode!=0:
            # Retry without drawtext so an export can still be produced if a host FFmpeg lacks a filter/font capability.
            fallback=[ffmpeg,"-hide_banner","-loglevel","error","-y","-i",str(master_path),"-vf",f"scale={ow}:{oh}:force_original_aspect_ratio=increase,crop={ow}:{oh}","-map","0:v:0","-map","0:a?","-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k","-movflags","+faststart",str(output_path)]
            retry=_run(fallback)
            if retry.returncode!=0:return None,"FFmpeg final export failed: "+(retry.stderr or result.stderr)[-3000:]
            warning="Export completed without burned subtitles/labels because the FFmpeg filter pass failed."
        else: warning=None
        if progress_cb: progress_cb(1.0)
        return output_path,warning
    finally:
        for p in work.glob("*"):
            try:p.unlink()
            except Exception:pass
        try:work.rmdir()
        except Exception:pass
