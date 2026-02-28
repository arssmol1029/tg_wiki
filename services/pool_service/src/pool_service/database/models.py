from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from pool_service.database.base import Base
from pool_service.domain.embedding import EMBEDDING_DIM


class Shard(Base):
    __tablename__ = "shards"

    lang: Mapped[str] = mapped_column(sa.String, primary_key=True)
    shard_id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    shard_gen: Mapped[int] = mapped_column(sa.Integer, primary_key=True)

    shard_size: Mapped[int] = mapped_column(sa.Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    articles: Mapped[list["Article"]] = relationship(
        back_populates="shard",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (sa.Index("ix_shards_lang_shard", "lang", "shard_id"),)


class Article(Base):
    __tablename__ = "articles"

    article_id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)

    lang: Mapped[str] = mapped_column(sa.String, nullable=False)
    pageid: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)

    shard_id: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    shard_gen: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    shift: Mapped[int] = mapped_column(sa.Integer, nullable=False)

    title: Mapped[str] = mapped_column(sa.Text, nullable=False)
    url: Mapped[str] = mapped_column(sa.Text, nullable=False)

    thumbnail_url: Mapped[str] = mapped_column(sa.Text, nullable=False, default="")
    extract: Mapped[str] = mapped_column(sa.Text, nullable=False, default="")
    extract_len: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )

    embedding: Mapped["ArticleEmbedding"] = relationship(
        back_populates="article",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    shard: Mapped["Shard"] = relationship(back_populates="articles")

    __table_args__ = (
        sa.UniqueConstraint("lang", "pageid", name="uq_articles_lang_pageid"),
        sa.UniqueConstraint(
            "lang", "shard_id", "shard_gen", "shift", name="uq_articles_slot"
        ),
        sa.ForeignKeyConstraint(
            ["lang", "shard_id", "shard_gen"],
            ["shards.lang", "shards.shard_id", "shards.shard_gen"],
            ondelete="CASCADE",
            name="fk_articles_shard_gen",
        ),
    )


class ArticleEmbedding(Base):
    __tablename__ = "article_embeddings"

    article_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("articles.article_id", ondelete="CASCADE"),
        primary_key=True,
    )

    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIM), nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )

    article: Mapped[Article] = relationship(back_populates="embedding")

    __table_args__ = (
        sa.Index(
            "ix_article_embeddings_hnsw_l2",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_l2_ops"},
            postgresql_with={"m": 16, "ef_construction": 200},
        ),
    )


class QuarantineArticle(Base):
    __tablename__ = "quarantine_articles"

    lang: Mapped[str] = mapped_column(sa.String, nullable=False)
    pageid: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)

    shard_id: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    shard_gen: Mapped[int] = mapped_column(sa.Integer, nullable=False)

    inserted_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )

    __table_args__ = (
        sa.PrimaryKeyConstraint("lang", "pageid", name="pk_quarantine_articles"),
        sa.Index("ix_quarantine_by_shard", "lang", "shard_id", "shard_gen"),
        sa.Index("ix_quarantine_inserted_at", "inserted_at"),
    )
