from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from tg_wiki.services.wiki_service import search_articles
from tg_wiki.bot.handlers.search import search_handler
from tg_wiki.bot.states import SearchState

router = Router()


@router.message(Command("cancel"))
async def default_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отмена")
