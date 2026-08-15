# blender/engine.py
# Cartoon Studio - Ultra Low Memory Blender Engine
# Blender 4.x
#
# Headless-safe, low-memory 3D cartoon renderer.
# No View3DShading / show_outline usage.
# No GUI context required.

import bpy
import os
import sys
import math
import subprocess
from mathutils import Vector


# ============================================================
# CONFIGURATION
# ============================================================

OUTPUT_DIR = "/app/output"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "cartoon.mp4")

WIDTH = 320
HEIGHT = 180
FPS = 12

START_FRAME = 1
END_FRAME = 120

# Keep rendering lightweight for Render's 512 MB environment.
SAMPLES = 1

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# LOGGING
# ============================================================

def log(message):
    print(f"[CARTOON ENGINE] {message}", flush=True)


def separator():
    log("==========================================")


# ============================================================
# CLEAN SCENE
# ============================================================

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    # Remove unused datablocks where possible.
    try:
        for block in bpy.data.meshes:
            if block.users == 0:
                bpy.data.meshes.remove(block)
    except Exception:
        pass

    try:
        for block in bpy.data.materials:
            if block.users == 0:
                bpy.data.materials.remove(block)
    except Exception:
        pass


# ============================================================
# MATERIAL
# ============================================================

def make_material(name, color):
    material = bpy.data.materials.new(name)

    material.diffuse_color = (
        float(color[0]),
        float(color[1]),
        float(color[2]),
        1.0,
    )

    # Use simple Principled BSDF where available.
    try:
        material.use_nodes = True

        nodes = material.node_tree.nodes
        bsdf = nodes.get("Principled BSDF")

        if bsdf:
            bsdf.inputs["Base Color"].default_value = (
                float(color[0]),
                float(color[1]),
                float(color[2]),
                1.0,
            )

            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = 0.8

            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = 0.0

    except Exception:
        pass

    return material


# ============================================================
# BASIC OBJECT HELPERS
# ============================================================

def add_cube(name, location, scale, material=None):
    bpy.ops.mesh.primitive_cube_add(
        size=1,
        location=location
    )

    obj = bpy.context.object
    obj.name = name
    obj.scale = scale

    bpy.ops.object.transform_apply(
        location=False,
        rotation=False,
        scale=True
    )

    if material:
        obj.data.materials.append(material)

    return obj


def add_uv_sphere(name, location, scale, material=None):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=12,
        ring_count=8,
        location=location
    )

    obj = bpy.context.object
    obj.name = name
    obj.scale = scale

    bpy.ops.object.transform_apply(
        location=False,
        rotation=False,
        scale=True
    )

    if material:
        obj.data.materials.append(material)

    return obj


def add_cylinder(name, location, radius, depth, material=None):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=12,
        radius=radius,
        depth=depth,
        location=location
    )

    obj = bpy.context.object
    obj.name = name

    if material:
        obj.data.materials.append(material)

    return obj


# ============================================================
# CHARACTER CREATION
# ============================================================

def create_character(
    name,
    x,
    shirt_color,
    skin_color,
    hair_color
):
    """
    Creates a very lightweight stylized 3D cartoon character.

    Character remains in a fixed position.
    Only simple facial/body animation is used.
    """

    # Materials
    skin = make_material(
        f"{name}_Skin",
        skin_color
    )

    shirt = make_material(
        f"{name}_Shirt",
        shirt_color
    )

    hair = make_material(
        f"{name}_Hair",
        hair_color
    )

    black = make_material(
        f"{name}_Black",
        (0.02, 0.02, 0.02)
    )

    white = make_material(
        f"{name}_White",
        (0.95, 0.95, 0.95)
    )

    # ----------------------------
    # Body
    # ----------------------------

    body = add_cube(
        f"{name}_Body",
        (x, 0, 1.15),
        (0.42, 0.28, 0.65),
        shirt
    )

    # ----------------------------
    # Head
    # ----------------------------

    head = add_uv_sphere(
        f"{name}_Head",
        (x, 0, 2.15),
        (0.45, 0.40, 0.48),
        skin
    )

    # ----------------------------
    # Hair
    # ----------------------------

    hair_obj = add_uv_sphere(
        f"{name}_Hair",
        (x, -0.01, 2.43),
        (0.46, 0.40, 0.25),
        hair
    )

    # ----------------------------
    # Eyes
    # ----------------------------

    left_eye = add_uv_sphere(
        f"{name}_LeftEye",
        (x - 0.16, -0.37, 2.20),
        (0.055, 0.035, 0.07),
        white
    )

    right_eye = add_uv_sphere(
        f"{name}_RightEye",
        (x + 0.16, -0.37, 2.20),
        (0.055, 0.035, 0.07),
        white
    )

    # Pupils
    left_pupil = add_uv_sphere(
        f"{name}_LeftPupil",
        (x - 0.16, -0.405, 2.20),
        (0.025, 0.015, 0.035),
        black
    )

    right_pupil = add_uv_sphere(
        f"{name}_RightPupil",
        (x + 0.16, -0.405, 2.20),
        (0.025, 0.015, 0.035),
        black
    )

    # ----------------------------
    # Nose
    # ----------------------------

    nose = add_uv_sphere(
        f"{name}_Nose",
        (x, -0.41, 2.08),
        (0.055, 0.04, 0.055),
        skin
    )

    # ----------------------------
    # Mouth
    # ----------------------------

    mouth = add_cube(
        f"{name}_Mouth",
        (x, -0.405, 1.96),
        (0.13, 0.025, 0.025),
        black
    )

    # ----------------------------
    # Arms
    # ----------------------------

    left_arm = add_cylinder(
        f"{name}_LeftArm",
        (x - 0.52, 0, 1.20),
        0.10,
        0.70,
        shirt
    )

    left_arm.rotation_euler[1] = math.radians(12)

    right_arm = add_cylinder(
        f"{name}_RightArm",
        (x + 0.52, 0, 1.20),
        0.10,
        0.70,
        shirt
    )

    right_arm.rotation_euler[1] = math.radians(-12)

    # ----------------------------
    # Legs
    # ----------------------------

    left_leg = add_cylinder(
        f"{name}_LeftLeg",
        (x - 0.20, 0, 0.35),
        0.11,
        0.65,
        black
    )

    right_leg = add_cylinder(
        f"{name}_RightLeg",
        (x + 0.20, 0, 0.35),
        0.11,
        0.65,
        black
    )

    # ----------------------------
    # Simple speaking animation
    # ----------------------------

    # Mouth scale changes slightly while speaking.
    # Character does NOT change position.

    mouth.scale = (1.0, 1.0, 1.0)
    mouth.keyframe_insert(
        data_path="scale",
        frame=1
    )

    mouth.scale = (1.25, 1.0, 1.5)
    mouth.keyframe_insert(
        data_path="scale",
        frame=12
    )

    mouth.scale = (1.0, 1.0, 1.0)
    mouth.keyframe_insert(
        data_path="scale",
        frame=24
    )

    mouth.scale = (1.25, 1.0, 1.5)
    mouth.keyframe_insert(
        data_path="scale",
        frame=36
    )

    mouth.scale = (1.0, 1.0, 1.0)
    mouth.keyframe_insert(
        data_path="scale",
        frame=48
    )

    mouth.scale = (1.2, 1.0, 1.4)
    mouth.keyframe_insert(
        data_path="scale",
        frame=60
    )

    mouth.scale = (1.0, 1.0, 1.0)
    mouth.keyframe_insert(
        data_path="scale",
        frame=END_FRAME
    )

    # Ensure interpolation is smooth.
    try:
        if mouth.animation_data and mouth.animation_data.action:
            for fc in mouth.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "BEZIER"
    except Exception:
        pass

    return {
        "body": body,
        "head": head,
        "mouth": mouth,
        "left_arm": left_arm,
        "right_arm": right_arm,
    }


# ============================================================
# CAMERA
# ============================================================

def create_camera():
    bpy.ops.object.camera_add(
        location=(0, -10.5, 2.6)
    )

    camera = bpy.context.object
    camera.name = "CartoonCamera"

    # Point camera toward scene.
    target = Vector((0, 0, 1.45))
    direction = target - camera.location

    camera.rotation_euler = direction.to_track_quat(
        "-Z",
        "Y"
    ).to_euler()

    camera.data.lens = 52

    bpy.context.scene.camera = camera

    return camera


# ============================================================
# LIGHT
# ============================================================

def create_lighting():
    # One simple area light.
    # Very low memory compared with complicated lighting setups.

    bpy.ops.object.light_add(
        type="AREA",
        location=(0, -4, 6)
    )

    light = bpy.context.object
    light.name = "MainLight"

    light.data.energy = 700
    light.data.shape = "DISK"
    light.data.size = 5

    target = Vector((0, 0, 1.3))
    direction = target - light.location

    light.rotation_euler = direction.to_track_quat(
        "-Z",
        "Y"
    ).to_euler()

    # Small fill light.
    bpy.ops.object.light_add(
        type="AREA",
        location=(4, -3, 3)
    )

    fill = bpy.context.object
    fill.name = "FillLight"
    fill.data.energy = 150
    fill.data.size = 3

    direction = Vector((0, 0, 1.4)) - fill.location

    fill.rotation_euler = direction.to_track_quat(
        "-Z",
        "Y"
    ).to_euler()


# ============================================================
# FLOOR
# ============================================================

def create_floor():
    floor_material = make_material(
        "FloorMaterial",
        (0.10, 0.12, 0.16)
    )

    floor = add_cube(
        "Floor",
        (0, 0, -0.10),
        (6, 4, 0.10),
        floor_material
    )

    return floor


# ============================================================
# BACKGROUND
# ============================================================

def create_background():
    world = bpy.context.scene.world

    if world is None:
        world = bpy.data.worlds.new("CartoonWorld")
        bpy.context.scene.world = world

    world.use_nodes = True

    try:
        background = world.node_tree.nodes.get("Background")

        if background:
            background.inputs["Color"].default_value = (
                0.025,
                0.035,
                0.055,
                1.0
            )

            background.inputs["Strength"].default_value = 0.35

    except Exception:
        pass


# ============================================================
# RENDER SETTINGS
# ============================================================

def configure_render():
    scene = bpy.context.scene

    # Resolution
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.resolution_percentage = 100

    # Frame range
    scene.frame_start = START_FRAME
    scene.frame_end = END_FRAME
    scene.render.fps = FPS

    # --------------------------------------------------------
    # IMPORTANT:
    # Do NOT use Workbench shading configuration.
    # This avoids View3DShading / show_outline and GUI context.
    # --------------------------------------------------------

    # Use Eevee for lightweight rendering.
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except Exception:
        try:
            scene.render.engine = "BLENDER_EEVEE"
        except Exception:
            pass

    # Minimal samples.
    try:
        scene.render.image_settings.color_mode = "RGB"
    except Exception:
        pass

    # Disable expensive effects.
    try:
        scene.render.film_transparent = False
    except Exception:
        pass

    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    scene.render.image_settings.file_format = "FFMPEG"

    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"

    # Low bitrate keeps temporary/output memory and file size down.
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"

    scene.render.filepath = OUTPUT_FILE

    # Avoid unnecessary metadata.
    try:
        scene.render.use_file_extension = True
    except Exception:
        pass

    # --------------------------------------------------------
    # COLOR
    # --------------------------------------------------------

    try:
        scene.view_settings.look = "None"
    except Exception:
        pass


# ============================================================
# BUILD SCENE
# ============================================================

def build_scene():
    log("Building ultra-light 3D cartoon scene...")

    clear_scene()

    create_background()
    create_floor()

    # Character positions are fixed.
    # They do not move when speaking.

    create_character(
        "Zuri",
        -1.15,
        shirt_color=(0.20, 0.55, 0.95),
        skin_color=(0.55, 0.32, 0.18),
        hair_color=(0.05, 0.025, 0.015)
    )

    create_character(
        "Milo",
        1.15,
        shirt_color=(0.95, 0.35, 0.25),
        skin_color=(0.65, 0.40, 0.22),
        hair_color=(0.08, 0.045, 0.02)
    )

    create_camera()
    create_lighting()

    configure_render()

    # Set first frame.
    bpy.context.scene.frame_set(START_FRAME)

    log("Scene successfully built.")


# ============================================================
# VERIFY OUTPUT
# ============================================================

def verify_output():
    if os.path.exists(OUTPUT_FILE):
        size = os.path.getsize(OUTPUT_FILE)

        log(
            f"Render completed successfully: "
            f"{OUTPUT_FILE}"
        )

        log(
            f"Output size: "
            f"{size / (1024 * 1024):.2f} MB"
        )

        return True

    return False


# ============================================================
# MAIN RENDER
# ============================================================

def main():
    separator()
    log("Cartoon Studio Blender Engine")
    log("Blender 4.x")
    log("Ultra-Low-Memory 3D Mode")
    log("Headless-safe configuration")
    log(f"{WIDTH}x{HEIGHT} / {FPS} FPS")
    separator()

    try:
        build_scene()

        log("Starting ultra-low-memory render...")
        log(f"Output: {OUTPUT_FILE}")
        log(
            f"Frames: "
            f"{START_FRAME} -> {END_FRAME}"
        )
        log(
            f"Internal resolution: "
            f"{WIDTH}x{HEIGHT}"
        )
        log(f"FPS: {FPS}")

        # Render animation directly.
        #
        # This does not require a View3D area or GUI context.
        bpy.ops.render.render(animation=True)

        if verify_output():
            log("==========================================")
            log("RENDER SUCCESSFUL")
            log("==========================================")
            return 0

        log("Blender finished but MP4 was not created.")
        return 1

    except Exception as exc:
        log("==========================================")
        log("RENDER ERROR")
        log("==========================================")
        log(str(exc))

        import traceback
        traceback.print_exc()

        return 1


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    exit_code = main()

    # Blender's Python environment accepts this.
    sys.exit(exit_code)
