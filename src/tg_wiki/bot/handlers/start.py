from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from tg_wiki.bot.utility import ensure_user
from tg_wiki.settings_service.user_settings import UserSettingsService
import tg_wiki.bot.messages as msg


router = Router()


@router.message(CommandStart())
async def start_handler(
    message: Message, settings_service: UserSettingsService, state: FSMContext
) -> None:
    await state.clear()

    user = message.from_user
    if user is not None:
        await settings_service.ensure_telegram_user(
            user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code,
            update_user=True,
        )
    else:
        await message.answer(msg.ERR_NO_USERID)

    await message.answer(msg.MSG_WELCOME)
