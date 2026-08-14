import streamlit as st
from pathlib import Path
import tempfile, subprocess, shutil, re, math, os
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="Cartoon Studio", page_icon="🎬", layout="wide")

WORK = Path(tempfile.gettempdir()) / "cartoon_studio"
WORK.mkdir(exist_ok=True)

def get_font(size=32, bold=False):
    names = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for name in names:
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()

def wrap_text(text, width=45):
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines

def split_story(script, scene_count):
    sentences = [x.strip() for x in re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", script.strip())) if x.strip()]
    if not sentences:
        return []
    if len(sentences) <= scene_count:
        return sentences
    size = math.ceil(len(sentences) / scene_count)
    return [" ".join(sentences[i:i+size]) for i in range(0, len(sentences), size)][:scene_count]

def draw_scene(text, scene_no, total, frame_no, frame_total, size=(1280,720)):
    w,h = size
    img = Image.new("RGB", size, (245,247,250))
    d = ImageDraw.Draw(img)

    # Simple 2D cartoon background
    d.rectangle([0,0,w,475], fill=(178,224,255))
    d.rectangle([0,475,w,h], fill=(151,211,128))
    d.ellipse([85,60,225,200], fill=(255,222,90))

    # Building
    d.rectangle([760,250,1165,475], fill=(236,220,196), outline=(80,80,80), width=5)
    d.rectangle([815,315,1110,440], fill=(190,225,245), outline=(70,70,70), width=4)
    d.text((830,265), "CARTOON WORLD", font=get_font(27,True), fill=(45,45,45))

    # Animated character
    bob = int(7 * math.sin(frame_no / max(frame_total,1) * math.pi * 4))
    cx, cy = 430, 380 + bob
    d.ellipse([cx-85,535,cx+85,570], fill=(105,150,90))
    d.line([cx-28,cy+135,cx-42,535], fill=(45,45,55), width=18)
    d.line([cx+28,cy+135,cx+48,535], fill=(45,45,55), width=18)
    d.rounded_rectangle([cx-75,cy+10,cx+75,cy+155], radius=35, fill=(78,132,225), outline=(40,70,120), width=5)
    d.ellipse([cx-78,cy-105,cx+78,cy+50], fill=(244,194,145), outline=(90,65,45), width=5)
    d.arc([cx-80,cy-120,cx+80,cy+15],180,355,fill=(55,40,30),width=22)
    d.ellipse([cx-38,cy-45,cx-20,cy-27], fill=(25,25,25))
    d.ellipse([cx+20,cy-45,cx+38,cy-27], fill=(25,25,25))
    mouth = 10 + int(5*abs(math.sin(frame_no/4)))
    d.arc([cx-22,cy-10,cx+22,cy+mouth+8],0,180,fill=(100,35,35),width=5)

    # Speech bubble
    bx,by,bw,bh = 75,225,555,220
    d.rounded_rectangle([bx,by,bx+bw,by+bh], radius=28, fill="white", outline=(60,60,60), width=4)
    d.polygon([(bx+470,by+bh),(bx+510,by+bh+48),(bx+420,by+bh-8)], fill="white", outline=(60,60,60))
    y = by+22
    for line in wrap_text(text, 42)[:5]:
        d.text((bx+25,y),line,font=get_font(29),fill=(30,30,30))
        y += 36

    d.rounded_rectangle([35,25,235,75], radius=18, fill="white", outline=(70,70,70), width=3)
    d.text((55,36),f"Scene {scene_no}/{total}",font=get_font(26,True),fill=(40,40,40))
    return img

def render_cartoon(scenes, seconds_per_scene, fps=12):
    out = WORK / f"cartoon_{os.getpid()}.mp4"
    frames = WORK / f"frames_{os.getpid()}"
    frames.mkdir(exist_ok=True)
    idx = 0
    for i, scene in enumerate(scenes,1):
        total_frames = max(1,int(seconds_per_scene*fps))
        for f in range(total_frames):
            draw_scene(scene,i,len(scenes),f,total_frames).save(frames/f"frame_{idx:06d}.png")
            idx += 1
    cmd = ["ffmpeg","-y","-framerate",str(fps),"-i",str(frames/"frame_%06d.png"),
           "-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart",str(out)]
    result = subprocess.run(cmd,capture_output=True,text=True)
    shutil.rmtree(frames,ignore_errors=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-2000:])
    return out

def join_videos(uploaded):
    work = WORK / f"join_{os.getpid()}"
    work.mkdir(exist_ok=True)
    normalized = []
    for i, item in enumerate(uploaded):
        source = work/f"source_{i}"
        source.write_bytes(item.getvalue())
        target = work/f"clip_{i}.mp4"
        cmd = ["ffmpeg","-y","-i",str(source),
               "-vf","scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
               "-r","30","-c:v","libx264","-preset","veryfast","-c:a","aac","-ar","48000","-ac","2",str(target)]
        result = subprocess.run(cmd,capture_output=True,text=True)
        if result.returncode:
            shutil.rmtree(work,ignore_errors=True)
            raise RuntimeError(result.stderr[-1500:])
        normalized.append(target)

    manifest = work/"concat.txt"
    manifest.write_text("\n".join(f"file '{p.as_posix()}'" for p in normalized))
    out = WORK/f"joined_{os.getpid()}.mp4"
    result = subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(manifest),
                             "-c","copy","-movflags","+faststart",str(out)],
                            capture_output=True,text=True)
    shutil.rmtree(work,ignore_errors=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-2000:])
    return out

st.markdown("""
<style>
.block-container{max-width:1150px;padding-top:2rem}
.big-title{font-size:3rem;font-weight:800;margin-bottom:.2rem}
.subtitle{font-size:1.15rem;opacity:.75;margin-bottom:1.5rem}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="big-title">🎬 Cartoon Studio</div>',unsafe_allow_html=True)
st.markdown('<div class="subtitle">Create simple 2D cartoons or join short clips into one long video.</div>',unsafe_allow_html=True)

create, join, help_tab = st.tabs(["✨ Create Cartoon","🎞️ Join Videos","ℹ️ Help"])

with create:
    st.subheader("Tell us your story")
    script = st.text_area("Story", placeholder="A young pharmacist opens the pharmacy. A customer walks in and asks for help. The pharmacist smiles and starts searching for the medicine.", height=170, label_visibility="collapsed")
    a,b = st.columns(2)
    with a:
        scene_count = st.slider("Number of scenes",2,10,4)
    with b:
        seconds = st.slider("Seconds per scene",2,8,4)

    if st.button("✨ Create My Cartoon",type="primary",use_container_width=True):
        if not script.strip():
            st.warning("Write a story first.")
        else:
            scenes = split_story(script,scene_count)
            st.session_state.scenes = scenes
            with st.spinner("Creating your cartoon..."):
                try:
                    st.session_state.video = str(render_cartoon(scenes,seconds))
                    st.success("Your cartoon is ready!")
                except Exception as e:
                    st.error(f"Could not create the video: {e}")

    if st.session_state.get("scenes"):
        st.subheader("Storyboard")
        for i, scene in enumerate(st.session_state.scenes,1):
            st.write(f"**Scene {i}:** {scene}")

    if st.session_state.get("video"):
        p=Path(st.session_state.video)
        if p.exists():
            st.video(str(p))
            st.download_button("⬇️ Download Cartoon",p.read_bytes(),"my_cartoon.mp4","video/mp4",use_container_width=True)

with join:
    st.subheader("Join short videos")
    st.write("Upload clips, arrange them in the order shown below, then create one long MP4.")
    uploads = st.file_uploader("Add video clips",type=["mp4","mov","m4v","webm"],accept_multiple_files=True)
    if uploads:
        for i,item in enumerate(uploads,1):
            st.write(f"**{i}.** {item.name}")
        if st.button("🎬 Create Long Video",type="primary",use_container_width=True):
            with st.spinner("Joining your videos..."):
                try:
                    st.session_state.joined = str(join_videos(uploads))
                    st.success("Your long video is ready!")
                except Exception as e:
                    st.error(f"Could not join the videos: {e}")
    if st.session_state.get("joined"):
        p=Path(st.session_state.joined)
        if p.exists():
            st.video(str(p))
            st.download_button("⬇️ Download Long Video",p.read_bytes(),"joined_cartoon.mp4","video/mp4",use_container_width=True)

with help_tab:
    st.subheader("How to use it")
    st.markdown("""
**Create Cartoon**
1. Write your story.
2. Choose the number of scenes.
3. Choose the scene length.
4. Tap **Create My Cartoon**.
5. Preview and download.

**Join Videos**
1. Upload your short clips.
2. Put them in the order you want.
3. Tap **Create Long Video**.
4. Preview and download.

No animation experience is required.
""")

st.caption("Cartoon Studio V1.1 • Streamlit-ready")
