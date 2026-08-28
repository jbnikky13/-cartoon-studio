"""RealityBlend V6 UI: animated backgrounds, art worlds, stick figures, motion and action timelines."""
from pathlib import Path
import tempfile
import streamlit as st
from PIL import Image
import realityblend_engine as rb
from realityblend_engine import Scene,load_rgba,remove_simple_background,chroma_key,render_timeline_video,EDGE_TTS_AVAILABLE
from realityblend_assets import BUILTIN_BACKGROUNDS,STICK_FIGURE_STYLES,generate_builtin_background,preview_builtin_background,generate_stick_figure
from realityblend_art import ART_BACKGROUNDS,generate_art_background,preview_art_background
from motion_presets import MOTION_PRESETS
from realityblend_models import build_timeline

NARRATOR_VOICES={"Bright / Female":"en-US-AriaNeural","Warm / Female":"en-US-JennyNeural","Calm / Male":"en-US-DavisNeural","Deep / Male":"en-US-GuyNeural"}
ACTION_HINT="0-2: Walk In\n2-4: Talk\n4-5: Point\n5-7: Walk"

def _camera_background_with_builtin(scene,t):
    selected=getattr(rb,"ACTIVE_BUILTIN_BACKGROUND",None)
    if selected:
        bg=generate_art_background(selected,(scene.width,scene.height),t) if selected in ART_BACKGROUNDS else generate_builtin_background(selected,(scene.width,scene.height),t)
        from PIL import ImageEnhance
        bg=ImageEnhance.Brightness(bg).enhance(scene.brightness); bg=ImageEnhance.Contrast(bg).enhance(scene.contrast); bg=ImageEnhance.Color(bg).enhance(scene.saturation); return bg
    return rb._original_camera_background(scene,t)
if not hasattr(rb,"_original_camera_background"):
    rb._original_camera_background=rb.camera_background; rb.camera_background=_camera_background_with_builtin


def render_realityblend():
    st.header("🌍 RealityBlend V6")
    st.caption("Put characters into real scenes, animated worlds, or lightweight stick-figure sets.")
    st.subheader("1. Background")
    source=st.radio("Background source",["Upload image","Built-in animated"],horizontal=True,key="rb_bg_source"); rb.ACTIVE_BUILTIN_BACKGROUND=None
    if source=="Built-in animated":
        groups={"Classic Motion Worlds":BUILTIN_BACKGROUNDS,"Art & Fantasy Worlds":ART_BACKGROUNDS}; group=st.selectbox("Background collection",list(groups),key="rb_bg_group"); name=st.selectbox("Choose an animated background",groups[group],key="rb_builtin_bg"); preview=preview_art_background(name) if name in ART_BACKGROUNDS else preview_builtin_background(name,size=(270,480)); st.image(preview,caption=f"Preview · {name}",width=220); rb.ACTIVE_BUILTIN_BACKGROUND=name; bg=generate_art_background(name,(540,960),0) if name in ART_BACKGROUNDS else generate_builtin_background(name,(540,960),0)
    else:
        f=st.file_uploader("Upload a real background",type=["png","jpg","jpeg"],key="rb_background")
        if not f: st.info("Upload a background image or switch to Built-in animated."); return
        bg=Image.open(f).convert('RGB'); st.image(bg,caption="Background",use_container_width=True)
    st.subheader("2. Characters")
    char_source=st.radio("Character source",["Upload characters","Use stick figures"],horizontal=True,key="rb_char_source"); prepared=[]
    if char_source=="Use stick figures":
        count=st.slider("Number of stick figures",1,4,2,key="rb_stick_count"); cols=st.columns(min(3,count)); palette=[(35,35,45),(30,75,125),(95,45,100),(45,95,60)]
        for i in range(count):
            with cols[i%len(cols)]:
                style=st.selectbox(f"Figure {i+1} style",STICK_FIGURE_STYLES,index=i%len(STICK_FIGURE_STYLES),key=f"stick_style_{i}"); img=generate_stick_figure(style,palette[i%len(palette)]); st.image(img,caption=f"Stick Figure {i+1} · {style}",width=130); prepared.append((f"stick_{i+1}_{style}",img))
    else:
        files=st.file_uploader("Upload one or more character PNGs",type=["png","jpg","jpeg"],accept_multiple_files=True,key="rb_chars")
        if not files: st.warning("Upload at least one character, or switch to Use stick figures."); return
        for i,f in enumerate(files):
            img=load_rgba(f); c1,c2=st.columns([2,1]); c1.image(img,caption=f.name,width=180); prep=c2.selectbox(f"Preparation · {f.name}",["Keep alpha","Remove simple background","Green-screen key"],key=f"prep_{i}"); img=remove_simple_background(img) if prep=="Remove simple background" else chroma_key(img) if prep=="Green-screen key" else img; prepared.append((f.name,img))
    st.subheader("3. Script")
    script=st.text_area("Dialogue",value="Character 1: What are you doing?\nCharacter 2: I'm trying to fix this.\nCharacter 1: Again?!",height=150,key="rb_script"); rows,duration=build_timeline(script); st.caption(f"Estimated duration: {duration:.1f}s")
    st.subheader("4. Scene controls")
    c1,c2,c3=st.columns(3)
    with c1: aspect=st.selectbox("Format",["TikTok / Shorts 9:16","YouTube 16:9","Square 1:1"]); fps=st.select_slider("FPS",options=[8,10,12,15,18,24],value=12)
    with c2: zoom=st.slider("Camera depth / zoom",1.0,1.35,1.04,.01); brightness=st.slider("Background brightness",.75,1.25,1.,.01)
    with c3: contrast=st.slider("Background contrast",.75,1.30,1.,.01); saturation=st.slider("Background saturation",.70,1.30,1.,.01)
    width,height=(540,960) if aspect=="TikTok / Shorts 9:16" else (640,360) if aspect=="YouTube 16:9" else (540,540)
    if not EDGE_TTS_AVAILABLE: st.warning("edge-tts is not installed, so the render will be silent.")
    st.subheader("5. Character placement, motion & timeline")
    chars={}; voices={}; timelines={}; cols=st.columns(min(3,len(prepared)))
    for i,(pname,img) in enumerate(prepared):
        with cols[i%len(cols)]:
            st.markdown(f"**{pname}**"); x=st.slider("X",.05,.95,min(.85,.28+i*.38),.01,key=f"x_{i}"); y=st.slider("Base/Y",.35,.98,.84,.01,key=f"y_{i}"); scale=st.slider("Size",.15,.90,.55,.01,key=f"s_{i}"); motion=st.selectbox("Default motion",MOTION_PRESETS,index=0 if i==0 else 1,key=f"motion_{i}"); flip=st.checkbox("Flip",False,key=f"flip_{i}"); voice=st.selectbox("Voice",list(NARRATOR_VOICES),index=i%len(NARRATOR_VOICES),key=f"v_{i}"); timeline=st.text_area("Action timeline",value=ACTION_HINT,height=120,key=f"timeline_{i}",help="One cue per line: start-end: Action. Example: 0-2: Walk In")
            chars[pname]=rb.Character(name=pname,image=img,x=x,y=y,scale=scale,z=i+10,motion=motion.lower(),flip=flip,shadow=True); voices[pname]=NARRATOR_VOICES[voice]; timelines[pname]=timeline
    st.caption("Timeline actions run against the complete scene: Walk In, Walk, Run, Jump, Dance, Celebrate, Crouch, Slide Left, Slide Right, Exit Right, plus the motion presets.")
    st.subheader("6. Generate")
    if st.button("🎬 Render RealityBlend Video",type="primary",use_container_width=True):
        out=Path(tempfile.gettempdir())/"cartoon_studio_v6_realityblend.mp4"; scene=Scene(background=bg,fps=fps,width=width,height=height,camera_zoom=zoom,brightness=brightness,contrast=contrast,saturation=saturation); progress=st.progress(0.0); status=st.empty(); status.text("Rendering action timeline + audio + animated background...")
        try:
            render_timeline_video(scene,chars,rows,voices,out,progress=lambda p:progress.progress(min(1.,p)),action_timelines=timelines); status.success("RealityBlend video created."); st.video(str(out)); st.download_button("⬇️ Download MP4",data=out.read_bytes(),file_name="realityblend_v6.mp4",mime="video/mp4")
        except Exception as exc: status.error(f"Render failed: {exc}")
