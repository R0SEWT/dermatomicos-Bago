from dataclasses import dataclass


@dataclass(frozen=True)
class Event:
    t_start: float
    t_end: float
    label: str
    score: float = 1.0


def frames_to_episodes(labels: list[str], frame_seconds: float) -> list[Event]:
    """Merge consecutive identical frame labels into episodes."""
    episodes: list[Event] = []
    if not labels:
        return episodes
    cur = labels[0]
    start = 0
    for i in range(1, len(labels) + 1):
        if i == len(labels) or labels[i] != cur:
            episodes.append(Event(start * frame_seconds, i * frame_seconds, cur, 1.0))
            if i < len(labels):
                cur = labels[i]
                start = i
    return episodes
