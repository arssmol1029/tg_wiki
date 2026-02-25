from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from tg_wiki.search_service.search import SearchService
from tg_wiki.settings_service.user_settings import UserSettingsService
from tg_wiki.bot.handlers.search import search_handler
import tg_wiki.bot.messages as msg


router = Router()


@router.message(F.text & ~F.text.startswith("/"))
async def default_handler(
    message: Message,
    search_service: SearchService,
    settings_service: UserSettingsService,
    state: FSMContext,
) -> None:
    if message.quote and message.quote.text:
        await state.clear()
        query = message.quote.text.strip()
    elif message.text and message.text.strip():
        await state.clear()
        query = message.text.strip()
    else:
        return

    await search_handler(message, query, search_service, settings_service)


@router.message(F.text & F.text.startswith("/"))
async def unknown_command_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(msg.ERR_UNKNOWN_COMMAND)
