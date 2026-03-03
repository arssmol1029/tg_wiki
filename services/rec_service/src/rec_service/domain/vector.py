import numpy as np
from numpy.typing import NDArray
from typing import Sequence, Self


VECTOR_DIM = 768


class Vector:
    _data: NDArray[np.float32]

    @property
    def data(self) -> list[float]:
        return np.asarray(self._data, dtype=np.float32).tolist()

    def __init__(self, data: list[float] | NDArray[np.floating] | None = None):
        if data is None:
            self._data = np.zeros((VECTOR_DIM,), dtype=np.float32)
        else:
            self._data = np.asarray(data, dtype=np.float32).ravel()

    def normalize(self, eps: float = 1e-12) -> Self:
        v = np.asarray(self._data, dtype=np.float32).ravel()
        norm = float(np.linalg.norm(v))
        if norm <= eps:
            return self
        self._data = (v / norm).astype(np.float32, copy=False)
        return self


def is_valid_vector(vector) -> bool:
    if isinstance(vector, Vector):
        return int(vector._data.size) == VECTOR_DIM
    if isinstance(vector, Sequence):
        return len(vector) == VECTOR_DIM
    return False
