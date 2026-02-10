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
    query = parts[1] if len(parts) > 1 else ""

    if not query:
        if message.quote and message.quote.text:
            query = message.quote.text.strip()
        elif message.reply_to_message and message.reply_to_message.text:
            query = message.reply_to_message.text.strip()
        else:
            await message.answer("Ошибка")
            return

    results = await search_articles(query)

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