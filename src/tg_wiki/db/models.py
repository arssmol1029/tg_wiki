from datetime import datetime

from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tg_wiki.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )

    identities: Mapped[list["UserIdentity"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    settings: Mapped["UserSettingsRow"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    preferences: Mapped["UserPreferencesRow"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )


class UserIdentity(Base):
    __tablename__ = "user_identities"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    provider: Mapped[str] = mapped_column(sa.Text, nullable=False)
    external_id: Mapped[str] = mapped_column(sa.Text, nullable=False)

    username: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    first_name: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    last_name: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    language_code: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="identities")

    __table_args__ = (
        sa.UniqueConstraint(
            "provider", "external_id", name="uq_user_identities_provider_external"
        ),
        sa.Index("ix_user_identities_provider_external", "provider", "external_id"),
    )


class UserSettingsRow(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    page_len: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("1024")
    )
    send_text: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    send_image: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )

    app_lang: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'ru'")
    )
    wiki_lang: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'ru'")
    )

    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="settings")


class UserPreferencesRow(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    pref_vector: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="preferences")
