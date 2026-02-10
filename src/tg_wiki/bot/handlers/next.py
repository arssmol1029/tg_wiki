from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, MaybeInaccessibleMessageUnion, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from tg_wiki.services.wiki_service import get_next_article
from tg_wiki.bot.utility import send_page, MAX_MESSAGE_PHOTO_LENGTH


router = Router()


async def next_handler(message: Message | MaybeInaccessibleMessageUnion) -> None:
    article = await get_next_article()
    if not article:
        await message.answer("Ошибка")
        return
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Следующий пост", callback_data="next")]
        ]
    )

    pageid = article["pageid"]
    full_text = f'<b><a href="{article["fullurl"]}">{article["title"]}</a></b>\n\n{article["extract"]}'

    if not (article.get("thumbnail", None) and article["thumbnail"].get("source", None)):
        await send_page(message, full_text, pageid=pageid, parse_mode="HTML", reply_markup=keyboard)
        return

    if len(full_text) > MAX_MESSAGE_PHOTO_LENGTH:
        await message.answer_photo(photo=article["thumbnail"]["source"])
        await send_page(message, full_text, pageid=pageid, parse_mode="HTML", reply_markup=keyboard)
        return
    
    await message.answer_photo(
        photo=article["thumbnail"]["source"],
        caption=full_text,
        parse_mode="HTML",
        reply_markup=keyboard
    )


@router.message(Command("next"))
async def next_massage_handler(message: Message) -> None:
    await next_handler(message)


@router.callback_query(lambda c: c.data and c.data == "next")
async def next_callback_handler(callback: CallbackQuery):
    if not callback.message:
        await callback.answer("Ошибка")
        return

    await next_handler(callback.message)
    await callback.answer()
