from dataclasses import dataclass
from typing import Optional, Sequence, Union


PreferenceVector = Sequence[float]
ExternalId = Union[str, int]


@dataclass(frozen=True, slots=True)
class ExternalIdentity:
    provider: str
    external_id: ExternalId

    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = None

    def external_id_str(self) -> str:
        return str(self.external_id)


@dataclass(frozen=True, slots=True)
class UserSettings:
    page_len: int = 1024
    send_text: bool = True
    send_image: bool = True

    app_lang: str = "ru"
    wiki_lang: str = "ru"


__all__ = ["PreferenceVector", "ExternalIdentity", "UserSettings"]
