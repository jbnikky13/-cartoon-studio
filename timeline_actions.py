"""Lightweight per-character action timeline for Cartoon Studio V6.

Timeline syntax:
  0-2: Walk In
  2-4: Talk
  4-5: Point
  5-7: Walk

The module is renderer-agnostic: it returns the active action and a
normalized elapsed time for any scene frame.
"""
from dataclasses import dataclass


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
