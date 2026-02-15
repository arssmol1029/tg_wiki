import html

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, MaybeInaccessibleMessageUnion, CallbackQuery
from aiogram.fsm.context import FSMContext

from tg_wiki.provider.reco import RecoProvide
from tg_wiki.bot.utility import get_user_id, send_page, MAX_MESSAGE_PHOTO_LENGTH
from tg_wiki.bot.keyboards import next_keyboard
import tg_wiki.bot.messages as msg


router = Router()


async def next_handler(
    message: Message | MaybeInaccessibleMessageUnion, user_id: int, reco: RecoProvide
) -> None:
    article = await reco.get_next_arcticle(user_id)
    if not article:
        await message.answer(msg.ERR_NETWORK)
        return

    keyboard = next_keyboard()

    pageid = article.meta.pageid
    full_text = (
        f'<b><a href="{html.escape(article.meta.url)}">{html.escape(article.meta.title)}</a></b>'
        + f"\n\n{html.escape(article.extract)}"
        if article.extract
        else ""
    )

    if not (article.meta.thumbnail_url):
        await send_page(
            message, full_text, pageid=pageid, parse_mode="HTML", reply_markup=keyboard
        )
        return

    if len(full_text) > MAX_MESSAGE_PHOTO_LENGTH:
        await message.answer_photo(photo=article.meta.thumbnail_url)
        await send_page(
            message, full_text, pageid=pageid, parse_mode="HTML", reply_markup=keyboard
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
    message: Message, reco: RecoProvide, state: FSMContext
) -> None:
    await state.clear()

    user_id = get_user_id(message)
    if not user_id:
        await message.answer(msg.ERR_NO_USERID)
        return

    await next_handler(message, user_id, reco)


@router.callback_query(lambda c: c.data and c.data == "next")
async def next_callback_handler(
    callback: CallbackQuery, reco: RecoProvide, state: FSMContext
) -> None:
    await state.clear()
    if not callback.message:
        await callback.answer()
        return

    user_id = get_user_id(callback)
    if not user_id:
        await callback.answer(msg.ERR_NO_USERID)
        return

    await next_handler(callback.message, user_id, reco)
    await callback.answer()
