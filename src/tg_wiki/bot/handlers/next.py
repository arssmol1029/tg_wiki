from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("next"))
async def next_handler(message: Message) -> None:
    await message.answer(
        "Article"
    )
