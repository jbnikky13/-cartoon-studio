from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime
import streamlit as st
from photoreal_engine import CharacterReference, SceneSpec, image_to_data_url


def _api_key() -> str:
    key = os.getenv("MINIMAX_API_KEY", "")
    try:
        key = st.secrets.get("MINIMAX_API_KEY", key)
    except Exception:
        pass
    return st.sidebar.text_input("MiniMax API key", value=key, type="password", help="Stored only in the current Streamlit session when entered here.").strip()


def _character_editor() -> list[CharacterReference]:
    st.subheader("👤 Recurring characters")
    st.caption("Use one clear human reference per recurring character. H3 reuses these references across scenes.")
    count = st.number_input("Number of characters", 1, 6, 2, 1)
    chars = []
    cols = st.columns(min(3, int(count)))
    defaults = ["Zuri", "Milo", "Kemi", "Ada", "Noah", "Tara"]
    for i in range(int(count)):
        with cols[i % len(cols)]:
            st.markdown(f"**Character {i + 1}**")
            name = st.text_input("Name", value=defaults[i], key=f"photo_char_name_{i}")
            desc = st.text_area("Identity / appearance", height=90, key=f"photo_char_desc_{i}", placeholder="28-year-old woman, warm brown skin, shoulder-length black hair, green blouse...")
            url = st.text_input("Reference image URL", key=f"photo_char_url_{i}", placeholder="https://...")
            upload = st.file_uploader("Or upload reference", type=["jpg", "jpeg", "png", "webp"], key=f"photo_char_upload_{i}")
            data_url = image_to_data_url(upload) if upload else ""
            if upload:
                st.image(upload, caption=f"{name or 'Character'} reference", width=180)
            chars.append(CharacterReference(name=name.strip() or f"Character {i + 1}", description=desc.strip(), image_url=url.strip(), image_data_url=data_url))
    return chars


def _scene_editor(chars: list[CharacterReference]) -> list[SceneSpec]:
    st.subheader("🎬 Microdrama scenes")
    st.caption("H3 supports 4–15 second clips. Keep each scene focused on one continuous action and enter spoken dialogue verbatim.")
    count = st.number_input("Number of scenes", 1, 12, 3, 1, key="photo_scene_count")
    scenes = []
    names = [c.name for c in chars]
    for i in range(int(count)):
        with st.expander(f"Scene {i + 1}", expanded=(i == 0)):
            title = st.text_input("Scene title", value=f"Scene {i + 1}", key=f"photo_scene_title_{i}")
            setting = st.text_area("Setting", height=70, key=f"photo_scene_setting_{i}", placeholder="Lagos apartment kitchen at sunset, warm window light...")
            selected = st.multiselect("Characters", names, default=names[:1], key=f"photo_scene_chars_{i}")
            action = st.text_area("Action / camera direction", height=90, key=f"photo_scene_action_{i}", placeholder="She enters, notices the phone, freezes, then slowly picks it up. Camera pushes in...")
            dialogue = st.text_area("Exact spoken dialogue", height=100, key=f"photo_scene_dialogue_{i}", placeholder="Put the exact words the character should say here.")
            duration = st.slider("Duration (seconds)", 4, 15, 6, key=f"photo_scene_duration_{i}")
            scenes.append(SceneSpec(i + 1, title.strip(), setting.strip(), action.strip(), dialogue.strip(), selected, int(duration)))
    return scenes


def render_photoreal_microdrama():
    st.header("🎥 Photoreal AI Microdrama")
    st.markdown("Turn recurring human references + a scene script into photorealistic, dialogue-driven short drama clips.")
    with st.sidebar:
        st.divider(); st.subheader("⚙️ Render")
        model = st.selectbox("Model", ["MiniMax-H3", "MiniMax-H3-Max"], index=0, help="Use H3 for reference-to-video. H3-Max does not support reference-to-video.")
        resolution = st.selectbox("Resolution", ["768P", "2K"], index=0)
        ratio = st.selectbox("Aspect ratio", ["9:16", "16:9", "1:1", "4:3", "3:4", "21:9"], index=0)
        captions = st.checkbox("Burn dialogue captions into final video", True)
        st.info("MiniMax charges for generation. Test one short scene before rendering a full episode.")
    key = _api_key()
    if model == "MiniMax-H3-Max":
        st.warning("H3-Max cannot use recurring reference images. Switch to MiniMax-H3 for this studio workflow.")
    chars = _character_editor(); scenes = _scene_editor(chars)
    missing = [c.name for c in chars if not (c.image_url or c.image_data_url)]
    st.divider()
    if missing: st.warning("Add a reference image URL or upload for: " + ", ".join(missing))
    if not key: st.info("Add MINIMAX_API_KEY to deployment secrets or enter it in the sidebar.")
    disabled = not key or bool(missing) or model == "MiniMax-H3-Max"
    if st.button("🚀 Generate Photoreal Microdrama", type="primary", use_container_width=True, disabled=disabled):
        from photoreal_engine import create_video_task, poll_video_task, download_video, stitch_clips, burn_captions, srt_for_scenes
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S"); workdir = Path("generated_microdramas") / run_id; workdir.mkdir(parents=True, exist_ok=True)
        status_box = st.empty(); progress = st.progress(0); total = len(scenes); current = {"n": 0}
        try:
            for idx, scene in enumerate(scenes, 1):
                current["n"] = idx
                def callback(status, task):
                    if status == "queued": status_box.info(f"Scene {idx}/{total}: queued…")
                    elif status == "running": status_box.info(f"Scene {idx}/{total}: MiniMax is rendering…")
                    elif status == "succeeded": status_box.success(f"Scene {idx}/{total}: complete")
                task_id = create_video_task(key, scene, chars, model=model, resolution=resolution, ratio=ratio)
                task = poll_video_task(key, task_id, progress_callback=callback)
                clip = workdir / f"scene_{idx:02d}.mp4"; download_video(task["content"]["url"], clip)
                st.video(clip.read_bytes()); st.caption(f"Scene {idx} task: `{task_id}`")
                progress.progress(int(idx / total * 100))
            clips = [workdir / f"scene_{i:02d}.mp4" for i in range(1, total + 1)]
            raw = workdir / "microdrama_raw.mp4"; stitch_clips(clips, raw)
            final = workdir / "microdrama_final.mp4"
            if captions: burn_captions(raw, srt_for_scenes(scenes), final)
            else: raw.replace(final)
            data = final.read_bytes(); st.success("🎬 Episode complete"); st.video(data)
            st.download_button("⬇️ Download final microdrama", data=data, file_name="photoreal_microdrama.mp4", mime="video/mp4", use_container_width=True)
        except Exception as exc:
            st.error(f"Generation failed: {exc}")
            st.caption("Check the MiniMax API key, reference image URL/upload, model, account balance, and exact dialogue.")
