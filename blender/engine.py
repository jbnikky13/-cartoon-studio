# ============================================================
# CARTOON STUDIO
# LOW-MEMORY 3D BLENDER ENGINE
# Blender 4.x / Render 512 MB
# ============================================================

import bpy
import sys
import os
import math
import subprocess
import shutil
import gc
from pathlib import Path

from mathutils import Vector


# ============================================================
# SETTINGS
# ============================================================

WIDTH = 320
HEIGHT = 180
FPS = 12
DEFAULT_FRAMES = 120

OUTPUT_DIR = Path("/app/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT = OUTPUT_DIR / "cartoon.mp4"

TMP_DIR = Path("/tmp/cartoon_studio")
TMP_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# LOGGING
# ============================================================

def log(message):
    print(
        f"[CARTOON ENGINE] {message}",
        flush=True
    )


# ============================================================
# COMMAND-LINE ARGUMENTS
# ============================================================

def get_arguments():

    result = {}

    if "--" not in sys.argv:
        return result

    args = sys.argv[
        sys.argv.index("--") + 1:
    ]

    i = 0

    while i < len(args):

        if args[i] == "--output" and i + 1 < len(args):
            result["output"] = args[i + 1]
            i += 2

        elif args[i] == "--frames" and i + 1 < len(args):

            try:
                result["frames"] = int(args[i + 1])
            except Exception:
                pass

            i += 2

        elif args[i] == "--fps" and i + 1 < len(args):

            try:
                result["fps"] = int(args[i + 1])
            except Exception:
                pass

            i += 2

        else:
            i += 1

    return result


ARGS = get_arguments()

if ARGS.get("output"):
    OUTPUT = Path(ARGS["output"])

FRAMES = max(
    1,
    int(
        ARGS.get(
            "frames",
            DEFAULT_FRAMES
        )
    )
)

FPS = max(
    1,
    int(
        ARGS.get(
            "fps",
            FPS
        )
    )
)


# ============================================================
# CLEAN SCENE
# ============================================================

def clean_scene():

    bpy.ops.object.select_all(
        action="SELECT"
    )

    try:
        bpy.ops.object.delete(
            use_global=False
        )
    except Exception:
        pass

    gc.collect()


# ============================================================
# MATERIAL
# ============================================================

def make_material(
    name,
    color
):

    mat = bpy.data.materials.get(name)

    if mat is None:

        mat = bpy.data.materials.new(
            name
        )

    mat.diffuse_color = (
        color[0],
        color[1],
        color[2],
        1
    )

    # Workbench uses the material viewport color.
    mat.use_nodes = False

    return mat


# ============================================================
# CUBE
# ============================================================

def create_cube(
    name,
    location,
    scale,
    material
):

    bpy.ops.mesh.primitive_cube_add(
        size=1,
        location=location
    )

    obj = bpy.context.object

    obj.name = name

    obj.scale = scale

    obj.data.materials.append(
        material
    )

    return obj


# ============================================================
# LOW-POLY SPHERE
# ============================================================

def create_sphere(
    name,
    location,
    scale,
    material
):

    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=8,
        ring_count=6,
        radius=1,
        location=location
    )

    obj = bpy.context.object

    obj.name = name

    obj.scale = scale

    obj.data.materials.append(
        material
    )

    return obj


# ============================================================
# CHARACTER COLORS
# ============================================================

CHARACTERS = {

    "Zuri Spark": {
        "skin": (0.55, 0.30, 0.20),
        "shirt": (0.90, 0.18, 0.12),
        "hair": (0.035, 0.018, 0.012),
    },

    "Milo Quirk": {
        "skin": (0.68, 0.40, 0.27),
        "shirt": (0.08, 0.38, 0.72),
        "hair": (0.055, 0.030, 0.018),
    },
}


# ============================================================
# CHARACTER CREATOR
# ============================================================

def create_character(
    name,
    x_position
):

    colors = CHARACTERS.get(
        name,
        CHARACTERS["Milo Quirk"]
    )

    skin = make_material(
        name + "_skin",
        colors["skin"]
    )

    shirt = make_material(
        name + "_shirt",
        colors["shirt"]
    )

    hair = make_material(
        name + "_hair",
        colors["hair"]
    )

    black = make_material(
        name + "_black",
        (0.01, 0.01, 0.01)
    )

    # --------------------------------------------------------
    # BODY
    # --------------------------------------------------------

    body = create_cube(
        name + "_body",
        (
            x_position,
            0,
            1.05
        ),
        (
            0.48,
            0.28,
            0.65
        ),
        shirt
    )

    # --------------------------------------------------------
    # HEAD
    # --------------------------------------------------------

    head = create_sphere(
        name + "_head",
        (
            x_position,
            0,
            2.05
        ),
        (
            0.55,
            0.45,
            0.60
        ),
        skin
    )

    # --------------------------------------------------------
    # HAIR
    # --------------------------------------------------------

    hair_object = create_sphere(
        name + "_hair",
        (
            x_position,
            0.01,
            2.38
        ),
        (
            0.56,
            0.46,
            0.25
        ),
        hair
    )

    # --------------------------------------------------------
    # EYES
    # --------------------------------------------------------

    eye_left = create_sphere(
        name + "_eye_left",
        (
            x_position - 0.18,
            -0.42,
            2.08
        ),
        (
            0.055,
            0.025,
            0.07
        ),
        black
    )

    eye_right = create_sphere(
        name + "_eye_right",
        (
            x_position + 0.18,
            -0.42,
            2.08
        ),
        (
            0.055,
            0.025,
            0.07
        ),
        black
    )

    # --------------------------------------------------------
    # MOUTH
    # --------------------------------------------------------

    mouth = create_cube(
        name + "_mouth",
        (
            x_position,
            -0.43,
            1.84
        ),
        (
            0.15,
            0.018,
            0.035
        ),
        black
    )

    # --------------------------------------------------------
    # ARMS
    # --------------------------------------------------------

    arm_left = create_cube(
        name + "_arm_left",
        (
            x_position - 0.62,
            0,
            1.10
        ),
        (
            0.15,
            0.16,
            0.48
        ),
        shirt
    )

    arm_right = create_cube(
        name + "_arm_right",
        (
            x_position + 0.62,
            0,
            1.10
        ),
        (
            0.15,
            0.16,
            0.48
        ),
        shirt
    )

    # --------------------------------------------------------
    # LEGS
    # --------------------------------------------------------

    pants = make_material(
        name + "_pants",
        (0.06, 0.07, 0.10)
    )

    leg_left = create_cube(
        name + "_leg_left",
        (
            x_position - 0.20,
            0,
            0.20
        ),
        (
            0.16,
            0.16,
            0.40
        ),
        pants
    )

    leg_right = create_cube(
        name + "_leg_right",
        (
            x_position + 0.20,
            0,
            0.20
        ),
        (
            0.16,
            0.16,
            0.40
        ),
        pants
    )

    return {
        "name": name,
        "x": x_position,
        "head": head,
        "mouth": mouth,
        "eye_left": eye_left,
        "eye_right": eye_right,
        "arm_left": arm_left,
        "arm_right": arm_right,
    }


# ============================================================
# FLOOR
# ============================================================

def create_floor():

    floor_material = make_material(
        "Floor",
        (0.12, 0.14, 0.18)
    )

    create_cube(
        "Floor",
        (
            0,
            0,
            -0.25
        ),
        (
            5,
            2.5,
            0.20
        ),
        floor_material
    )


# ============================================================
# BACKGROUND
# ============================================================

def create_background():

    background_material = make_material(
        "Background",
        (0.04, 0.07, 0.12)
    )

    create_cube(
        "Background",
        (
            0,
            1.0,
            2
        ),
        (
            5,
            0.10,
            2.5
        ),
        background_material
    )


# ============================================================
# CAMERA
# ============================================================

def create_camera():

    bpy.ops.object.camera_add(
        location=(
            0,
            -8,
            2.2
        )
    )

    camera = bpy.context.object

    camera.name = "CartoonCamera"

    camera.data.type = "ORTHO"

    camera.data.ortho_scale = 5.5

    direction = Vector(
        (
            0,
            0,
            1.3
        )
    ) - camera.location

    camera.rotation_euler = (
        direction.to_track_quat(
            "-Z",
            "Y"
        ).to_euler()
    )

    bpy.context.scene.camera = camera

    return camera


# ============================================================
# WORKBENCH SETTINGS
# ============================================================

def configure_workbench():

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
    # Workbench
    # --------------------------------------------------------

    try:

        scene.render.engine = (
            "BLENDER_WORKBENCH"
        )

    except Exception as error:

        log(
            f"Workbench unavailable: {error}"
        )

    # --------------------------------------------------------
    # Workbench display
    # --------------------------------------------------------

    try:

        shading = scene.display.shading

        shading.light = "FLAT"

        shading.color_type = "MATERIAL"

        shading.show_shadows = False

        shading.show_cavity = False

        shading.show_specular_highlight = False

        shading.show_outline = False

        shading.background_type = "WORLD"

        shading.show_xray = False

    except Exception as error:

        log(
            f"Workbench configuration warning: {error}"
        )

    # --------------------------------------------------------
    # No transparency
    # --------------------------------------------------------

    scene.render.film_transparent = False

    # --------------------------------------------------------
    # PNG render target
    # --------------------------------------------------------

    scene.render.image_settings.file_format = "PNG"

    # --------------------------------------------------------
    # Frame range
    # --------------------------------------------------------

    scene.frame_start = 1

    scene.frame_end = FRAMES


# ============================================================
# WORLD
# ============================================================

def configure_world():

    world = bpy.context.scene.world

    if world is None:

        world = bpy.data.worlds.new(
            "CartoonWorld"
        )

        bpy.context.scene.world = world

    try:

        world.color = (
            0.025,
            0.035,
            0.06
        )

    except Exception:
        pass


# ============================================================
# ANIMATION
# ============================================================

def animate_character(
    character,
    frame,
    talking
):

    # --------------------------------------------------------
    # Talking mouth
    # --------------------------------------------------------

    mouth = character["mouth"]

    if talking:

        cycle = frame % 6

        if cycle < 3:

            mouth.scale.z = 1.0

        else:

            mouth.scale.z = 2.0

    else:

        mouth.scale.z = 1.0

    # --------------------------------------------------------
    # Small head movement
    # --------------------------------------------------------

    head = character["head"]

    if talking:

        head.rotation_euler.y = (
            math.sin(frame * 0.12) * 0.025
        )

    else:

        head.rotation_euler.y = 0

    # --------------------------------------------------------
    # Small arm gesture
    # --------------------------------------------------------

    left_arm = character["arm_left"]

    right_arm = character["arm_right"]

    if talking:

        movement = (
            math.sin(frame * 0.16) * 0.08
        )

        left_arm.rotation_euler.y = movement

        right_arm.rotation_euler.y = -movement

    else:

        left_arm.rotation_euler.y = 0

        right_arm.rotation_euler.y = 0


# ============================================================
# BUILD SCENE
# ============================================================

def build_scene():

    log(
        "Building ultra-light 3D cartoon scene..."
    )

    clean_scene()

    configure_world()

    create_background()

    create_floor()

    camera = create_camera()

    zuri = create_character(
        "Zuri Spark",
        -1.45
    )

    milo = create_character(
        "Milo Quirk",
        1.45
    )

    configure_workbench()

    return {
        "camera": camera,
        "zuri": zuri,
        "milo": milo
    }


# ============================================================
# FFMPEG
# ============================================================

def find_ffmpeg():

    locations = [
        shutil.which("ffmpeg"),
        "/usr/bin/ffmpeg",
        "/usr/local/bin/ffmpeg"
    ]

    for location in locations:

        if location and os.path.exists(location):

            return location

    return None


# ============================================================
# VIDEO ENCODER
# ============================================================

class VideoEncoder:

    def __init__(
        self,
        output
    ):

        ffmpeg = find_ffmpeg()

        if not ffmpeg:

            raise RuntimeError(
                "FFmpeg is not installed."
            )

        self.process = subprocess.Popen(
            [
                ffmpeg,

                "-y",

                "-f",
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

                "-crf",
                "30",

                "-pix_fmt",
                "yuv420p",

                "-vf",
                "scale=640:360:flags=fast_bilinear",

                "-movflags",
                "+faststart",

                str(output)
            ],

            stdin=subprocess.PIPE,

            stdout=subprocess.DEVNULL,

            stderr=subprocess.PIPE
        )


    def write_frame(self):

        image = bpy.data.images.get(
            "Render Result"
        )

        if image is None:

            raise RuntimeError(
                "Blender did not produce a Render Result."
            )

        pixels = image.pixels

        raw = bytearray()

        # ----------------------------------------------------
        # Convert Blender RGBA floats to RGB bytes.
        # ----------------------------------------------------

        for index in range(
            0,
            len(pixels),
            4
        ):

            raw.append(
                max(
                    0,
                    min(
                        255,
                        int(
                            pixels[index] * 255
                        )
                    )
                )
            )

            raw.append(
                max(
                    0,
                    min(
                        255,
                        int(
                            pixels[index + 1] * 255
                        )
                    )
                )
            )

            raw.append(
                max(
                    0,
                    min(
                        255,
                        int(
                            pixels[index + 2] * 255
                        )
                    )
                )

            )

        self.process.stdin.write(
            raw
        )


    def finish(self):

        try:

            self.process.stdin.close()

        except Exception:
            pass

        error_output = (
            self.process.stderr.read()
        )

        return_code = (
            self.process.wait()
        )

        if return_code != 0:

            raise RuntimeError(
                error_output.decode(
                    "utf-8",
                    errors="replace"
                )[-4000:]
            )


# ============================================================
# RENDER
# ============================================================

def render_video(
    objects
):

    log(
        "Starting ultra-low-memory render..."
    )

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

    log(
        f"FPS: {FPS}"
    )

    encoder = None

    try:

        encoder = VideoEncoder(
            OUTPUT
        )

        scene = bpy.context.scene

        zuri = objects["zuri"]

        milo = objects["milo"]

        for frame in range(
            1,
            FRAMES + 1
        ):

            scene.frame_set(
                frame
            )

            # ------------------------------------------------
            # Simple dialogue simulation.
            #
            # Zuri speaks first.
            # Milo speaks second.
            #
            # Positions NEVER change.
            # ------------------------------------------------

            zuri_talking = (
                frame <= FRAMES // 2
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
            # Render one frame.
            # ------------------------------------------------

            bpy.ops.render.render(
                write_still=False
            )

            # ------------------------------------------------
            # Immediately send frame to FFmpeg.
            # ------------------------------------------------

            encoder.write_frame()

            # ------------------------------------------------
            # Free render result.
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
            # Memory cleanup every 6 frames.
            # ------------------------------------------------

            if frame % 6 == 0:

                gc.collect()

            # ------------------------------------------------
            # Progress log every 12 frames.
            # ------------------------------------------------

            if frame % 12 == 0:

                percent = (
                    frame /
                    FRAMES *
                    100
                )

                log(
                    f"Rendered "
                    f"{frame}/{FRAMES} "
                    f"({percent:.0f}%)"
                )

        encoder.finish()

        encoder = None

        if not OUTPUT.exists():

            raise RuntimeError(
                "MP4 was not created."
            )

        file_size = (
            OUTPUT.stat().st_size
        )

        log(
            "=========================================="
        )

        log(
            "3D CARTOON RENDER COMPLETE"
        )

        log(
            f"File size: "
            f"{file_size / 1024 / 1024:.2f} MB"
        )

        log(
            f"Output: {OUTPUT}"
        )

        log(
            "=========================================="
        )

        return True

    except Exception as error:

        log(
            f"Render failed: {error}"
        )

        if encoder:

            try:

                encoder.process.kill()

            except Exception:
                pass

        return False


# ============================================================
# MAIN
# ============================================================

def main():

    log(
        "=========================================="
    )

    log(
        " Cartoon Studio Blender Engine"
    )

    log(
        " Blender 4.x"
    )

    log(
        " Ultra-Low-Memory 3D Mode"
    )

    log(
        " 320x180 / 12 FPS"
    )

    log(
        "=========================================="
    )

    try:

        objects = build_scene()

        success = render_video(
            objects
        )

        if success:

            log(
                "Cartoon video created successfully."
            )

            return 0

        log(
            "Cartoon video creation failed."
        )

        return 1

    except Exception as error:

        log(
            f"FATAL ENGINE ERROR: {error}"
        )

        return 1


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    exit_code = main()

    try:

        bpy.ops.wm.quit_blender(
            exit=exit_code
        )

    except Exception:
        pass
