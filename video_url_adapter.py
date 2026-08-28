"""Public video URL adapter; never bypasses private/DRM/paywalled content."""
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
 if not media:
  for script in soup.find_all("script",type="application/ld+json"):
   try:
    data=json.loads(script.string or ""); items=data if isinstance(data,list) else [data]
    for x in items:
     if isinstance(x,dict) and (x.get("contentUrl") or x.get("embedUrl")): media=urljoin(r.url,x.get("contentUrl") or x.get("embedUrl")); break
   except Exception: pass
   if media: break
 return {"source_url":r.url,"kind":"video_page","title":title,"description":desc,"thumbnail_url":urljoin(r.url,thumb) if thumb else "","media_url":media}

def download_accessible_media(info,max_mb=250,timeout=30):
 media=info.get("media_url")
 if not media: return None
 r=requests.get(media,headers={"User-Agent":"CartoonStudioPublicVideo/1.0"},stream=True,timeout=timeout,allow_redirects=True); r.raise_for_status(); c=r.headers.get("content-type","").lower(); path=urlparse(r.url).path.lower()
 if not (c.startswith("video/") or path.endswith(VIDEO_EXTS)): raise ValueError("The page did not expose an accessible video file.")
 if r.headers.get("content-length") and int(r.headers["content-length"])>max_mb*1024*1024: raise ValueError(f"Video exceeds {max_mb} MB.")
 suffix=Path(path).suffix if Path(path).suffix in VIDEO_EXTS else ".mp4"; out=Path(tempfile.mkdtemp(prefix="cartoon_public_video_"))/f"source{suffix}"; total=0
 with open(out,"wb") as f:
  for chunk in r.iter_content(1024*1024):
   if not chunk: continue
   total+=len(chunk)
   if total>max_mb*1024*1024: out.unlink(missing_ok=True); raise ValueError(f"Video exceeds {max_mb} MB.")
   f.write(chunk)
 return str(out)
