"""Database package.

The current codebase runs without a database. The modules in this package are a
foundation for adding a persistent user database (PostgreSQL is the intended
backend).

Nothing in the existing runtime imports this package yet.

Where to hook it later (high-level):
  1) In `tg_wiki/main.py`: create a DB pool/engine and a `UserRepository`.
  2) Put it into `dp.workflow_data["users"]` (similar to `reco`/`search`).
  3) Add an aiogram middleware that:
       - upserts the user on every update
       - loads `UserSettings`
       - injects settings into handler data
"""

from .config import DBConfig
from .ports import PreferenceVector, ExternalIdentity, UserRepository, UserSettings

__all__ = [
    "DBConfig",
    "PreferenceVector",
    "ExternalIdentity",
    "UserRepository",
    "UserSettings",
]
