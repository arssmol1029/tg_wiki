import numpy as np
from typing import Self

from rec_service.domain.vector import Vector
from rec_service.domain.embedding import Embedding


def sign(num):
    if num > 0:
        return 1
    elif num < 0:
        return -1
    else:
        return 0


class Preference(Vector):
    def update(
        self,
        reaction: int,
        embedding: Embedding,
        total_seen: int,
        *,
        calibration: bool = False,
        base_lr: float | None = None,
        calibration_boost: float = 2.0,
        eps: float = 1e-12,
    ) -> Self:
        """
        Update preference vector using online mean update.

        Args:
            reaction: User reaction sign (+1/-1/0).
            embedding: Article embedding.
            total_seen: How many updates were already incorporated (included 0 reactions).
            calibration: Whether this update is from calibration pool.
            base_lr: If set, fixed learning rate. If None, lr = 1/(total_seen+1).
            calibration_boost: Extra multiplier for calibration updates.
            eps: Numeric stability for normalization.

        Returns:
            Updated preference (new object).
        """
        s = np.float32(sign(reaction))
        if s == 0.0:
            return self

        if base_lr is None:
            lr = np.float32(1.0 / max(total_seen + 1, 1))
        else:
            lr = np.float32(base_lr)

        w = lr * (np.float32(calibration_boost) if calibration else np.float32(1.0))

        e = np.asarray(embedding._data, dtype=np.float32).ravel()
        en = float(np.linalg.norm(e))
        if en > eps:
            e = (e / np.float32(en)).astype(np.float32, copy=False)

        p = np.asarray(self._data, dtype=np.float32).ravel()

        new = (np.float32(1.0) - w) * p + w * (s * e)

        return self.__class__(new).normalize(eps=eps)
