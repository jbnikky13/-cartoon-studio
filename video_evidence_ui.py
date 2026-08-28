"""Streamlit panel connecting video sources to the visual evidence scorer."""
from pathlib import Path
import tempfile,io,traceback
import streamlit as st
from PIL import Image
from video_story_extractor import extract_video_frames
from video_visual_analysis import analyze_video_frames
from video_url_adapter import inspect_public_video_url,download_accessible_media

def _run_analysis(video_path,work_dir):
    raw=extract_video_frames(str(video_path),output_dir=work_dir/"frames",max_frames=18)
    if not raw.get("frames"): raise RuntimeError("No video frames could be extracted. Check that the video is valid and FFmpeg is available.")
    ranked=analyze_video_frames(raw["frames"])
    return raw,ranked

def render_video_evidence_panel():
    st.subheader("🎥 Video → Evidence")
    st.caption("Upload a video or paste a public video page/direct-file URL.")
    source=st.radio("Video source",["Upload video","Public video URL"],horizontal=True,key="eb_video_source_type")
    video=None; info=None
    if source=="Upload video":
        video=st.file_uploader("Upload source video",type=["mp4","mov","m4v","webm"],key="eb_video_upload")
        if video: st.caption(f"Selected: {video.name} ({len(video.getvalue())/1024/1024:.1f} MB)")
    else:
        url=st.text_input("Public video URL",placeholder="https://example.com/video-page",key="eb_video_url")
        if st.button("🔎 Inspect URL",key="eb_inspect_url") and url.strip():
            try:
                info=inspect_public_video_url(url); st.session_state.eb_video_url_info=info
                st.success(f"Found: {info.get('title','Public video')}")
                if info.get("thumbnail_url"): st.image(info["thumbnail_url"],width=280)
                if not info.get("media_url"): st.warning("This page does not expose directly accessible video media. Upload the video or use a direct public video-file URL.")
            except Exception as e: st.error(f"URL inspection failed: {e}")
        info=st.session_state.get("eb_video_url_info")
    if st.button("🧠 Analyze Video Frames",type="primary",use_container_width=True,key="eb_analyze_video"):
        try:
            work=Path(tempfile.mkdtemp(prefix="cartoon_video_analysis_"))
            if video:
                vp=work/video.name; vp.write_bytes(video.getbuffer()); source_name=video.name
            elif info and info.get("media_url"):
                with st.spinner("Fetching accessible public video..."):
                    downloaded=download_accessible_media(info)
                if not downloaded: raise RuntimeError("The public page did not expose an accessible video file.")
                vp=Path(downloaded); source_name=info.get("source_url","")
            else:
                st.warning("Upload a video or inspect a public URL that exposes accessible video media first."); return
            progress=st.progress(0,text="Starting video analysis...")
            progress.progress(.15,text="Extracting video frames...")
            raw,ranked=_run_analysis(vp,work)
            progress.progress(1.0,text=f"Finished — analyzed {len(ranked)} frames")
            st.session_state.eb_video_ranked=ranked; st.session_state.eb_video_source_url=source_name
            st.success(f"✅ Analyzed {len(ranked)} frames. Top evidence score: {ranked[0]['scores']['overall_relevance'] if ranked else 0}")
        except Exception as e:
            st.error(f"❌ Video analysis failed: {e}")
            with st.expander("Technical details"):
                st.code(traceback.format_exc())
    ranked=st.session_state.get("eb_video_ranked",[])
    if not ranked:return
    top_n=st.slider("Number of evidence frames",2,min(6,len(ranked)),min(6,len(ranked)),key="eb_video_topn")
    st.markdown("**Top evidence frames**")
    selected=[]; cols=st.columns(min(3,len(ranked)))
    for i,rec in enumerate(ranked[:12]):
        with cols[i%len(cols)]:
            st.image(rec["path"],caption=f"#{i+1} • {rec['timestamp']}s • Score {rec['scores']['overall_relevance']}",width=180)
            s=rec["scores"]; st.caption(f"{rec['reason']} · scene {s['scene_change']} · people {s['faces_people']} · text {s['documents_text']} · objects {s['objects']}")
            if st.checkbox("Use frame",value=i<top_n,key=f"eb_video_use_{i}"): selected.append(rec)
    if selected and st.button("📌 Send Selected Frames to Evidence Board",use_container_width=True,key="eb_send_video_frames"):
        payload=[]
        for i,rec in enumerate(selected[:6]):
            im=Image.open(rec["path"]).convert("RGBA"); b=io.BytesIO(); im.save(b,format="PNG")
            payload.append({"name":f"video_evidence_{i+1}_{rec['timestamp']}s.png","bytes":b.getvalue(),"url":f"Video source: {st.session_state.get('eb_video_source_url','')} • timestamp: {rec['timestamp']}s","reason":rec["reason"],"scores":rec["scores"]})
        st.session_state.eb_video_selected=payload; st.success(f"Sent {len(payload)} evidence frames to the board.")
