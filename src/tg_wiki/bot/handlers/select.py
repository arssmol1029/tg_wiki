import html

from aiogram import Router
from aiogram.types import CallbackQuery

from tg_wiki.provider.search import SearchProvide
from tg_wiki.bot.utility import get_user_id, send_page, MAX_MESSAGE_PHOTO_LENGTH
from tg_wiki.bot.keyboards import next_keyboard
import tg_wiki.bot.messages as msg


router = Router()


# Command format: select:{pageid} or select:{page_num}:{pageid}
@router.callback_query(lambda c: c.data and c.data.startswith("select:"))
async def select_callback_handler(
    callback: CallbackQuery, search: SearchProvide
) -> None:
    if not callback.data:
        await callback.answer()
        return

    user_id = get_user_id(callback)
    if not user_id:
        await callback.answer(msg.ERR_NO_USERID)
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
        await callback.answer(msg.ERR_BAD_INPUT)
        return

    article = await search.get_arcticle_by_pageid(int(pageid), user_id)

    if not callback.message:
        await callback.answer(msg.ERR_MESSAGE_EMPTY)
        return

    if not article:
        await callback.answer(msg.ERR_NOT_FOUND)
        return

    keyboard = next_keyboard()

    pageid = article.meta.pageid
    full_text = (
        f'<b><a href="{html.escape(article.meta.url)}">{html.escape(article.meta.title)}</a></b>'
        + f"\n\n{html.escape(article.extract)}"
        if article.extract
        else ""
    )

    if is_edit or not (article.meta.thumbnail_url):
        await send_page(
            callback.message,
            full_text,
            pageid=pageid,
            page=page_num,
            is_edit=is_edit,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        await callback.answer()
        return

    if len(full_text) > MAX_MESSAGE_PHOTO_LENGTH:
        await callback.message.answer_photo(photo=article.meta.thumbnail_url)
        await send_page(
            callback.message,
            full_text,
            pageid=pageid,
            page=page_num,
            is_edit=is_edit,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        await callback.answer()
        return

    await callback.message.answer_photo(
        photo=article.meta.thumbnail_url,
        caption=full_text,
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await callback.answer()
