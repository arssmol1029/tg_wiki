from pool_service.domain.article import Article
from pool_service.domain.embedding import EmbeddingVector

from pool_service.domain.embedding import EMBEDDING_DIM


class ModelClient:
    def get_embedding(self, article: Article) -> EmbeddingVector:
        return EmbeddingVector(dim=EMBEDDING_DIM, data=[0] * EMBEDDING_DIM)
