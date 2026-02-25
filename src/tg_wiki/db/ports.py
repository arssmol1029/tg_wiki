from typing import Optional, Protocol

from tg_wiki.domain.user import ExternalIdentity, UserSettings, PreferenceVector


class UserRepository(Protocol):
    async def resolve_user_id(
        self, identity: ExternalIdentity, *, update_user: bool = False
    ) -> int:
        """
        (provider, external_id) -> internal users.id.
        """
        ...

    async def touch_last_seen(self, user_id: int) -> None:
        """Update users.last_seen_at for internal user_id."""
        ...

    async def get_settings(self, user_id: int) -> UserSettings:
        """Return settings, creating defaults if needed."""
        ...

    async def update_settings(self, user_id: int, patch: UserSettings) -> UserSettings:
        """Replace settings."""
        ...

    async def get_pref_vector(self, user_id: int) -> Optional[PreferenceVector]:
        """Return user's preference vector, if present."""
        ...

    async def set_pref_vector(self, user_id: int, vector: PreferenceVector) -> None:
        """Persist user's preference vector."""
        ...
