from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from tg_wiki.services.wiki_service import search_articles


router = Router()


@router.message(Command("search"))
async def search_message_handler(message: Message) -> None:
    if not message.text:
        await message.answer("Ошибка")
        return
    parts = message.text.split(maxsplit=1)
    title = parts[1] if len(parts) > 1 else ""

    results = await search_articles(title)

    if not results:
        await message.answer("Ошибка")
        return
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=result["title"],
                    callback_data=f"select:{result['pageid']}"
                )
            ]
            for result in results
        ]
    )

    await message.answer(
        "Результаты поиска:",
        reply_markup=keyboard
    )
