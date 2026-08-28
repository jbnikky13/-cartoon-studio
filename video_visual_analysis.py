"""Deployment-safe visual evidence scoring for sampled video frames.

OpenCV is optional. The base implementation uses only Pillow, so video
analysis does not fail on hosts that do not install OpenCV/NumPy.
"""
from PIL import Image,ImageStat,ImageFilter,ImageChops
try:
 import cv2
 CV2_AVAILABLE=True
except Exception:
 cv2=None; CV2_AVAILABLE=False

def _resize(img,w=320):
 r=w/max(1,img.width); return img.resize((w,max(1,int(img.height*r))),Image.Resampling.BILINEAR)
def _edge(img): return max(0,min(100,ImageStat.Stat(img.convert('L').filter(ImageFilter.FIND_EDGES)).mean[0]*2.2))
def _color(img): return max(0,min(100,sum(ImageStat.Stat(img.convert('RGB')).stddev)/3*1.6))
def _cv(img):
 if not CV2_AVAILABLE:return {'faces':0,'text':0,'objects':0}
 import numpy as np, math
 arr=cv2.cvtColor(np.array(img),cv2.COLOR_RGB2BGR); gray=cv2.cvtColor(arr,cv2.COLOR_BGR2GRAY); faces=0
 try:
  clf=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml'); faces=len(clf.detectMultiScale(gray,1.1,4,minSize=(28,28))) if not clf.empty() else 0
 except Exception: pass
 lines=cv2.HoughLinesP(cv2.Canny(gray,80,180),1,math.pi/180,45,minLineLength=max(20,gray.shape[1]//8),maxLineGap=8)
 return {'faces':min(100,faces*25),'text':min(100,(len(lines) if lines is not None else 0)*4),'objects':min(100,float(cv2.Laplacian(gray,cv2.CV_64F).var())/25)}
def analyze_frame(image_path,previous_image=None):
 img=_resize(Image.open(image_path).convert('RGB')); prev=_resize(Image.open(previous_image).convert('RGB')) if previous_image else None; f=_cv(img); scene=0
 if prev:
  # PIL-only difference avoids a mandatory NumPy dependency.
  diff=ImageChops.difference(img,prev); scene=min(100,ImageStat.Stat(diff).mean[0]*2)
 distinct=min(100,.55*_color(img)+.45*_edge(img)); location=min(100,.65*_color(img)+.35*_edge(img))
 s={'scene_change':round(scene,1),'faces_people':round(f['faces'],1),'documents_text':round(f['text'],1),'objects':round(f['objects'],1),'locations':round(location,1),'visual_distinctiveness':round(distinct,1)}
 s['overall_relevance']=round(.20*s['scene_change']+.18*s['faces_people']+.17*s['documents_text']+.15*s['objects']+.15*s['locations']+.15*s['visual_distinctiveness'],1); return s
def analyze_video_frames(frame_records):
 reasons={'scene_change':'major scene change','faces_people':'person/face detected','documents_text':'document or text-like structure','objects':'strong object/detail structure','locations':'rich location/scene composition','visual_distinctiveness':'visually distinctive frame'}; out=[]; prev=None
 for rec in frame_records:
  scores=analyze_frame(rec['path'],prev); best=max(scores,key=scores.get); item=dict(rec); item['scores']=scores; item['reason']=reasons.get(best,'strong evidence frame'); out.append(item); prev=rec['path']
 return sorted(out,key=lambda x:x['scores']['overall_relevance'],reverse=True)
