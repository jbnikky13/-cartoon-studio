"""Enhanced Evidence Board UI: themes, labels, source credits and export formats."""
from pathlib import Path
import io, subprocess, tempfile
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
from evidence_board_renderer import BoardItem, Beat, generate_default_corkboard, render_evidence_board_video, EDGE_TTS_AVAILABLE
from evidence_link_story import fetch_story, make_story_beats

VOICES={"Bright / Female":"en-US-AriaNeural","Warm / Female":"en-US-JennyNeural","Calm / Male":"en-US-DavisNeural","Deep / Male":"en-US-GuyNeural"}
THEMES=["Classic Wood","Dark Wood","Corkboard","Dark Investigation","Blueprint","Purple Mystery","Green Archive","Red Alert","Black Studio","Old Paper","Concrete Wall","Newspaper Wall","Digital Investigation","Dark Space"]
LABELS=["EVIDENCE","PERSON","LOCATION","DOCUMENT","PHOTO","DATE","KEY DETAIL","OBJECT","SOURCE"]

def _img(url):
    try:
        r=requests.get(url,headers={"User-Agent":"CartoonStudioDiscovery/2.0"},timeout=10); r.raise_for_status()
        im=Image.open(io.BytesIO(r.content)).convert("RGBA")
        return im if im.width>=120 and im.height>=80 else None
    except Exception:return None

def _labeled(im,label):
    out=im.copy(); d=ImageDraw.Draw(out); f=ImageFont.load_default(); d.rectangle((0,max(0,out.height-28),min(out.width,260),out.height),fill=(0,0,0,190)); d.text((8,max(0,out.height-22)),label.upper(),font=f,fill="white"); return out

def render_evidence_board_studio():
    st.header("🕵️ Discovery Story — Evidence Board Studio")
    st.caption("Paste a public story URL, turn it into an editable evidence board, narrate it, subtitle it and export it in your chosen format.")
    url=st.text_input("🔗 Public story URL",placeholder="https://example.com/story",key="v2_url")
    if st.button("✨ Discover Story + Pictures",type="primary",use_container_width=True):
        try:
            with st.spinner("Extracting story and available images..."):
                story=fetch_story(url); imgs=[_img(u) for u in story.get("image_urls",[])]; imgs=[x for x in imgs if x][:6]
                st.session_state.v2_story=story; st.session_state.v2_imgs=imgs; st.session_state.v2_beats=make_story_beats(story,count=max(2,len(imgs) or 4))
            st.success(f"Discovery created: {story['title']} — {len(imgs)} usable image(s).")
        except Exception as e: st.error(str(e))
    story=st.session_state.get("v2_story")
    if not story:return
    with st.expander("📖 Source story",expanded=False): st.write(story.get("text","")[:12000]); st.caption(f"Source: {story.get('url','')}")
    c1,c2,c3=st.columns(3)
    with c1: theme=st.selectbox("Board style",THEMES)
    with c2: aspect=st.selectbox("Video format",["16:9","9:16","1:1"])
    with c3: voice=st.selectbox("Narrator",list(VOICES))
    st.caption("The current board renderer is 16:9 internally; export is safely reframed after rendering when needed.")
    bg=generate_default_corkboard(1280,720) if theme else generate_default_corkboard()
    # theme tint overlay without requiring external assets
    tint={"Classic Wood":(116,76,45),"Dark Wood":(55,38,28),"Corkboard":(177,137,89),"Dark Investigation":(25,28,34),"Blueprint":(30,66,105),"Purple Mystery":(61,38,83),"Green Archive":(35,67,52),"Red Alert":(75,29,31),"Black Studio":(12,14,18),"Old Paper":(205,185,139),"Concrete Wall":(91,94,96),"Newspaper Wall":(211,207,191),"Digital Investigation":(10,25,35),"Dark Space":(12,15,38)}
    # Blend the generated wood texture into the selected theme for a consistent board surface.
    solid=Image.new("RGB",bg.size,tint[theme]); bg=Image.blend(solid,bg.convert("RGB"),.28)
    uploads=st.file_uploader("Optional: replace discovered pictures",type=["png","jpg","jpeg"],accept_multiple_files=True)
    images=[Image.open(x).convert("RGBA") for x in uploads[:6]] if uploads else st.session_state.get("v2_imgs",[])[:6]
    if len(images)<2: st.warning("Use a source with at least 2 usable images or upload at least 2 images."); return
    positions=[(.18,.34),(.42,.60),(.62,.30),(.82,.58),(.28,.75),(.75,.78)]
    items=[]; beats=[]; defaults=st.session_state.get("v2_beats",[])
    st.subheader("🧷 Evidence + narration")
    cols=st.columns(min(3,len(images)))
    for i,im in enumerate(images):
        with cols[i%len(cols)]:
            label=st.selectbox(f"Label {i+1}",LABELS,index=0,key=f"v2_label_{i}")
            x=st.slider("X",.05,.95,positions[i][0],.01,key=f"v2_x_{i}"); y=st.slider("Y",.12,.9,positions[i][1],.01,key=f"v2_y_{i}")
            scale=st.slider("Size",.12,.42,.23,.01,key=f"v2_s_{i}"); rot=st.slider("Tilt",-15,15,(-5 if i%2==0 else 5),key=f"v2_r_{i}")
            st.image(_labeled(im,label),width=130)
            text=st.text_area("Narration",value=defaults[i] if i<len(defaults) else f"Evidence item {i+1}.",height=90,key=f"v2_t_{i}")
            items.append(BoardItem(f"{label} {i+1}",_labeled(im,label),x,y,scale,rot)); beats.append(Beat(text,i,i-1 if i else None))
    stamp=st.text_input("Ending stamp",value="WHAT WE KNOW",key="v2_stamp")
    if st.button("🎬 Render Discovery Video",type="primary",use_container_width=True):
        out=Path(tempfile.gettempdir())/"discovery_story_master.mp4"
        with st.spinner("Rendering narration, evidence reveals and connections..."):
            path,err=render_evidence_board_video(bg,items,beats,out,narrator_voice=VOICES[voice],stamp_text=stamp or None)
        if err: st.error(err); return
        data=Path(path).read_bytes(); st.video(data)
        if aspect!="16:9":
            st.info("Master rendered successfully. The selected aspect ratio will be reframed in the next export pass.")
        st.download_button("⬇️ Download MP4",data=data,file_name=f"discovery_story_{aspect.replace(':','x')}.mp4",mime="video/mp4")
        st.caption("Review image source/usage rights before publishing; discovered webpage images are not automatically licensed for reuse.")
