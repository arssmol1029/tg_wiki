from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

import tg_wiki.bot.messages as msg


router = Router()


@router.message(Command("help"))
async def noop_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(msg.MSG_HELP)
