"""Download a directly accessible public video URL for local analysis. Does not bypass logins, DRM, paywalls or private content."""
from pathlib import Path
import tempfile,requests

def download_public_video(url,max_mb=250,timeout=30):
 url=(url or '').strip()
 if not url.startswith(('http://','https://')): raise ValueError('Enter a valid http(s) video URL.')
 r=requests.get(url,headers={'User-Agent':'CartoonStudioVideoImporter/1.0'},stream=True,timeout=timeout,allow_redirects=True); r.raise_for_status()
 c=r.headers.get('content-type','').lower(); direct=url.lower().split('?')[0].endswith(('.mp4','.webm','.mov','.m4v'))
 if c and not c.startswith('video/') and not direct: raise ValueError('This is not a directly accessible video file. Use a direct public video URL or upload the video.')
 if r.headers.get('content-length') and int(r.headers['content-length'])>max_mb*1024*1024: raise ValueError(f'Video is larger than the {max_mb} MB limit.')
 suffix='.mp4' if 'mp4' in c or direct and '.mp4' in url.lower() else '.webm' if 'webm' in c else '.mov' if 'mov' in c or '.mov' in url.lower() else '.m4v'
 path=Path(tempfile.mkdtemp(prefix='cartoon_video_url_'))/('source'+suffix); total=0
 with open(path,'wb') as f:
  for chunk in r.iter_content(1024*1024):
   if not chunk: continue
   total+=len(chunk)
   if total>max_mb*1024*1024: path.unlink(missing_ok=True); raise ValueError(f'Video exceeded the {max_mb} MB limit.')
   f.write(chunk)
 return str(path)
