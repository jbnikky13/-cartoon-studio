"""Public video URL adapter for direct files and supported public video pages."""
from pathlib import Path
from urllib.parse import urljoin,urlparse
import tempfile,requests
from bs4 import BeautifulSoup
VIDEO_EXTS=(".mp4",".webm",".mov",".m4v")
SUPPORTED_HOSTS=("youtube.com","youtu.be","x.com","twitter.com","tiktok.com")

def _meta(soup,*names):
 for name in names:
  n=soup.find("meta",attrs={"property":name}) or soup.find("meta",attrs={"name":name})
  if n and n.get("content"): return n["content"].strip()
 return ""

def _is_supported_host(url):
 host=urlparse(url).netloc.lower().split(":")[0]
 return any(host==h or host.endswith("."+h) for h in SUPPORTED_HOSTS)

def inspect_public_video_url(url,timeout=20):
 url=(url or "").strip()
 if not url.startswith(("http://","https://")): raise ValueError("Enter a valid public http(s) URL.")
 # Do not request YouTube/X/TikTok pages with requests first: their anti-bot
 # responses can redirect to Google rate-limit pages. Let yt-dlp handle them.
 if _is_supported_host(url):
  try:
   import yt_dlp
   opts={'quiet':True,'no_warnings':True,'noplaylist':True,'skip_download':True}
   with yt_dlp.YoutubeDL(opts) as ydl:
    info=ydl.extract_info(url,download=False)
   return {'source_url':url,'kind':'supported_video_page','title':info.get('title') or 'Public video','description':info.get('description') or '', 'thumbnail_url':info.get('thumbnail') or '', 'media_url':info.get('url') or '', 'duration':info.get('duration')}
  except Exception as e:
   raise ValueError(f"Could not inspect this public {urlparse(url).netloc} video. The platform may be rate-limiting the server or the video may not be publicly accessible: {e}") from e
 r=requests.get(url,headers={'User-Agent':'CartoonStudioPublicVideo/1.0'},timeout=timeout,allow_redirects=True); r.raise_for_status(); c=r.headers.get('content-type','').lower()
 if c.startswith('video/') or urlparse(r.url).path.lower().endswith(VIDEO_EXTS): return {'source_url':r.url,'kind':'direct_video','title':Path(urlparse(r.url).path).name or 'Video','media_url':r.url,'thumbnail_url':'','description':''}
 if 'text/html' not in c: raise ValueError('The URL is not a public video or HTML video page.')
 soup=BeautifulSoup(r.text,'html.parser'); title=_meta(soup,'og:title','twitter:title') or (soup.title.get_text(' ',strip=True) if soup.title else 'Public video'); desc=_meta(soup,'og:description','description'); thumb=_meta(soup,'og:image','twitter:image'); media=''
 for tag in soup.find_all(['video','source']):
  src=tag.get('src')
  if src: media=urljoin(r.url,src); break
 return {'source_url':r.url,'kind':'video_page','title':title,'description':desc,'thumbnail_url':urljoin(r.url,thumb) if thumb else '','media_url':media}

def download_accessible_media(info,max_mb=250,timeout=60):
 url=info.get('media_url') or info.get('source_url')
 if not url:return None
 if info.get('media_url') and info.get('kind')=='direct_video':
  r=requests.get(url,headers={'User-Agent':'CartoonStudioPublicVideo/1.0'},stream=True,timeout=timeout,allow_redirects=True); r.raise_for_status(); return _stream_to_file(r,max_mb,urlparse(r.url).path)
 try:
  import yt_dlp
  folder=Path(tempfile.mkdtemp(prefix='cartoon_public_video_')); template=str(folder/'source.%(ext)s')
  opts={'outtmpl':template,'format':'best[ext=mp4]/best','noplaylist':True,'quiet':True,'no_warnings':True,'max_filesize':max_mb*1024*1024,'restrictfilenames':True}
  with yt_dlp.YoutubeDL(opts) as ydl: ydl.extract_info(info.get('source_url') or url,download=True)
  files=[p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTS]
  if not files: raise ValueError('No accessible video media was returned by the public page.')
  return str(files[0])
 except Exception as e: raise ValueError(f'Could not retrieve accessible public video: {e}') from e

def _stream_to_file(r,max_mb,path):
 suffix=Path(path).suffix if Path(path).suffix in VIDEO_EXTS else '.mp4'; out=Path(tempfile.mkdtemp(prefix='cartoon_public_video_'))/f'source{suffix}'; total=0
 if r.headers.get('content-length') and int(r.headers['content-length'])>max_mb*1024*1024: raise ValueError(f'Video exceeds {max_mb} MB.')
 with open(out,'wb') as f:
  for chunk in r.iter_content(1024*1024):
   if not chunk:continue
   total+=len(chunk)
   if total>max_mb*1024*1024: out.unlink(missing_ok=True); raise ValueError(f'Video exceeds {max_mb} MB.')
   f.write(chunk)
 return str(out)
