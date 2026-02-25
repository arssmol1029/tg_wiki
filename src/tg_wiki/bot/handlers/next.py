import html
import asyncio

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from tg_wiki.reco_service.reco import RecoService
from tg_wiki.settings_service.user_settings import UserSettingsService
from tg_wiki.bot.utility import Event, get_user_id, send_page, MAX_MESSAGE_PHOTO_LENGTH
from tg_wiki.bot.keyboards import next_keyboard
import tg_wiki.bot.messages as msg


router = Router()


async def next_handler(
    event: Event,
    user_id: int,
    reco_service: RecoService,
    settings_service: UserSettingsService,
) -> None:
    tg_user_id = get_user_id(event)

    message = (
        event
        if isinstance(event, Message)
        else event.message if event.message else None
    )
    if not message:
        return

    if not tg_user_id:
        await message.answer(msg.ERR_NO_USERID)
        return

    user_id = await settings_service.ensure_telegram_user(tg_user_id)

    settings, article = await asyncio.gather(
        settings_service.get_settings(user_id),
        reco_service.get_next_article(user_id),
    )

    article = await reco_service.get_next_article(user_id)
    if not article:
        await message.answer(msg.ERR_NETWORK)
        return

    keyboard = next_keyboard()

    pageid = article.meta.pageid

    full_text = f'<b><a href="{html.escape(article.meta.url)}">{html.escape(article.meta.title)}</a></b>'

    if article.extract and settings.send_text:
        full_text += f"\n\n{html.escape(article.extract)}"

    page_len = settings.page_len

    if not article.meta.thumbnail_url or not settings.send_image:
        await send_page(
            message,
            full_text,
            pageid=pageid,
            page_len=page_len,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        return

    if len(full_text) > page_len:
        await message.answer_photo(photo=article.meta.thumbnail_url)
        await send_page(
            message,
            full_text,
            pageid=pageid,
            page_len=page_len,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        return

    await message.answer_photo(
        photo=article.meta.thumbnail_url,
        caption=full_text,
        parse_mode="HTML",
        reply_markup=keyboard,
    )


@router.message(Command("next"))
async def next_message_handler(
    message: Message,
    reco_service: RecoService,
    settings_service: UserSettingsService,
    state: FSMContext,
) -> None:
    await state.clear()

    user_id = get_user_id(message)
    if not user_id:
        await message.answer(msg.ERR_NO_USERID)
        return

    await next_handler(message, user_id, reco_service, settings_service)


@router.callback_query(F.data == "next")
async def next_callback_handler(
    callback: CallbackQuery,
    reco_service: RecoService,
    settings_service: UserSettingsService,
    state: FSMContext,
) -> None:
    await state.clear()
    if not callback.message:
        await callback.answer()
        return

    user_id = get_user_id(callback)
    if not user_id:
        await callback.answer(msg.ERR_NO_USERID)
        return

    await next_handler(callback, user_id, reco_service, settings_service)
    await callback.answer()
