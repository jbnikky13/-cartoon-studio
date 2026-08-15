# 🎬 Cartoon Studio — 3D

A Streamlit front end controlling a Blender-based procedural 3D cartoon engine.

## What it does

- Original procedural 3D characters: Zuri Spark and Milo Quirk
- Stable character staging
- Dialogue-driven animation
- Procedural talking/lip movement
- Blinking and simple expressions
- Gestures such as wave, point, nod and laugh
- 3D environments
- Camera and lighting
- Bottom subtitles synchronized to dialogue timing
- Optional voice/audio track
- MP4 rendering
- `.blend` scene saved beside the MP4

## Important deployment note

Blender is a separate rendering application. `requirements.txt` installs only Streamlit; Blender is not a normal pip dependency.

For local Windows/macOS/Linux use, install Blender and set its executable path in the app sidebar. Blender supports background execution with Python, which is the mechanism used by this project.

Streamlit Community Cloud is not enough by itself for this renderer unless you move the Blender worker into a compatible container/server. The current repository is therefore designed first as a real local 3D engine and can later be connected to a remote render worker.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then set the Blender executable in the sidebar if `blender` is not on PATH.

## Script format

```text
Zuri Spark: [wave] Hey Milo!
Milo Quirk: [nod] Hey Zuri!
Zuri Spark: [point] Look over there.
Milo Quirk: [laugh] That's funny!
```

Supported action tags currently include:

`wave`, `point`, `nod`, `shake`, `laugh`, `surprised`, `walk`, `sit`

## Assets

The repository intentionally does not include commercial/proprietary character models. The included characters are generated procedurally by Blender.
