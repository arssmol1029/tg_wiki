import os

from dataclasses import dataclass
from typing import Callable, Optional

from rec_service.database.ports import Uow
from rec_service.domain.preference import Preference


class UserProvisionFailed(RuntimeError):
    pass


@dataclass
class RecServiceConfig:
    calibration_size: int = 20

    @staticmethod
    def from_env(*, prefix: str = "REC_SERVICE") -> "RecServiceConfig":
        def _get_int(name: str, default: int) -> int:
            raw = os.getenv(f"{prefix}_{name}")
            if raw is None or not raw.strip():
                return default
            try:
                return int(raw)
            except ValueError as e:
                raise ValueError(f"{name} must be an int, got: {raw!r}") from e

        return RecServiceConfig(
            calibration_size=_get_int("CALIBRATION_SIZE", 20),
        )


class RecService:
    def __init__(
        self, *, uow_factory: Callable[[], Uow], cfg: RecServiceConfig | None = None
    ):
        self._uow_factory = uow_factory
        self._cfg = cfg or RecServiceConfig.from_env()

    async def get_user_pref(self, *, user_id: int) -> Optional[Preference]:
        """
        Retrieve user preference vector. Create user if not exists.

        Args:
            user_id: The unique identifier of the user.

        Returns:
            User preference vector or None if user or his preference not found.
        """
        async with self._uow_factory() as uow:
            preference = await uow.users.get_user_pref(user_id=user_id)

        if not preference:
            async with self._uow_factory() as uow:
                success = await uow.users.create_user(
                    user_id=user_id, calibration_size=self._cfg.calibration_size
                )
            if success:
                return Preference()
            else:
                raise UserProvisionFailed(f"Failed to provision user {user_id}")

        return Preference(data=preference)

    async def get_user_calibration_size(self, *, user_id: int) -> int | None:
        """
        Returns:
            User calibration size or None if user not found.
        """
        async with self._uow_factory() as uow:
            return await uow.users.get_user_calibration_size(user_id=user_id)

    async def get_user_total_seen(self, *, user_id: int) -> int | None:
        """
        Returns:
            User total seen articles field value or None if user not found.
        """
        async with self._uow_factory() as uow:
            return await uow.users.get_user_total_seen(user_id=user_id)

    async def update_user_pref(self, *, user_id: int, pref: Preference) -> bool:
        """
        Update user preference vector.

        Args:
            user_id: The unique identifier of the user.
            pref: The preference vector to be updated.

        Returns:
            True if the user preference was successfully updated, False otherwise.
        """
        async with self._uow_factory() as uow:
            return await uow.users.update_user_pref(user_id=user_id, pref=pref.data)

    async def create_user(
        self, *, user_id: int, calibration_size: int | None = None
    ) -> bool:
        """
        Create a new user.

        Args:
            user_id: The unique identifier of the user to be created.
            calibration_size: User calibration pool size (if None set default)

        Returns:
            True if the user was successfully created, False otherwise.
        """
        async with self._uow_factory() as uow:
            return await uow.users.create_user(
                user_id=user_id,
                calibration_size=calibration_size or self._cfg.calibration_size,
            )

    async def reset_user(
        self, *, user_id: int, calibration_size: int | None = None
    ) -> bool:
        """
        Reset user preference.

        Args:
            user_id: The unique identifier of the user to be added.
            calibration_size: User calibration pool size (if None set default)

        Returns:
            True if the user preference was successfully reseted, False otherwise.
        """
        async with self._uow_factory() as uow:
            return await uow.users.reset_user(
                user_id=user_id,
                calibration_size=calibration_size or self._cfg.calibration_size,
            )

    async def delete_user(self, *, user_id: int) -> bool:
        """
        Delete user

        Args:
            user_id: The unique identifier of the user to be deleted.

        Returns:
            True if the user was successfully deleted or not exists, False otherwise.
        """
        async with self._uow_factory() as uow:
            return await uow.users.delete_user(user_id=user_id)
