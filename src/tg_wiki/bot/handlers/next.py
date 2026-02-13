import html

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, MaybeInaccessibleMessageUnion, CallbackQuery
from aiogram.fsm.context import FSMContext

from tg_wiki.clients.http import HttpClient
from tg_wiki.services.wiki_service import get_next_article
from tg_wiki.bot.utility import send_page, MAX_MESSAGE_PHOTO_LENGTH
from tg_wiki.bot.keyboards import next_keyboard
import tg_wiki.bot.messages as msg


router = Router()


async def next_handler(
    message: Message | MaybeInaccessibleMessageUnion, http: HttpClient
) -> None:
    article = await get_next_article(http)
    if not article:
        await message.answer(msg.ERR_NETWORK)
        return

    keyboard = next_keyboard()

    pageid = article["pageid"]
    full_text = f'<b><a href="{html.escape(article["fullurl"])}">{html.escape(article["title"])}</a></b>\n\n{html.escape(article["extract"])}'

    if not (
        article.get("thumbnail", None) and article["thumbnail"].get("source", None)
    ):
        await send_page(
            message, full_text, pageid=pageid, parse_mode="HTML", reply_markup=keyboard
        )
        return

    if len(full_text) > MAX_MESSAGE_PHOTO_LENGTH:
        await message.answer_photo(photo=article["thumbnail"]["source"])
        await send_page(
            message, full_text, pageid=pageid, parse_mode="HTML", reply_markup=keyboard
        )
        return

    await message.answer_photo(
        photo=article["thumbnail"]["source"],
        caption=full_text,
        parse_mode="HTML",
        reply_markup=keyboard,
    )


@router.message(Command("next"))
async def next_message_handler(
    message: Message, http: HttpClient, state: FSMContext
) -> None:
    await state.clear()
    await next_handler(message, http)


@router.callback_query(lambda c: c.data and c.data == "next")
async def next_callback_handler(
    callback: CallbackQuery, http: HttpClient, state: FSMContext
) -> None:
    await state.clear()
    if not callback.message:
        await callback.answer(msg.ERR_MESSAGE_EMPTY)
        return

    await next_handler(callback.message, http)
    await callback.answer()
