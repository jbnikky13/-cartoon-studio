"""Public video URL adapter for direct files and supported public video pages.
Uses yt-dlp only for publicly accessible media; never bypasses private content, DRM,
login walls, paywalls, or access controls.
"""
from pathlib import Path
from urllib.parse import urljoin,urlparse
import json,tempfile,requests
from bs4 import BeautifulSoup
VIDEO_EXTS=(".mp4",".webm",".mov",".m4v")

def _meta(soup,*names):
 for name in names:
  n=soup.find("meta",attrs={"property":name}) or soup.find("meta",attrs={"name":name})
  if n and n.get("content"): return n["content"].strip()
 return ""

def inspect_public_video_url(url,timeout=20):
 url=(url or "").strip()
 if not url.startswith(("http://","https://")): raise ValueError("Enter a valid public http(s) URL.")
 r=requests.get(url,headers={"User-Agent":"CartoonStudioPublicVideo/1.0"},timeout=timeout,allow_redirects=True); r.raise_for_status(); c=r.headers.get("content-type","").lower()
 if c.startswith("video/") or urlparse(r.url).path.lower().endswith(VIDEO_EXTS): return {"source_url":r.url,"kind":"direct_video","title":Path(urlparse(r.url).path).name or "Video","media_url":r.url,"thumbnail_url":"","description":""}
 if "text/html" not in c: raise ValueError("The URL is not a public video or HTML video page.")
 soup=BeautifulSoup(r.text,"html.parser"); title=_meta(soup,"og:title","twitter:title") or (soup.title.get_text(" ",strip=True) if soup.title else "Public video"); desc=_meta(soup,"og:description","description"); thumb=_meta(soup,"og:image","twitter:image"); media=""
 for tag in soup.find_all(["video","source"]):
  src=tag.get("src")
  if src: media=urljoin(r.url,src); break
 return {"source_url":r.url,"kind":"video_page","title":title,"description":desc,"thumbnail_url":urljoin(r.url,thumb) if thumb else "","media_url":media}

def download_accessible_media(info,max_mb=250,timeout=60):
 url=info.get("media_url") or info.get("source_url")
 if not url:return None
 # First use a directly exposed media URL when available.
 if info.get("media_url"):
  r=requests.get(url,headers={"User-Agent":"CartoonStudioPublicVideo/1.0"},stream=True,timeout=timeout,allow_redirects=True); r.raise_for_status(); c=r.headers.get("content-type","").lower(); path=urlparse(r.url).path.lower()
  if c.startswith("video/") or path.endswith(VIDEO_EXTS): return _stream_to_file(r,max_mb,path)
 # Fall back to yt-dlp for supported public video pages such as YouTube, X and TikTok.
 try:
  import yt_dlp
  folder=Path(tempfile.mkdtemp(prefix="cartoon_public_video_")); template=str(folder/"source.%(ext)s")
  opts={'outtmpl':template,'format':'best[ext=mp4]/best','noplaylist':True,'quiet':True,'no_warnings':True,'max_filesize':max_mb*1024*1024,'restrictfilenames':True}
  with yt_dlp.YoutubeDL(opts) as ydl:
   ydl.extract_info(info.get("source_url") or url,download=True)
  files=[p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTS]
  if not files: raise ValueError("No accessible video media was returned by the public page.")
  return str(files[0])
 except Exception as e:
  raise ValueError(f"Could not retrieve accessible video from this public page: {e}") from e

def _stream_to_file(r,max_mb,path):
 suffix=Path(path).suffix if Path(path).suffix in VIDEO_EXTS else ".mp4"; out=Path(tempfile.mkdtemp(prefix="cartoon_public_video_"))/f"source{suffix}"; total=0
 if r.headers.get("content-length") and int(r.headers["content-length"])>max_mb*1024*1024: raise ValueError(f"Video exceeds {max_mb} MB.")
 with open(out,"wb") as f:
  for chunk in r.iter_content(1024*1024):
   if not chunk:continue
   total+=len(chunk)
   if total>max_mb*1024*1024: out.unlink(missing_ok=True); raise ValueError(f"Video exceeds {max_mb} MB.")
   f.write(chunk)
 return str(out)
