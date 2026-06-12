from dataclasses import dataclass


@dataclass(frozen=True)
class DetectConfig:
    sample_rate: int = 16000
    frame_seconds: float = 1.0          # ventana enviada a YAMNet
    hop_seconds: float = 1.0            # sin solape para el MVP (1 etiqueta/seg)
    cry_threshold: float = 0.20        # score mínimo de clase cry
    scratch_threshold: float = 0.50    # prob mínima de la cabeza de rascado
    quiet_rms: float = 0.005           # por debajo => quiet/sueño
    cry_class_names: tuple = ("Baby cry, infant cry", "Crying, sobbing")


@dataclass(frozen=True)
class SeverityConfig:
    decay: float = 0.6                  # carryover de severidad noche-a-noche
    w_cry: float = 0.4                  # peso de la carga de llanto [0..1]
    w_scratch: float = 0.6             # peso de la carga de rascado [0..1]
    clean_bonus: float = 0.15          # decay extra si la noche fue limpia
    clean_threshold: float = 0.10      # carga total por debajo => noche "limpia"
    max_value: float = 1.0


@dataclass(frozen=True)
class FeatureConfig:
    min_quiet_seconds: float = 30.0    # tramo quiet mínimo para contar como "dormido"
    awakening_active_label: tuple = ("cry", "scratch")
