from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from rec_service.database.base import Base
from rec_service.domain.vector import VECTOR_DIM


user_seen_articles = sa.Table(
    "user_seen_articles",
    Base.metadata,
    sa.Column(
        "user_id",
        sa.BigInteger,
        sa.ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    sa.Column(
        "article_id",
        sa.BigInteger,
        sa.ForeignKey("articles.article_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    sa.Column(
        "inserted_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    ),
)


class Article(Base):
    __tablename__ = "articles"

    article_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.Identity(), primary_key=True
    )

    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)

    lang: Mapped[str] = mapped_column(sa.String, nullable=False)
    pageid: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)

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

    seen_by_users: Mapped[list["User"]] = relationship(
        "User",
        secondary=user_seen_articles,
        back_populates="seen_articles",
        lazy="selectin",
    )

    __table_args__ = (
        sa.UniqueConstraint("lang", "pageid", name="uq_articles_lang_pageid"),
    )


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(sa.BigInteger, sa.Identity(), primary_key=True)

    preference: Mapped[list[float]] = mapped_column(Vector(VECTOR_DIM), nullable=False)
    calibration_size: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)

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

    total_seen_articles: Mapped[int] = mapped_column(
        sa.Integer, default=0, nullable=False
    )

    pool_seen_articles: Mapped[list["Article"]] = relationship(
        "Article",
        secondary=user_seen_articles,
        primaryjoin=(user_id == user_seen_articles.c.user_id),
        secondaryjoin=sa.and_(
            Article.article_id == user_seen_articles.c.article_id,
            Article.is_active.is_(True),
        ),
        back_populates="seen_by_users",
        lazy="selectin",
        viewonly=True,
    )

    __table_args__ = (
        sa.UniqueConstraint("user_id", name="uq_users_user_id"),
        sa.CheckConstraint(
            "total_seen_articles >= 0", name="ck_users_total_seen_nonneg"
        ),
        sa.CheckConstraint(
            "calibration_size >= 0", name="ck_users_calibration_size_nonneg"
        ),
    )


class ArticleEmbedding(Base):
    __tablename__ = "article_embeddings"

    article_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("articles.article_id", ondelete="CASCADE"),
        primary_key=True,
    )

    embedding: Mapped[list[float]] = mapped_column(Vector(VECTOR_DIM), nullable=False)

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

    inserted_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )

    __table_args__ = (
        sa.PrimaryKeyConstraint("lang", "pageid", name="pk_quarantine_articles"),
        sa.Index("ix_quarantine_inserted_at", "inserted_at"),
    )
