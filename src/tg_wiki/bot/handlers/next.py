from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from tg_wiki.services.wiki_service import get_next_article


router = Router()


@router.message(Command("next"))
async def next_handler(message: Message) -> None:
    article = await get_next_article()
    if not article:
        await message.answer("Ошибка")
        return
    
    if article.get("thumbnail", None) and article["thumbnail"].get("source", None):
        await message.answer_photo(
            photo=article["thumbnail"]["source"],
            caption=f'<b><a href="{article["fullurl"]}">{article["title"]}</a></b>\n\n{article["extract"]}',
            parse_mode="HTML"
        )
        return

    await message.answer(
        f'<b><a href="{article["fullurl"]}">{article["title"]}</a></b>\n\n{article["extract"]}',
        parse_mode="HTML"
    )
