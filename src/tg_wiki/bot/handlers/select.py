from aiogram import Router
from aiogram.types import CallbackQuery

from tg_wiki.services.wiki_service import get_article_by_pageid
from tg_wiki.bot.utility import send_page, MAX_MESSAGE_PHOTO_LENGTH
from tg_wiki.bot.keyboards import next_keyboard


router = Router()

# Command format: select:{pageid} or select:{page_num}:{pageid}
@router.callback_query(lambda c: c.data and c.data.startswith("select:"))
async def select_callback_handler(callback: CallbackQuery) -> None:
    if not callback.data:
        await callback.answer()
        return
    
    data = callback.data.split(":")

    page_num = 1
    is_edit = False

    if len(data) == 2:
        pageid = data[1]
    elif len(data) == 3:
        page_num = int(data[1])
        pageid = data[2]
        is_edit = True
    else:
        await callback.answer("Ошибка")
        return

    article = await get_article_by_pageid(pageid)
    
    if not callback.message:
        await callback.answer("Ошибка")
        return

    if not article:
        await callback.answer("Ошибка")
        return
    
    keyboard = next_keyboard()

    pageid = article["pageid"]
    full_text = f'<b><a href="{article["fullurl"]}">{article["title"]}</a></b>\n\n{article["extract"]}'

    if is_edit or not (article.get("thumbnail", None) and article["thumbnail"].get("source", None)):
        await send_page(callback.message, full_text, pageid=pageid, page=page_num, is_edit=is_edit, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer()
        return

    if len(full_text) > MAX_MESSAGE_PHOTO_LENGTH:
        await callback.message.answer_photo(photo=article["thumbnail"]["source"])
        await send_page(callback.message, full_text, pageid=pageid, page=page_num, is_edit=is_edit, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer()
        return
    
    await callback.message.answer_photo(
        photo=article["thumbnail"]["source"],
        caption=full_text,
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()
