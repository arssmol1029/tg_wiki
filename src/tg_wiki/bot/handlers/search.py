import re

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from tg_wiki.services.wiki_service import get_article_by_pageid
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


@router.callback_query(lambda c: c.data and c.data.startswith("select:"))
async def select_callback_handler(callback: CallbackQuery):
    if not callback.data:
        await callback.answer()
        return
    
    pageid = callback.data.removeprefix("select:")

    article = await get_article_by_pageid(pageid)
    
    if not callback.message:
        await callback.answer("Ошибка")
        return

    if not article:
        await callback.answer("Ошибка")
        return
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="next", callback_data="next")]
        ]
    )

    if article.get("thumbnail", None) and article["thumbnail"].get("source", None):
        await callback.message.answer_photo(
            photo=article["thumbnail"]["source"],
            caption=f'<b><a href="{article["fullurl"]}">{article["title"]}</a></b>\n\n{article["extract"]}',
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return

    await callback.message.answer(
        f'<b><a href="{article["fullurl"]}">{article["title"]}</a></b>\n\n{article["extract"]}',
        parse_mode="HTML",
        reply_markup=keyboard
    )

    await callback.answer()
