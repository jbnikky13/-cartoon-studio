"""Shared lightweight animation primitives for Cartoon Studio.

Designed for PIL/FFmpeg rendering on memory-constrained hosts. It produces
normalized pose/camera values instead of retaining video frames in memory.
"""
from dataclasses import dataclass, field
import math
from typing import Dict, List, Tuple


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, float(v)))


def ease_in_out(t):
    t = clamp(t)
    return t * t * (3.0 - 2.0 * t)


def ease_out(t):
    t = clamp(t)
    return 1.0 - (1.0 - t) ** 3


def pingpong(t):
    x = t % 2.0
    return x if x <= 1.0 else 2.0 - x


@dataclass
class CharacterPose:
    x: float = 0.5
    y: float = 0.72
    scale: float = 1.0
    rotation: float = 0.0
    head_turn: float = 0.0
    body_lean: float = 0.0
    left_arm: float = 0.0
    right_arm: float = 0.0
    left_leg: float = 0.0
    right_leg: float = 0.0
    mouth: float = 0.0
    blink: float = 0.0
    expression: str = "neutral"


@dataclass
class CameraState:
    x: float = 0.5
    y: float = 0.5
    zoom: float = 1.0
    rotation: float = 0.0
    target: str = "scene"


@dataclass
class MotionCue:
    action: str
    start: float
    duration: float
    params: Dict = field(default_factory=dict)


ACTIONS = [
    "idle", "walk_in", "walk", "run", "talk", "look_left", "look_right",
    "point_left", "point_right", "wave", "nod", "shake_head", "jump",
    "sit", "stand", "surprise", "happy", "sad", "think", "celebrate",
    "turn", "walk_out"
]


def _phase(t, duration):
    return clamp(t / max(0.001, duration))


def pose_for_action(action: str, t: float, duration: float, base=None, params=None) -> CharacterPose:
    """Return a procedural pose. Coordinates are normalized 0..1."""
    p = CharacterPose(**vars(base)) if base else CharacterPose()
    params = params or {}
    q = _phase(t, duration)
    cyc = t * float(params.get("frequency", 2.0))

    if action in ("walk", "walk_in", "walk_out", "run"):
        speed = 2.8 if action != "run" else 5.0
        phase = math.sin(cyc * speed * math.pi)
        p.left_leg = phase * (24 if action != "run" else 34)
        p.right_leg = -p.left_leg
        p.left_arm = -phase * (18 if action != "run" else 28)
        p.right_arm = -p.left_arm
        p.y += abs(phase) * (0.008 if action != "run" else 0.015)
        p.body_lean = 4 if action == "run" else 1.5
        if action == "walk_in": p.x = -0.12 + 0.62 * ease_out(q)
        if action == "walk_out": p.x = 0.62 + 0.62 * ease_in_out(q)

    elif action == "talk":
        p.mouth = 0.5 + 0.5 * math.sin(cyc * 3.0 * math.pi)
        p.head_turn = 3.0 * math.sin(cyc * 0.7 * math.pi)
        p.body_lean = 1.2 * math.sin(cyc * 0.8 * math.pi)
        p.left_arm = 5 * math.sin(cyc * 1.3 * math.pi)
        p.right_arm = -4 * math.sin(cyc * 1.1 * math.pi)
        p.blink = 1.0 if abs(math.sin(cyc * 0.31 * math.pi)) > 0.985 else 0.0

    elif action == "point_left":
        p.left_arm = -62 * ease_out(q)
        p.body_lean = -3 * ease_in_out(q)
        p.head_turn = -8 * ease_in_out(q)

    elif action == "point_right":
        p.right_arm = 62 * ease_out(q)
        p.body_lean = 3 * ease_in_out(q)
        p.head_turn = 8 * ease_in_out(q)

    elif action == "wave":
        p.right_arm = 25 + 28 * math.sin(cyc * 3.0 * math.pi)
        p.head_turn = 4 * math.sin(cyc * math.pi)

    elif action == "nod":
        p.rotation = 5 * math.sin(q * math.pi * 2)

    elif action == "shake_head":
        p.head_turn = 14 * math.sin(q * math.pi * 5)

    elif action == "jump":
        # anticipation -> lift -> apex -> landing with subtle squash/recovery
        if q < 0.18:
            a = ease_in_out(q / 0.18); p.y += 0.035 * a; p.scale *= 1 - 0.06 * a
        elif q < 0.75:
            a = (q - 0.18) / 0.57; p.y -= 0.18 * math.sin(a * math.pi); p.scale *= 1 + 0.025 * math.sin(a * math.pi)
        else:
            a = (q - 0.75) / 0.25; p.y += 0.025 * math.sin(a * math.pi); p.scale *= 1 - 0.05 * math.sin(a * math.pi)

    elif action == "turn":
        p.head_turn = (params.get("direction", 1) * 25) * ease_in_out(q)
        p.rotation = (params.get("direction", 1) * 8) * ease_in_out(q)

    elif action == "surprise":
        p.expression = "surprised"; p.scale *= 1 + 0.035 * math.sin(q * math.pi)
        p.head_turn = 4 * math.sin(q * math.pi)

    elif action == "happy":
        p.expression = "happy"; p.left_arm = -18 * math.sin(q * math.pi); p.right_arm = 18 * math.sin(q * math.pi)

    elif action == "sad":
        p.expression = "sad"; p.body_lean = -5 * math.sin(q * math.pi)

    elif action == "think":
        p.expression = "thinking"; p.head_turn = -10 * ease_in_out(q); p.right_arm = -35 * ease_out(q)

    elif action == "celebrate":
        p.expression = "happy"; p.left_arm = -55 * math.sin(q * math.pi * 3); p.right_arm = 55 * math.sin(q * math.pi * 3)

    return p


def pose_from_timeline(cues: List[MotionCue], t: float, base=None) -> CharacterPose:
    """Blend the active cue over a base pose; only one primary action is applied."""
    active = [c for c in cues if c.start <= t <= c.start + c.duration]
    if not active:
        return pose_for_action("idle", t, 1.0, base)
    cue = active[-1]
    return pose_for_action(cue.action, t - cue.start, cue.duration, base, cue.params)


def camera_motion(kind="slow_push", t=0.0, duration=1.0, params=None):
    params = params or {}; q = ease_in_out(_phase(t, duration)); c = CameraState()
    if kind == "slow_push": c.zoom = 1.0 + 0.10 * q
    elif kind == "slow_pull": c.zoom = 1.10 - 0.10 * q
    elif kind == "pan_left": c.x = 0.5 - 0.12 * q
    elif kind == "pan_right": c.x = 0.5 + 0.12 * q
    elif kind == "focus":
        c.x = float(params.get("x", 0.5)); c.y = float(params.get("y", 0.5)); c.zoom = 1.0 + 0.16 * q
        c.target = str(params.get("target", "evidence"))
    elif kind == "shake":
        amp = float(params.get("amplitude", 0.008)); c.x += math.sin(t * 42) * amp; c.y += math.cos(t * 47) * amp
    return c
