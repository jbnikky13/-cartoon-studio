"""Streamlit panel connecting uploaded or direct-public video URLs to Evidence Board."""
from pathlib import Path
import tempfile,io
import streamlit as st
from PIL import Image
from video_story_extractor import extract_video_frames
from video_visual_analysis import analyze_video_frames
from video_url_source import download_public_video

def render_video_evidence_panel():
 st.subheader("🎥 Video → Evidence"); st.caption("Upload a video or provide a direct public video-file URL. The app extracts frames, scores visual evidence, and sends selected moments to the board.")
 source=st.radio("Video source",["Upload video","Public video URL"],horizontal=True,key="eb_video_source_type")
 video=None; url=""
 if source=="Upload video": video=st.file_uploader("Upload source video",type=["mp4","mov","m4v","webm"],key="eb_video_upload")
 else:
  url=st.text_input("Direct public video URL",placeholder="https://example.com/video.mp4",key="eb_video_url"); st.caption("Use a URL that directly serves the video file. This importer does not bypass logins, DRM, paywalls or private/platform-restricted media.")
 if st.button("🧠 Analyze Video Frames",type="primary",use_container_width=True):
  if not video and not url.strip(): st.warning("Upload a video or paste a direct public video URL first.")
  else:
   try:
    work=Path(tempfile.mkdtemp(prefix="cartoon_video_analysis_"))
    if video: vp=work/video.name; vp.write_bytes(video.getbuffer()); source_name=video.name
    else:
     with st.spinner("Downloading public video..."): vp=Path(download_public_video(url)); source_name=url
    with st.spinner("Extracting and scoring visual evidence..."):
     raw=extract_video_frames(vp,output_dir=work/"frames",max_frames=18); ranked=analyze_video_frames(raw["frames"])
    st.session_state.eb_video_ranked=ranked; st.session_state.eb_video_source_url=source_name
    st.success(f"Analyzed {len(ranked)} frames. Highest evidence score: {ranked[0]['scores']['overall_relevance'] if ranked else 0}")
   except Exception as exc: st.error(f"Video analysis failed: {exc}")
 ranked=st.session_state.get("eb_video_ranked",[])
 if not ranked:return
 top_n=st.slider("Number of evidence frames",2,min(6,len(ranked)),min(6,len(ranked)),key="eb_video_topn"); st.markdown("**Top evidence frames**")
 selected=[]; cols=st.columns(min(3,len(ranked)))
 for i,rec in enumerate(ranked[:12]):
  with cols[i%len(cols)]:
   st.image(rec["path"],caption=f"#{i+1} • {rec['timestamp']}s • Score {rec['scores']['overall_relevance']}",width=180); s=rec["scores"]
   st.caption(f"{rec['reason']} · scene {s['scene_change']} · people {s['faces_people']} · text {s['documents_text']} · objects {s['objects']}")
   if st.checkbox("Use frame",value=i<top_n,key=f"eb_video_use_{i}"): selected.append(rec)
 if selected and st.button("📌 Send Selected Frames to Evidence Board",use_container_width=True):
  payload=[]
  for i,rec in enumerate(selected[:6]):
   try:
    im=Image.open(rec["path"]).convert("RGBA"); b=io.BytesIO(); im.save(b,format="PNG"); payload.append({"name":f"video_evidence_{i+1}_{rec['timestamp']}s.png","bytes":b.getvalue(),"url":f"Video source: {st.session_state.get('eb_video_source_url','')} • timestamp: {rec['timestamp']}s","reason":rec["reason"],"scores":rec["scores"]})
   except Exception: pass
  st.session_state.eb_video_selected=payload; st.success(f"Sent {len(payload)} evidence frames to the board.")
