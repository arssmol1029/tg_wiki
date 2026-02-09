import re

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from tg_wiki.services.wiki_service import get_article_by_pageid
from tg_wiki.services.wiki_service import search_articles


router = Router()


@router.message(Command("search"))
async def search_handler(message: Message) -> None:
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
                    callback_data=f"wiki:{result['pageid']}"
                )
            ]
            for result in results
        ]
    )

    await message.answer(
        "Результаты поиска:",
        reply_markup=keyboard
    )


@router.callback_query(lambda c: c.data and c.data.startswith("wiki:"))
async def wiki_select(callback: CallbackQuery):
    if not callback.data:
        await callback.answer()
        return
    
    pageid = callback.data.removeprefix("wiki:")

    article = await get_article_by_pageid(pageid)
    
    if not callback.message:
        await callback.answer("Ошибка")
        return

    if not article:
        await callback.answer("Ошибка")
        return

    await callback.message.answer(
        f"{article['title']}\n\n{article['extract']}"
    )

    await callback.answer()
