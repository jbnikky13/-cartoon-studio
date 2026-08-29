"""Low-memory video-to-story/evidence workflow with optional audio analysis."""
from pathlib import Path
import tempfile,io,traceback
import streamlit as st
from PIL import Image
from video_story_extractor import analyze_video_frames
from video_url_adapter import inspect_public_video_url,download_accessible_media
from video_audio_story import analyze_audio_story

def _run_analysis(video_path): return analyze_video_frames(str(video_path),max_frames=8,top_n=6)
def _normalize_scores(s): return {"scene_change":s.get("scene_change",0),"faces_people":s.get("people_faces",0),"documents_text":s.get("documents_text",0),"objects":s.get("objects",0),"locations":s.get("locations",0),"visual_distinctiveness":s.get("visually_distinctive",0),"overall_relevance":s.get("overall",0)}

def render_video_evidence_panel():
 st.subheader("🎥 Video → Story + Evidence"); st.caption("Visual analysis stays lightweight; audio/story processing is a separate bounded step.")
 source=st.radio("Video source",["Upload video","Public video URL"],horizontal=True,key="eb_video_source_type"); video=None; info=st.session_state.get("eb_video_url_info")
 if source=="Upload video":
  video=st.file_uploader("Upload source video",type=["mp4","mov","m4v","webm"],key="eb_video_upload")
  if video: st.caption(f"Selected: {video.name} ({video.size/1024/1024:.1f} MB)")
 else:
  url=st.text_input("Public video URL",placeholder="https://youtube.com/watch?v=...",key="eb_video_url")
  if st.button("🔎 Inspect URL",key="eb_inspect_url") and url.strip():
   try:
    info=inspect_public_video_url(url); st.session_state.eb_video_url_info=info; st.success(f"Found: {info.get('title','Public video')}")
    if info.get("thumbnail_url"): st.image(info["thumbnail_url"],width=240)
    if not info.get("media_url"): st.warning("No directly accessible video media was exposed by this public page.")
   except Exception as e: st.error(f"URL inspection failed: {e}")
  info=st.session_state.get("eb_video_url_info")
 audio_story=st.checkbox("🎙️ Extract audio + build story beats",value=True,key="eb_audio_story")
 transcribe=st.checkbox("🗣️ Speech-to-text transcription",value=False,key="eb_video_transcribe",help="Optional. Uses faster-whisper only when installed and can use substantial memory.")
 transcript_input=st.text_area("Optional transcript/captions",value="",height=90,key="eb_manual_transcript",placeholder="Paste captions/transcript here for story generation without loading a speech model.")
 if st.button("🧠 Analyze Video",type="primary",use_container_width=True,key="eb_analyze_video"):
  try:
   work=Path(tempfile.mkdtemp(prefix="cartoon_video_analysis_"))
   if video: vp=work/video.name; vp.write_bytes(video.getbuffer()); source_name=video.name
   elif info and info.get("media_url"):
    with st.spinner("Fetching accessible public video..."): downloaded=download_accessible_media(info)
    if not downloaded: raise RuntimeError("The public page did not expose an accessible video file.")
    vp=Path(downloaded); source_name=info.get("source_url","")
   else: st.warning("Upload a video or inspect a public URL that exposes accessible video media first."); return
   progress=st.progress(.0,text="Starting visual analysis..."); progress.progress(.15,text="Extracting and scoring visual evidence..."); visual=_run_analysis(vp)
   audio={"audio_path":"","transcript":"","story_beats":[],"note":""}
   if audio_story:
    progress.progress(.72,text="Extracting audio and building story beats..."); audio=analyze_audio_story(str(vp),transcript=transcript_input,transcribe=transcribe,count=max(4,min(6,len(visual.get("top_evidence",[])))))
   progress.progress(1.0,text="Analysis complete")
   st.session_state.eb_video_analysis=visual; st.session_state.eb_video_ranked=visual.get("top_evidence",[]); st.session_state.eb_video_source_url=source_name; st.session_state.eb_video_audio_story=audio
   if audio.get("story_beats"): st.session_state.eb_beats=audio["story_beats"]
   st.success(f"✅ Video analyzed — {len(visual.get('top_evidence',[]))} evidence frames retained" + (f", {len(audio.get('story_beats',[]))} story beats generated" if audio.get("story_beats") else ""))
  except Exception as e:
   st.error(f"❌ Video analysis failed: {e}")
   with st.expander("Technical details"): st.code(traceback.format_exc())
 ranked=st.session_state.get("eb_video_ranked",[])
 if not ranked:return
 audio=st.session_state.get("eb_video_audio_story",{})
 with st.expander("🎙️ Audio + story",expanded=bool(audio.get("story_beats"))):
  if audio.get("audio_path"): st.audio(audio["audio_path"])
  if audio.get("transcript"): st.text_area("Transcript",audio["transcript"],height=150,key="eb_video_transcript_view")
  elif audio.get("note"): st.info(audio["note"])
  if audio.get("story_beats"):
   st.markdown("**Generated story beats**")
   for i,b in enumerate(audio["story_beats"],1): st.write(f"**{i}.** {b}")
 top_n=st.slider("Evidence frames to send",1,min(6,len(ranked)),min(4,len(ranked)),key="eb_video_topn"); st.markdown("**⭐ Strongest evidence**"); selected=[]; cols=st.columns(min(2,len(ranked)))
 for i,rec in enumerate(ranked):
  with cols[i%len(cols)]:
   s=_normalize_scores(rec["scores"]); st.image(rec["path"],caption=f"#{i+1} • {rec['timestamp']}s • Score {s['overall_relevance']}",width=220); st.caption(f"Scene {s['scene_change']} · People {s['faces_people']} · Text {s['documents_text']} · Objects {s['objects']} · Location {s['locations']}")
   if st.checkbox("Use frame",value=i<top_n,key=f"eb_video_use_{i}"): selected.append({**rec,"scores":s})
 if selected and st.button("📌 Send Selected Frames to Evidence Board",use_container_width=True,key="eb_send_video_frames"):
  payload=[]
  for i,rec in enumerate(selected[:6]):
   with Image.open(rec["path"]) as src:
    im=src.convert("RGB"); b=io.BytesIO(); im.save(b,format="JPEG",quality=80,optimize=True); data=b.getvalue()
   payload.append({"name":f"video_evidence_{i+1}_{rec['timestamp']}s.jpg","bytes":data,"url":f"Video source: {st.session_state.get('eb_video_source_url','')} • timestamp: {rec['timestamp']}s","reason":rec.get("reason","evidence frame"),"scores":rec["scores"]})
  st.session_state.eb_video_selected=payload; st.session_state.eb_found=payload; st.session_state.eb_story={"title":"Video Evidence Story","description":"Evidence frames selected from the analyzed video.","text":" ".join(audio.get("story_beats",[])),"url":st.session_state.get("eb_video_source_url","")}; st.success(f"Sent {len(payload)} evidence frames to the board. Open the Evidence Board and choose Discovered pictures.")
