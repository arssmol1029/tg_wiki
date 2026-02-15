from typing import Protocol


class UserCache(Protocol):
    async def get(self, user_id: int) -> list[int]:
        """
        Retrieves a list of recently viewed article pageids for a given user.

        Args:
            user_id: The user_id of the user to retrieve recent articles for.

        Returns:
            A list of article pageids that the user has recently viewed.
        """
        ...

    async def add(self, user_id: int, pageid: int) -> None:
        """
        Stores a pageid in the cache for a given user.

        Args:
            user_id: The user_id of the user to store the pageid for.
            pageid: The pageid to store in the cache.
        """
        ...
