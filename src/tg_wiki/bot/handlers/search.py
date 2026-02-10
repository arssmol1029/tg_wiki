from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, MaybeInaccessibleMessageUnion
from aiogram.fsm.context import FSMContext

from tg_wiki.services.wiki_service import search_articles
from tg_wiki.bot.states import SearchState


router = Router()


async def search_handler(message: Message | MaybeInaccessibleMessageUnion, query: str) -> None:
    results = await search_articles(query)

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


@router.message(Command("search"))
async def search_message_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    if not message.text:
        await message.answer("Ошибка")
        return
    parts = message.text.split(maxsplit=1)
    query = parts[1] if len(parts) > 1 else ""

    if not query:
        if message.quote and message.quote.text:
            query = message.quote.text.strip()
        elif message.reply_to_message and message.reply_to_message.text:
            query = message.reply_to_message.text.strip()
        else:
            await message.answer("Введите запрос для поиска")
            await state.set_state(SearchState.waiting_for_query)
    else:
        await search_handler(message, query)


@router.message(SearchState.waiting_for_query)
async def process_search_query(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.strip():
        await message.answer("Ошибка")
        return
    query = message.text.strip()

    await search_handler(message, query)
    await state.clear()
