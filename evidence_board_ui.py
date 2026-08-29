"""Evidence Board / Discovery Story studio UI."""
from pathlib import Path
import io,tempfile,random
import streamlit as st
from PIL import Image,ImageDraw
from evidence_board_renderer import BoardItem,Beat,generate_default_corkboard,render_evidence_board_video
from evidence_board_export import finalize_discovery_export
from evidence_link_story import fetch_story,make_story_beats,download_images,narration_for_image
NARRATOR_VOICES={"Bright / Female":"en-US-AriaNeural","Warm / Female":"en-US-JennyNeural","Calm / Male":"en-US-DavisNeural","Deep / Male":"en-US-GuyNeural","Documentary / Male":"en-US-ChristopherNeural"}
BG_STYLES=["Classic Wood","Dark Wood","Corkboard","Dark Investigation","Blueprint","Purple Mystery","Green Archive","Red Alert","Black Studio","Old Paper","Concrete Wall","Newspaper Wall","Digital Investigation","Dark Space"]
def make_board_background(style,w=1280,h=720):
 if style=="Classic Wood":return generate_default_corkboard(w,h)
 colors={"Dark Wood":(58,39,28),"Corkboard":(150,112,73),"Dark Investigation":(25,27,32),"Blueprint":(27,58,86),"Purple Mystery":(55,35,72),"Green Archive":(35,61,49),"Red Alert":(72,28,30),"Black Studio":(14,16,20),"Old Paper":(190,174,132),"Concrete Wall":(100,103,105),"Newspaper Wall":(205,202,190),"Digital Investigation":(18,31,42),"Dark Space":(10,15,30)}
 img=Image.new("RGB",(w,h),colors[style]); d=ImageDraw.Draw(img)
 if style in ("Blueprint","Digital Investigation"):
  step=50 if style=="Blueprint" else 70
  for x in range(0,w,step):d.line((x,0,x,h),fill=(65,105,135),width=1)
  for y in range(0,h,step):d.line((0,y,w,y),fill=(65,105,135),width=1)
 elif style=="Newspaper Wall":
  for y in range(25,h,55):d.line((20,y,w-20,y),fill=(175,172,162),width=1)
 elif style=="Dark Space":
  rng=random.Random(11)
  for _ in range(180):
   x,y=rng.randrange(w),rng.randrange(h); r=rng.choice([1,1,1,2]); d.ellipse((x-r,y-r,x+r,y+r),fill=(210,215,225))
 elif style=="Concrete Wall":
  rng=random.Random(4)
  for _ in range(700):
   x,y=rng.randrange(w),rng.randrange(h); q=rng.randrange(85,125); d.point((x,y),fill=(q,q,q))
 elif style=="Old Paper":
  for y in range(20,h,35):d.line((15,y,w-15,y),fill=(175,157,115),width=1)
 return img

def positions(n):
 p={1:[(.5,.5)],2:[(.32,.42),(.68,.55)],3:[(.22,.35),(.52,.55),(.80,.32)],4:[(.20,.30),(.45,.60),(.68,.28),(.85,.58)],5:[(.16,.30),(.38,.55),(.58,.28),(.78,.55),(.90,.25)],6:[(.14,.28),(.32,.58),(.50,.25),(.68,.58),(.84,.28),(.92,.62)]}; return p.get(n,[(.1+.8*i/max(1,n-1),.4) for i in range(n)])
def _img(data):
 try:return Image.open(io.BytesIO(data)).convert("RGBA")
 except Exception:return None

def render_evidence_board_studio():
 st.header("🕵️ Evidence Board / Discovery Story"); st.caption("Paste a public story, discover evidence, choose a visual investigation style, edit the narration, and render a documentary-style board.")
 st.subheader("1. Discovery Story"); url=st.text_input("Public article / webpage URL",placeholder="https://example.com/story",key="eb_url")
 if st.button("🔎 Discover Story + Pictures",type="primary",use_container_width=True):
  if not url.strip():st.warning("Paste a public URL first.")
  else:
   try:
    with st.spinner("Analyzing public page and collecting available images..."):
     story=fetch_story(url,max_images=12); found=download_images(story,max_downloads=8); beats=make_story_beats(story,count=max(2,min(6,len(found) or 4)))
    st.session_state.update(eb_story=story,eb_found=found,eb_beats=beats); st.success(f"Draft created: {story['title']} — {len(found)} usable pictures")
   except Exception as exc:st.error(f"Discovery failed: {exc}")
 story=st.session_state.get("eb_story"); found=st.session_state.get("eb_found",[]); video_found=st.session_state.get("eb_video_selected",[])
 if story:
  st.markdown(f"**{story.get('title','Story')}**"); st.caption(story.get("description","")[:600]); st.caption(f"Source: {story.get('url','')}")
  with st.expander("📖 Extracted story text"):st.write(story.get("text","")[:16000])
 st.subheader("2. Investigation background"); style=st.selectbox("Board style",BG_STYLES,key="eb_style"); board_bg=make_board_background(style); st.image(board_bg,caption=style,width=430); custom=st.file_uploader("Or upload your own background",type=["png","jpg","jpeg"],key="eb_bg")
 if custom:board_bg=Image.open(custom).convert("RGB").resize((1280,720))
 st.subheader("3. Evidence"); options=["Discovered pictures","Upload manually"]+(["Video evidence"] if video_found else []); source=st.radio("Evidence source",options,horizontal=True,key="eb_source"); selected=[]; credits=[]
 if source=="Discovered pictures" and found:
  st.caption("Only use images you have permission to publish. Source URLs are retained for attribution/review."); cols=st.columns(min(4,max(1,len(found))))
  for i,v in enumerate(found):
   im=_img(v.get("bytes",b""))
   if im is None:continue
   with cols[i%len(cols)]:
    st.image(im,width=140,caption=f"Evidence {i+1}")
    if st.checkbox("Use",value=i<min(6,len(found)),key=f"eb_use_{i}"):selected.append((f"evidence_{i+1}.jpg",im,v.get("url",""))); credits.append(v.get("url",""))
 elif source=="Video evidence":
  st.caption("Frames selected by Video Intelligence are ready for the board."); cols=st.columns(min(3,max(1,len(video_found))))
  for i,v in enumerate(video_found[:6]):
   im=_img(v.get("bytes",b""))
   if im is None:continue
   with cols[i%len(cols)]:
    st.image(im,width=160,caption=v.get("name",f"Video evidence {i+1}")); st.caption(v.get("reason","")[:180])
    if st.checkbox("Use",value=i<min(6,len(video_found)),key=f"eb_video_board_use_{i}"):selected.append((v.get("name",f"video_evidence_{i+1}.jpg"),im,v.get("url","Video source"))); credits.append(v.get("url","Video source"))
 else:
  ups=st.file_uploader("Upload 2-6 photos/documents",type=["png","jpg","jpeg"],accept_multiple_files=True,key="eb_uploads")
  for u in (ups or [])[:6]:selected.append((u.name,Image.open(u).convert("RGBA"),"User-provided")); credits.append("User-provided")
 if len(selected)<2:st.info("Choose at least 2 evidence items to continue."); return
 selected=selected[:6]; pos=positions(len(selected)); items=[]; beats=[]; st.subheader("4. Evidence placement + narration"); sentences_used=set(); auto=st.session_state.get("eb_beats",[]); cols=st.columns(min(3,len(selected)))
 for i,(name,im,src) in enumerate(selected):
  x,y=pos[i]
  with cols[i%len(cols)]:
   st.image(im,width=120,caption=name); x=st.slider("X",.05,.95,x,.01,key=f"eb_x_{i}"); y=st.slider("Y",.10,.90,y,.01,key=f"eb_y_{i}"); rot=st.slider("Tilt",-20,20,-8 if i%2==0 else 8,key=f"eb_rot_{i}"); scale=st.slider("Size",.10,.40,.22,.01,key=f"eb_scale_{i}")
   default_line=narration_for_image(story,src,sentences_used,intro=(i==0)) if story else (auto[i] if i<len(auto) else f"Evidence item {i+1} reveals another part of the story.")
   line=st.text_area("Narration",value=default_line,height=90,key=f"eb_line_{i}")
  items.append(BoardItem(name=name,image=im,x=x,y=y,scale=scale,rotation=rot)); beats.append(Beat(text=line,item_index=i,connect_from_index=i-1 if i else None))
 st.subheader("5. Audio + visual annotations"); narrator=st.selectbox("Narrator voice",list(NARRATOR_VOICES.keys())); subtitles=st.checkbox("Burn subtitles into MP4",True,key="eb_subtitles"); labels=st.checkbox("Burn evidence labels into MP4",True,key="eb_labels"); stamp=st.text_input("Final conclusion / stamp",placeholder="CONNECTED • WHAT WE KNOW",key="eb_stamp"); st.caption("Animated connecting strings are rendered between each revealed evidence item.")
 st.subheader("6. Render"); fmt=st.selectbox("Output format",["16:9 Landscape","9:16 Vertical","1:1 Square"],key="eb_format"); aspect={"16:9 Landscape":"16:9","9:16 Vertical":"9:16","1:1 Square":"1:1"}[fmt]
 if st.button("🎬 Create Discovery Story Video",type="primary",use_container_width=True):
  master=Path(tempfile.gettempdir())/"discovery_story_master.mp4"; out=Path(tempfile.gettempdir())/f"discovery_story_{aspect.replace(':','x')}.mp4"; progress=st.progress(0.0); status=st.empty()
  try:
   result,err=render_evidence_board_video(board_bg,items,beats,master,narrator_voice=NARRATOR_VOICES[narrator],stamp_text=stamp or None,progress_cb=lambda p:progress.progress(min(.9,p*.9)))
   if err:status.error(f"Render failed: {err}"); return
   final,warning=finalize_discovery_export(result,out,beats,items,aspect=aspect,subtitles=subtitles,labels=labels,title=story.get("title","DISCOVERY STORY") if story else "DISCOVERY STORY",progress_cb=lambda p:progress.progress(min(1,p)))
   if not final:status.error(f"Final export failed: {warning or 'Unknown FFmpeg error'}"); return
   if warning:status.warning(warning)
   status.success(f"Discovery Story created — {fmt}"); data=Path(final).read_bytes(); st.video(data); st.download_button("⬇️ Download MP4",data=data,file_name=f"discovery_story_{aspect.replace(':','x')}.mp4",mime="video/mp4"); st.subheader("🧾 Evidence source / credit record")
   for i,c in enumerate(credits,1):st.write(f"{i}. {c}")
  except Exception as exc:status.error(f"Render failed: {exc}")
