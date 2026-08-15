import json
import math
import os
import re
import sys

import bpy
from mathutils import Vector


# ============================================================
# CARTOON STUDIO - BLENDER 3D ENGINE
# ============================================================

def args_after_separator():
    if "--" not in sys.argv:
        raise RuntimeError("Missing engine arguments.")

    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) < 2:
        raise RuntimeError(
            "Expected: scene.json output.mp4 [audio_file]"
        )

    return args[0], args[1], args[2] if len(args) > 2 else ""


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def material(name, color, roughness=0.55, metallic=0.0):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)

    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic

    return mat


def sphere(name, loc, scale, mat, parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=32,
        ring_count=20,
        location=loc,
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(
        location=False,
        rotation=False,
        scale=True,
    )
    obj.data.materials.append(mat)
    if parent:
        obj.parent = parent
    return obj


def cube(name, loc, scale, mat, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(
        location=False,
        rotation=False,
        scale=True,
    )
    if bevel:
        mod = obj.modifiers.new("Rounded", "BEVEL")
        mod.width = bevel
        mod.segments = 4
    obj.data.materials.append(mat)
    return obj


def cylinder(name, loc, radius, depth, mat):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32,
        radius=radius,
        depth=depth,
        location=loc,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    return obj


def create_character(name, x, shirt_color, hair_color, skin_color):
    root = bpy.data.objects.new(name + "_ROOT", None)
    bpy.context.collection.objects.link(root)

    skin = material(name + "_skin", skin_color)
    shirt = material(name + "_shirt", shirt_color)
    hair = material(name + "_hair", hair_color)
    white = material(name + "_white", (0.96, 0.96, 0.96), 0.3)
    black = material(name + "_black", (0.01, 0.01, 0.015), 0.35)
    mouth_mat = material(name + "_mouth", (0.10, 0.008, 0.015), 0.4)
    shoe = material(name + "_shoe", (0.025, 0.03, 0.04), 0.5)

    sphere(
        name + "_BODY",
        (x, 0, 2.15),
        (0.82, 0.58, 1.0),
        shirt,
        root,
    )

    sphere(
        name + "_HEAD",
        (x, 0, 3.72),
        (0.84, 0.72, 0.84),
        skin,
        root,
    )

    sphere(
        name + "_HAIR",
        (x, 0.03, 4.25),
        (0.87, 0.74, 0.42),
        hair,
        root,
    )

    for side, dx in (("L", -0.28), ("R", 0.28)):
        sphere(
            name + "_EYE_" + side,
            (x + dx, -0.68, 3.82),
            (0.13, 0.06, 0.16),
            white,
            root,
        )
        sphere(
            name + "_PUPIL_" + side,
            (x + dx, -0.735, 3.82),
            (0.055, 0.025, 0.075),
            black,
            root,
        )

    sphere(
        name + "_NOSE",
        (x, -0.72, 3.62),
        (0.09, 0.07, 0.09),
        skin,
        root,
    )

    sphere(
        name + "_MOUTH",
        (x, -0.70, 3.45),
        (0.22, 0.045, 0.08),
        mouth_mat,
        root,
    )

    for side, dx in (("L", -0.92), ("R", 0.92)):
        arm = sphere(
            name + "_ARM_" + side,
            (x + dx, 0, 2.35),
            (0.23, 0.25, 0.78),
            shirt,
            root,
        )
        arm["rest_z"] = arm.rotation_euler.z

        sphere(
            name + "_HAND_" + side,
            (x + dx, 0, 1.62),
            (0.23, 0.23, 0.23),
            skin,
            root,
        )

    for side, dx in (("L", -0.34), ("R", 0.34)):
        cylinder(
            name + "_LEG_" + side,
            (x + dx, 0, 0.86),
            0.21,
            1.05,
            shirt,
        )
        sphere(
            name + "_SHOE_" + side,
            (x + dx, -0.16, 0.28),
            (0.30, 0.48, 0.18),
            shoe,
            root,
        )

    return root


def build_environment(kind):
    floor = material("floor", (0.12, 0.16, 0.20))
    wall = material("wall", (0.24, 0.28, 0.34))
    grass = material("grass", (0.08, 0.32, 0.10))
    wood = material("wood", (0.38, 0.20, 0.08))
    white = material("white_env", (0.82, 0.84, 0.88))
    accent = material("accent", (0.10, 0.38, 0.55))

    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
    plane = bpy.context.object
    plane.data.materials.append(grass if kind == "park" else floor)

    if kind != "park":
        cube("BACK_WALL", (0, 4.2, 4), (7, 0.18, 4), wall, 0.1)

    if kind == "classroom":
        cube("BOARD", (0, 3.95, 4.4), (3, 0.08, 1.2), accent, 0.05)
        for x in (-4, -1.5, 1.5, 4):
            cube("DESK", (x, 1.2, 0.9), (1, 0.55, 0.08), wood, 0.05)

    elif kind == "bedroom":
        cube("BED", (2.5, 1.8, 0.55), (2.2, 1.2, 0.25), white, 0.18)
        cube("PILLOW", (2.5, 2.55, 0.9), (0.8, 0.35, 0.18), white, 0.12)

    elif kind == "pharmacy":
        cube(
            "COUNTER",
            (0, 2.6, 1),
            (3.2, 0.7, 0.5),
            white,
            0.12,
        )
        cube(
            "SIGN",
            (0, 3.8, 5),
            (2.3, 0.08, 0.55),
            accent,
            0.05,
        )

    elif kind == "street":
        road = material("road", (0.05, 0.05, 0.06))
        cube("ROAD", (0, 2, 0.05), (7, 6, 0.05), road)

    elif kind == "park":
        trunk = material("trunk", (0.28, 0.12, 0.04))
        leaves = material("leaves", (0.04, 0.30, 0.07))
        for x in (-5, 5):
            cylinder("TREE_TRUNK", (x, 3, 1.5), 0.35, 3, trunk)
            sphere(
                "TREE_TOP",
                (x, 3, 3.7),
                (1.6, 1.6, 1.6),
                leaves,
            )


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def create_camera():
    bpy.ops.object.camera_add(location=(0, -14, 4.2))
    camera = bpy.context.object
    camera.name = "MAIN_CAMERA"
    camera.data.lens = 52
    look_at(camera, (0, 0, 2.45))
    bpy.context.scene.camera = camera
    return camera


def create_lighting():
    for location, energy, size in (
        ((-4, -5, 8), 1100, 5),
        ((5, -2, 5), 700, 4),
        ((0, 4, 7), 900, 3),
    ):
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        look_at(light, (0, 0, 2.5))


ACTION_RE = re.compile(r"\[([A-Za-z_]+)\]")


def parse_script(script):
    result = []
    for raw in script.splitlines():
        raw = raw.strip()
        if not raw or ":" not in raw:
            continue

        speaker, dialogue = raw.split(":", 1)
        actions = ACTION_RE.findall(dialogue)
        dialogue = ACTION_RE.sub("", dialogue).strip()

        if dialogue:
            result.append(
                {
                    "speaker": speaker.strip(),
                    "dialogue": dialogue,
                    "actions": [a.lower() for a in actions],
                }
            )
    return result


def duration_seconds(text):
    words = max(1, len(text.split()))
    return max(1.2, words / 2.45)


def keyframe(obj, path, frame):
    obj.keyframe_insert(data_path=path, frame=frame)


def animate_blink(name, start, end):
    if end - start < 35:
        return

    for side in ("L", "R"):
        eye = bpy.data.objects.get(name + "_EYE_" + side)
        if not eye:
            continue

        original = eye.scale.copy()
        frame = start + 28

        while frame < end - 5:
            eye.scale.z = 0.015
            keyframe(eye, "scale", frame)

            eye.scale = original
            keyframe(eye, "scale", frame + 4)

            frame += 75


def animate_talking(name, start, end):
    mouth = bpy.data.objects.get(name + "_MOUTH")
    if not mouth:
        return

    original = mouth.scale.copy()
    frame = start

    while frame <= end:
        mouth.scale = original
        keyframe(mouth, "scale", frame)

        mouth.scale.z = original.z * 1.8
        keyframe(mouth, "scale", frame + 3)

        mouth.scale = original
        keyframe(mouth, "scale", frame + 7)

        frame += 7


def animate_expression(name, action, frame):
    if action not in ("laugh", "surprised", "shake"):
        return

    head = bpy.data.objects.get(name + "_HEAD")
    mouth = bpy.data.objects.get(name + "_MOUTH")

    if head:
        original = head.rotation_euler.copy()

        if action == "surprised":
            head.rotation_euler.x = math.radians(-5)
        elif action == "laugh":
            head.rotation_euler.z = math.radians(4)
        else:
            head.rotation_euler.z = math.radians(-5)

        keyframe(head, "rotation_euler", frame)
        head.rotation_euler = original
        keyframe(head, "rotation_euler", frame + 14)

    if mouth:
        original = mouth.scale.copy()

        if action == "surprised":
            mouth.scale.z = original.z * 2.8
        elif action == "laugh":
            mouth.scale.z = original.z * 1.6

        keyframe(mouth, "scale", frame)
        mouth.scale = original
        keyframe(mouth, "scale", frame + 14)


def animate_gesture(name, action, frame):
    root = bpy.data.objects.get(name + "_ROOT")
    arm = bpy.data.objects.get(name + "_ARM_R")
    if not arm:
        return

    if action == "nod" and root:
        original = root.rotation_euler.copy()
        root.rotation_euler.x = math.radians(-7)
        keyframe(root, "rotation_euler", frame)
        root.rotation_euler = original
        keyframe(root, "rotation_euler", frame + 10)
        return

    if action == "shake" and root:
        original = root.rotation_euler.copy()
        root.rotation_euler.z = math.radians(-5)
        keyframe(root, "rotation_euler", frame)
        root.rotation_euler.z = math.radians(5)
        keyframe(root, "rotation_euler", frame + 6)
        root.rotation_euler = original
        keyframe(root, "rotation_euler", frame + 12)
        return

    angles = {
        "wave": -35,
        "point": -22,
        "laugh": -14,
        "surprised": -8,
        "walk": -25,
        "sit": 5,
    }

    angle = math.radians(angles.get(action, -10))
    original = arm.rotation_euler.copy()

    arm.rotation_euler.z = original.z + angle
    keyframe(arm, "rotation_euler", frame)

    arm.rotation_euler = original
    keyframe(arm, "rotation_euler", frame + 14)


def animate_script(lines, fps, config):
    current = 1
    subtitles = []

    for line in lines:
        name = line["speaker"]
        start = current
        end = start + int(duration_seconds(line["dialogue"]) * fps)

        root = bpy.data.objects.get(name + "_ROOT")
        if root:
            original_z = root.location.z

            for f, offset in (
                (start, 0),
                (start + 18, 0.035),
                (start + 36, 0),
                (end, 0),
            ):
                root.location.z = original_z + offset
                keyframe(root, "location", f)

            if config.get("blinking", True):
                animate_blink(name, start, end)

            animate_talking(name, start, end)

            if config.get("gestures", True):
                for action in line["actions"]:
                    animate_gesture(name, action, start + 12)

            if config.get("expressions", True):
                for action in line["actions"]:
                    animate_expression(name, action, start + 10)

        subtitles.append(
            {
                "speaker": name,
                "text": line["dialogue"],
                "start": start,
                "end": end,
            }
        )

        current = end + int(0.15 * fps)

    return current, subtitles


def add_subtitle(text, start, end):
    mat = material(
        "subtitle_mat",
        (1.0, 1.0, 1.0),
        0.25,
    )

    bpy.ops.object.text_add(location=(0, -0.75, 0.45))
    obj = bpy.context.object
    obj.name = "SUBTITLE_" + str(start)

    obj.data.body = text
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.data.size = 0.34
    obj.data.extrude = 0.002
    obj.data.materials.append(mat)

    # Text lies in the XY plane by default.
    # Rotate it so its face points toward the camera.
    obj.rotation_euler = (math.radians(90), 0, 0)

    obj.hide_render = True
    keyframe(obj, "hide_render", max(1, start - 1))

    obj.hide_render = False
    keyframe(obj, "hide_render", start)

    keyframe(obj, "hide_render", end)

    obj.hide_render = True
    keyframe(obj, "hide_render", end + 1)


def add_audio(audio_path):
    if not audio_path or not os.path.exists(audio_path):
        return

    scene = bpy.context.scene
    scene.sequence_editor_create()

    bpy.ops.sequencer.sound_strip_add(
        filepath=os.path.abspath(audio_path),
        frame_start=1,
    )


def configure_render(config, output):
    scene = bpy.context.scene

    width, height = (
        int(x) for x in config.get("resolution", "1280x720").split("x")
    )

    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.fps = int(config.get("fps", 24))

    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except Exception:
        scene.render.engine = "BLENDER_EEVEE"

    quality = config.get("quality", "Balanced")
    if quality == "Fast":
        scene.render.image_settings.color_mode = "RGB"
    elif quality == "High":
        scene.render.image_settings.color_mode = "RGBA"

    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.audio_codec = "AAC"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.filepath = os.path.abspath(output)

    scene.render.film_transparent = False
    scene.world.color = (0.025, 0.035, 0.055)


def main():
    config_path, output_path, audio_path = args_after_separator()

    with open(config_path, "r", encoding="utf-8") as handle:
        config = json.load(handle)

    clear_scene()

    build_environment(config.get("environment", "studio"))

    characters = config.get("characters", [])

    if "Zuri Spark" in characters:
        create_character(
            "Zuri Spark",
            -2.0,
            (0.95, 0.30, 0.48),
            (0.08, 0.025, 0.01),
            (0.55, 0.28, 0.14),
        )

    if "Milo Quirk" in characters:
        create_character(
            "Milo Quirk",
            2.0,
            (0.95, 0.68, 0.15),
            (0.025, 0.025, 0.03),
            (0.55, 0.28, 0.14),
        )

    create_camera()
    create_lighting()

    lines = parse_script(config.get("script", ""))
    fps = int(config.get("fps", 24))

    last_frame, subtitle_events = animate_script(
        lines,
        fps,
        config,
    )

    if config.get("subtitles", True):
        for event in subtitle_events:
            add_subtitle(
                f'{event["speaker"]}: {event["text"]}',
                event["start"],
                event["end"],
            )

    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = max(last_frame + fps, 48)

    add_audio(audio_path)
    configure_render(config, output_path)

    blend_path = os.path.splitext(output_path)[0] + ".blend"
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(blend_path))

    print("=== CARTOON STUDIO 3D ===")
    print("Rendering:", output_path)

    bpy.ops.render.render(animation=True)

    print("=== RENDER COMPLETE ===")
    print(output_path)


if __name__ == "__main__":
    main()
