"""Persist canonical events to JSON for replay and dashboard use."""

import json
from pathlib import Path
from typing import List

from schemas import CanonicalEvent


def load_events(path: Path) -> List[CanonicalEvent]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return [CanonicalEvent.model_validate(item) for item in data]


def save_events(path: Path, events: List[CanonicalEvent]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [event.model_dump(mode="json") for event in events]
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def append_event(path: Path, event: CanonicalEvent) -> None:
    events = load_events(path)
    events.append(event)
    save_events(path, events)
