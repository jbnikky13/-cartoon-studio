"""
Small data models/helpers for Cartoon Studio V6.
"""
from dataclasses import dataclass, asdict
from typing import List


@dataclass
class DialogueLine:
    speaker: str
    text: str
    emotion: str = "Auto"
    motion: str = "talk"
    start: float = 0.0
    duration: float = 3.0


def parse_dialogue(text: str) -> List[DialogueLine]:
    import re
    rows = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^([^:]{1,40}):\s*(.+)$", line)
        if m:
            rows.append(DialogueLine(m.group(1).strip(), m.group(2).strip()))
        else:
            rows.append(DialogueLine("Narrator", line))
    return rows


def estimate_duration(text: str, words_per_second=2.7) -> float:
    words = max(1, len(text.split()))
    return max(1.5, min(15.0, words / words_per_second + 0.6))


def build_timeline(text: str):
    rows = parse_dialogue(text)
    cursor = 0.0
    for row in rows:
        row.duration = estimate_duration(row.text)
        row.start = cursor
        cursor += row.duration
    return rows, max(1.0, cursor)


def to_dict(rows):
    return [asdict(x) for x in rows]
