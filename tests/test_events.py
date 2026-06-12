from dermatomicos_bago.pipeline.events import Event, frames_to_episodes


def test_consecutive_same_labels_merge_into_one_episode():
    labels = ["quiet", "quiet", "cry", "cry", "cry", "quiet"]
    eps = frames_to_episodes(labels, frame_seconds=1.0)
    assert eps == [
        Event(0.0, 2.0, "quiet", 1.0),
        Event(2.0, 5.0, "cry", 1.0),
        Event(5.0, 6.0, "quiet", 1.0),
    ]


def test_empty():
    assert frames_to_episodes([], 1.0) == []
