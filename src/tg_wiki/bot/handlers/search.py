from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, MaybeInaccessibleMessageUnion
from aiogram.fsm.context import FSMContext

from tg_wiki.clients.http import HttpClient
from tg_wiki.services.wiki_service import search_articles
from tg_wiki.bot.states import SearchState
from tg_wiki.bot.keyboards import search_results_keyboard
import tg_wiki.bot.messages as msg


router = Router()


async def search_handler(
    message: Message | MaybeInaccessibleMessageUnion, query: str, http: HttpClient
) -> None:
    results = await search_articles(http, query)

    if not results:
        await message.answer(msg.ERR_NOT_FOUND)
        return

    keyboard = search_results_keyboard(results)

    await message.answer(msg.MSG_SEARCH_RESULTS, reply_markup=keyboard)


@router.message(Command("search"))
async def search_message_handler(
    message: Message, http: HttpClient, state: FSMContext
) -> None:
    await state.clear()
    if not message.text:
        await message.answer(msg.ERR_BAD_INPUT)
        return
    parts = message.text.split(maxsplit=1)
    query = parts[1] if len(parts) > 1 else ""

    if not query:
        if message.quote and message.quote.text:
            query = message.quote.text.strip()
        elif message.reply_to_message and message.reply_to_message.text:
            query = message.reply_to_message.text.strip()
        else:
            await message.answer(msg.MSG_ENTER_QUERY)
            await state.set_state(SearchState.waiting_for_query)
    else:
        await search_handler(message, query, http)


@router.message(SearchState.waiting_for_query)
async def process_search_query(
    message: Message, http: HttpClient, state: FSMContext
) -> None:
    if not message.text or not message.text.strip():
        await message.answer(msg.ERR_BAD_INPUT)
        return
    query = message.text.strip()

    await search_handler(message, query, http)
    await state.clear()
