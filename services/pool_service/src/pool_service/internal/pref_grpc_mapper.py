import struct

from scpedia_protos.pool.v1 import pool_pb2

from pool_service.domain.preference import PreferenceVector, PREFERENCE_DIM


class InvalidPreference(ValueError):
    pass


def validate_preference(pref: pool_pb2.PreferenceVector) -> None:
    if pref.dim != PREFERENCE_DIM:
        raise InvalidPreference(f"preference.dim must be {PREFERENCE_DIM}")

    data = pref.data
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise InvalidPreference("preference.data must be bytes-like")

    nbytes = len(data)
    need = pref.dim * 4
    if nbytes != need:
        raise InvalidPreference(
            f"preference.data has {nbytes} bytes, expected {need} (=dim*4)"
        )


def from_pool_pb_embedding(pref: pool_pb2.PreferenceVector) -> PreferenceVector:
    fmt = f"<{pref.dim}f"
    return PreferenceVector(dim=pref.dim, data=list(struct.unpack(fmt, pref.data)))
