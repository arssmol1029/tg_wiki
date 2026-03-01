from dataclasses import dataclass


# constant
EMBEDDING_DIM = 768  # must be equal to preference dim


@dataclass
class EmbeddingVector:
    dim: int
    data: list[float]


class InvalidEmbedding(ValueError):
    pass
