import math

from rec_service.domain.preference import Preference, sign
from rec_service.domain.embedding import Embedding
from rec_service.domain.vector import VECTOR_DIM


def _unit_embedding_first_coord() -> Embedding:
    data = [0.0] * VECTOR_DIM
    data[0] = 3.0
    return Embedding(data)


def test_sign():
    assert sign(10) == 1
    assert sign(-2) == -1
    assert sign(0) == 0


def test_update_reaction_zero_no_change():
    p = Preference()
    e = _unit_embedding_first_coord()
    p2 = p.update(reaction=0, embedding=e, total_seen=0)
    assert p2 is p


def test_update_first_positive_sets_direction():
    p = Preference()
    e = _unit_embedding_first_coord()

    # total_seen=0 -> lr=1, starting from 0 -> should become +unit(e)
    p2 = p.update(reaction=+1, embedding=e, total_seen=0)
    assert isinstance(p2, Preference)

    got = p2.data
    norm = math.sqrt(sum(x * x for x in got))
    assert abs(norm - 1.0) < 1e-5

    assert got[0] > 0.99
    assert all(abs(got[i]) < 1e-6 for i in range(1, VECTOR_DIM))


def test_update_negative_flips_direction():
    p = Preference()
    e = _unit_embedding_first_coord()

    p2 = p.update(reaction=-1, embedding=e, total_seen=0)
    got = p2.data
    assert got[0] < -0.99


def test_update_base_lr_overrides_total_seen():
    p = Preference([1.0] + [0.0] * (VECTOR_DIM - 1)).normalize()
    e = _unit_embedding_first_coord()

    # Fixed lr makes update independent of total_seen.
    p2 = p.update(reaction=+1, embedding=e, total_seen=10, base_lr=0.25)

    # Still a unit vector.
    norm = math.sqrt(sum(x * x for x in p2.data))
    assert abs(norm - 1.0) < 1e-5
