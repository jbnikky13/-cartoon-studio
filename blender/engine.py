# ============================================================
# CARTOON STUDIO — LOW MEMORY BLENDER ENGINE
# ============================================================
#
# Designed for Render instances with ~512 MB RAM.
#
# IMPORTANT:
# - Eevee only
# - 480x270 internal render
# - no Cycles
# - no compositor
# - no image sequences
# - one frame at a time
# - simple geometry
# - direct FFmpeg encoding
#
# Blender 4.x compatible
# ============================================================

import bpy
import sys
import os
import math
import subprocess
import shutil
import gc
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

FPS = 24

# Very small working resolution.
# The final video is later scaled to 720p by FFmpeg.
WIDTH = 480
HEIGHT = 270

# Default episode length.
DEFAULT_FRAMES = 240

OUTPUT_DIR = Path("/app/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT = OUTPUT_DIR / "cartoon.mp4"

TMP_DIR = Path("/tmp/cartoon_engine")
TMP_DIR.mkdir(parents=True, exist_ok=True)

FRAME_FILE = TMP_DIR / "frame.png"


# ============================================================
# LOGGING
# ============================================================

def log(message):
    print(f"[CARTOON ENGINE] {message}", flush=True)


# ============================================================
# ARGUMENTS
# ============================================================

def get_args():
    """
    Read arguments after Blender's -- separator.

    Supported:

        --output /app/output/cartoon.mp4
        --frames 240
        --fps 24
    """

    args = sys.argv

    if "--" not in args:
        return {}

    args = args[args.index("--") + 1:]

    result = {}

    i = 0

    while i < len(args):

        arg = args[i]

        if arg == "--output" and i + 1 < len(args):
            result["output"] = args[i + 1]
            i += 2
            continue

        if arg == "--frames" and i + 1 < len(args):
            try:
                result["frames"] = int(args[i + 1])
            except Exception:
                pass

            i += 2
            continue

        if arg == "--fps" and i + 1 < len(args):
            try:
                result["fps"] = int(args[i + 1])
            except Exception:
                pass

            i += 2
            continue

        i += 1

    return result


ARGS = get_args()

if ARGS.get("output"):
    OUTPUT = Path(ARGS["output"])

FRAMES = max(
    1,
    int(ARGS.get("frames", DEFAULT_FRAMES))
)

FPS = max(
    1,
    int(ARGS.get("fps", FPS))
)


# ============================================================
# CLEAN BLENDER FILE
# ============================================================

def clean_scene():

    bpy.ops.object.select_all(action="SELECT")

    try:
        bpy.ops.object.delete(
            use_global=False
        )
    except Exception:
        pass

    # Remove unused datablocks.

    for collection in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        try:
            for item in list(collection):
                if item.users == 0:
                    collection.remove(item)
        except Exception:
            pass

    gc.collect()


# ============================================================
# MATERIAL
# ============================================================

def material(name, color):

    mat = bpy.data.materials.get(name)

    if mat is None:
        mat = bpy.data.materials.new(name)

    mat.diffuse_color = (
        color[0],
        color[1],
        color[2],
        1.0
    )

    # Use simple diffuse material.
    try:
        mat.use_nodes = True

        nodes = mat.node_tree.nodes

        for node in list(nodes):
            nodes.remove(node)

        output = nodes.new(
            "ShaderNodeOutputMaterial"
        )

        diffuse = nodes.new(
            "ShaderNodeBsdfDiffuse"
        )

        diffuse.inputs["Color"].default_value = (
            color[0],
            color[1],
            color[2],
            1.0
        )

        diffuse.inputs["Roughness"].default_value = 1.0

        mat.node_tree.links.new(
            diffuse.outputs["BSDF"],
            output.inputs["Surface"]
        )

    except Exception:
        pass

    return mat


# ============================================================
# BASIC OBJECTS
# ============================================================

def cube(name, location, scale, mat):

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

    obj.data.materials.append(mat)

    return obj


def sphere(name, location, scale, mat):

    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=12,
        ring_count=8,
        radius=1,
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

    obj.data.materials.append(mat)

    return obj


# ============================================================
# CHARACTER
# ============================================================

CHARACTER_COLORS = {
    "Zuri Spark": {
        "skin": (0.55, 0.32, 0.22),
        "shirt": (0.90, 0.18, 0.14),
        "hair": (0.08, 0.04, 0.03),
    },

    "Milo Quirk": {
        "skin": (0.70, 0.43, 0.30),
        "shirt": (0.08, 0.42, 0.68),
        "hair": (0.12, 0.07, 0.04),
    },

    "Kemi Bolt": {
        "skin": (0.45, 0.27, 0.19),
        "shirt": (0.95, 0.60, 0.08),
        "hair": (0.06, 0.04, 0.03),
    },

    "Tari Reed": {
        "skin": (0.60, 0.36, 0.26),
        "shirt": (0.20, 0.65, 0.42),
        "hair": (0.10, 0.06, 0.05),
    },
}


def get_character_colors(name):

    if name in CHARACTER_COLORS:
        return CHARACTER_COLORS[name]

    return {
        "skin": (0.55, 0.34, 0.24),
        "shirt": (0.25, 0.45, 0.75),
        "hair": (0.08, 0.05, 0.04),
    }


def create_character(name, x):

    c = get_character_colors(name)

    skin = material(
        f"{name}_skin",
        c["skin"]
    )

    shirt = material(
        f"{name}_shirt",
        c["shirt"]
    )

    hair = material(
        f"{name}_hair",
        c["hair"]
    )

    black = material(
        f"{name}_black",
        (0.015, 0.015, 0.02)
    )

    # --------------------------------------------------------
    # Body
    # --------------------------------------------------------

    body = cube(
        f"{name}_body",
        (x, 0, 1.25),
        (0.55, 0.32, 0.75),
        shirt
    )

    # --------------------------------------------------------
    # Head
    # --------------------------------------------------------

    head = sphere(
        f"{name}_head",
        (x, 0, 2.35),
        (0.62, 0.50, 0.68),
        skin
    )

    # --------------------------------------------------------
    # Hair
    # --------------------------------------------------------

    hair_obj = sphere(
        f"{name}_hair",
        (x, -0.01, 2.72),
        (0.63, 0.51, 0.28),
        hair
    )

    # --------------------------------------------------------
    # Eyes
    # --------------------------------------------------------

    eye_l = sphere(
        f"{name}_eye_l",
        (x - 0.20, -0.47, 2.40),
        (0.07, 0.035, 0.09),
        black
    )

    eye_r = sphere(
        f"{name}_eye_r",
        (x + 0.20, -0.47, 2.40),
        (0.07, 0.035, 0.09),
        black
    )

    # --------------------------------------------------------
    # Mouth
    # --------------------------------------------------------

    mouth = cube(
        f"{name}_mouth",
        (x, -0.49, 2.16),
        (0.18, 0.025, 0.045),
        black
    )

    # --------------------------------------------------------
    # Arms
    # --------------------------------------------------------

    arm_l = cube(
        f"{name}_arm_l",
        (x - 0.72, 0, 1.30),
        (0.18, 0.20, 0.55),
        shirt
    )

    arm_r = cube(
        f"{name}_arm_r",
        (x + 0.72, 0, 1.30),
        (0.18, 0.20, 0.55),
        shirt
    )

    # --------------------------------------------------------
    # Legs
    # --------------------------------------------------------

    pants = material(
        f"{name}_pants",
        (0.08, 0.10, 0.15)
    )

    leg_l = cube(
        f"{name}_leg_l",
        (x - 0.25, 0, 0.25),
        (0.18, 0.20, 0.50),
        pants
    )

    leg_r = cube(
        f"{name}_leg_r",
        (x + 0.25, 0, 0.25),
        (0.18, 0.20, 0.50),
        pants
    )

    return {
        "name": name,
        "x": x,
        "head": head,
        "mouth": mouth,
        "arm_l": arm_l,
        "arm_r": arm_r,
        "eye_l": eye_l,
        "eye_r": eye_r,
    }


# ============================================================
# ANIMATION
# ============================================================

def animate_character(character, frame, talking=False):

    # Very small animation.
    # No expensive modifiers or simulations.

    phase = math.sin(
        frame * 0.18
    )

    # --------------------------------------------------------
    # Talking mouth
    # --------------------------------------------------------

    mouth = character["mouth"]

    if talking:

        cycle = frame % 8

        if cycle < 4:
            mouth.scale.z = 0.045
        else:
            mouth.scale.z = 0.10

    else:

        mouth.scale.z = 0.045

    # --------------------------------------------------------
    # Tiny arm movement
    # --------------------------------------------------------

    arm_l = character["arm_l"]
    arm_r = character["arm_r"]

    arm_l.rotation_euler[1] = (
        phase * 0.04
    )

    arm_r.rotation_euler[1] = (
        -phase * 0.04
    )


# ============================================================
# WORLD
# ============================================================

def create_world():

    world = bpy.context.scene.world

    if world is None:
        world = bpy.data.worlds.new(
            "CartoonWorld"
        )

        bpy.context.scene.world = world

    world.use_nodes = True

    bg = world.node_tree.nodes.get(
        "Background"
    )

    if bg:

        bg.inputs["Color"].default_value = (
            0.025,
            0.035,
            0.06,
            1.0
        )

        bg.inputs["Strength"].default_value = 0.7


# ============================================================
# FLOOR
# ============================================================

def create_floor():

    floor_mat = material(
        "Floor",
        (0.12, 0.14, 0.18)
    )

    cube(
        "Floor",
        (0, 0, -0.30),
        (5.5, 3.0, 0.25),
        floor_mat
    )


# ============================================================
# CAMERA
# ============================================================

def create_camera():

    bpy.ops.object.camera_add(
        location=(0, -9.0, 3.0)
    )

    camera = bpy.context.object

    camera.name = "CartoonCamera"

    # Point toward the characters.

    target = (
        0,
        0,
        1.55
    )

    direction = (
        target[0] - camera.location.x,
        target[1] - camera.location.y,
        target[2] - camera.location.z
    )

    camera.rotation_euler = direction_to_rotation(
        direction
    )

    camera.data.type = "ORTHO"

    camera.data.ortho_scale = 6.2

    bpy.context.scene.camera = camera

    return camera


def direction_to_rotation(direction):

    import mathutils

    vec = mathutils.Vector(direction)

    return vec.to_track_quat(
        "-Z",
        "Y"
    ).to_euler()


# ============================================================
# LIGHTING
# ============================================================

def create_lighting():

    # One tiny area light.
    # Avoid multiple lights.

    bpy.ops.object.light_add(
        type="AREA",
        location=(0, -4, 6)
    )

    light = bpy.context.object

    light.data.energy = 350

    light.data.shape = "DISK"

    light.data.size = 5

    light.rotation_euler = (
        math.radians(25),
        0,
        0
    )


# ============================================================
# RENDER SETTINGS
# ============================================================

def configure_render():

    scene = bpy.context.scene

    # --------------------------------------------------------
    # Resolution
    # --------------------------------------------------------

    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.resolution_percentage = 100

    # --------------------------------------------------------
    # FPS
    # --------------------------------------------------------

    scene.render.fps = FPS

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
    # Low memory settings
    # --------------------------------------------------------

    scene.render.image_settings.file_format = "PNG"

    # Don't render transparent images.
    scene.render.film_transparent = False

    # --------------------------------------------------------
    # Color
    # --------------------------------------------------------

    try:
        scene.view_settings.look = "None"
    except Exception:
        pass

    # --------------------------------------------------------
    # Disable expensive features
    # --------------------------------------------------------

    try:
        scene.render.use_file_extension = True
    except Exception:
        pass

    # --------------------------------------------------------
    # Frame range
    # --------------------------------------------------------

    scene.frame_start = 1
    scene.frame_end = FRAMES


# ============================================================
# BUILD SCENE
# ============================================================

def build_scene():

    log("Building lightweight cartoon scene...")

    clean_scene()

    create_world()

    create_floor()

    create_lighting()

    camera = create_camera()

    # Fixed character positions.
    #
    # They do NOT move around the scene when speaking.
    #

    zuri = create_character(
        "Zuri Spark",
        -1.55
    )

    milo = create_character(
        "Milo Quirk",
        1.55
    )

    return {
        "camera": camera,
        "zuri": zuri,
        "milo": milo,
    }


# ============================================================
# FFMPEG
# ============================================================

def find_ffmpeg():

    candidates = [
        shutil.which("ffmpeg"),
        "/usr/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
    ]

    for path in candidates:

        if path and os.path.exists(path):
            return path

    return None


# ============================================================
# DIRECT VIDEO PIPE
# ============================================================

class VideoEncoder:

    def __init__(self, output):

        self.output = str(output)

        ffmpeg = find_ffmpeg()

        if not ffmpeg:
            raise RuntimeError(
                "FFmpeg was not found in the Render container."
            )

        # ----------------------------------------------------
        # IMPORTANT
        #
        # raw RGB frames are streamed directly into FFmpeg.
        #
        # There is NO 240-frame PNG sequence in memory/disk.
        # ----------------------------------------------------

        self.process = subprocess.Popen(
            [
                ffmpeg,

                "-y",

                "-f",
                "rawvideo",

                "-vcodec",
                "rawvideo",

                "-pix_fmt",
                "rgb24",

                "-s",
                f"{WIDTH}x{HEIGHT}",

                "-r",
                str(FPS),

                "-i",
                "-",

                "-an",

                "-c:v",
                "libx264",

                "-preset",
                "ultrafast",

                "-tune",
                "animation",

                "-crf",
                "30",

                "-pix_fmt",
                "yuv420p",

                "-movflags",
                "+faststart",

                self.output,
            ],

            stdin=subprocess.PIPE,

            stdout=subprocess.DEVNULL,

            stderr=subprocess.PIPE
        )


    def write_frame(self):

        scene = bpy.context.scene

        pixels = scene.render.image.pixels

        # Blender gives RGBA float pixels.
        #
        # Convert to compact RGB bytes.
        #

        data = bytearray()

        length = len(pixels)

        for i in range(0, length, 4):

            r = int(
                max(
                    0,
                    min(
                        255,
                        pixels[i] * 255
                    )
                )
            )

            g = int(
                max(
                    0,
                    min(
                        255,
                        pixels[i + 1] * 255
                    )
                )
            )

            b = int(
                max(
                    0,
                    min(
                        255,
                        pixels[i + 2] * 255
                    )
                )
            )

            data.extend(
                (r, g, b)
            )

        self.process.stdin.write(data)


    def finish(self):

        try:

            self.process.stdin.close()

        except Exception:
            pass

        stderr = self.process.stderr.read()

        code = self.process.wait()

        if code != 0:

            raise RuntimeError(
                stderr.decode(
                    "utf-8",
                    errors="replace"
                )[-5000:]
            )


# ============================================================
# RENDER
# ============================================================

def render_scene(scene_objects):

    log("Starting low-memory Blender render...")

    log(
        f"Output: {OUTPUT}"
    )

    log(
        f"Frames: 1 -> {FRAMES}"
    )

    log(
        f"Internal resolution: "
        f"{WIDTH}x{HEIGHT}"
    )

    encoder = None

    try:

        encoder = VideoEncoder(
            OUTPUT
        )

        zuri = scene_objects["zuri"]

        milo = scene_objects["milo"]

        scene = bpy.context.scene

        for frame in range(
            1,
            FRAMES + 1
        ):

            scene.frame_set(frame)

            # ------------------------------------------------
            # Speaker changes by scene.
            #
            # For this lightweight engine:
            #
            # 0-50% = Zuri speaking
            # 50-100% = Milo speaking
            #
            # This keeps the characters stationary.
            # ------------------------------------------------

            zuri_talking = (
                frame < FRAMES / 2
            )

            milo_talking = not zuri_talking

            animate_character(
                zuri,
                frame,
                zuri_talking
            )

            animate_character(
                milo,
                frame,
                milo_talking
            )

            # ------------------------------------------------
            # Render ONE frame only.
            # ------------------------------------------------

            scene.render.filepath = str(
                FRAME_FILE
            )

            bpy.ops.render.render(
                write_still=False
            )

            encoder.write_frame()

            # ------------------------------------------------
            # Explicitly remove render image data.
            # ------------------------------------------------

            try:

                image = bpy.data.images.get(
                    "Render Result"
                )

                if image:
                    image.buffers_free()

            except Exception:
                pass

            # ------------------------------------------------
            # Periodic memory cleanup.
            # ------------------------------------------------

            if frame % 12 == 0:

                gc.collect()

                percent = (
                    frame / FRAMES
                ) * 100

                log(
                    f"Rendered "
                    f"{frame}/{FRAMES} "
                    f"({percent:.0f}%)"
                )

        encoder.finish()

        encoder = None

        log(
            "Blender render completed."
        )

        if not OUTPUT.exists():

            raise RuntimeError(
                "Blender finished but "
                "cartoon.mp4 was not created."
            )

        size = OUTPUT.stat().st_size

        log(
            f"MP4 created successfully: "
            f"{size / 1024 / 1024:.2f} MB"
        )

        return True

    except Exception as exc:

        log(
            f"Render error: {exc}"
        )

        if encoder:

            try:
                encoder.process.kill()
            except Exception:
                pass

        return False


# ============================================================
# FINAL CLEANUP
# ============================================================

def cleanup():

    try:

        if FRAME_FILE.exists():
            FRAME_FILE.unlink()

    except Exception:
        pass

    try:

        if TMP_DIR.exists():

            for item in TMP_DIR.iterdir():

                try:

                    if item.is_file():
                        item.unlink()

                except Exception:
                    pass

    except Exception:
        pass

    gc.collect()


# ============================================================
# MAIN
# ============================================================

def main():

    log("==========================================")
    log(" Cartoon Studio Blender Engine")
    log(" Low-Memory Blender 4.x")
    log(" Render-safe configuration")
    log("==========================================")

    try:

        objects = build_scene()

        success = render_scene(
            objects
        )

        if not success:

            log(
                "Blender render failed."
            )

            return 1

        log(
            "=========================================="
        )

        log(
            " CARTOON VIDEO CREATED SUCCESSFULLY"
        )

        log(
            f" {OUTPUT}"
        )

        log(
            "=========================================="
        )

        return 0

    except Exception as exc:

        log(
            f"FATAL ENGINE ERROR: {exc}"
        )

        return 1

    finally:

        cleanup()


if __name__ == "__main__":

    exit_code = main()

    try:

        bpy.ops.wm.quit_blender(
            exit=exit_code
        )

    except Exception:

        pass
