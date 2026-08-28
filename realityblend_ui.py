"""RealityBlend V6 UI: animated backgrounds, stick figures and motion presets."""
from pathlib import Path
import tempfile
import streamlit as st
from PIL import Image
import realityblend_engine as rb
from realityblend_engine import Character, Scene, load_rgba, remove_simple_background, chroma_key, render_timeline_video, EDGE_TTS_AVAILABLE
from realityblend_assets import BUILTIN_BACKGROUNDS, STICK_FIGURE_STYLES, generate_builtin_background, preview_builtin_background, generate_stick_figure
from realityblend_art import ART_BACKGROUNDS, generate_art_background, preview_art_background
from motion_presets import MOTION_PRESETS
from realityblend_models import build_timeline

NARRATOR_VOICES={"Bright / Female":"en-US-AriaNeural","Warm / Female":"en-US-JennyNeural","Calm / Male":"en-US-DavisNeural","Deep / Male":"en-US-GuyNeural"}

# Selected procedural background is read by the renderer on every frame.
def _camera_background_with_builtin(scene,t):
    selected=getattr(rb,"ACTIVE_BUILTIN_BACKGROUND",None)
    if selected:
        if selected in ART_BACKGROUNDS:
            bg=generate_art_background(selected,(scene.width,scene.height),t)
        else:
            bg=generate_builtin_background(selected,(scene.width,scene.height),t)
        from PIL import ImageEnhance
        bg=ImageEnhance.Brightness(bg).enhance(scene.brightness)
        bg=ImageEnhance.Contrast(bg).enhance(scene.contrast)
        bg=ImageEnhance.Color(bg).enhance(scene.saturation)
        return bg
    return rb._original_camera_background(scene,t)

if not hasattr(rb,"_original_camera_background"):
    rb._original_camera_background=rb.camera_background
    rb.camera_background=_camera_background_with_builtin

# Extend the existing engine motion vocabulary without changing its public API.
def _enhanced_motion_values(motion,t):
    from motion_presets import motion_values
    return motion_values(motion,t)
rb._motion_values=_enhanced_motion_values


def render_realityblend():
    st.header("🌍 RealityBlend V6")
    st.caption("Put characters into real scenes, animated worlds, or lightweight stick-figure sets.")

    st.subheader("1. Background")
    bg_source=st.radio("Background source",["Upload image","Built-in animated"],horizontal=True,key="rb_bg_source")
    rb.ACTIVE_BUILTIN_BACKGROUND=None
    if bg_source=="Built-in animated":
        bg_groups={"Classic Motion Worlds":BUILTIN_BACKGROUNDS,"Art & Fantasy Worlds":ART_BACKGROUNDS}
        group=st.selectbox("Background collection",list(bg_groups),key="rb_bg_group")
        bg_name=st.selectbox("Choose an animated background",bg_groups[group],key="rb_builtin_bg")
        if bg_name in ART_BACKGROUNDS:
            preview=preview_art_background(bg_name)
        else:
            preview=preview_builtin_background(bg_name,size=(270,480))
        st.image(preview,caption=f"Preview · {bg_name}",width=220)
        st.caption("Preview is a still frame; the exported video animates continuously.")
        rb.ACTIVE_BUILTIN_BACKGROUND=bg_name
        if bg_name in ART_BACKGROUNDS:
            bg=generate_art_background(bg_name,size=(540,960),t=0.0)
        else:
            bg=generate_builtin_background(bg_name,size=(540,960),t=0.0)
    else:
        bg_file=st.file_uploader("Upload a real background",type=["png","jpg","jpeg"],key="rb_background")
        if not bg_file:
            st.info("Upload a kitchen, bedroom, office, street, classroom, or any other background image.")
            return
        bg=Image.open(bg_file).convert("RGB")
        st.image(bg,caption="Background",use_container_width=True)

    st.subheader("2. Characters")
    char_source=st.radio("Character source",["Upload characters","Use stick figures"],horizontal=True,key="rb_char_source")
    prepared=[]
    if char_source=="Use stick figures":
        count=st.slider("Number of stick figures",1,4,2,key="rb_stick_count")
        cols=st.columns(min(3,count)); palette=[(35,35,45),(30,75,125),(95,45,100),(45,95,60)]
        for i in range(count):
            with cols[i%len(cols)]:
                style=st.selectbox(f"Figure {i+1} style",STICK_FIGURE_STYLES,index=i%len(STICK_FIGURE_STYLES),key=f"stick_style_{i}")
                img=generate_stick_figure(style,palette[i%len(palette)])
                st.image(img,caption=f"Stick Figure {i+1} · {style}",width=130)
                prepared.append((f"stick_{i+1}_{style}",img))
    else:
        char_files=st.file_uploader("Upload one or more character PNGs",type=["png","jpg","jpeg"],accept_multiple_files=True,key="rb_chars")
        if not char_files:
            st.warning("Upload at least one character, or switch to Use stick figures.")
            return
        for i,f in enumerate(char_files):
            img=load_rgba(f); c1,c2=st.columns([2,1])
            with c1: st.image(img,caption=f.name,width=180)
            with c2:
                prep=st.selectbox(f"Preparation · {f.name}",["Keep alpha","Remove simple background","Green-screen key"],key=f"prep_{i}")
                if prep=="Remove simple background": img=remove_simple_background(img)
                elif prep=="Green-screen key": img=chroma_key(img)
            prepared.append((f.name,img))

    st.subheader("3. Script")
    script=st.text_area("Dialogue",value="Character 1: What are you doing?\nCharacter 2: I'm trying to fix this.\nCharacter 1: Again?!",height=150,key="rb_script")
    rows,duration=build_timeline(script)
    st.caption(f"Estimated duration: {duration:.1f}s")

    st.subheader("4. Scene controls")
    col1,col2,col3=st.columns(3)
    with col1:
        aspect=st.selectbox("Format",["TikTok / Shorts 9:16","YouTube 16:9","Square 1:1"]); fps=st.select_slider("FPS",options=[8,10,12,15,18,24],value=12)
    with col2:
        zoom=st.slider("Camera depth / zoom",1.0,1.35,1.04,0.01); brightness=st.slider("Background brightness",0.75,1.25,1.0,0.01)
    with col3:
        contrast=st.slider("Background contrast",0.75,1.30,1.0,0.01); saturation=st.slider("Background saturation",0.70,1.30,1.0,0.01)
    if aspect=="TikTok / Shorts 9:16": width,height=540,960
    elif aspect=="YouTube 16:9": width,height=640,360
    else: width,height=540,540
    if not EDGE_TTS_AVAILABLE: st.warning("⚠️ edge-tts isn't installed, so beats will render silent. Add edge-tts>=6.1.12 to requirements_v6.txt.")

    st.subheader("5. Character placement & motion")
    chars,voices={},{}; cols=st.columns(min(3,len(prepared)))
    for i,(name,img) in enumerate(prepared):
        with cols[i%len(cols)]:
            st.markdown(f"**{name}**")
            x=st.slider("X",0.05,0.95,min(0.85,0.28+i*0.38),0.01,key=f"x_{i}")
            y=st.slider("Base/Y",0.35,0.98,0.84,0.01,key=f"y_{i}")
            scale=st.slider("Size",0.15,0.90,0.55,0.01,key=f"s_{i}")
            motion=st.selectbox("Motion",MOTION_PRESETS,index=0 if i==0 else 1,key=f"motion_{i}")
            flip=st.checkbox("Flip",value=False,key=f"flip_{i}")
            voice_label=st.selectbox("Voice",list(NARRATOR_VOICES.keys()),index=i%len(NARRATOR_VOICES),key=f"v_{i}")
            char_key=Path(name).stem
            chars[char_key]=Character(name=char_key,image=img,x=x,y=y,scale=scale,z=i+10,motion=motion.lower(),flip=flip,shadow=True)
            voices[char_key]=NARRATOR_VOICES[voice_label]
    st.caption("Motion presets animate each character while they speak or wait: walk, run, bounce, float, nod, wave, point, shake, spin, slide and pulse.")

    st.subheader("6. Generate")
    if st.button("🎬 Render RealityBlend Video",type="primary",use_container_width=True):
        out=Path(tempfile.gettempdir())/"cartoon_studio_v6_realityblend.mp4"
        scene_template=Scene(background=bg,fps=fps,width=width,height=height,camera_zoom=zoom,brightness=brightness,contrast=contrast,saturation=saturation)
        progress=st.progress(0.0); status=st.empty(); status.text("Rendering beats (audio + animated background + character motion)...")
        try:
            render_timeline_video(scene_template,chars,rows,voices,out,progress=lambda p: progress.progress(min(1.0,p)))
            status.success("RealityBlend video created."); st.video(str(out)); st.download_button("⬇️ Download MP4",data=out.read_bytes(),file_name="realityblend_v6.mp4",mime="video/mp4")
        except Exception as exc: status.error(f"Render failed: {exc}")
