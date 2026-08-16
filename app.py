import streamlit as st
from pathlib import Path
import tempfile, subprocess, shutil, re, os, json, math, wave, struct
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont, ImageOps
import imageio_ffmpeg

# ============================================================
# CARTOON STUDIO V5 — IMAGE CHARACTER 2D ENGINE
# Uses the uploaded three-view character sheets as the actual
# character art. No Blender / OpenGL required.
# ============================================================

st.set_page_config(
    page_title="Cartoon Studio V5",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = Path(tempfile.gettempdir()) / "cartoon_studio_v5"
ROOT.mkdir(parents=True, exist_ok=True)
ASSET_ROOT = Path(__file__).resolve().parent / "assets" / "characters"

# Memory-safe render target for small Render instances.
FPS = 12
W, H = 640, 360

# ------------------------------------------------------------
# CHARACTER LIBRARY
# ------------------------------------------------------------

CHARACTERS = {
    "Zuri Spark": dict(tag="Fast-talking optimist", accent="★", voice="bright"),
    "Milo Quirk": dict(tag="Deadpan problem-solver", accent="◇", voice="calm"),
    "Kemi Bolt": dict(tag="Fearless tinkerer", accent="⚡", voice="energetic"),
    "Tari Reed": dict(tag="Calm observer", accent="○", voice="calm"),
    "Biko Bean": dict(tag="Snack philosopher", accent="●", voice="warm"),
    "Nala Vee": dict(tag="Ambitious overachiever", accent="▲", voice="bright"),
    "Dex Orbit": dict(tag="Conspiracy-minded friend", accent="◎", voice="dramatic"),
    "Ayo Finch": dict(tag="Quiet comedian", accent="~", voice="dry"),
    "Rhea Moss": dict(tag="Practical realist", accent="+", voice="firm"),
    "Professor Pogo": dict(tag="Eccentric explainer", accent="!", voice="dramatic"),
    "Jax Noon": dict(tag="Dramatic storyteller", accent="◆", voice="dramatic"),
    "Simi Ray": dict(tag="Curious newcomer", accent="?", voice="bright"),
}

LOCATIONS = [
    "Apartment", "Classroom", "Pharmacy", "Office", "Street",
    "Restaurant", "Park", "Bus Stop", "Corner Shop", "Rooftop"
]
STYLES = ["Clean Character Art", "Comic Panel", "Storybook", "Bold 2D Comedy"]
POSTURES = ["Auto", "Standing", "Sitting", "Leaning"]
EMOTIONS = ["Auto", "Neutral", "Happy", "Surprised", "Thinking", "Annoyed", "Laughing", "Confused", "Excited", "Sad"]
GESTURES = ["Auto", "Talking Hands", "Pointing", "Waving", "Thinking", "Shrugging", "Laughing", "Nervous", "None"]
CAMERAS = ["Auto", "Wide", "Medium", "Close-up", "Over-the-shoulder"]
PACE = ["Natural", "Comedic", "Calm", "Fast"]

# ------------------------------------------------------------
# CHARACTER ASSET LOADING
# ------------------------------------------------------------

def safe_name(name):
    return name.replace(" ", "_")


def asset_path(name, view):
    return ASSET_ROOT / safe_name(name) / f"{view}.png"


@lru_cache(maxsize=64)
def load_character(name, view):
    path = asset_path(name, view)
    if not path.exists():
        return None
    return Image.open(path).convert("RGBA")


def character_exists(name):
    return asset_path(name, "front").exists() and asset_path(name, "portrait").exists()

# ------------------------------------------------------------
# FONT / TEXT
# ------------------------------------------------------------

def get_font(size=20, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def wrap_text(text, width=55):
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if len(trial) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines

# ------------------------------------------------------------
# SCRIPT UNDERSTANDING
# ------------------------------------------------------------

def parse_script(text):
    rows = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^([^:]{1,40}):\s*(.+)$", line)
        if m:
            rows.append((m.group(1).strip(), m.group(2).strip()))
        else:
            rows.append(("Narrator", line))
    return rows


def infer_emotion(text):
    t = text.lower()
    if any(x in t for x in ["haha", "lol", "hilarious", "funny"]):
        return "Laughing"
    if any(x in t for x in ["wow", "amazing", "yes!", "finally", "awesome"]):
        return "Excited"
    if "?" in text or any(x in t for x in ["really", "why", "how", "what", "huh"]):
        return "Confused"
    if any(x in t for x in ["no", "never", "stop", "seriously", "annoying"]):
        return "Annoyed"
    if any(x in t for x in ["maybe", "think", "perhaps", "wonder"]):
        return "Thinking"
    if any(x in t for x in ["sorry", "unfortunately", "sad"]):
        return "Sad"
    if any(x in t for x in ["great", "good", "nice", "love", "thank"]):
        return "Happy"
    return "Neutral"


def infer_gesture(text, emotion):
    t = text.lower()
    if any(x in t for x in ["look", "there", "that", "this"]):
        return "Pointing"
    if any(x in t for x in ["hello", "hi", "hey", "bye"]):
        return "Waving"
    if emotion == "Thinking":
        return "Thinking"
    if emotion == "Laughing":
        return "Laughing"
    if any(x in t for x in ["maybe", "i guess", "not sure"]):
        return "Nervous"
    if emotion == "Excited":
        return "Talking Hands"
    return "Talking Hands"


def infer_posture(location, text):
    if location in ["Apartment", "Restaurant", "Office", "Classroom", "Pharmacy"]:
        if any(x in text.lower() for x in ["stand", "standing", "come", "walk"]):
            return "Standing"
        return "Sitting"
    return "Standing"


def estimate_duration(text, pace="Natural"):
    words = max(1, len(text.split()))
    base = words / {"Natural": 2.7, "Comedic": 2.25, "Calm": 2.0, "Fast": 3.25}[pace]
    return max(2.0, min(12.0, base + 0.7))

# ------------------------------------------------------------
# AUDIO
# ------------------------------------------------------------

def make_silent_audio(duration, path, sample_rate=8000):
    n = max(1, int(duration * sample_rate))
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        silence = struct.pack("<h", 0)
        chunk = silence * min(n, sample_rate)
        remaining = n
        while remaining:
            count = min(remaining, len(chunk) // 2)
            wf.writeframes(chunk[:count * 2])
            remaining -= count

# ------------------------------------------------------------
# BACKGROUNDS
# ------------------------------------------------------------

def draw_background(d, location):
    d.rectangle([0, 0, W, H], fill=(238, 232, 220))
    d.rectangle([0, 285, W, H], fill=(150, 139, 120))
    d.rectangle([0, 0, W, 34], fill=(27, 31, 38))
    d.text((14, 8), location.upper(), font=get_font(13, True), fill=(250, 250, 250))

    if location in ["Park", "Rooftop"]:
        d.rectangle([0, 235, W, H], fill=(112, 156, 94))
        for x in (70, 570):
            d.rectangle([x, 130, x + 14, 285], fill=(105, 73, 47))
            d.ellipse([x - 48, 85, x + 62, 175], fill=(65, 125, 70))
    elif location == "Street" or location == "Bus Stop":
        d.rectangle([0, 235, W, H], fill=(78, 82, 88))
        for x in range(0, W, 120):
            d.rectangle([x, 300, x + 65, 307], fill=(230, 210, 125))
        if location == "Bus Stop":
            d.rectangle([70, 105, 190, 235], outline=(50, 55, 60), width=4)
            d.rectangle([80, 115, 180, 185], fill=(157, 205, 224))
    else:
        d.rectangle([28, 48, W - 28, 285], fill=(245, 238, 225), outline=(75, 70, 68), width=2)
        d.rectangle([85, 92, 205, 170], fill=(157, 207, 228), outline=(65, 70, 75), width=2)
        d.line([145, 92, 145, 170], fill=(65, 70, 75), width=2)
        d.line([85, 131, 205, 131], fill=(65, 70, 75), width=2)
        if location == "Classroom":
            d.rectangle([260, 210, 555, 235], fill=(132, 95, 61))
        elif location == "Pharmacy":
            d.rectangle([270, 165, 530, 215], fill=(215, 220, 225), outline=(70, 70, 75), width=2)
            d.text((325, 181), "PHARMACY", font=get_font(15, True), fill=(55, 60, 65))
        else:
            d.rounded_rectangle([255, 205, 555, 255], radius=12, fill=(122, 95, 82), outline=(70, 62, 58), width=2)

# ------------------------------------------------------------
# IMAGE CHARACTER PERFORMANCE
# ------------------------------------------------------------

def paste_sprite(canvas, sprite, cx, ground_y, target_h, motion_x=0, motion_y=0, flip=False):
    if sprite is None:
        return
    img = sprite.copy()
    if flip:
        img = ImageOps.mirror(img)
    ratio = target_h / max(1, img.height)
    size = (max(1, int(img.width * ratio)), max(1, int(img.height * ratio)))
    img = img.resize(size, Image.Resampling.LANCZOS)
    x = int(cx - img.width / 2 + motion_x)
    y = int(ground_y - img.height + motion_y)
    canvas.alpha_composite(img, (x, y))


def draw_talking_indicator(d, cx, y, frame):
    # Tiny speech motion marker; it avoids modifying the artwork itself.
    phase = frame % 18
    if phase < 9:
        d.ellipse([cx + 66, y - 18, cx + 70, y - 14], fill=(70, 75, 82))
        d.ellipse([cx + 74, y - 26, cx + 80, y - 20], fill=(70, 75, 82))


def draw_character(canvas, name, cx, ground, frame, expression, camera, talking, listener=False, seed=1):
    # Gentle 2D puppet motion while preserving the uploaded artwork.
    sway = 2.5 * math.sin(frame / 9.0 + seed)
    bob = 1.8 * math.sin(frame / 7.0 + seed * 0.4)
    if talking:
        bob += 2.2 * math.sin(frame / 2.7 + seed)
    elif listener:
        bob += 1.0 * math.sin(frame / 15.0 + seed)

    if camera in ["Close-up", "Over-the-shoulder"]:
        sprite = load_character(name, "portrait")
        target_h = 245
    else:
        sprite = load_character(name, "front")
        target_h = 285

    # Slightly enlarge the speaker during speech.
    if talking:
        target_h += int(3 * math.sin(frame / 4.0))

    paste_sprite(canvas, sprite, cx, ground, target_h, sway, bob)

    if talking and camera in ["Close-up", "Over-the-shoulder"]:
        draw_talking_indicator(ImageDraw.Draw(canvas), cx, ground - 225, frame)

# ------------------------------------------------------------
# DIALOGUE CARD
# ------------------------------------------------------------

def draw_dialogue_card(d, speaker, text, emotion, progress):
    d.rounded_rectangle([16, 40, W - 16, 105], radius=12, fill=(255, 255, 255), outline=(40, 43, 48), width=2)
    d.text((28, 48), speaker, font=get_font(15, True), fill=(28, 30, 35))
    lines = wrap_text(text, 72)[:2]
    y = 69
    for line in lines:
        d.text((28, y), line, font=get_font(12), fill=(50, 52, 56))
        y += 15
    d.rounded_rectangle([W - 105, 12, W - 16, 34], radius=9, fill=(28, 31, 36))
    d.text((W - 95, 16), emotion.upper(), font=get_font(9, True), fill=(245, 245, 245))

# ------------------------------------------------------------
# FRAME RENDER
# ------------------------------------------------------------

def render_frame(scene, project, frame):
    img = Image.new("RGBA", (W, H), (235, 235, 235, 255))
    d = ImageDraw.Draw(img)
    draw_background(d, scene["location"])

    cast = project["cast"]
    speaker = scene["speaker"]
    listener = next((x for x in cast if x != speaker), None)
    progress = frame / max(1, scene["frames"] - 1)

    camera = scene["camera"]
    if camera == "Auto":
        camera = "Close-up" if len(scene["dialogue"].split()) > 12 else "Medium"

    # Keep characters fixed to their side; only tiny natural motion is applied.
    # This prevents characters jumping positions when dialogue changes.
    left_x, right_x = 175, 465
    if camera == "Wide":
        left_x, right_x = 160, 480
    elif camera == "Close-up":
        left_x, right_x = 205, 435
    elif camera == "Over-the-shoulder":
        left_x, right_x = 180, 460

    emotion = scene["emotion"] if scene["emotion"] != "Auto" else infer_emotion(scene["dialogue"])
    _gesture = scene["gesture"] if scene["gesture"] != "Auto" else infer_gesture(scene["dialogue"], emotion)

    draw_character(img, speaker, left_x, 330, frame, emotion, camera, True, False, 11)

    if listener:
        listener_emotion = "Surprised" if emotion == "Surprised" and progress < 0.35 else "Neutral"
        draw_character(img, listener, right_x, 330, frame + 8, listener_emotion, camera, False, True, 23)

    draw_dialogue_card(d, speaker, scene["dialogue"], emotion, progress)

    d.rectangle([16, H - 12, W - 16, H - 7], fill=(48, 51, 56))
    d.rectangle([16, H - 12, 16 + int((W - 32) * progress), H - 7], fill=(235, 95, 78))
    return img.convert("RGB")

# ------------------------------------------------------------
# MP4 RENDER
# ------------------------------------------------------------

def render_video(scenes, project, progress_cb=None):
    frames_dir = ROOT / f"frames_{os.getpid()}"
    frames_dir.mkdir(exist_ok=True)
    output = ROOT / f"cartoon_studio_v5_{os.getpid()}.mp4"
    silent = ROOT / f"silent_{os.getpid()}.wav"
    total = sum(max(1, int(float(s["duration"]) * FPS)) for s in scenes)
    done = 0
    idx = 0

    try:
        for scene in scenes:
            scene["frames"] = max(1, int(float(scene["duration"]) * FPS))
            for f in range(scene["frames"]):
                frame = render_frame(scene, project, f)
                frame.save(frames_dir / f"frame_{idx:07d}.jpg", quality=90, optimize=True)
                idx += 1
                done += 1
                if progress_cb and (done % 6 == 0 or done == total):
                    progress_cb(done / max(1, total))

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        duration = sum(float(s["duration"]) for s in scenes)
        make_silent_audio(duration, silent)

        result = subprocess.run([
            ffmpeg, "-y",
            "-framerate", str(FPS),
            "-i", str(frames_dir / "frame_%07d.jpg"),
            "-i", str(silent),
            "-c:v", "libx264", "-preset", "ultrafast",
            "-crf", "25", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "32k", "-shortest",
            "-movflags", "+faststart", str(output)
        ], capture_output=True, text=True)

        if result.returncode == 0 and output.exists():
            return output, None
        return None, result.stderr[-5000:]
    except Exception as exc:
        return None, repr(exc)
    finally:
        shutil.rmtree(frames_dir, ignore_errors=True)
        try:
            silent.unlink()
        except Exception:
            pass

# ------------------------------------------------------------
# JOIN CLIPS
# ------------------------------------------------------------

def join_videos(files):
    work = ROOT / f"join_{os.getpid()}"
    work.mkdir(exist_ok=True)
    clips = []
    try:
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        for i, f in enumerate(files):
            src = work / f"src_{i}.mp4"
            clip = work / f"clip_{i}.mp4"
            src.write_bytes(f.getvalue())
            r = subprocess.run([
                ffmpeg, "-y", "-i", str(src),
                "-vf", "scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
                "-r", str(FPS), "-c:v", "libx264", "-preset", "ultrafast", "-crf", "25",
                "-c:a", "aac", "-b:a", "32k", str(clip)
            ], capture_output=True, text=True)
            if r.returncode != 0:
                return None, r.stderr[-3000:]
            clips.append(clip)
        manifest = work / "concat.txt"
        manifest.write_text("\n".join(f"file '{x.as_posix()}'" for x in clips))
        out = ROOT / f"episode_{os.getpid()}.mp4"
        r = subprocess.run([
            ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(manifest),
            "-c", "copy", "-movflags", "+faststart", str(out)
        ], capture_output=True, text=True)
        if r.returncode == 0:
            return out, None
        return None, r.stderr[-3000:]
    finally:
        shutil.rmtree(work, ignore_errors=True)

# ------------------------------------------------------------
# STATE
# ------------------------------------------------------------

if "project" not in st.session_state:
    st.session_state.project = {
        "name": "My Cartoon Episode",
        "style": "Clean Character Art",
        "location": "Apartment",
        "cast": ["Zuri Spark", "Milo Quirk"],
        "pace": "Natural",
    }
if "scenes" not in st.session_state:
    st.session_state.scenes = []

# ------------------------------------------------------------
# UI
# ------------------------------------------------------------

st.title("🎬 Cartoon Studio V5")
st.caption("Image-based 2D cartoon animation using your uploaded character designs — lightweight and Render-safe.")

with st.sidebar:
    st.header("🎨 Episode")
    st.session_state.project["name"] = st.text_input("Project name", st.session_state.project["name"])
    st.session_state.project["style"] = st.selectbox("Visual style", STYLES, index=STYLES.index(st.session_state.project["style"]))
    st.session_state.project["location"] = st.selectbox("Default location", LOCATIONS, index=LOCATIONS.index(st.session_state.project["location"]))
    st.session_state.project["pace"] = st.selectbox("Dialogue pace", PACE, index=PACE.index(st.session_state.project["pace"]))
    st.divider()
    st.caption(f"Render: {W}×{H} · {FPS} FPS")
    st.caption("No Blender / OpenGL required")

tabs = st.tabs(["✨ Create", "🎭 Acting", "🎬 Storyboard", "🎞️ Join", "💾 Project"])

# CREATE
with tabs[0]:
    st.subheader("1. Choose your cast")
    st.session_state.project["cast"] = st.multiselect(
        "Original characters",
        list(CHARACTERS),
        default=st.session_state.project["cast"],
        max_selections=4,
    )
    if not st.session_state.project["cast"]:
        st.session_state.project["cast"] = ["Zuri Spark", "Milo Quirk"]

    selected = st.session_state.project["cast"]
    cols = st.columns(min(4, len(selected)))
    for i, name in enumerate(selected):
        with cols[i]:
            st.image(load_character(name, "portrait"), use_container_width=True)
            c = CHARACTERS[name]
            st.markdown(f"**{c['accent']} {name}**")
            st.caption(c["tag"])

    with st.expander("👥 View all 12 uploaded characters"):
        all_cols = st.columns(4)
        for i, name in enumerate(CHARACTERS):
            with all_cols[i % 4]:
                st.image(load_character(name, "portrait"), use_container_width=True)
                st.caption(name)

    st.subheader("2. Paste your script")
    script = st.text_area(
        "Use Character: dialogue",
        height=220,
        placeholder=(
            "Zuri Spark: Why does the fridge light disappear when I close the door?\n"
            "Milo Quirk: It doesn't disappear. You just can't see it.\n"
            "Zuri Spark: So the fridge is hiding things from me?\n"
            "Milo Quirk: That is a surprisingly accurate description."
        ),
    )

    if st.button("🧠 Build Episode Automatically", type="primary", use_container_width=True):
        rows = parse_script(script)
        scenes = []
        if not rows:
            st.warning("Add a script first.")
        else:
            for i, (speaker, text) in enumerate(rows):
                if speaker not in selected:
                    speaker = selected[0]
                emotion = infer_emotion(text)
                gesture = infer_gesture(text, emotion)
                scenes.append({
                    "id": i + 1,
                    "speaker": speaker,
                    "dialogue": text,
                    "location": st.session_state.project["location"],
                    "duration": estimate_duration(text, st.session_state.project["pace"]),
                    "posture": infer_posture(st.session_state.project["location"], text),
                    "emotion": emotion,
                    "gesture": gesture,
                    "camera": "Auto",
                })
            st.session_state.scenes = scenes
            st.success(f"Built {len(scenes)} acted shots using your character artwork.")

# ACTING
with tabs[1]:
    st.subheader("🎭 Acting Director")
    st.write("Characters keep their positions while performing subtle motion, reacting and speaking.")
    if not st.session_state.scenes:
        st.info("Build an episode from the Create tab first.")
    else:
        for scene in st.session_state.scenes:
            with st.expander(f"Shot {scene['id']} · {scene['speaker']} · {scene['emotion']} · {scene['gesture']}", expanded=False):
                a, b, c, d, e = st.columns(5)
                with a:
                    opts = POSTURES
                    scene["posture"] = st.selectbox("Posture", opts, index=opts.index(scene["posture"]) if scene["posture"] in opts else 0, key=f"p{scene['id']}")
                with b:
                    opts = EMOTIONS
                    scene["emotion"] = st.selectbox("Emotion", opts, index=opts.index(scene["emotion"]) if scene["emotion"] in opts else 0, key=f"e{scene['id']}")
                with c:
                    opts = GESTURES
                    scene["gesture"] = st.selectbox("Gesture", opts, index=opts.index(scene["gesture"]) if scene["gesture"] in opts else 0, key=f"g{scene['id']}")
                with d:
                    opts = CAMERAS
                    scene["camera"] = st.selectbox("Camera", opts, index=opts.index(scene["camera"]) if scene["camera"] in opts else 0, key=f"c{scene['id']}")
                with e:
                    scene["duration"] = st.number_input("Seconds", 1.5, 15.0, float(scene["duration"]), 0.5, key=f"d{scene['id']}")

# STORYBOARD
with tabs[2]:
    st.subheader("🎬 Storyboard & Render")
    if not st.session_state.scenes:
        st.info("Build an episode first.")
    else:
        for scene in st.session_state.scenes:
            st.markdown(f"**SHOT {scene['id']} — {scene['speaker']}**  \n{scene['dialogue']}")
        st.divider()
        progress = st.progress(0)
        status = st.empty()
        if st.button("🚀 Render 2D Cartoon", type="primary", use_container_width=True):
            def cb(v):
                progress.progress(min(1.0, v))
                status.write(f"Animating… {int(v * 100)}%")
            with st.spinner("Rendering your uploaded characters…"):
                out, err = render_video(st.session_state.scenes, st.session_state.project, cb)
            if out:
                progress.progress(1.0)
                status.success("Finished.")
                st.session_state.output = str(out)
            else:
                status.error("Render failed.")
                st.code(err or "Unknown FFmpeg error")

        if st.session_state.get("output") and Path(st.session_state.output).exists():
            st.video(st.session_state.output)
            st.download_button(
                "⬇️ Download MP4",
                Path(st.session_state.output).read_bytes(),
                "cartoon_studio_v5.mp4",
                "video/mp4",
                use_container_width=True,
            )

# JOIN
with tabs[3]:
    st.subheader("🎞️ Make a long episode from short videos")
    files = st.file_uploader("Upload clips in the order they should play", type=["mp4", "mov", "m4v"], accept_multiple_files=True)
    if files:
        for i, f in enumerate(files, 1):
            st.write(f"{i}. **{f.name}**")
        if st.button("🔗 Join Clips", type="primary", use_container_width=True):
            with st.spinner("Joining clips…"):
                out, err = join_videos(files)
            if out:
                st.session_state.joined = str(out)
                st.success("Full episode created.")
            else:
                st.error(err or "Join failed.")
    if st.session_state.get("joined") and Path(st.session_state.joined).exists():
        st.video(st.session_state.joined)
        st.download_button("⬇️ Download Full Episode", Path(st.session_state.joined).read_bytes(), "cartoon_episode.mp4", "video/mp4", use_container_width=True)

# PROJECT
with tabs[4]:
    st.subheader("💾 Project")
    project_data = {"project": st.session_state.project, "scenes": st.session_state.scenes, "version": "5.0-image-characters"}
    st.json({
        "name": st.session_state.project["name"],
        "characters": st.session_state.project["cast"],
        "style": st.session_state.project["style"],
        "shots": len(st.session_state.scenes),
        "render": f"{W}x{H} @ {FPS} FPS",
    })
    st.download_button("💾 Save Project JSON", json.dumps(project_data, indent=2), "cartoon_studio_v5_project.json", "application/json", use_container_width=True)

st.divider()
st.caption("Cartoon Studio V5 · Uses the uploaded original character artwork · 640×360 / 12 FPS memory-safe renderer")
