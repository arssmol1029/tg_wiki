from aiogram import Router
from aiogram.types import CallbackQuery


router = Router()


@router.callback_query(lambda c: c.data == "noop")
async def noop_handler(callback: CallbackQuery):
    await callback.answer()
