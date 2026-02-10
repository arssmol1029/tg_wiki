from aiogram.types import Message, MaybeInaccessibleMessageUnion, InlineKeyboardMarkup

from tg_wiki.bot.keyboards import nav_keyboard


MAX_MESSAGE_LENGTH = 1024
MAX_MESSAGE_PHOTO_LENGTH = 1024


def split_text_pages(text: str, max_len: int = MAX_MESSAGE_LENGTH) -> list[str]:
    chunks: list[str] = []
    remaining = text

    while len(remaining) > max_len:
        part = remaining[:max_len]

        last_space = part.rfind(" ")
        if last_space > 0:
            part = part[:last_space]

        chunks.append(part)
        remaining = remaining[len(part):].lstrip()

    if remaining:
        chunks.append(remaining)

    return chunks


async def send_page(
    message: Message | MaybeInaccessibleMessageUnion,
    text: str, pageid: int,
    page: int = 1,
    is_edit: bool = False,
    parse_mode: str = "HTML",
    reply_markup: InlineKeyboardMarkup | None = None,
    max_len: int = MAX_MESSAGE_LENGTH
) -> None:
    chunks = split_text_pages(text, max_len)
    total_pages = len(chunks)

    if page < 1 or page > total_pages:
        await message.answer("Ошибка")
        return
    
    if not chunks:
        await message.answer("Ошибка")
        return

    if total_pages == 1:
        if is_edit and isinstance(message, Message):
            await message.edit_text(chunks[page-1], parse_mode=parse_mode, reply_markup=reply_markup)
        else:
            await message.answer(chunks[page-1], parse_mode=parse_mode, reply_markup=reply_markup)
        return

    keyboard = nav_keyboard(page, total_pages, pageid)

    if reply_markup:
        keyboard.inline_keyboard.extend(reply_markup.inline_keyboard)

    if is_edit and isinstance(message, Message):
        await message.edit_text(chunks[page-1], parse_mode=parse_mode, reply_markup=keyboard)
    else:
        await message.answer(chunks[page-1], parse_mode=parse_mode, reply_markup=keyboard)
