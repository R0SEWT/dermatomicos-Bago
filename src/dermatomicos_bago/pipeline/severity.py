from ..config import SeverityConfig


class SeverityTracker:
    """Acumulador con decay: instancia mínima del framework EczemaPred."""

    def __init__(self, cfg: SeverityConfig | None = None):
        self.cfg = cfg or SeverityConfig()
        self.value = 0.0
        self.history: list[float] = []

    def update(self, cry_load: float, scratch_load: float) -> float:
        c = self.cfg
        load = c.w_cry * cry_load + c.w_scratch * scratch_load
        decay = c.decay - (c.clean_bonus if load < c.clean_threshold else 0.0)
        self.value = min(c.max_value, max(0.0, self.value * decay + load))
        self.history.append(self.value)
        return self.value
