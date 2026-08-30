"""Lightweight per-character action timeline for Cartoon Studio V6/V2.

Keeps the existing text timeline API while exposing procedural pose samples
for Classic Cartoon, RealityBlend and Evidence Board renderers.
"""
from dataclasses import dataclass

from animation_engine import MotionCue, pose_for_action, pose_from_timeline


@dataclass(frozen=True)
class ActionCue:
    start: float
    end: float
    action: str


def parse_timeline(text):
    cues = []
    for raw in str(text or "").splitlines():
        raw = raw.strip()
        if not raw or ":" not in raw or "-" not in raw.split(":", 1)[0]:
            continue
        span, action = raw.split(":", 1)
        try:
            start_s, end_s = span.strip().split("-", 1)
            start, end = float(start_s), float(end_s)
        except ValueError:
            continue
        if end > start and action.strip():
            cues.append(ActionCue(start, end, action.strip()))
    return sorted(cues, key=lambda c: c.start)


def active_action(text, seconds, default="Idle"):
    cues = parse_timeline(text)
    for cue in cues:
        if cue.start <= seconds < cue.end:
            return cue.action, seconds - cue.start
    return default, 0.0


def timeline_duration(text):
    cues = parse_timeline(text)
    return max((c.end for c in cues), default=0.0)


def procedural_pose(text, seconds, base=None):
    """Sample the realistic procedural pose for the current timeline time."""
    cues = [MotionCue(c.action.lower().replace(" ", "_"), c.start, c.end-c.start) for c in parse_timeline(text)]
    return pose_from_timeline(cues, float(seconds), base=base)


def procedural_action(action, elapsed, duration=1.0, base=None, **params):
    """Direct procedural action sampler for renderers."""
    normalized = str(action or "idle").lower().replace(" ", "_")
    return pose_for_action(normalized, float(elapsed), max(0.001, float(duration)), base=base, params=params)
