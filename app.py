"""
Cartoon Studio V6 shell.
Adds optional global motion enhancement for Classic Cartoon while keeping its
existing automatic gesture system, plus the expanded RealityBlend motion/art
features.
"""
import sys, os
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Cartoon Studio V6",page_icon="🎬",layout="wide",initial_sidebar_state="expanded")

REALITYBLEND_AVAILABLE=False; REALITYBLEND_ERROR=None
try:
    from realityblend_ui import render_realityblend
    REALITYBLEND_AVAILABLE=True
except Exception as exc: REALITYBLEND_ERROR=exc

CLASSIC_AVAILABLE=False; CLASSIC_ERROR=None
try:
    from classic_cartoon_ui import render_classic_cartoon, join_videos
    CLASSIC_AVAILABLE=True
except Exception as exc: CLASSIC_ERROR=exc

EXPLAINER_STUDIO_AVAILABLE=False; EXPLAINER_STUDIO_ERROR=None
try:
    from explainer_studio_ui import render_explainer_studio
    EXPLAINER_STUDIO_AVAILABLE=True
except Exception as exc: EXPLAINER_STUDIO_ERROR=exc

EVIDENCE_BOARD_AVAILABLE=False; EVIDENCE_BOARD_ERROR=None
try:
    from evidence_board_ui import render_evidence_board_studio
    EVIDENCE_BOARD_AVAILABLE=True
except Exception as exc: EVIDENCE_BOARD_ERROR=exc

MOTION_PRESETS=["Automatic (dialogue gestures)","Idle","Talk","Walk","Run","Bounce","Float","Nod","Wave","Point","Shake","Spin","Slide Left","Slide Right","Pulse"]

# Optional Classic motion override. Existing dialogue gesture behavior remains
# the default, while a selected preset can drive the whole-body sprite motion.
CLASSIC_MOTION_MAP={"Idle":"None","Talk":"Talking Hands","Walk":"Talking Hands","Run":"Laughing","Bounce":"Laughing","Float":"Thinking","Nod":"Thinking","Wave":"Waving","Point":"Pointing","Shake":"Nervous","Spin":"Waving","Slide Left":"None","Slide Right":"None","Pulse":"None"}

def apply_classic_motion_override(label):
    if label==MOTION_PRESETS[0]: return
    try:
        import sprite_renderer as SPRITE
        if not hasattr(SPRITE,"_v6_original_compose_character_frame"):
            SPRITE._v6_original_compose_character_frame=SPRITE.compose_character_frame
        original=SPRITE._v6_original_compose_character_frame
        gesture=CLASSIC_MOTION_MAP.get(label,"None")
        def wrapped(character_name,global_frame,talking,seed,scale=1.0,gesture=gesture):
            return original(character_name,global_frame,talking,seed,scale,gesture=gesture)
        SPRITE.compose_character_frame=wrapped
    except Exception:
        pass

st.markdown("""<style>.block-container{padding-top:1.5rem;padding-bottom:3rem}.v6-card{padding:1rem 1.2rem;border:1px solid rgba(128,128,128,.25);border-radius:14px;margin-bottom:1rem}.v6-badge{display:inline-block;padding:.25rem .6rem;border-radius:999px;font-size:.8rem;font-weight:600;background:rgba(70,130,180,.14)}</style>""",unsafe_allow_html=True)
st.title("🎬 Cartoon Studio V6")
st.caption("Character dialogue cartoons, faceless explainers, RealityBlend scenes, and evidence-board videos — one lightweight studio.")

with st.sidebar:
    st.header("🎛️ Studio")
    mode=st.radio("Creation mode",["🎭 Classic Cartoon","🌍 RealityBlend","📊 Explainer","🕵️ Evidence Board","🎞️ Join Clips"],index=0)
    st.divider()
    if mode=="🎭 Classic Cartoon":
        st.subheader("🎞️ Motion")
        classic_motion=st.selectbox("Character movement",MOTION_PRESETS,key="classic_motion")
        st.caption("Automatic keeps the existing dialogue-driven gestures. Presets add a stronger whole-body movement style.")
        apply_classic_motion_override(classic_motion)
    st.caption("Mode status:")
    st.caption(f"{'✅' if CLASSIC_AVAILABLE else '❌'} Classic Cartoon")
    st.caption(f"{'✅' if REALITYBLEND_AVAILABLE else '❌'} RealityBlend")
    st.caption(f"{'✅' if EXPLAINER_STUDIO_AVAILABLE else '❌'} Explainer")
    st.caption(f"{'✅' if EVIDENCE_BOARD_AVAILABLE else '❌'} Evidence Board")

if mode=="🎭 Classic Cartoon":
    if CLASSIC_AVAILABLE: render_classic_cartoon()
    else: st.error("Classic Cartoon mode could not be loaded."); st.code(str(CLASSIC_ERROR))

elif mode=="🌍 RealityBlend":
    if REALITYBLEND_AVAILABLE: render_realityblend()
    else: st.error("RealityBlend could not be loaded."); st.code(str(REALITYBLEND_ERROR))

elif mode=="📊 Explainer":
    if EXPLAINER_STUDIO_AVAILABLE: render_explainer_studio()
    else: st.error("Explainer mode could not be loaded."); st.code(str(EXPLAINER_STUDIO_ERROR))

elif mode=="🕵️ Evidence Board":
    if EVIDENCE_BOARD_AVAILABLE: render_evidence_board_studio()
    else: st.error("Evidence Board could not be loaded."); st.code(str(EVIDENCE_BOARD_ERROR))

elif mode=="🎞️ Join Clips":
    st.header("🎞️ Join Clips")
    st.write("Combine exported clips from any mode into one video.")
    if not CLASSIC_AVAILABLE:
        st.error("Join Clips needs classic_cartoon_ui.py.")
    else:
        uploads=st.file_uploader("Upload MP4 clips, in the order you want them joined",type=["mp4","mov","m4v"],accept_multiple_files=True)
        if uploads:
            st.success(f"{len(uploads)} clip(s) ready.")
            for i,upload in enumerate(uploads,1): st.write(f"{i}. {upload.name}")
            if st.button("🔗 Join Clips",type="primary"):
                with st.spinner("Joining clips..."): result_path,err=join_videos(uploads)
                if err: st.error(f"Join failed: {err}")
                elif result_path and Path(result_path).exists():
                    video_bytes=Path(result_path).read_bytes(); st.success("Joined successfully."); st.video(video_bytes)
                    st.download_button("⬇️ Download Joined MP4",data=video_bytes,file_name="joined_episode.mp4",mime="video/mp4")
                    try: Path(result_path).unlink()
                    except Exception: pass
                else: st.error("Join finished, but no output file was produced.")

st.divider()
with st.expander("🔧 V6 Diagnostics"):
    st.write("Python:",sys.version.split()[0]); st.write("Working directory:",os.getcwd())
    st.write("Modes",{"Classic Cartoon":CLASSIC_AVAILABLE,"RealityBlend":REALITYBLEND_AVAILABLE,"Explainer":EXPLAINER_STUDIO_AVAILABLE,"Evidence Board":EVIDENCE_BOARD_AVAILABLE})
    if CLASSIC_ERROR: st.write("Classic Cartoon import error:",repr(CLASSIC_ERROR))
    if REALITYBLEND_ERROR: st.write("RealityBlend import error:",repr(REALITYBLEND_ERROR))
    if EXPLAINER_STUDIO_ERROR: st.write("Explainer import error:",repr(EXPLAINER_STUDIO_ERROR))
    if EVIDENCE_BOARD_ERROR: st.write("Evidence Board import error:",repr(EVIDENCE_BOARD_ERROR))
    st.write("Motion engine:",Path("motion_presets.py").exists())
    st.write("Expanded art pack:",Path("realityblend_art.py").exists())
st.caption("Cartoon Studio V6")
