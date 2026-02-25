import asyncio

from dataclasses import dataclass, replace
from typing import Optional

from tg_wiki.domain.user import UserSettings, ExternalIdentity, PreferenceVector
from tg_wiki.db.ports import UserRepository
from tg_wiki.cache.ports import Cache


@dataclass
class UserSettingsService:

    _repo: UserRepository
    _cache: Cache

    @property
    def repo(self) -> UserRepository:
        return self._repo

    @property
    def cache(self) -> Cache:
        return self._cache

    async def _ensure_user(
        self, identity: ExternalIdentity, update_user: bool = False
    ) -> int:
        return await self.repo.resolve_user_id(identity, update_user=update_user)

    async def _update_settings(
        self, user_id: int, settings: UserSettings
    ) -> UserSettings:
        await asyncio.gather(
            self.repo.update_settings(user_id, settings),
            self.cache.user_settings.update(user_id, settings),
        )
        return settings

    async def ensure_telegram_user(
        self,
        tg_user_id: int,
        *,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        language_code: str | None = None,
        update_user: bool = False,
    ) -> int:
        provider = "telegram"

        if not update_user:
            user_id = await self.cache.user_ids.get(
                provider=provider, external_id=tg_user_id
            )
            if user_id:
                return user_id

        identity = ExternalIdentity(
            provider=provider,
            external_id=tg_user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
        )
        user_id = await self._ensure_user(identity, update_user=update_user)
        await self.cache.user_ids.update(
            user_id, provider=provider, external_id=tg_user_id
        )
        return user_id

    async def get_settings(self, user_id: int) -> UserSettings:
        settings = await self.cache.user_settings.get(user_id)
        if settings:
            return settings
        settings = await self.repo.get_settings(user_id)
        asyncio.create_task(self.cache.user_settings.update(user_id, settings))
        return settings

    async def touch_last_seen(self, user_id: int) -> None:
        await self._repo.touch_last_seen(user_id)

    async def set_page_len(self, user_id: int, page_len: int) -> UserSettings:
        if page_len < 128:
            page_len = 128
        if page_len > 4096:
            page_len = 4096

        current = await self.repo.get_settings(user_id)
        updated = replace(current, page_len=page_len)
        return await self._update_settings(user_id, updated)

    async def set_rendering(
        self,
        user_id: int,
        *,
        send_text: bool | None = None,
        send_image: bool | None = None,
    ) -> UserSettings:
        current = await self.repo.get_settings(user_id)
        updated = replace(
            current,
            send_text=send_text if send_text is not None else current.send_text,
            send_image=send_image if send_image is not None else current.send_image,
        )
        return await self._update_settings(user_id, updated)

    async def set_app_lang(self, user_id: int, lang: str) -> UserSettings:
        lang = (lang or "").strip().lower()
        if not lang:
            lang = "ru"
        current = await self.repo.get_settings(user_id)
        updated = replace(current, app_lang=lang)
        return await self._update_settings(user_id, updated)

    async def set_wiki_lang(self, user_id: int, lang: str) -> UserSettings:
        lang = (lang or "").strip().lower()
        if not lang:
            lang = "ru"
        current = await self.repo.get_settings(user_id)
        updated = replace(current, wiki_lang=lang)
        return await self._update_settings(user_id, updated)

    async def get_pref_vector(self, user_id: int) -> Optional[PreferenceVector]:
        return await self.repo.get_pref_vector(user_id)

    async def set_pref_vector(self, user_id: int, vector: PreferenceVector) -> None:
        await self.repo.set_pref_vector(user_id, vector)
