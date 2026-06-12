class LabelSmoother:
    """Debounce temporal: cambia de estado solo tras `min_run` frames seguidos del nuevo label."""

    def __init__(self, min_run: int = 2):
        self.min_run = max(1, min_run)
        self.committed: str | None = None
        self._candidate: str | None = None
        self._count = 0

    def push(self, label: str) -> str:
        if self.committed is None:
            self.committed = label
            self._candidate = label
            self._count = 0
            return self.committed
        if label == self.committed:
            self._candidate = label
            self._count = 0
            return self.committed
        # label difiere del estado comprometido
        if label == self._candidate:
            self._count += 1
        else:
            self._candidate = label
            self._count = 1
        if self._count >= self.min_run:
            self.committed = label
            self._count = 0
        return self.committed
