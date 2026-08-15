import bpy
import json
import math
import os
import re
import sys

from mathutils import Vector


# ============================================================
# CARTOON STUDIO 3D - CORRECTED BLENDER ENGINE
# ============================================================

def get_arguments():
    if "--" not in sys.argv:
        raise RuntimeError("Missing Cartoon Studio arguments.")

    args = sys.argv[sys.argv.index("--") + 1:]

    if len(args) < 2:
        raise RuntimeError(
            "Expected: config.json output.mp4 [audio_file]"
        )

    config_file = args[0]
    output_file = args[1]
    audio_file = args[2] if len(args) >= 3 and args[2] else None

    return config_file, output_file, audio_file


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def create_material(name, color, roughness=0.5, metallic=0.0):
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


def add_sphere(name, location, scale, mat, parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=32,
        ring_count=20,
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

    if parent:
        obj.parent = parent

    return obj


def add_cube(name, location, scale, mat, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=location)

    obj = bpy.context.object
    obj.name = name
    obj.scale = scale

    bpy.ops.object.transform_apply(
        location=False,
        rotation=False,
        scale=True
    )

    if bevel:
        modifier = obj.modifiers.new(
            "Rounded Edges",
            "BEVEL"
        )
        modifier.width = bevel
        modifier.segments = 4

    obj.data.materials.append(mat)

    return obj


def add_cylinder(name, location, radius, depth, mat, parent=None):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32,
        radius=radius,
        depth=depth,
        location=location
    )

    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)

    if parent:
        obj.parent = parent

    return obj


# ============================================================
# CHARACTER SYSTEM
# ============================================================

def create_character(
    name,
    x_position,
    shirt_color,
    hair_color,
    skin_color
):
    root = bpy.data.objects.new(
        name + "_ROOT",
        None
    )

    bpy.context.collection.objects.link(root)

    skin = create_material(
        name + "_SKIN",
        skin_color,
        0.55
    )

    shirt = create_material(
        name + "_SHIRT",
        shirt_color,
        0.6
    )

    hair = create_material(
        name + "_HAIR",
        hair_color,
        0.65
    )

    white = create_material(
        name + "_EYE_WHITE",
        (0.95, 0.95, 0.95),
        0.3
    )

    black = create_material(
        name + "_BLACK",
        (0.01, 0.01, 0.015),
        0.35
    )

    mouth_material = create_material(
        name + "_MOUTH",
        (0.12, 0.01, 0.02),
        0.4
    )

    shoe = create_material(
        name + "_SHOE",
        (0.025, 0.03, 0.04),
        0.5
    )

    # Body
    add_sphere(
        name + "_BODY",
        (x_position, 0, 2.15),
        (0.82, 0.58, 1.0),
        shirt,
        root
    )

    # Head
    add_sphere(
        name + "_HEAD",
        (x_position, 0, 3.72),
        (0.84, 0.72, 0.84),
        skin,
        root
    )

    # Hair
    add_sphere(
        name + "_HAIR",
        (x_position, 0.03, 4.25),
        (0.87, 0.74, 0.42),
        hair,
        root
    )

    # Eyes
    for side, offset in (
        ("L", -0.28),
        ("R", 0.28)
    ):
        add_sphere(
            name + "_EYE_" + side,
            (
                x_position + offset,
                -0.68,
                3.82
            ),
            (0.13, 0.06, 0.16),
            white,
            root
        )

        add_sphere(
            name + "_PUPIL_" + side,
            (
                x_position + offset,
                -0.735,
                3.82
            ),
            (0.055, 0.025, 0.075),
            black,
            root
        )

    # Nose
    add_sphere(
        name + "_NOSE",
        (
            x_position,
            -0.72,
            3.62
        ),
        (0.09, 0.07, 0.09),
        skin,
        root
    )

    # Mouth
    add_sphere(
        name + "_MOUTH",
        (
            x_position,
            -0.70,
            3.45
        ),
        (0.22, 0.045, 0.08),
        mouth_material,
        root
    )

    # Arms
    for side, offset in (
        ("L", -0.92),
        ("R", 0.92)
    ):
        arm = add_sphere(
            name + "_ARM_" + side,
            (
                x_position + offset,
                0,
                2.35
            ),
            (0.23, 0.25, 0.78),
            shirt,
            root
        )

        arm["rest_rotation"] = list(
            arm.rotation_euler
        )

        add_sphere(
            name + "_HAND_" + side,
            (
                x_position + offset,
                0,
                1.62
            ),
            (0.23, 0.23, 0.23),
            skin,
            root
        )

    # Legs
    for side, offset in (
        ("L", -0.34),
        ("R", 0.34)
    ):
        add_cylinder(
            name + "_LEG_" + side,
            (
                x_position + offset,
                0,
                0.86
            ),
            0.21,
            1.05,
            shirt,
            root
        )

        add_sphere(
            name + "_SHOE_" + side,
            (
                x_position + offset,
                -0.16,
                0.28
            ),
            (0.30, 0.48, 0.18),
            shoe,
            root
        )

    return root


# ============================================================
# ENVIRONMENTS
# ============================================================

def create_environment(environment_name):
    floor = create_material(
        "FLOOR",
        (0.12, 0.16, 0.20)
    )

    wall = create_material(
        "WALL",
        (0.24, 0.28, 0.34)
    )

    green = create_material(
        "GRASS",
        (0.08, 0.32, 0.10)
    )

    wood = create_material(
        "WOOD",
        (0.38, 0.20, 0.08)
    )

    white = create_material(
        "WHITE",
        (0.80, 0.82, 0.84)
    )

    accent = create_material(
        "ACCENT",
        (0.10, 0.38, 0.55)
    )

    bpy.ops.mesh.primitive_plane_add(
        size=30,
        location=(0, 0, 0)
    )

    floor_object = bpy.context.object

    floor_object.data.materials.append(
        green if environment_name == "park" else floor
    )

    if environment_name != "park":
        add_cube(
            "BACK_WALL",
            (0, 4.2, 4.0),
            (7, 0.18, 4),
            wall,
            0.1
        )

    if environment_name == "classroom":
        add_cube(
            "CLASSROOM_BOARD",
            (0, 3.95, 4.4),
            (3.0, 0.08, 1.2),
            accent,
            0.05
        )

        for x in (-4, -1.5, 1.5, 4):
            add_cube(
                "DESK",
                (x, 1.2, 0.9),
                (1.0, 0.55, 0.08),
                wood,
                0.05
            )

    elif environment_name == "bedroom":
        add_cube(
            "BED",
            (2.5, 1.8, 0.55),
            (2.2, 1.2, 0.25),
            white,
            0.18
        )

        add_cube(
            "PILLOW",
            (2.5, 2.55, 0.9),
            (0.8, 0.35, 0.18),
            white,
            0.12
        )

    elif environment_name == "pharmacy":
        add_cube(
            "PHARMACY_COUNTER",
            (0, 2.6, 1.0),
            (3.2, 0.7, 0.5),
            white,
            0.12
        )

        add_cube(
            "PHARMACY_SIGN",
            (0, 3.8, 5.0),
            (2.3, 0.08, 0.55),
            accent,
            0.05
        )

    elif environment_name == "street":
        road = create_material(
            "ROAD",
            (0.05, 0.05, 0.06)
        )

        add_cube(
            "ROAD",
            (0, 2, 0.05),
            (7, 6, 0.05),
            road
        )

    elif environment_name == "park":
        trunk = create_material(
            "TREE_TRUNK",
            (0.28, 0.12, 0.04)
        )

        leaves = create_material(
            "TREE_LEAVES",
            (0.04, 0.30, 0.07)
        )

        for x in (-5, 5):
            add_cylinder(
                "TREE_TRUNK",
                (x, 3, 1.5),
                0.35,
                3,
                trunk
            )

            add_sphere(
                "TREE_TOP",
                (x, 3, 3.7),
                (1.6, 1.6, 1.6),
                leaves
            )


# ============================================================
# CAMERA AND LIGHTING
# ============================================================

def look_at(obj, target):
    direction = Vector(target) - obj.location

    obj.rotation_euler = (
        direction
        .to_track_quat("-Z", "Y")
        .to_euler()
    )


def create_camera():
    bpy.ops.object.camera_add(
        location=(0, -14, 4.2)
    )

    camera = bpy.context.object
    camera.name = "MAIN_CAMERA"
    camera.data.lens = 52

    look_at(
        camera,
        (0, 0, 2.4)
    )

    bpy.context.scene.camera = camera

    return camera


def create_lighting():
    lights = [
        ((-4, -5, 8), 1100, 5),
        ((5, -2, 5), 700, 4),
        ((0, 4, 7), 900, 3)
    ]

    for location, energy, size in lights:
        bpy.ops.object.light_add(
            type="AREA",
            location=location
        )

        light = bpy.context.object
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size

        look_at(
            light,
            (0, 0, 2.5)
        )


# ============================================================
# SCRIPT PARSER
# ============================================================

ACTION_PATTERN = re.compile(
    r"\[([a-zA-Z_]+)\]"
)


def parse_script(script):
    lines = []

    for raw_line in script.splitlines():
        raw_line = raw_line.strip()

        if not raw_line or ":" not in raw_line:
            continue

        speaker, dialogue = raw_line.split(
            ":",
            1
        )

        actions = [
            action.lower()
            for action in ACTION_PATTERN.findall(
                dialogue
            )
        ]

        dialogue = ACTION_PATTERN.sub(
            "",
            dialogue
        ).strip()

        if dialogue:
            lines.append({
                "speaker": speaker.strip(),
                "dialogue": dialogue,
                "actions": actions
            })

    return lines


def dialogue_duration(text):
    words = len(text.split())

    return max(
        1.2,
        words / 2.45
    )


# ============================================================
# ANIMATION HELPERS
# ============================================================

def animate_idle(
    character_name,
    start_frame,
    end_frame
):
    root = bpy.data.objects.get(
        character_name + "_ROOT"
    )

    if not root:
        return

    original_z = root.location.z

    points = [
        (start_frame, 0),
        (start_frame + 20, 0.035),
        (start_frame + 40, 0),
        (end_frame, 0)
    ]

    for frame, movement in points:
        root.location.z = (
            original_z + movement
        )

        root.keyframe_insert(
            data_path="location",
            frame=frame
        )


def animate_blink(
    character_name,
    start_frame,
    end_frame
):
    for side in ("L", "R"):
        eye = bpy.data.objects.get(
            character_name
            + "_EYE_"
            + side
        )

        if not eye:
            continue

        original_scale = eye.scale.copy()

        frame = start_frame + 25

        while frame < end_frame - 5:
            eye.scale.z = 0.015

            eye.keyframe_insert(
                data_path="scale",
                frame=frame
            )

            eye.scale = original_scale

            eye.keyframe_insert(
                data_path="scale",
                frame=frame + 4
            )

            frame += 80


def animate_talking(
    character_name,
    start_frame,
    end_frame
):
    mouth = bpy.data.objects.get(
        character_name + "_MOUTH"
    )

    if not mouth:
        return

    original_scale = mouth.scale.copy()

    frame = start_frame

    while frame <= end_frame:
        mouth.scale = original_scale

        mouth.keyframe_insert(
            data_path="scale",
            frame=frame
        )

        mouth.scale.z = (
            original_scale.z * 2.0
        )

        mouth.keyframe_insert(
            data_path="scale",
            frame=frame + 4
        )

        mouth.scale = original_scale

        mouth.keyframe_insert(
            data_path="scale",
            frame=frame + 8
        )

        frame += 8


def animate_expression(
    character_name,
    action,
    frame
):
    head = bpy.data.objects.get(
        character_name + "_HEAD"
    )

    mouth = bpy.data.objects.get(
        character_name + "_MOUTH"
    )

    if head:
        original = head.rotation_euler.copy()

        if action == "surprised":
            head.rotation_euler.x = math.radians(-5)

        elif action == "laugh":
            head.rotation_euler.z = math.radians(4)

        elif action == "shake":
            head.rotation_euler.z = math.radians(-5)

        else:
            original = None

        if original is not None:
            head.keyframe_insert(
                data_path="rotation_euler",
                frame=frame
            )

            head.rotation_euler = original

            head.keyframe_insert(
                data_path="rotation_euler",
                frame=frame + 14
            )

    if mouth and action in (
        "surprised",
        "laugh"
    ):
        original_scale = mouth.scale.copy()

        if action == "surprised":
            mouth.scale.z = (
                original_scale.z * 2.8
            )
        else:
            mouth.scale.z = (
                original_scale.z * 1.6
            )

        mouth.keyframe_insert(
            data_path="scale",
            frame=frame
        )

        mouth.scale = original_scale

        mouth.keyframe_insert(
            data_path="scale",
            frame=frame + 14
        )


def animate_gesture(
    character_name,
    action,
    frame
):
    root = bpy.data.objects.get(
        character_name + "_ROOT"
    )

    arm = bpy.data.objects.get(
        character_name + "_ARM_R"
    )

    if action == "nod" and root:
        original = root.rotation_euler.copy()

        root.rotation_euler.x = math.radians(-7)

        root.keyframe_insert(
            data_path="rotation_euler",
            frame=frame
        )

        root.rotation_euler = original

        root.keyframe_insert(
            data_path="rotation_euler",
            frame=frame + 10
        )

        return

    if action == "shake" and root:
        original = root.rotation_euler.copy()

        root.rotation_euler.z = math.radians(-5)

        root.keyframe_insert(
            data_path="rotation_euler",
            frame=frame
        )

        root.rotation_euler.z = math.radians(5)

        root.keyframe_insert(
            data_path="rotation_euler",
            frame=frame + 6
        )

        root.rotation_euler = original

        root.keyframe_insert(
            data_path="rotation_euler",
            frame=frame + 12
        )

        return

    if not arm:
        return

    movements = {
        "wave": math.radians(-35),
        "point": math.radians(-22),
        "laugh": math.radians(-14),
        "surprised": math.radians(-8),
        "walk": math.radians(-25),
        "sit": math.radians(5)
    }

    if action not in movements:
        return

    original = arm.rotation_euler.copy()

    arm.rotation_euler.z = (
        original.z
        + movements[action]
    )

    arm.keyframe_insert(
        data_path="rotation_euler",
        frame=frame
    )

    arm.rotation_euler = original

    arm.keyframe_insert(
        data_path="rotation_euler",
        frame=frame + 14
    )


# ============================================================
# SCRIPT ANIMATION
# ============================================================

def animate_script(
    lines,
    fps,
    config
):
    current_frame = 1
    subtitle_events = []

    for line in lines:
        character_name = line["speaker"]

        root = bpy.data.objects.get(
            character_name + "_ROOT"
        )

        duration = dialogue_duration(
            line["dialogue"]
        )

        duration_frames = int(
            duration * fps
        )

        start_frame = current_frame

        end_frame = (
            current_frame
            + duration_frames
        )

        if root:
            animate_idle(
                character_name,
                start_frame,
                end_frame
            )

            animate_talking(
                character_name,
                start_frame,
                end_frame
            )

            if config.get(
                "blinking",
                True
            ):
                animate_blink(
                    character_name,
                    start_frame,
                    end_frame
                )

            if config.get(
                "gestures",
                True
            ):
                for action in line["actions"]:
                    animate_gesture(
                        character_name,
                        action,
                        start_frame + 15
                    )

            if config.get(
                "expressions",
                True
            ):
                for action in line["actions"]:
                    animate_expression(
                        character_name,
                        action,
                        start_frame + 15
                    )

        subtitle_events.append({
            "start": start_frame,
            "end": end_frame,
            "speaker": character_name,
            "text": line["dialogue"]
        })

        current_frame = (
            end_frame
            + int(0.15 * fps)
        )

    return (
        current_frame,
        subtitle_events
    )


# ============================================================
# SUBTITLES
# ============================================================

def create_subtitle(
    text,
    start_frame,
    end_frame
):
    subtitle_material = create_material(
        "SUBTITLE_MATERIAL",
        (1.0, 1.0, 1.0),
        0.3
    )

    # The camera is on the negative Y axis and looks
    # toward positive Y. Keep subtitles near the camera,
    # but inside the camera view.
    bpy.ops.object.text_add(
        location=(0, -0.85, 0.55),
        rotation=(math.radians(90), 0, 0)
    )

    subtitle = bpy.context.object

    subtitle.name = (
        "SUBTITLE_"
        + str(start_frame)
    )

    subtitle.data.body = text

    subtitle.data.align_x = "CENTER"
    subtitle.data.align_y = "CENTER"

    subtitle.data.size = 0.34
    subtitle.data.extrude = 0.002

    subtitle.data.materials.append(
        subtitle_material
    )

    # Face the camera.
    subtitle.rotation_euler = (
        math.radians(90),
        0,
        0
    )

    # Prevent depth problems with the scene.
    subtitle.show_in_front = True

    subtitle.hide_render = True

    subtitle.keyframe_insert(
        data_path="hide_render",
        frame=max(
            1,
            start_frame - 1
        )
    )

    subtitle.hide_render = False

    subtitle.keyframe_insert(
        data_path="hide_render",
        frame=start_frame
    )

    subtitle.keyframe_insert(
        data_path="hide_render",
        frame=end_frame
    )

    subtitle.hide_render = True

    subtitle.keyframe_insert(
        data_path="hide_render",
        frame=end_frame + 1
    )


# ============================================================
# AUDIO
# ============================================================

def add_audio(audio_file):
    if not audio_file:
        return

    if not os.path.exists(audio_file):
        return

    scene = bpy.context.scene

    scene.sequence_editor_create()

    bpy.ops.sequencer.sound_strip_add(
        filepath=os.path.abspath(audio_file),
        frame_start=1
    )


# ============================================================
# RENDER SETTINGS
# ============================================================

def configure_render(
    config,
    output_file
):
    scene = bpy.context.scene

    resolution = config.get(
        "resolution",
        "1280x720"
    )

    width, height = map(
        int,
        resolution.split("x")
    )

    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100

    scene.render.fps = int(
        config.get(
            "fps",
            24
        )
    )

    try:
        scene.render.engine = (
            "BLENDER_EEVEE_NEXT"
        )
    except Exception:
        scene.render.engine = (
            "BLENDER_EEVEE"
        )

    scene.render.image_settings.file_format = (
        "FFMPEG"
    )

    scene.render.ffmpeg.format = (
        "MPEG4"
    )

    scene.render.ffmpeg.codec = (
        "H264"
    )

    scene.render.ffmpeg.audio_codec = (
        "AAC"
    )

    scene.render.ffmpeg.constant_rate_factor = (
        "MEDIUM"
    )

    scene.render.filepath = (
        os.path.abspath(
            output_file
        )
    )

    scene.render.film_transparent = False

    scene.world.color = (
        0.025,
        0.035,
        0.055
    )


# ============================================================
# MAIN
# ============================================================

def main():
    config_file, output_file, audio_file = (
        get_arguments()
    )

    with open(
        config_file,
        "r",
        encoding="utf-8"
    ) as file:
        config = json.load(file)

    clear_scene()

    create_environment(
        config.get(
            "environment",
            "studio"
        )
    )

    characters = config.get(
        "characters",
        []
    )

    # Fixed character staging:
    # Zuri remains on the left.
    # Milo remains on the right.
    if "Zuri Spark" in characters:
        create_character(
            "Zuri Spark",
            -2.0,
            (0.95, 0.30, 0.48),
            (0.08, 0.025, 0.01),
            (0.55, 0.28, 0.14)
        )

    if "Milo Quirk" in characters:
        create_character(
            "Milo Quirk",
            2.0,
            (0.95, 0.68, 0.15),
            (0.025, 0.025, 0.03),
            (0.55, 0.28, 0.14)
        )

    create_camera()
    create_lighting()

    lines = parse_script(
        config.get(
            "script",
            ""
        )
    )

    fps = int(
        config.get(
            "fps",
            24
        )
    )

    final_frame, subtitle_events = (
        animate_script(
            lines,
            fps,
            config
        )
    )

    if config.get(
        "subtitles",
        True
    ):
        for event in subtitle_events:
            create_subtitle(
                event["speaker"]
                + ": "
                + event["text"],
                event["start"],
                event["end"]
            )

    scene = bpy.context.scene

    scene.frame_start = 1

    scene.frame_end = max(
        final_frame + fps,
        48
    )

    add_audio(audio_file)

    configure_render(
        config,
        output_file
    )

    blend_file = os.path.splitext(
        output_file
    )[0] + ".blend"

    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.abspath(
            blend_file
        )
    )

    print("")
    print("======================================")
    print(" CARTOON STUDIO 3D")
    print("======================================")
    print("Rendering:", output_file)
    print("======================================")

    bpy.ops.render.render(
        animation=True
    )

    print("")
    print("======================================")
    print(" RENDER COMPLETE")
    print("======================================")
    print(output_file)
    print("======================================")


if __name__ == "__main__":
    main()
