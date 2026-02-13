from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from tg_wiki.services.wiki_service import WikiService
from tg_wiki.bot.handlers.search import search_handler
import tg_wiki.bot.messages as msg

router = Router()


@router.message()
async def default_handler(
    message: Message, wiki_service: WikiService, state: FSMContext
) -> None:
    if message.quote and message.quote.text:
        await state.clear()
        query = message.quote.text.strip()
    elif message.text and message.text.strip():
        await state.clear()
        query = message.text.strip()
    else:
        return

    await search_handler(message, query, wiki_service)
