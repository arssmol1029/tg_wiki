from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from tg_wiki.search_service.search import SearchService
from tg_wiki.settings_service.user_settings import UserSettingsService
from tg_wiki.bot.utility import Event
from tg_wiki.bot.states import SearchState
from tg_wiki.bot.keyboards import search_results_keyboard
import tg_wiki.bot.messages as msg


router = Router()


async def search_handler(
    event: Event,
    query: str,
    search_service: SearchService,
    settings_service: UserSettingsService,
) -> None:
    results = await search_service.search_articles(query)

    message = (
        event
        if isinstance(event, Message)
        else event.message if event.message else None
    )
    if not message:
        return

    if not results:
        await message.answer(msg.ERR_NOT_FOUND)
        return

    keyboard = search_results_keyboard(results)

    await message.answer(msg.MSG_SEARCH_RESULTS, reply_markup=keyboard)


@router.message(Command("search"))
async def search_message_handler(
    message: Message,
    search_service: SearchService,
    settings_service: UserSettingsService,
    state: FSMContext,
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
        await search_handler(message, query, search_service, settings_service)


@router.message(SearchState.waiting_for_query)
async def process_search_query(
    message: Message,
    search_service: SearchService,
    settings_service: UserSettingsService,
    state: FSMContext,
) -> None:
    await state.clear()
    if not message.text or not message.text.strip():
        await message.answer(msg.ERR_BAD_INPUT)
        return
    query = message.text.strip()

    await search_handler(message, query, search_service, settings_service)
