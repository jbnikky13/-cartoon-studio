"""
Cartoon Studio - Ultra Low Memory 3D Blender Engine
====================================================

Designed for headless Render.com environments with limited RAM.

IMPORTANT:
- No Workbench
- No bpy.context.space_data
- No View3DShading
- No show_outline
- No OpenGL viewport operations
- No EGL-dependent viewport rendering
- CPU-only rendering
- Very low resolution
- Very low samples
- Simple 3D geometry
"""

import bpy
import os
import sys
import math
import shutil
import subprocess

from mathutils import Vector


# ============================================================
# CONFIGURATION
# ============================================================

WIDTH = int(os.environ.get("CARTOON_WIDTH", "640"))
HEIGHT = int(os.environ.get("CARTOON_HEIGHT", "360"))
FPS = int(os.environ.get("CARTOON_FPS", "12"))

# Default = 10 seconds
DEFAULT_FRAMES = FPS * 10
FRAMES = int(os.environ.get("CARTOON_FRAMES", str(DEFAULT_FRAMES)))

OUTPUT_DIR = os.environ.get(
    "CARTOON_OUTPUT_DIR",
    "/app/output"
)

OUTPUT_FILE = os.environ.get(
    "CARTOON_OUTPUT",
    os.path.join(OUTPUT_DIR, "cartoon.mp4")
)

TEMP_DIR = "/tmp/cartoon_blender"

# Cycles sample count. Higher = less noise but slower. 1 sample
# (the old value) produces very visible speckled noise on CPU
# Cycles — 24 with denoising on is a much better tradeoff for a
# small, flat-shaded cartoon character.
SAMPLES = int(os.environ.get("CARTOON_SAMPLES", "24"))


# ============================================================
# LOGGING
# ============================================================

def log(message):
    print(f"[CARTOON ENGINE] {message}", flush=True)


# ============================================================
# CLEANUP
# ============================================================

def clean_previous_files():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if os.path.exists(OUTPUT_FILE):
        try:
            os.remove(OUTPUT_FILE)
        except Exception:
            pass

    if os.path.exists(TEMP_DIR):
        try:
            shutil.rmtree(TEMP_DIR)
        except Exception:
            pass

    os.makedirs(TEMP_DIR, exist_ok=True)


# ============================================================
# MATERIAL
# ============================================================

def make_material(name, color):
    mat = bpy.data.materials.get(name)

    if mat is None:
        mat = bpy.data.materials.new(name)

    mat.diffuse_color = (
        color[0],
        color[1],
        color[2],
        color[3] if len(color) > 3 else 1.0
    )

    # Avoid unnecessary material complexity.
    mat.use_nodes = True

    nodes = mat.node_tree.nodes

    for node in list(nodes):
        nodes.remove(node)

    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfDiffuse")

    shader.inputs["Color"].default_value = (
        color[0],
        color[1],
        color[2],
        color[3] if len(color) > 3 else 1.0
    )

    shader.inputs["Roughness"].default_value = 1.0

    mat.node_tree.links.new(
        shader.outputs["BSDF"],
        output.inputs["Surface"]
    )

    return mat


# ============================================================
# BASIC OBJECT CREATION
# ============================================================

def add_cube(name, location, scale, material):
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
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


def add_uv_sphere(name, location, scale, material):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=8,
        ring_count=6,
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


def add_cylinder(name, location, radius, depth, material):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=8,
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
# CHARACTER
# ============================================================

def create_character(
    name,
    x,
    body_color,
    head_color,
    hair_color,
    shirt_color
):

    # -----------------------------
    # BODY
    # -----------------------------

    body = add_cube(
        f"{name}_Body",
        (x, 0, 1.35),
        (0.42, 0.28, 0.62),
        make_material(
            f"{name}_Shirt",
            shirt_color
        )
    )

    # -----------------------------
    # HEAD
    # -----------------------------

    head = add_uv_sphere(
        f"{name}_Head",
        (x, 0, 2.25),
        (0.48, 0.40, 0.50),
        make_material(
            f"{name}_Skin",
            head_color
        )
    )

    # -----------------------------
    # HAIR
    # -----------------------------

    hair = add_uv_sphere(
        f"{name}_Hair",
        (x, -0.01, 2.55),
        (0.50, 0.42, 0.28),
        make_material(
            f"{name}_HairMaterial",
            hair_color
        )
    )

    # -----------------------------
    # EYES
    # -----------------------------

    eye_material = make_material(
        f"{name}_Eye",
        (0.02, 0.02, 0.02, 1)
    )

    left_eye = add_uv_sphere(
        f"{name}_LeftEye",
        (x - 0.16, -0.38, 2.32),
        (0.055, 0.035, 0.075),
        eye_material
    )

    right_eye = add_uv_sphere(
        f"{name}_RightEye",
        (x + 0.16, -0.38, 2.32),
        (0.055, 0.035, 0.075),
        eye_material
    )

    # -----------------------------
    # MOUTH
    # -----------------------------

    mouth_material = make_material(
        f"{name}_Mouth",
        (0.20, 0.02, 0.02, 1)
    )

    mouth = add_cube(
        f"{name}_Mouth",
        (x, -0.405, 2.08),
        (0.12, 0.025, 0.025),
        mouth_material
    )

    # -----------------------------
    # ARMS
    # -----------------------------

    arm_material = make_material(
        f"{name}_Arm",
        shirt_color
    )

    left_arm = add_cylinder(
        f"{name}_LeftArm",
        (x - 0.52, 0, 1.40),
        0.12,
        0.75,
        arm_material
    )

    right_arm = add_cylinder(
        f"{name}_RightArm",
        (x + 0.52, 0, 1.40),
        0.12,
        0.75,
        arm_material
    )

    # Rest pose: arms hanging naturally at the sides, not
    # straight out horizontal. A full 90-degree horizontal
    # rotation put both arms in a stiff "T-pose" for the whole
    # video, which read as robotic/unsettling rather than a
    # character at rest.
    left_arm.rotation_euler[1] = math.radians(12)
    right_arm.rotation_euler[1] = math.radians(-12)

    # -----------------------------
    # LEGS
    # -----------------------------

    leg_material = make_material(
        f"{name}_Leg",
        body_color
    )

    left_leg = add_cube(
        f"{name}_LeftLeg",
        (x - 0.18, 0, 0.52),
        (0.16, 0.18, 1.04),
        leg_material
    )

    right_leg = add_cube(
        f"{name}_RightLeg",
        (x + 0.18, 0, 0.52),
        (0.16, 0.18, 1.04),
        leg_material
    )

    # Return main body objects.
    return {
        "body": body,
        "head": head,
        "hair": hair,
        "left_eye": left_eye,
        "right_eye": right_eye,
        "mouth": mouth,
        "left_arm": left_arm,
        "right_arm": right_arm,
        "left_leg": left_leg,
        "right_leg": right_leg,
    }


# ============================================================
# BACKGROUND
# ============================================================

def create_background():

    floor_material = make_material(
        "FloorMaterial",
        (0.22, 0.24, 0.27, 1)
    )

    wall_material = make_material(
        "WallMaterial",
        (0.32, 0.48, 0.60, 1)
    )

    # Floor
    add_cube(
        "Floor",
        (0, 0.6, 0),
        (7, 5, 0.05),
        floor_material
    )

    # Back wall
    add_cube(
        "BackWall",
        (0, 2.5, 3),
        (7, 0.05, 3),
        wall_material
    )


# ============================================================
# CAMERA
# ============================================================

def create_camera():

    bpy.ops.object.camera_add(
        location=(0, -10, 3.0)
    )

    camera = bpy.context.object
    camera.name = "CartoonCamera"

    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 5.8

    # Point camera toward scene.
    target = Vector((0, 0, 1.5))

    direction = target - camera.location

    camera.rotation_euler = direction.to_track_quat(
        "-Z",
        "Y"
    ).to_euler()

    bpy.context.scene.camera = camera

    return camera


# ============================================================
# LIGHTING
# ============================================================

def create_lighting():

    # One simple area light.
    # No viewport lighting APIs are used.

    bpy.ops.object.light_add(
        type="AREA",
        location=(0, -3, 6)
    )

    light = bpy.context.object
    light.name = "MainLight"

    light.data.energy = 350
    light.data.shape = "DISK"
    light.data.size = 5

    target = Vector((0, 0, 1.5))

    direction = target - light.location

    light.rotation_euler = direction.to_track_quat(
        "-Z",
        "Y"
    ).to_euler()


# ============================================================
# ANIMATION
# ============================================================

def animate_character(character, start_frame, end_frame):

    body = character["body"]
    head = character["head"]
    left_arm = character["left_arm"]
    right_arm = character["right_arm"]
    mouth = character["mouth"]

    mid = (start_frame + end_frame) // 2

    body.location.z = 1.35
    body.keyframe_insert(
        data_path="location",
        frame=start_frame
    )

    body.location.z = 1.39
    body.keyframe_insert(
        data_path="location",
        frame=mid
    )

    body.location.z = 1.35
    body.keyframe_insert(
        data_path="location",
        frame=end_frame
    )

    head.location.z = 2.25
    head.keyframe_insert(
        data_path="location",
        frame=start_frame
    )

    head.location.z = 2.29
    head.keyframe_insert(
        data_path="location",
        frame=mid
    )

    head.location.z = 2.25
    head.keyframe_insert(
        data_path="location",
        frame=end_frame
    )

    # Arm movement — both arms now actually animate (previously
    # the right arm had zero keyframes and just stayed frozen in
    # its T-pose start position for the entire video). Swing from
    # the relaxed rest pose to a slightly raised "talking" gesture
    # and back, offset between the two arms so the motion doesn't
    # look perfectly symmetrical/robotic.
    rest_l = math.radians(12)
    rest_r = math.radians(-12)
    raised_l = math.radians(38)
    raised_r = math.radians(-30)

    quarter = start_frame + (end_frame - start_frame) // 4
    three_quarter = start_frame + (end_frame - start_frame) * 3 // 4

    for arm, rest, raised, frames in (
        (
            left_arm, rest_l, raised_l,
            (start_frame, quarter, mid, three_quarter, end_frame)
        ),
        (
            right_arm, rest_r, raised_r,
            (start_frame, three_quarter, mid, quarter, end_frame)
        ),
    ):

        f0, f1, f2, f3, f4 = frames

        for frame, angle in (
            (f0, rest),
            (f1, raised),
            (f2, rest),
            (f3, raised),
            (f4, rest),
        ):

            arm.rotation_euler[1] = angle
            arm.keyframe_insert(
                data_path="rotation_euler",
                index=1,
                frame=frame
            )

    # Simple mouth open/close cycle so the character doesn't sit
    # there with a static frozen mouth the whole time — cheap
    # approximation of talking, not true lip sync.
    base_scale = mouth.scale.copy()
    open_scale = (
        base_scale[0],
        base_scale[1],
        base_scale[2] * 2.4
    )

    step = max(1, (end_frame - start_frame) // 8)

    for i, frame in enumerate(
        range(start_frame, end_frame + 1, step)
    ):

        mouth.scale = open_scale if i % 2 == 0 else base_scale

        mouth.keyframe_insert(
            data_path="scale",
            frame=frame
        )


# ============================================================
# SCENE
# ============================================================

def build_scene():

    log("Building ultra-light 3D cartoon scene...")

    # Delete everything.
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    # Remove unused datablocks.
    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for block in list(datablocks):
            if block.users == 0:
                try:
                    datablocks.remove(block)
                except Exception:
                    pass

    scene = bpy.context.scene

    # --------------------------------------------------------
    # RENDER ENGINE
    # --------------------------------------------------------

    # CPU-only Cycles.
    # This avoids Workbench/OpenGL/EGL entirely — Render.com's
    # instances have no GPU, and EEVEE requires a real GPU/OpenGL
    # context to initialize even in "headless" mode. Cycles on the
    # CPU device is a fully software raytracer with no GPU/display
    # dependency at all, so it's the only engine that can actually
    # run here.
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"

    # Make sure Blender doesn't even try to probe for a GPU compute
    # device (some containers report a "device" that then fails to
    # initialize instead of cleanly falling back).
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "NONE"

    for device in prefs.devices:
        device.use = False

    # Cycles is a real raytracer, unlike EEVEE, so unbounded sample
    # counts get slow fast. Keep this low + use the noise threshold
    # to stop early once it's "clean enough" for a small, low-detail
    # cartoon character — full photoreal sample counts (4096+) would
    # make even a short clip take hours on CPU-only rendering.
    scene.cycles.samples = SAMPLES
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.05
    scene.cycles.use_denoising = True

    # --------------------------------------------------------
    # RESOLUTION
    # --------------------------------------------------------

    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.resolution_percentage = 100

    scene.render.fps = FPS

    scene.frame_start = 1
    scene.frame_end = FRAMES

    # --------------------------------------------------------
    # COLOR
    # --------------------------------------------------------

    scene.view_settings.look = "None"

    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    scene.render.image_settings.file_format = "FFMPEG"

    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"

    # "VERYLOW" is Blender's name for its *worst* quality tier
    # (heavy compression, not "very low compression") — that's
    # what was producing the ~20kb/s blurry/noisy output. MEDIUM
    # is a much more reasonable default for something meant to
    # actually look good to a viewer.
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"

    scene.render.filepath = OUTPUT_FILE

    # --------------------------------------------------------
    # WORLD
    # --------------------------------------------------------

    scene.world.color = (
        0.08,
        0.10,
        0.14
    )

    # --------------------------------------------------------
    # BUILD SCENE
    # --------------------------------------------------------

    create_background()

    create_camera()

    create_lighting()

    # --------------------------------------------------------
    # CHARACTERS
    # --------------------------------------------------------

    zuri = create_character(
        name="ZuriSpark",
        x=-1.15,
        body_color=(0.20, 0.30, 0.60, 1),
        head_color=(0.65, 0.38, 0.22, 1),
        hair_color=(0.08, 0.04, 0.02, 1),
        shirt_color=(0.20, 0.55, 0.90, 1)
    )

    milo = create_character(
        name="MiloQuirk",
        x=1.15,
        body_color=(0.20, 0.20, 0.25, 1),
        head_color=(0.72, 0.48, 0.30, 1),
        hair_color=(0.12, 0.07, 0.03, 1),
        shirt_color=(0.80, 0.38, 0.20, 1)
    )

    # --------------------------------------------------------
    # ANIMATION
    # --------------------------------------------------------

    animate_character(
        zuri,
        1,
        FRAMES
    )

    animate_character(
        milo,
        1,
        FRAMES
    )

    # --------------------------------------------------------
    # INTERPOLATION
    # --------------------------------------------------------

    if scene.animation_data:

        for obj in bpy.data.objects:

            if obj.animation_data and obj.animation_data.action:

                for fc in obj.animation_data.action.fcurves:

                    for kp in fc.keyframe_points:
                        kp.interpolation = "BEZIER"

    # --------------------------------------------------------
    # MEMORY-SAFE SETTINGS
    # --------------------------------------------------------

    # Avoid unnecessary motion blur.
    scene.render.use_file_extension = True

    # Disable compositing nodes.
    scene.use_nodes = False

    # --------------------------------------------------------
    # AUDIO
    # --------------------------------------------------------

    # Audio is deliberately handled outside Blender.
    # This keeps Blender memory usage lower.

    log("Scene built successfully.")
    log(f"Resolution: {WIDTH}x{HEIGHT}")
    log(f"FPS: {FPS}")
    log(f"Frames: 1 -> {FRAMES}")


# ============================================================
# RENDER
# ============================================================

def render_scene():

    log("Starting low-memory Blender render...")
    log(f"Output: {OUTPUT_FILE}")

    scene = bpy.context.scene

    # Make absolutely sure output directory exists.
    os.makedirs(
        os.path.dirname(OUTPUT_FILE),
        exist_ok=True
    )

    # Start from frame 1.
    scene.frame_set(1)

    # Render animation.
    bpy.ops.render.render(
        animation=True
    )

    if os.path.exists(OUTPUT_FILE):

        size = os.path.getsize(OUTPUT_FILE)

        log(
            f"Render complete: {OUTPUT_FILE} "
            f"({size / 1024 / 1024:.2f} MB)"
        )

        return True

    log("ERROR: Blender finished but no MP4 was created.")

    return False


# ============================================================
# MAIN
# ============================================================

def main():

    log("==========================================")
    log(" Cartoon Studio Blender Engine")
    log(" Headless-safe 3D Mode")
    log(" No Workbench / No OpenGL viewport")
    log(f" {WIDTH}x{HEIGHT} / {FPS} FPS")
    log("==========================================")

    clean_previous_files()

    try:

        build_scene()

        success = render_scene()

        if not success:
            sys.exit(1)

    except Exception as exc:

        log("==========================================")
        log("BLENDER ENGINE ERROR")
        log(str(exc))
        log("==========================================")

        import traceback
        traceback.print_exc()

        sys.exit(1)


if __name__ == "__main__":
    main()
