from .features import NightFeatures
from .severity import SeverityTracker


class ReportBuilder:
    def __init__(self, escalation_threshold: float = 0.5):
        self.escalation_threshold = escalation_threshold

    def build(self, f: NightFeatures, tracker: SeverityTracker) -> str:
        sev = tracker.value
        escalated = sev >= self.escalation_threshold
        flag = (
            "> ⚠️ **Escalada de brote detectada** — considera registrarlo para tu consulta dermatológica.\n"
            if escalated else ""
        )
        return f"""# Reporte nocturno — dermatomicos

{flag}
| Métrica | Valor |
|---|---|
| Llanto (total) | {f.cry_seconds/60:.1f} min ({f.cry_events} episodios) |
| Rascado (total) | {f.scratch_seconds/60:.1f} min ({f.scratch_events} episodios) |
| Despertares | {f.awakenings} |
| Fragmentación del sueño | {f.sleep_fragmentation:.1f} /h |
| **Severidad estimada** | **{sev:.2f}** / 1.00 |

_Severidad = instancia mínima del framework EczemaPred (acumulador con decay sobre carga acústica nocturna)._

---
_Este reporte es una medición acústica objetiva, **no es un diagnóstico**. Consulta a tu dermatólogo._
"""
