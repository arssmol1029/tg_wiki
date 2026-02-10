from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from tg_wiki.services.wiki_service import get_next_article


router = Router()


@router.message(Command("next"))
async def next_massage_handler(message: Message) -> None:
    article = await get_next_article()
    if not article:
        await message.answer("Ошибка")
        return
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="next", callback_data="next")]
        ]
    )

    if article.get("thumbnail", None) and article["thumbnail"].get("source", None):
        await message.answer_photo(
            photo=article["thumbnail"]["source"],
            caption=f'<b><a href="{article["fullurl"]}">{article["title"]}</a></b>\n\n{article["extract"]}',
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return

    await message.answer(
        f'<b><a href="{article["fullurl"]}">{article["title"]}</a></b>\n\n{article["extract"]}',
        parse_mode="HTML",
        reply_markup=keyboard
    )
