import html

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, MaybeInaccessibleMessageUnion, CallbackQuery
from aiogram.fsm.context import FSMContext

from tg_wiki.services.wiki_service import WikiService
from tg_wiki.domain.article import Article, ArticleMeta
from tg_wiki.bot.utility import send_page, MAX_MESSAGE_PHOTO_LENGTH
from tg_wiki.bot.keyboards import next_keyboard
import tg_wiki.bot.messages as msg


router = Router()


async def next_handler(
    message: Message | MaybeInaccessibleMessageUnion, wiki_service: WikiService
) -> None:
    article = await wiki_service.get_random_article()
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
    message: Message, wiki_service: WikiService, state: FSMContext
) -> None:
    await state.clear()
    await next_handler(message, wiki_service)


@router.callback_query(lambda c: c.data and c.data == "next")
async def next_callback_handler(
    callback: CallbackQuery, wiki_service: WikiService, state: FSMContext
) -> None:
    await state.clear()
    if not callback.message:
        await callback.answer(msg.ERR_MESSAGE_EMPTY)
        return

    await next_handler(callback.message, wiki_service)
    await callback.answer()
