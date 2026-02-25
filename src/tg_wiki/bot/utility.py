from aiogram.types import (
    Message,
    CallbackQuery,
    MaybeInaccessibleMessageUnion,
    InlineKeyboardMarkup,
)
from typing import Optional, Union

from tg_wiki.settings_service.user_settings import UserSettingsService
from tg_wiki.bot.keyboards import nav_keyboard
import tg_wiki.bot.messages as msg


MAX_MESSAGE_LENGTH = 1024
MAX_MESSAGE_PHOTO_LENGTH = 1024


Event = Union[Message, CallbackQuery]


def get_user_id(event: Event) -> Optional[int]:
    return event.from_user.id if event.from_user else None


async def ensure_user(
    event: Event, settings_service: UserSettingsService
) -> Optional[int]:
    user = event.from_user
    if not user:
        return None

    return await settings_service.ensure_telegram_user(
        user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code,
        update_user=True,
    )


def split_text_pages(text: str, page_len: int = MAX_MESSAGE_LENGTH) -> list[str]:
    chunks: list[str] = []
    remaining = text

    while len(remaining) > page_len:
        part = remaining[:page_len]

        last_space = part.rfind(" ")
        if last_space > 0:
            part = part[:last_space]

        chunks.append(part)
        remaining = remaining[len(part) :].lstrip()

    if remaining:
        chunks.append(remaining)

    return chunks


async def send_page(
    message: Message | MaybeInaccessibleMessageUnion,
    text: str,
    pageid: int,
    *,
    page: int = 1,
    is_edit: bool = False,
    parse_mode: str = "HTML",
    reply_markup: InlineKeyboardMarkup | None = None,
    page_len: int = MAX_MESSAGE_LENGTH,
) -> None:
    chunks = split_text_pages(text, page_len)
    total_pages = len(chunks)

    if page < 1 or page > total_pages:
        await message.answer(msg.ERR_BUTTON_STALE)
        return

    if not chunks:
        await message.answer(msg.ERR_NOT_FOUND)
        return

    if total_pages == 1:
        if is_edit and isinstance(message, Message):
            await message.edit_text(
                chunks[page - 1], parse_mode=parse_mode, reply_markup=reply_markup
            )
        else:
            await message.answer(
                chunks[page - 1], parse_mode=parse_mode, reply_markup=reply_markup
            )
        return

    keyboard = nav_keyboard(page, total_pages, pageid, page_len)

    if reply_markup:
        keyboard.inline_keyboard.extend(reply_markup.inline_keyboard)

    if is_edit and isinstance(message, Message):
        await message.edit_text(
            chunks[page - 1], parse_mode=parse_mode, reply_markup=keyboard
        )
    else:
        await message.answer(
            chunks[page - 1], parse_mode=parse_mode, reply_markup=keyboard
        )
