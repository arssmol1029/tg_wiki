from dataclasses import dataclass


# constant
PREFERENCE_DIM = 768  # must be equal to embedding dim


@dataclass
class PreferenceVector:
    dim: int
    data: list[float]
