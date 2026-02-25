from dataclasses import dataclass
from typing import Optional, Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from tg_wiki.domain.user import ExternalIdentity, UserSettings, PreferenceVector

from tg_wiki.db.config import DBConfig
from tg_wiki.db.engine import create_engine, create_session_factory
from tg_wiki.db.models import User, UserIdentity, UserSettingsRow, UserPreferencesRow
from tg_wiki.db.ports import UserRepository


def _settings_from_row(row: UserSettingsRow | None) -> UserSettings:
    if row is None:
        return UserSettings()
    return UserSettings(
        page_len=int(row.page_len),
        send_text=bool(row.send_text),
        send_image=bool(row.send_image),
        app_lang=str(row.app_lang),
        wiki_lang=str(row.wiki_lang),
    )


@dataclass(slots=True)
class PostgresUserRepository(UserRepository):
    cfg: DBConfig

    _engine: AsyncEngine | None = None
    _session_factory: async_sessionmaker | None = None

    async def start(self) -> None:
        if self._engine is not None:
            return
        self._engine = create_engine(self.cfg)
        self._session_factory = create_session_factory(self._engine)

    async def close(self) -> None:
        if self._engine is None:
            return
        await self._engine.dispose()
        self._engine = None
        self._session_factory = None

    def _sf(self) -> async_sessionmaker:
        if self._session_factory is None:
            raise RuntimeError("PostgresUserRepository is not started (call start())")
        return self._session_factory

    async def resolve_user_id(
        self, identity: ExternalIdentity, *, update_user: bool = False
    ) -> int:
        provider = identity.provider.strip().lower()
        external_id = identity.external_id_str()

        async with self._sf()() as session:
            async with session.begin():
                stmt = sa.select(UserIdentity).where(
                    UserIdentity.provider == provider,
                    UserIdentity.external_id == external_id,
                )
                row = await session.scalar(stmt)
                if row is not None:
                    if not update_user:
                        return int(row.user_id)

                    row.username = identity.username
                    row.first_name = identity.first_name
                    row.last_name = identity.last_name
                    row.language_code = identity.language_code
                    row.updated_at = sa.func.now()
                    await session.execute(
                        sa.update(User)
                        .where(User.id == row.user_id)
                        .values(last_seen_at=sa.func.now())
                    )
                    return int(row.user_id)

                user = User()
                session.add(user)
                await session.flush()

                ident = UserIdentity(
                    user_id=user.id,
                    provider=provider,
                    external_id=external_id,
                    username=identity.username,
                    first_name=identity.first_name,
                    last_name=identity.last_name,
                    language_code=identity.language_code,
                )
                session.add(ident)
                return int(user.id)

    async def touch_last_seen(self, user_id: int) -> None:
        async with self._sf()() as session:
            async with session.begin():
                await session.execute(
                    sa.update(User)
                    .where(User.id == user_id)
                    .values(last_seen_at=sa.func.now())
                )

    async def get_settings(self, user_id: int) -> UserSettings:
        async with self._sf()() as session:
            async with session.begin():
                row = await session.get(UserSettingsRow, user_id)
                if row is None:
                    row = UserSettingsRow(user_id=user_id)
                    session.add(row)
                    await session.flush()

                return UserSettings(
                    page_len=int(row.page_len),
                    send_text=bool(row.send_text),
                    send_image=bool(row.send_image),
                    app_lang=str(row.app_lang),
                    wiki_lang=str(row.wiki_lang),
                )

    async def update_settings(
        self, user_id: int, settings: UserSettings
    ) -> UserSettings:
        async with self._sf()() as session:
            async with session.begin():
                row = await session.get(UserSettingsRow, user_id)
                if row is None:
                    row = UserSettingsRow(user_id=user_id)
                    session.add(row)

                row.page_len = settings.page_len
                row.send_text = settings.send_text
                row.send_image = settings.send_image
                row.app_lang = settings.app_lang
                row.wiki_lang = settings.wiki_lang
                row.updated_at = sa.func.now()
                await session.flush()

                return settings

    async def get_pref_vector(self, user_id: int) -> Optional[PreferenceVector]:
        async with self._sf()() as session:
            async with session.begin():
                row = await session.get(UserPreferencesRow, user_id)
                if row is None or row.pref_vector is None:
                    return None
                return list(row.pref_vector)

    async def set_pref_vector(self, user_id: int, vector: PreferenceVector) -> None:
        vec = list(vector)
        if len(vec) != self.cfg.pref_vector_dim:
            raise ValueError(
                f"Preference vector dim mismatch: got {len(vec)}, expected {self.cfg.pref_vector_dim}"
            )

        async with self._sf()() as session:
            async with session.begin():
                row = await session.get(UserPreferencesRow, user_id)
                if row is None:
                    row = UserPreferencesRow(user_id=user_id, pref_vector=vec)
                    session.add(row)
                else:
                    row.pref_vector = vec
                    row.updated_at = sa.func.now()
                await session.flush()
