# blender/engine.py
# Cartoon Studio 3D Rendering Engine
# Blender 4.x compatible
#
# This file is ONLY Python.
# Dockerfile commands such as FROM, RUN, COPY, CMD do NOT belong here.

import bpy
import os
import sys
import math
import subprocess
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path("/app")

PROJECT_DIR = BASE_DIR / "projects"
OUTPUT_DIR = BASE_DIR / "output"

PROJECT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# LOGGING
# ============================================================

def log(message):
    print(f"[CARTOON ENGINE] {message}", flush=True)


# ============================================================
# CLEAN SCENE
# ============================================================

def clear_scene():
    """Remove everything from the current Blender scene."""

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    # Remove unused datablocks
    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for block in list(datablocks):
            try:
                datablocks.remove(block)
            except Exception:
                pass


# ============================================================
# MATERIALS
# ============================================================

def make_material(name, color, roughness=0.65):
    mat = bpy.data.materials.get(name)

    if mat is None:
        mat = bpy.data.materials.new(name)

    mat.diffuse_color = (
        float(color[0]),
        float(color[1]),
        float(color[2]),
        1.0,
    )

    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")

    if bsdf:
        bsdf.inputs["Base Color"].default_value = (
            float(color[0]),
            float(color[1]),
            float(color[2]),
            1.0,
        )

        bsdf.inputs["Roughness"].default_value = roughness

    return mat


# ============================================================
# BASIC OBJECT HELPERS
# ============================================================

def add_uv_sphere(name, location, scale, material):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=32,
        ring_count=16,
        location=location,
    )

    obj = bpy.context.object
    obj.name = name
    obj.scale = scale

    bpy.ops.object.transform_apply(
        location=False,
        rotation=False,
        scale=True,
    )

    if material:
        obj.data.materials.append(material)

    return obj


def add_cube(name, location, scale, material, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(
        location=location,
    )

    obj = bpy.context.object
    obj.name = name
    obj.scale = scale

    bpy.ops.object.transform_apply(
        location=False,
        rotation=False,
        scale=True,
    )

    if bevel > 0:
        modifier = obj.modifiers.new(
            name="Soft Edges",
            type="BEVEL",
        )
        modifier.width = bevel
        modifier.segments = 3

    if material:
        obj.data.materials.append(material)

    return obj


def add_cylinder(name, location, radius, depth, material):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32,
        radius=radius,
        depth=depth,
        location=location,
    )

    obj = bpy.context.object
    obj.name = name

    if material:
        obj.data.materials.append(material)

    return obj


# ============================================================
# CARTOON CHARACTER
# ============================================================

def create_character(
    name,
    x,
    y,
    body_color,
    hair_color,
    skin_color,
):
    """
    Creates a simple stylized 3D cartoon character.

    Character parts are parented to an Empty so the whole
    character can be moved without changing relative positions.
    """

    root = bpy.data.objects.new(name + "_ROOT", None)
    bpy.context.collection.objects.link(root)
    root.location = (x, y, 0)

    body_mat = make_material(
        name + "_BODY",
        body_color,
    )

    hair_mat = make_material(
        name + "_HAIR",
        hair_color,
    )

    skin_mat = make_material(
        name + "_SKIN",
        skin_color,
    )

    shoe_mat = make_material(
        name + "_SHOES",
        (0.04, 0.04, 0.05),
    )

    eye_mat = make_material(
        name + "_EYES",
        (0.02, 0.02, 0.02),
    )

    # --------------------------------------------------------
    # BODY
    # --------------------------------------------------------

    body = add_uv_sphere(
        name + "_BODY",
        (x, y, 1.35),
        (0.65, 0.42, 0.9),
        body_mat,
    )

    body.parent = root
    body.location = (0, 0, 1.35)

    # --------------------------------------------------------
    # HEAD
    # --------------------------------------------------------

    head = add_uv_sphere(
        name + "_HEAD",
        (x, y, 2.65),
        (0.63, 0.55, 0.65),
        skin_mat,
    )

    head.parent = root
    head.location = (0, 0, 2.65)

    # --------------------------------------------------------
    # HAIR
    # --------------------------------------------------------

    hair = add_uv_sphere(
        name + "_HAIR",
        (x, -0.01, 3.05),
        (0.65, 0.57, 0.35),
        hair_mat,
    )

    hair.parent = root
    hair.location = (0, -0.01, 3.05)

    # --------------------------------------------------------
    # EYES
    # --------------------------------------------------------

    left_eye = add_uv_sphere(
        name + "_LEFT_EYE",
        (x - 0.22, -0.51, 2.72),
        (0.075, 0.035, 0.105),
        eye_mat,
    )

    right_eye = add_uv_sphere(
        name + "_RIGHT_EYE",
        (x + 0.22, -0.51, 2.72),
        (0.075, 0.035, 0.105),
        eye_mat,
    )

    left_eye.parent = root
    right_eye.parent = root

    left_eye.location = (-0.22, -0.51, 2.72)
    right_eye.location = (0.22, -0.51, 2.72)

    # --------------------------------------------------------
    # NOSE
    # --------------------------------------------------------

    nose = add_uv_sphere(
        name + "_NOSE",
        (x, -0.57, 2.55),
        (0.075, 0.06, 0.075),
        skin_mat,
    )

    nose.parent = root
    nose.location = (0, -0.57, 2.55)

    # --------------------------------------------------------
    # ARMS
    # --------------------------------------------------------

    left_arm = add_cylinder(
        name + "_LEFT_ARM",
        (x - 0.72, y, 1.4),
        0.15,
        1.1,
        skin_mat,
    )

    right_arm = add_cylinder(
        name + "_RIGHT_ARM",
        (x + 0.72, y, 1.4),
        0.15,
        1.1,
        skin_mat,
    )

    left_arm.rotation_euler[1] = math.radians(90)
    right_arm.rotation_euler[1] = math.radians(90)

    left_arm.parent = root
    right_arm.parent = root

    left_arm.location = (-0.72, 0, 1.4)
    right_arm.location = (0.72, 0, 1.4)

    # --------------------------------------------------------
    # LEGS
    # --------------------------------------------------------

    left_leg = add_cylinder(
        name + "_LEFT_LEG",
        (x - 0.28, y, 0.35),
        0.18,
        0.75,
        shoe_mat,
    )

    right_leg = add_cylinder(
        name + "_RIGHT_LEG",
        (x + 0.28, y, 0.35),
        0.18,
        0.75,
        shoe_mat,
    )

    left_leg.parent = root
    right_leg.parent = root

    left_leg.location = (-0.28, 0, 0.35)
    right_leg.location = (0.28, 0, 0.35)

    return root


# ============================================================
# BACKGROUND
# ============================================================

def create_environment():
    ground_mat = make_material(
        "GROUND",
        (0.12, 0.16, 0.20),
    )

    wall_mat = make_material(
        "WALL",
        (0.08, 0.10, 0.14),
    )

    # Ground
    ground = add_cube(
        "GROUND",
        (0, 0, -0.12),
        (8, 5, 0.1),
        ground_mat,
        bevel=0.05,
    )

    # Back wall
    wall = add_cube(
        "BACK_WALL",
        (0, 2.0, 4),
        (8, 0.1, 4),
        wall_mat,
    )

    return ground, wall


# ============================================================
# CAMERA
# ============================================================

def create_camera():
    bpy.ops.object.camera_add(
        location=(0, -11, 3.2)
    )

    camera = bpy.context.object
    camera.name = "MAIN_CAMERA"

    bpy.context.scene.camera = camera

    camera.data.lens = 48

    # Point camera at scene
    target = bpy.data.objects.new(
        "CAMERA_TARGET",
        None,
    )

    bpy.context.collection.objects.link(target)
    target.location = (0, 0, 1.7)

    constraint = camera.constraints.new(
        type="TRACK_TO"
    )

    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"

    return camera


# ============================================================
# LIGHTING
# ============================================================

def create_lighting():
    # Main soft light
    bpy.ops.object.light_add(
        type="AREA",
        location=(-4, -5, 7),
    )

    key = bpy.context.object
    key.name = "KEY_LIGHT"
    key.data.energy = 900
    key.data.shape = "DISK"
    key.data.size = 5

    key.rotation_euler = (
        math.radians(25),
        0,
        math.radians(-30),
    )

    # Fill light
    bpy.ops.object.light_add(
        type="AREA",
        location=(4, -3, 5),
    )

    fill = bpy.context.object
    fill.name = "FILL_LIGHT"
    fill.data.energy = 500
    fill.data.size = 4

    # Back light
    bpy.ops.object.light_add(
        type="AREA",
        location=(0, 3, 6),
    )

    back = bpy.context.object
    back.name = "BACK_LIGHT"
    back.data.energy = 600
    back.data.size = 3


# ============================================================
# RENDER SETTINGS
# ============================================================

def configure_render(output_file):
    scene = bpy.context.scene

    # --------------------------------------------------------
    # Resolution
    # --------------------------------------------------------

    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100

    # --------------------------------------------------------
    # Frame rate
    # --------------------------------------------------------

    scene.render.fps = 24

    # --------------------------------------------------------
    # Eevee
    # --------------------------------------------------------

    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except Exception:
        try:
            scene.render.engine = "BLENDER_EEVEE"
        except Exception:
            pass

    # --------------------------------------------------------
    # Color
    # --------------------------------------------------------

    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass

    # --------------------------------------------------------
    # MP4
    # --------------------------------------------------------

    scene.render.image_settings.file_format = "FFMPEG"

    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"

    try:
        scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    except Exception:
        pass

    scene.render.filepath = str(output_file)

    # --------------------------------------------------------
    # Avoid GPU/CUDA/OptiX dependencies
    # --------------------------------------------------------

    try:
        scene.cycles.device = "CPU"
    except Exception:
        pass


# ============================================================
# ANIMATION
# ============================================================

def animate_character(character, start_frame, end_frame):
    """
    Subtle animation.

    Characters remain in their assigned positions.
    They do NOT move around the scene just because they speak.
    """

    # Keep root at same location
    original = character.location.copy()

    character.location = original
    character.keyframe_insert(
        data_path="location",
        frame=start_frame,
    )

    character.location = original
    character.keyframe_insert(
        data_path="location",
        frame=end_frame,
    )

    # Small natural breathing motion
    character.scale = (1, 1, 1)
    character.keyframe_insert(
        data_path="scale",
        frame=start_frame,
    )

    character.scale = (1.015, 1.015, 1.015)
    character.keyframe_insert(
        data_path="scale",
        frame=start_frame + 12,
    )

    character.scale = (1, 1, 1)
    character.keyframe_insert(
        data_path="scale",
        frame=start_frame + 24,
    )

    character.scale = (1, 1, 1)
    character.keyframe_insert(
        data_path="scale",
        frame=end_frame,
    )


# ============================================================
# SIMPLE TALKING ANIMATION
# ============================================================

def animate_talking(character, start_frame, end_frame):
    """
    Very subtle talking motion.

    The character stays in place.
    """

    if character is None:
        return

    original_scale = character.scale.copy()

    frame = start_frame

    while frame <= end_frame:
        character.scale = (
            1.0,
            1.0,
            1.0,
        )

        character.keyframe_insert(
            data_path="scale",
            frame=frame,
        )

        if frame + 4 <= end_frame:
            character.scale = (
                1.01,
                1.01,
                1.0,
            )

            character.keyframe_insert(
                data_path="scale",
                frame=frame + 2,
            )

        frame += 6

    character.scale = original_scale


# ============================================================
# SUBTITLE / TEXT
# ============================================================

def add_subtitle(text, start_frame, end_frame):
    """
    Adds subtitles near the bottom of the camera view.

    Text changes according to the dialogue timing.
    """

    if not text:
        return None

    curve = bpy.data.curves.new(
        name="SubtitleCurve",
        type="FONT",
    )

    curve.body = str(text)

    curve.align_x = "CENTER"
    curve.align_y = "CENTER"

    curve.size = 0.42
    curve.extrude = 0.01

    text_obj = bpy.data.objects.new(
        "SUBTITLE",
        curve,
    )

    bpy.context.collection.objects.link(text_obj)

    # Place text in front of camera
    text_obj.location = (
        0,
        -0.5,
        0.35,
    )

    # Rotate to face camera
    text_obj.rotation_euler = (
        math.radians(90),
        0,
        0,
    )

    subtitle_mat = make_material(
        "SUBTITLE_MATERIAL",
        (1.0, 1.0, 1.0),
    )

    text_obj.data.materials.append(
        subtitle_mat
    )

    text_obj.hide_render = True
    text_obj.keyframe_insert(
        data_path="hide_render",
        frame=max(1, start_frame - 1),
    )

    text_obj.hide_render = False
    text_obj.keyframe_insert(
        data_path="hide_render",
        frame=start_frame,
    )

    text_obj.hide_render = False
    text_obj.keyframe_insert(
        data_path="hide_render",
        frame=end_frame,
    )

    text_obj.hide_render = True
    text_obj.keyframe_insert(
        data_path="hide_render",
        frame=end_frame + 1,
    )

    return text_obj


# ============================================================
# BUILD SCENE
# ============================================================

def build_scene():
    log("Building cartoon scene...")

    clear_scene()

    create_environment()

    create_lighting()

    create_camera()

    # --------------------------------------------------------
    # ZURI
    # --------------------------------------------------------

    zuri = create_character(
        "Zuri",
        -1.8,
        0,
        body_color=(0.55, 0.20, 0.80),
        hair_color=(0.08, 0.04, 0.12),
        skin_color=(0.55, 0.30, 0.18),
    )

    # --------------------------------------------------------
    # MILO
    # --------------------------------------------------------

    milo = create_character(
        "Milo",
        1.8,
        0,
        body_color=(0.10, 0.40, 0.85),
        hair_color=(0.12, 0.07, 0.03),
        skin_color=(0.68, 0.40, 0.24),
    )

    # --------------------------------------------------------
    # Animation
    # --------------------------------------------------------

    animate_character(
        zuri,
        1,
        240,
    )

    animate_character(
        milo,
        1,
        240,
    )

    # Talking motion
    animate_talking(
        zuri,
        1,
        120,
    )

    animate_talking(
        milo,
        121,
        240,
    )

    return zuri, milo


# ============================================================
# OPTIONAL AUDIO
# ============================================================

def add_audio(audio_file):
    """
    Adds supplied audio to the Blender scene if available.
    """

    if not audio_file:
        return False

    audio_file = Path(audio_file)

    if not audio_file.exists():
        log(f"Audio file not found: {audio_file}")
        return False

    try:
        scene = bpy.context.scene

        if scene.sequence_editor:
            scene.sequence_editor_clear()

        sequence = scene.sequence_editor_create()

        sound = sequence.sequences.new_sound(
            name="VOICE_TRACK",
            filepath=str(audio_file),
            channel=1,
            frame_start=1,
        )

        log(f"Audio added: {audio_file}")

        # Automatically extend scene duration
        if sound.frame_final_duration > 0:
            scene.frame_end = max(
                scene.frame_end,
                int(sound.frame_final_duration) + 1,
            )

        return True

    except Exception as exc:
        log(f"Could not add audio: {exc}")
        return False


# ============================================================
# RENDER
# ============================================================

def render_video(output_file):
    output_file = Path(output_file)

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    configure_render(output_file)

    scene = bpy.context.scene

    # --------------------------------------------------------
    # Render
    # --------------------------------------------------------

    log("Starting Blender render...")
    log(f"Output: {output_file}")
    log(f"Frames: {scene.frame_start} -> {scene.frame_end}")

    try:
        bpy.ops.render.render(
            animation=True,
        )

    except Exception as exc:
        log(f"Blender render failed: {exc}")
        raise

    # --------------------------------------------------------
    # Verify output
    # --------------------------------------------------------

    if output_file.exists():
        size = output_file.stat().st_size

        log(
            f"Render completed successfully. "
            f"File size: {size} bytes"
        )

        return True

    log("Blender finished but MP4 was not created.")

    return False


# ============================================================
# COMMAND LINE
# ============================================================

def get_argument(name, default=None):
    """
    Read an argument after Blender's -- separator.

    Example:

    blender -b --python engine.py -- --output /app/output/video.mp4
    """

    args = sys.argv

    if "--" not in args:
        return default

    args = args[args.index("--") + 1:]

    for i, arg in enumerate(args):
        if arg == name and i + 1 < len(args):
            return args[i + 1]

    return default


# ============================================================
# MAIN
# ============================================================

def main():
    log("==========================================")
    log(" Cartoon Studio Blender Engine")
    log(" Blender 4.x")
    log("==========================================")

    output_file = get_argument(
        "--output",
        str(OUTPUT_DIR / "cartoon.mp4"),
    )

    audio_file = get_argument(
        "--audio",
        None,
    )

    duration = get_argument(
        "--duration",
        "10",
    )

    try:
        duration = float(duration)
    except Exception:
        duration = 10.0

    # Build scene
    build_scene()

    # Set duration
    scene = bpy.context.scene

    scene.frame_start = 1

    scene.frame_end = max(
        24,
        int(duration * scene.render.fps),
    )

    # Add audio if supplied
    if audio_file:
        add_audio(audio_file)

    # Render
    success = render_video(
        output_file,
    )

    if success:
        log("==========================================")
        log(" RENDER SUCCESS")
        log(f" MP4: {output_file}")
        log("==========================================")
    else:
        log("==========================================")
        log(" RENDER FAILED")
        log(" No MP4 was created.")
        log("==========================================")

        # Do not hide the failure from Render
        raise RuntimeError(
            "Blender finished but the MP4 was not created."
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
