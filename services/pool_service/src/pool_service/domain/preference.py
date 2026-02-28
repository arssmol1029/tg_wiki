import struct

from dataclasses import dataclass

from scpedia_protos.pool.v1 import pool_pb2


# constant
PREFERENCE_DIM = 768  # must be equal to embedding dim


@dataclass
class PreferenceVector:
    dim: int
    data: list[float]


class InvalidPreference(ValueError):
    pass


def validate_preference(
    pref: pool_pb2.PreferenceVector, *, expected_dim: int | None = None
) -> None:
    if pref.dim <= 0:
        raise InvalidPreference("preference.dim must be > 0")

    if expected_dim is not None and pref.dim != expected_dim:
        raise InvalidPreference(
            f"preference.dim must be {expected_dim}, got {pref.dim}"
        )

    data = pref.data
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise InvalidPreference("preference.data must be bytes-like")

    nbytes = len(data)
    need = pref.dim * 4
    if nbytes != need:
        raise InvalidPreference(
            f"preference.data has {nbytes} bytes, expected {need} (=dim*4)"
        )

    if pref.dim > 8192:
        raise InvalidPreference("preference.dim too large")


def unpack_f32le(pref: pool_pb2.PreferenceVector) -> PreferenceVector:
    fmt = f"<{pref.dim}f"
    return PreferenceVector(dim=pref.dim, data=list(struct.unpack(fmt, pref.data)))
