"""True-action adapter for the Classic Cartoon renderer.

The existing Classic renderer is a procedural 2D rig. This adapter keeps
that renderer intact and adds action-driven movement at the scene level:
walk/run travel, jump arcs, dance, celebrate, crouch and slide.
"""
import math

ACTION_PRESETS = [
    "Idle", "Walk In", "Walk", "Run", "Jump", "Dance",
    "Celebrate", "Crouch", "Slide Left", "Slide Right", "Exit Right"
]


def action_offsets(action, t, seed=0):
    """Return (dx, dy, extra_rotation, posture_override)."""
    a = (action or "Idle").lower()
    dx = dy = rot = 0.0
    posture = None

    if a == "walk in":
        # Enters from the left and settles near the original anchor.
        p = min(1.0, max(0.0, t / 1.6))
        ease = p * p * (3 - 2 * p)
        dx = -0.38 + 0.38 * ease
        dy = -abs(math.sin(t * 9.0 + seed)) * 0.012
        rot = math.sin(t * 9.0 + seed) * 2.0
    elif a == "walk":
        dx = 0.055 * t
        dy = -abs(math.sin(t * 8.0 + seed)) * 0.012
        rot = math.sin(t * 8.0 + seed) * 2.2
    elif a == "run":
        dx = 0.12 * t
        dy = -abs(math.sin(t * 13.0 + seed)) * 0.025
        rot = math.sin(t * 13.0 + seed) * 4.0
    elif a == "jump":
        p = (t * 1.1 + seed * 0.1) % 1.0
        dy = -(4 * p * (1 - p)) * 120
        rot = math.sin(p * math.pi) * 3.0
    elif a == "dance":
        dx = math.sin(t * 5.5 + seed) * 22
        dy = -abs(math.sin(t * 5.5 + seed)) * 12
        rot = math.sin(t * 5.5 + seed) * 7
    elif a == "celebrate":
        dy = -abs(math.sin(t * 5 + seed)) * 18
        rot = math.sin(t * 7 + seed) * 4
    elif a == "crouch":
        dy = 35 + math.sin(t * 2 + seed) * 4
        posture = "Sitting"
    elif a == "slide left":
        dx = -120 * min(1.0, t / 1.2)
    elif a == "slide right":
        dx = 120 * min(1.0, t / 1.2)
    elif a == "exit right":
        dx = 0.55 * min(1.0, max(0.0, t / 1.8))
        dy = -abs(math.sin(t * 9.0 + seed)) * 0.012
        rot = math.sin(t * 9.0 + seed) * 2.0

    return dx, dy, rot, posture


def patch_classic_module(classic_module):
    """Wrap draw_rigged_character while preserving its existing API."""
    original = getattr(classic_module, "draw_rigged_character", None)
    if original is None or getattr(original, "_v6_actions_patched", False):
        return

    def wrapped(draw, name, cx, ground, frame, seed, expression="Neutral",
                posture="Standing", gesture="Talking Hands", talking=False,
                look_x=None, scale=1.0, style="Bold 2D Comedy", mouth_frame=None):
        action = "Idle"
        try:
            import streamlit as st
            action = st.session_state.get(f"v6_action_{name}", "Idle")
        except Exception:
            pass

        # Classic renderer uses 24fps, so frame/24 gives stable scene time.
        dx, dy, rot, posture_override = action_offsets(action, frame / 24.0, seed)
        if posture_override:
            posture = posture_override
        return original(draw, name, cx + dx, ground + dy, frame, seed,
                        expression=expression, posture=posture, gesture=gesture,
                        talking=talking, look_x=look_x, scale=scale,
                        style=style, mouth_frame=mouth_frame)

    wrapped._v6_actions_patched = True
    classic_module.draw_rigged_character = wrapped
