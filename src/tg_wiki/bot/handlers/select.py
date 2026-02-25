import html

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from tg_wiki.search_service.search import SearchService
from tg_wiki.settings_service.user_settings import UserSettingsService
from tg_wiki.bot.utility import get_user_id, send_page
from tg_wiki.bot.keyboards import next_keyboard
import tg_wiki.bot.messages as msg


router = Router()


# Command format: select:{pageid} or select:{page_num}:{pageid} or select:{page_num}:{page_len}:{pageid}
@router.callback_query(F.data.startswith("select:"))
async def select_callback_handler(
    callback: CallbackQuery,
    search_service: SearchService,
    settings_service: UserSettingsService,
    state: FSMContext,
) -> None:
    await state.clear()
    if not callback.data:
        await callback.answer()
        return

    data = callback.data.split(":")

    tg_user_id = get_user_id(callback)
    if not tg_user_id:
        await callback.answer(msg.ERR_NO_USERID)
        return
    user_id = await settings_service.ensure_telegram_user(tg_user_id)
    settings = await settings_service.get_settings(user_id)

    page_num = 1
    page_len = settings.page_len
    is_edit = False

    if len(data) == 2:
        pageid = int(data[1])
    elif len(data) == 3:
        page_num = int(data[1])
        pageid = int(data[2])
    elif len(data) == 4:
        page_num = int(data[1])
        page_len = int(data[2])
        pageid = int(data[3])
        is_edit = True
    else:
        await callback.answer(msg.ERR_BAD_INPUT)
        return

    article = await search_service.get_arcticle_by_pageid(pageid, user_id)

    if not callback.message:
        await callback.answer(msg.ERR_MESSAGE_EMPTY)
        return

    if not article:
        await callback.answer(msg.ERR_NOT_FOUND)
        return

    keyboard = next_keyboard()

    full_text = f'<b><a href="{html.escape(article.meta.url)}">{html.escape(article.meta.title)}</a></b>'

    full_text += (
        f"\n\n{html.escape(article.extract)}"
        if article.extract and (is_edit or settings.send_text)
        else ""
    )

    if is_edit or not (article.meta.thumbnail_url) or not settings.send_image:
        await send_page(
            callback.message,
            full_text,
            pageid=pageid,
            page=page_num,
            page_len=page_len,
            is_edit=is_edit,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        await callback.answer()
        return

    if len(full_text) > page_len:
        await callback.message.answer_photo(photo=article.meta.thumbnail_url)
        await send_page(
            callback.message,
            full_text,
            pageid=pageid,
            page=page_num,
            page_len=page_len,
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
