"""Streamlit panel connecting video frame scoring to Evidence Board."""
from pathlib import Path
import tempfile, io
import streamlit as st
from PIL import Image
from video_story_extractor import extract_video_frames
from video_visual_analysis import analyze_video_frames

def render_video_evidence_panel():
    st.subheader("🎥 Video → Evidence")
    st.caption("Upload a video, score its frames, and send the strongest evidence directly to the board.")
    video=st.file_uploader("Upload source video",type=["mp4","mov","m4v","webm"],key="eb_video_source")
    if not video: return
    if st.button("🧠 Analyze Video Frames",type="primary",use_container_width=True):
        try:
            work=Path(tempfile.mkdtemp(prefix="cartoon_video_analysis_")); vp=work/video.name; vp.write_bytes(video.getbuffer())
            with st.spinner("Extracting and scoring visual evidence..."):
                raw=extract_video_frames(vp,output_dir=work/"frames",max_frames=18); ranked=analyze_video_frames(raw["frames"])
            st.session_state.eb_video_ranked=ranked
            st.success(f"Analyzed {len(ranked)} frames. Highest score: {ranked[0]['scores']['overall_relevance'] if ranked else 0}")
        except Exception as exc: st.error(f"Video analysis failed: {exc}")
    ranked=st.session_state.get("eb_video_ranked",[])
    if not ranked: return
    top_n=st.slider("Number of evidence frames",2,min(6,len(ranked)),min(6,len(ranked)),key="eb_video_topn")
    st.markdown("**Top evidence frames**")
    selected=[]; cols=st.columns(min(3,len(ranked)))
    for i,rec in enumerate(ranked[:min(12,len(ranked))]):
        with cols[i%len(cols)]:
            st.image(rec["path"],caption=f"#{i+1} • {rec['timestamp']}s • Score {rec['scores']['overall_relevance']}",width=180)
            s=rec["scores"]; st.caption(f"{rec['reason']} · scene {s['scene_change']} · people {s['faces_people']} · text {s['documents_text']}")
            if st.checkbox("Use frame",value=i<top_n,key=f"eb_video_use_{i}"): selected.append(rec)
    if selected and st.button("📌 Send Selected Frames to Evidence Board",use_container_width=True):
        payload=[]
        for i,rec in enumerate(selected[:6]):
            try:
                im=Image.open(rec["path"]).convert("RGBA"); b=io.BytesIO(); im.save(b,format="PNG")
                payload.append({"name":f"video_evidence_{i+1}_{rec['timestamp']}s.png","bytes":b.getvalue(),"url":f"Video timestamp: {rec['timestamp']}s","reason":rec["reason"],"scores":rec["scores"]})
            except Exception: pass
        st.session_state.eb_video_selected=payload; st.success(f"Sent {len(payload)} evidence frames to the board.")
