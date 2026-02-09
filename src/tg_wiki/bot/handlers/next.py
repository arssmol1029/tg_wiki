from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from tg_wiki.services.wiki_service import get_next_article


router = Router()


@router.message(Command("next"))
async def next_handler(message: Message) -> None:
    article = await get_next_article()
    if not article:
        await message.answer(
            "No valid article found. Please try again."
        )
        return
    await message.answer(
        f"{article['title']}\n\n{article['extract']}"
    )
