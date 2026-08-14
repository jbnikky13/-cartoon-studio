import streamlit as st
from pathlib import Path
import tempfile, subprocess, shutil, re, math, os, io
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="Cartoon Studio", page_icon="🎬", layout="wide")

WORK = Path(tempfile.gettempdir()) / "cartoon_studio"
WORK.mkdir(exist_ok=True)

# ---------------- Characters ----------------
CHARACTERS = {
    "Alex": ("👨", "young man"),
    "Maya": ("👩", "young woman"),
    "Jay": ("👦", "teen boy"),
    "Nia": ("👧", "teen girl"),
    "Dr. James": ("🧑‍⚕️", "doctor"),
    "Pharmacist": ("💊", "pharmacist"),
    "Teacher": ("🧑‍🏫", "teacher"),
    "Mr. Cole": ("👔", "businessman"),
    "Chris": ("🎓", "student"),
    "Uncle Ben": ("👴", "elder"),
    "Officer Ray": ("👮", "police officer"),
    "DJ K": ("🎤", "performer"),
}

VOICE_OPTIONS = [
    "Warm narrator",
    "Young male",
    "Young female",
    "Deep male",
    "Bright female",
    "Calm adult",
    "Energetic",
    "Comic",
]

STYLE_OPTIONS = [
    "Classic 2D",
    "Modern 2D",
    "Anime-inspired",
    "Comic-book",
    "Urban animated comedy",
    "Kids cartoon",
    "Educational cartoon",
]

def get_font(size=32, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def wrap_text(text, width=45):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        if len(test) <= width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines

def parse_script(script):
    """
    Accepts:
      Character: dialogue
    and also ordinary narration lines.
    """
    rows = []
    for raw in script.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^([^:]{1,40}):\s*(.+)$", line)
        if m:
            speaker, dialogue = m.group(1).strip(), m.group(2).strip()
            rows.append((speaker, dialogue))
        else:
            rows.append(("Narrator", line))
    return rows

def render_frame(dialogue, speaker, scene_no, total, frame_no, frame_total,
                 character_name="Alex", style="Classic 2D", size=(1280,720)):
    w,h = size
    img = Image.new("RGB", size, (245,247,250))
    d = ImageDraw.Draw(img)

    # Background varies slightly by style
    if style == "Urban animated comedy":
        sky, ground, building = (150,190,225), (105,115,105), (185,175,160)
    elif style == "Anime-inspired":
        sky, ground, building = (180,225,250), (145,210,140), (230,220,210)
    else:
        sky, ground, building = (178,224,255), (151,211,128), (236,220,196)

    d.rectangle([0,0,w,475], fill=sky)
    d.rectangle([0,475,w,h], fill=ground)
    d.ellipse([85,60,225,200], fill=(255,222,90))

    # Urban/simple building
    d.rectangle([760,250,1165,475], fill=building, outline=(70,70,70), width=5)
    for x in (805, 925, 1045):
        d.rectangle([x,315,x+75,400], fill=(190,225,245), outline=(65,65,65), width=3)
    d.text((800,265), "CARTOON CITY", font=get_font(27,True), fill=(45,45,45))

    # Character palette is intentionally original/simple.
    palette = {
        "Alex": (70,130,220), "Maya": (205,95,150), "Jay": (75,160,105),
        "Nia": (165,100,205), "Dr. James": (235,235,235),
        "Pharmacist": (65,170,150), "Teacher": (220,155,65),
        "Mr. Cole": (55,65,95), "Chris": (95,125,190),
        "Uncle Ben": (145,100,65), "Officer Ray": (55,95,155),
        "DJ K": (155,75,180)
    }
    shirt = palette.get(character_name, (78,132,225))

    bob = int(8 * math.sin(frame_no / max(frame_total,1) * math.pi * 4))
    walk = int(10 * math.sin(frame_no / max(frame_total,1) * math.pi * 2))
    cx, cy = 430 + walk, 380 + bob

    d.ellipse([cx-90,535,cx+90,570], fill=(80,100,80))
    d.line([cx-28,cy+135,cx-42,535], fill=(45,45,55), width=18)
    d.line([cx+28,cy+135,cx+48,535], fill=(45,45,55), width=18)
    d.rounded_rectangle([cx-75,cy+10,cx+75,cy+155], radius=35, fill=shirt, outline=(40,55,80), width=5)
    d.ellipse([cx-78,cy-105,cx+78,cy+50], fill=(244,194,145), outline=(90,65,45), width=5)

    # Different simple hair silhouettes
    if character_name in ("Maya","Nia"):
        d.ellipse([cx-88,cy-125,cx+88,cy+25], outline=(45,30,25), width=25)
    elif character_name in ("Uncle Ben","Dr. James"):
        d.arc([cx-80,cy-120,cx+80,cy+15],180,355,fill=(150,150,150),width=16)
    else:
        d.arc([cx-80,cy-120,cx+80,cy+15],180,355,fill=(55,40,30),width=22)

    d.ellipse([cx-38,cy-45,cx-20,cy-27], fill=(25,25,25))
    d.ellipse([cx+20,cy-45,cx+38,cy-27], fill=(25,25,25))

    # Mouth opens/closes during dialogue to suggest lip-sync.
    mouth_h = 8 + int(9*abs(math.sin(frame_no/3)))
    d.arc([cx-22,cy-10,cx+22,cy+mouth_h+8],0,180,fill=(100,35,35),width=5)

    # Speech bubble
    bx,by,bw,bh = 60,215,590,235
    d.rounded_rectangle([bx,by,bx+bw,by+bh], radius=28, fill="white", outline=(55,55,55), width=4)
    d.polygon([(bx+470,by+bh),(bx+510,by+bh+48),(bx+420,by+bh-8)], fill="white", outline=(55,55,55))
    d.text((bx+25,by+18), speaker, font=get_font(28,True), fill=(35,35,35))
    y=by+58
    for line in wrap_text(dialogue,42)[:4]:
        d.text((bx+25,y),line,font=get_font(28),fill=(35,35,35))
        y += 35

    d.rounded_rectangle([35,25,310,75], radius=18, fill="white", outline=(70,70,70), width=3)
    d.text((55,36),f"Scene {scene_no}/{total}",font=get_font(25,True),fill=(40,40,40))
    return img

def make_video(script_rows, selected_characters, style, seconds_per_line=3, fps=12):
    out = WORK/f"cartoon_{os.getpid()}.mp4"
    frames = WORK/f"frames_{os.getpid()}"
    frames.mkdir(exist_ok=True)
    idx=0
    usable = {x.lower(): x for x in selected_characters}

    for scene_no,(speaker,dialogue) in enumerate(script_rows,1):
        chosen = usable.get(speaker.lower(), selected_characters[0] if selected_characters else "Alex")
        # Give longer dialogue more screen time.
        duration = max(seconds_per_line, min(10, 1.5 + len(dialogue)/16))
        total_frames=max(1,int(duration*fps))
        for f in range(total_frames):
            render_frame(dialogue,speaker,scene_no,len(script_rows),f,total_frames,chosen,style).save(
                frames/f"frame_{idx:06d}.png"
            )
            idx += 1

    result=subprocess.run(
        ["ffmpeg","-y","-framerate",str(fps),"-i",str(frames/"frame_%06d.png"),
         "-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart",str(out)],
        capture_output=True,text=True
    )
    shutil.rmtree(frames,ignore_errors=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-2000:])
    return out

def join_videos(uploaded):
    work=WORK/f"join_{os.getpid()}"
    work.mkdir(exist_ok=True)
    normalized=[]
    for i,item in enumerate(uploaded):
        source=work/f"source_{i}"
        source.write_bytes(item.getvalue())
        target=work/f"clip_{i}.mp4"
        result=subprocess.run(
            ["ffmpeg","-y","-i",str(source),
             "-vf","scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
             "-r","30","-c:v","libx264","-preset","veryfast","-c:a","aac","-ar","48000","-ac","2",str(target)],
            capture_output=True,text=True
        )
        if result.returncode:
            shutil.rmtree(work,ignore_errors=True)
            raise RuntimeError(result.stderr[-1500:])
        normalized.append(target)

    manifest=work/"concat.txt"
    manifest.write_text("\n".join(f"file '{p.as_posix()}'" for p in normalized))
    out=WORK/f"joined_{os.getpid()}.mp4"
    result=subprocess.run(
        ["ffmpeg","-y","-f","concat","-safe","0","-i",str(manifest),"-c","copy","-movflags","+faststart",str(out)],
        capture_output=True,text=True
    )
    shutil.rmtree(work,ignore_errors=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-1500:])
    return out

# ---------------- UI ----------------
st.markdown("""
<style>
.block-container{max-width:1180px;padding-top:2rem}
.big-title{font-size:3rem;font-weight:800;margin-bottom:.2rem}
.subtitle{font-size:1.15rem;opacity:.75;margin-bottom:1.5rem}
.char-card{padding:.7rem;border:1px solid rgba(128,128,128,.25);border-radius:15px}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="big-title">🎬 Cartoon Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Turn a script into an original animated 2D cartoon, with characters, dialogue timing and voice-ready scenes.</div>', unsafe_allow_html=True)

create, join, help_tab = st.tabs(["✨ Create Cartoon","🎞️ Join Videos","ℹ️ Help"])

with create:
    st.subheader("1. Choose your characters")
    selected = st.multiselect(
        "Characters",
        list(CHARACTERS.keys()),
        default=["Alex","Maya"],
        help="Choose the characters that appear in your script."
    )
    if not selected:
        selected=["Alex"]

    cols=st.columns(4)
    for i,name in enumerate(selected[:12]):
        emoji, role=CHARACTERS[name]
        with cols[i%4]:
            st.markdown(f"**{emoji} {name}**  \n{role}")

    st.subheader("2. Choose a cartoon style")
    style=st.selectbox("Style",STYLE_OPTIONS,index=0)
    if style=="Urban animated comedy":
        st.info("Original urban-comedy look: bold outlines, expressive faces, dynamic poses and city settings. It does not reproduce characters or artwork from existing shows.")

    st.subheader("3. Give each character a voice")
    voice_map={}
    for name in selected:
        voice_map[name]=st.selectbox(f"Voice for {name}",VOICE_OPTIONS,key=f"voice_{name}")
    st.caption("Voice selection is stored with the character setup. Connect an AI TTS provider in the next backend upgrade to synthesize the final spoken audio.")

    st.subheader("4. Write your script")
    st.markdown("Use **Character: dialogue** on each line.")
    script=st.text_area(
        "Script",
        height=230,
        placeholder="""Pharmacist: Good morning! How can I help you?
Customer: I'm looking for some medicine.
Pharmacist: Sure, let me check for you.
Customer: Thank you!""",
        label_visibility="collapsed"
    )

    if st.button("✨ Generate Cartoon",type="primary",use_container_width=True):
        if not script.strip():
            st.warning("Write a script first.")
        else:
            rows=parse_script(script)
            st.session_state.script_rows=rows
            with st.spinner("Animating your scenes..."):
                try:
                    video=make_video(rows,selected,style)
                    st.session_state.cartoon_video=str(video)
                    st.success("Your animated cartoon is ready!")
                except Exception as e:
                    st.error(f"Video generation failed: {e}")

    if st.session_state.get("script_rows"):
        st.subheader("Storyboard")
        for i,(speaker,line) in enumerate(st.session_state.script_rows,1):
            st.write(f"**Scene {i} — {speaker}:** {line}")

    if st.session_state.get("cartoon_video"):
        p=Path(st.session_state.cartoon_video)
        if p.exists():
            st.video(str(p))
            st.download_button("⬇️ Download Cartoon",p.read_bytes(),"my_cartoon.mp4","video/mp4",use_container_width=True)

with join:
    st.subheader("🎞️ Join short videos into one long video")
    uploads=st.file_uploader("Upload your clips",type=["mp4","mov","m4v","webm"],accept_multiple_files=True)
    if uploads:
        for i,item in enumerate(uploads,1):
            st.write(f"**{i}.** {item.name}")
        if st.button("🎬 Create Long Video",type="primary",use_container_width=True):
            with st.spinner("Joining your clips..."):
                try:
                    result=join_videos(uploads)
                    st.session_state.long_video=str(result)
                    st.success("Long video created!")
                except Exception as e:
                    st.error(f"Could not join clips: {e}")
    if st.session_state.get("long_video"):
        p=Path(st.session_state.long_video)
        if p.exists():
            st.video(str(p))
            st.download_button("⬇️ Download Long Video",p.read_bytes(),"joined_cartoon.mp4","video/mp4",use_container_width=True)

with help_tab:
    st.subheader("Simple workflow")
    st.markdown("""
1. **Choose characters.**
2. **Choose a style.**
3. **Assign voices.**
4. **Write dialogue as `Character: words`.**
5. Tap **Generate Cartoon**.
6. Preview and download.
7. Use **Join Videos** to combine episodes or short clips.

The current renderer creates original 2D animated characters and synchronized dialogue timing. The voice controls are prepared for an AI text-to-speech backend; actual speech synthesis requires connecting a TTS service/API.
""")

st.caption("Cartoon Studio V1.2 • Original characters • Streamlit-ready")
