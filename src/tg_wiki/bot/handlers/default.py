from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from tg_wiki.services.wiki_service import search_articles

router = Router()


@router.message()
async def default_handler(message: Message) -> None:
    if message.quote and message.quote.text:
        query = message.quote.text.strip()
    else:
        return
    
    print(f"Default handler: {query}")
    
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