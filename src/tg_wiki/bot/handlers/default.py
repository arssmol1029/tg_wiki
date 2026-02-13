from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from tg_wiki.clients.http import HttpClient
from tg_wiki.bot.handlers.search import search_handler

router = Router()


@router.message()
async def default_handler(
    message: Message, http: HttpClient, state: FSMContext
) -> None:
    if message.quote and message.quote.text:
        await state.clear()
        query = message.quote.text.strip()
    else:
        return

    await search_handler(message, query, http)
