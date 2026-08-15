import bpy
import json
import math
import os
import re
import sys
import shutil
import subprocess
from mathutils import Vector

# ---------- utilities ----------

def args():
    a = sys.argv
    if "--" not in a:
        raise RuntimeError("Missing engine arguments.")
    x = a[a.index("--") + 1:]
    if len(x) < 2:
        raise RuntimeError("Expected config and output.")
    return x[0], x[1], (x[2] if len(x) > 2 and x[2] else None)

def mat(name, color, metallic=0.0, rough=0.55):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1)
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metallic
    return m

def sphere(name, loc, scale, material, parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    if parent: o.parent = parent
    return o

def cube(name, loc, scale, material, bevel=0.15, parent=None):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        b = o.modifiers.new("Rounded", "BEVEL")
        b.width = bevel
        b.segments = 4
    o.data.materials.append(material)
    if parent: o.parent = parent
    return o

def cylinder(name, loc, radius, depth, material, parent=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius, depth=depth, location=loc)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(material)
    if parent: o.parent = parent
    return o

def clear():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        pass

# ---------- characters ----------

def character(name, x, shirt, hair, skin=(0.55, 0.28, 0.14)):
    root = bpy.data.objects.new(name + "_ROOT", None)
    bpy.context.collection.objects.link(root)

    skin_m = mat(name+"_skin", skin)
    shirt_m = mat(name+"_shirt", shirt)
    hair_m = mat(name+"_hair", hair)
    white = mat(name+"_white", (0.95, 0.95, 0.95), rough=0.35)
    black = mat(name+"_black", (0.015, 0.015, 0.02), rough=0.35)
    mouth_m = mat(name+"_mouth", (0.12, 0.015, 0.02), rough=0.35)
    shoe_m = mat(name+"_shoe", (0.035, 0.04, 0.05))

    # Stable body placement: x is never changed by dialogue animation.
    sphere(name+"_body", (x, 0, 2.15), (0.82, 0.58, 1.0), shirt_m, root)
    sphere(name+"_head", (x, 0, 3.72), (0.84, 0.72, 0.84), skin_m, root)
    sphere(name+"_hair", (x, 0.03, 4.25), (0.87, 0.74, 0.42), hair_m, root)

    for side, dx in [("L", -0.28), ("R", 0.28)]:
        sphere(name+"_eye_"+side, (x+dx, -0.68, 3.82), (0.13, 0.06, 0.16), white, root)
        sphere(name+"_pupil_"+side, (x+dx, -0.735, 3.82), (0.055, 0.025, 0.075), black, root)

    sphere(name+"_mouth", (x, -0.70, 3.45), (0.22, 0.045, 0.08), mouth_m, root)
    sphere(name+"_nose", (x, -0.72, 3.62), (0.09, 0.07, 0.09), skin_m, root)

    for side, dx in [("L", -0.92), ("R", 0.92)]:
        arm = sphere(name+"_arm_"+side, (x+dx, 0, 2.35), (0.23, 0.25, 0.78), shirt_m, root)
        hand = sphere(name+"_hand_"+side, (x+dx, 0, 1.62), (0.23, 0.23, 0.23), skin_m, root)
        arm["rest_rot"] = [arm.rotation_euler.x, arm.rotation_euler.y, arm.rotation_euler.z]
        hand["rest_rot"] = [hand.rotation_euler.x, hand.rotation_euler.y, hand.rotation_euler.z]

    for side, dx in [("L", -0.34), ("R", 0.34)]:
        cylinder(name+"_leg_"+side, (x+dx, 0, 0.86), 0.21, 1.05, shirt_m, root)
        sphere(name+"_shoe_"+side, (x+dx, -0.16, 0.28), (0.30, 0.48, 0.18), shoe_m, root)

    # simple facial expression control object
    expr = bpy.data.objects.new(name+"_FACE_CTRL", None)
    bpy.context.collection.objects.link(expr)
    expr.parent = root
    expr.location = (0, 0, 0)

    return root

# ---------- environment ----------

def environment(kind):
    floor = mat("floor", (0.12, 0.16, 0.20))
    wall = mat("wall", (0.24, 0.28, 0.34))
    accent = mat("accent", (0.12, 0.38, 0.55))
    green = mat("grass", (0.08, 0.32, 0.10))
    wood = mat("wood", (0.38, 0.20, 0.08))
    white = mat("white", (0.8, 0.82, 0.84))

    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
    bpy.context.object.data.materials.append(green if kind == "park" else floor)

    if kind in ("studio", "classroom", "bedroom", "pharmacy", "street"):
        cube("back_wall", (0, 4.2, 4.0), (7, 0.18, 4), wall, 0.1)

    if kind == "classroom":
        cube("board", (0, 3.95, 4.4), (3.0, 0.08, 1.2), accent, 0.05)
        for x in (-4, -1.5, 1.5, 4):
            cube("desk", (x, 1.2, 0.9), (1.0, 0.55, 0.08), wood, 0.05)

    elif kind == "bedroom":
        cube("bed", (2.5, 1.8, 0.55), (2.2, 1.2, 0.25), white, 0.18)
        cube("pillow", (2.5, 2.55, 0.9), (0.8, 0.35, 0.18), white, 0.12)

    elif kind == "pharmacy":
        cube("counter", (0, 2.6, 1.0), (3.2, 0.7, 0.5), white, 0.12)
        cube("sign", (0, 3.8, 5.0), (2.3, 0.08, 0.55), accent, 0.05)

    elif kind == "street":
        road = mat("road", (0.05, 0.05, 0.06))
        cube("road", (0, 2, 0.05), (7, 6, 0.05), road, 0)

    elif kind == "park":
        trunk = mat("trunk", (0.28, 0.12, 0.04))
        leaves = mat("leaves", (0.04, 0.30, 0.07))
        for x in (-5, 5):
            cylinder("tree_trunk", (x, 3, 1.5), 0.35, 3, trunk)
            sphere("tree_top", (x, 3, 3.7), (1.6, 1.6, 1.6), leaves)

# ---------- camera / lights ----------

def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()

def setup_camera():
    bpy.ops.object.camera_add(location=(0, -14, 4.2))
    cam = bpy.context.object
    cam.data.lens = 52
    look_at(cam, (0, 0, 2.4))
    bpy.context.scene.camera = cam
    return cam

def setup_lights():
    for loc, energy, size in [
        ((-4, -5, 8), 1100, 5),
        ((5, -2, 5), 700, 4),
        ((0, 4, 7), 900, 3),
    ]:
        bpy.ops.object.light_add(type="AREA", location=loc)
        l = bpy.context.object
        l.data.energy = energy
        l.data.shape = "DISK"
        l.data.size = size
        look_at(l, (0, 0, 2.5))

# ---------- script parsing / animation ----------

ACTION_RE = re.compile(r"\[([a-zA-Z_]+)\]")

def parse_script(text):
    out = []
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw or ":" not in raw:
            continue
        speaker, words = raw.split(":", 1)
        actions = ACTION_RE.findall(words)
        words = ACTION_RE.sub("", words).strip()
        out.append({"speaker": speaker.strip(), "text": words, "actions": actions})
    return out

def duration_seconds(text):
    return max(1.2, len(text.split()) / 2.45)

def animate_idle(name, start, end):
    root = bpy.data.objects.get(name+"_ROOT")
    if not root: return
    z = root.location.z
    for f, dz in [(start,0), (start+20,0.035), (start+40,0), (end,0)]:
        root.location.z = z + dz
        root.keyframe_insert("location", frame=f)

def animate_blink(name, start, end):
    for side in ("L","R"):
        eye = bpy.data.objects.get(name+"_eye_"+side)
        if not eye: continue
        original = eye.scale.copy()
        f = start + 25
        while f < end - 5:
            eye.scale.z = 0.015
            eye.keyframe_insert("scale", frame=f)
            eye.scale = original
            eye.keyframe_insert("scale", frame=f+4)
            f += 80

def animate_talking(name, start, end):
    mouth = bpy.data.objects.get(name+"_mouth")
    if not mouth: return
    original = mouth.scale.copy()
    f = start
    while f <= end:
        mouth.scale = original
        mouth.keyframe_insert("scale", frame=f)
        mouth.scale.z = original.z * 2.0
        mouth.keyframe_insert("scale", frame=f+4)
        mouth.scale = original
        mouth.keyframe_insert("scale", frame=f+8)
        f += 8

def gesture(name, action, frame):
    arm = bpy.data.objects.get(name+"_arm_R")
    root = bpy.data.objects.get(name+"_ROOT")
    if not arm: return
    rest = arm.rotation_euler.copy()
    delta = {
        "wave": math.radians(-28),
        "point": math.radians(-18),
        "nod": 0,
        "shake": 0,
        "laugh": math.radians(-12),
        "surprised": math.radians(-8),
        "walk": math.radians(-25),
        "sit": math.radians(5),
    }.get(action, math.radians(-10))
    arm.rotation_euler.z = rest.z + delta
    arm.keyframe_insert("rotation_euler", frame=frame)
    arm.rotation_euler = rest
    arm.keyframe_insert("rotation_euler", frame=frame+12)
    if action == "nod" and root:
        r = root.rotation_euler.copy()
        root.rotation_euler.x = math.radians(-7)
        root.keyframe_insert("rotation_euler", frame=frame)
        root.rotation_euler = r
        root.keyframe_insert("rotation_euler", frame=frame+10)

def animate_lines(lines, fps, cfg):
    current = 1
    subtitle_events = []
    for line in lines:
        name = line["speaker"]
        if not bpy.data.objects.get(name+"_ROOT"):
            current += int(duration_seconds(line["text"]) * fps)
            continue
        dur = int(duration_seconds(line["text"]) * fps)
        start, end = current, current + dur
        animate_idle(name, start, end)
        animate_talking(name, start, end)
        if cfg.get("blinking", True):
            animate_blink(name, start, end)
        if cfg.get("gestures", True):
            for a in line["actions"]:
                gesture(name, a, start + min(15, dur//3))
        subtitle_events.append((start, end, name, line["text"]))
        current = end + int(0.15 * fps)
    return current, subtitle_events

# ---------- subtitles ----------

def subtitle_plane(text, start, end):
    # Text object is placed in front of camera and keyframed for visibility.
    bpy.ops.object.text_add(location=(0, -13.1, 0.55))
    t = bpy.context.object
    t.name = "SUBTITLE"
    t.data.body = text
    t.data.align_x = "CENTER"
    t.data.align_y = "CENTER"
    t.data.size = 0.34
    t.data.extrude = 0.002
    t.data.materials.append(mat("subtitle_mat", (1,1,1), rough=0.3))
    t.hide_render = True
    t.keyframe_insert("hide_render", frame=start-1)
    t.hide_render = False
    t.keyframe_insert("hide_render", frame=start)
    t.keyframe_insert("hide_render", frame=end)
    t.hide_render = True
    t.keyframe_insert("hide_render", frame=end+1)

# ---------- audio ----------

def add_audio(path):
    if not path or not os.path.exists(path):
        return
    scene = bpy.context.scene
    scene.sequence_editor_create()
    # Blender's sequence editor accepts common audio formats.
    bpy.ops.sequencer.sound_strip_add(filepath=os.path.abspath(path), frame_start=1)
    strip = scene.sequence_editor.sequences_all[-1]
    scene.frame_end = max(scene.frame_end, int(strip.frame_final_duration + 1))

# ---------- render ----------

def render_setup(cfg, output):
    scene = bpy.context.scene
    w, h = map(int, cfg.get("resolution", "1280x720").split("x"))
    scene.render.resolution_x = w
    scene.render.resolution_y = h
    scene.render.resolution_percentage = 100
    scene.render.fps = int(cfg.get("fps", 24))
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.filepath = os.path.abspath(output)
    scene.render.film_transparent = False
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except Exception:
        pass
    scene.world.color = (0.025, 0.035, 0.055)

def main():
    config_path, output, audio = args()
    cfg = json.loads(open(config_path, encoding="utf-8").read())
    clear()
    environment(cfg.get("environment", "studio"))

    chars = cfg.get("characters", [])
    if "Zuri Spark" in chars:
        character("Zuri Spark", -2.0, (0.95,0.30,0.48), (0.08,0.025,0.01))
    if "Milo Quirk" in chars:
        character("Milo Quirk", 2.0, (0.95,0.68,0.15), (0.025,0.025,0.03))

    setup_camera()
    setup_lights()

    lines = parse_script(cfg.get("script", ""))
    end_frame, subtitles = animate_lines(lines, int(cfg.get("fps",24)), cfg)
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = max(end_frame + int(cfg.get("fps",24)), 48)

    if cfg.get("subtitles", True):
        # Bottom-center 3D subtitles, synchronized to each dialogue interval.
        for start, end, name, text in subtitles:
            subtitle_plane(f"{name}: {text}", start, end)

    add_audio(audio)
    render_setup(cfg, output)

    blend_path = os.path.splitext(output)[0] + ".blend"
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(blend_path))
    print("RENDER_START")
    bpy.ops.render.render(animation=True)
    print("RENDER_DONE", os.path.abspath(output))

if __name__ == "__main__":
    main()
