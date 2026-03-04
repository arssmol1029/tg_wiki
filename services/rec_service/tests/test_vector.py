import math

from rec_service.domain.vector import Vector, VECTOR_DIM, is_valid_vector


def test_vector_default_is_zero():
    v = Vector()
    assert len(v.data) == VECTOR_DIM
    assert all(x == 0.0 for x in v.data)


def test_vector_normalize_zero_is_noop():
    v = Vector()
    v.normalize()
    assert all(x == 0.0 for x in v.data)


def test_vector_normalize_non_zero():
    v = Vector([1.0] * VECTOR_DIM)
    v.normalize()
    norm = math.sqrt(sum(x * x for x in v.data))
    assert abs(norm - 1.0) < 1e-5


def test_is_valid_vector():
    assert is_valid_vector(Vector()) is True
    assert is_valid_vector([0.0] * VECTOR_DIM) is True
    assert is_valid_vector([0.0] * (VECTOR_DIM - 1)) is False
    assert is_valid_vector("not a vector") is False
