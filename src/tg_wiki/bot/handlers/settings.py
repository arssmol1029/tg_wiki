from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from tg_wiki.domain.user import UserSettings
from tg_wiki.settings_service.user_settings import UserSettingsService
from tg_wiki.bot.utility import Event, get_user_id
from tg_wiki.bot.states import SettingsEditState
from tg_wiki.bot.keyboards import (
    settings_keyboard,
    bool_choice_keyboard,
    lang_choice_keyboard,
    back_to_settings_keyboard,
)
import tg_wiki.bot.messages as msg


router = Router()

app_langs = {"ru": "Русский"}
wiki_langs = {"ru": "Русский"}


def render_settings_text(settings: UserSettings) -> str:
    text = "Текущие настройки:\n"
    text += f"1. Длина страницы: {settings.page_len}\n"
    text += f"2. Получать краткое содержание статьи: {"✅ Вкл" if settings.send_text else "❌ Выкл"}\n"
    text += f"3. Получать изображение при его наличии: {"✅ Вкл" if settings.send_image else "❌ Выкл"}\n"
    text += f"4. Язык интерфейса: {app_langs.get(settings.app_lang, 'Русский')}\n"
    text += f"5. Язык википедии: {wiki_langs.get(settings.wiki_lang, 'Русский')}\n\n"
    text += "Для смены параметров воспользуйтесь кнопками ниже"
    return text


async def show_settings(event: Event, settings_service: UserSettingsService) -> None:
    message = (
        event
        if isinstance(event, Message)
        else event.message if event.message else None
    )
    if not message:
        return

    tg_user_id = get_user_id(event)
    if not tg_user_id:
        await message.answer(msg.ERR_NO_USERID)
        return

    user_id = await settings_service.ensure_telegram_user(tg_user_id)
    settings = await settings_service.get_settings(user_id)

    await message.answer(
        render_settings_text(settings),
        parse_mode="HTML",
        reply_markup=settings_keyboard(),
    )


@router.message(Command("settings"))
async def settings_handler(
    message: Message, settings_service: UserSettingsService, state: FSMContext
) -> None:
    await state.clear()
    await show_settings(message, settings_service)


@router.callback_query(F.data == "settings:back")
async def settings_back_handler(
    callback: CallbackQuery, settings_service: UserSettingsService, state: FSMContext
) -> None:
    await state.clear()
    await callback.answer()

    if isinstance(callback.message, Message):
        await show_settings(callback.message, settings_service)


@router.callback_query(F.data.startswith("settings:"))
async def settings_choose_field_handler(
    callback: CallbackQuery, state: FSMContext
) -> None:
    await state.clear()
    await callback.answer()

    if not callback.data or not callback.message:
        return

    _, field = callback.data.split(":", 1)

    if field in ("send_text", "send_image"):
        await callback.message.answer(
            "Выберите значение:",
            reply_markup=bool_choice_keyboard(field),
        )
        return

    if field in ("app_lang", "wiki_lang"):
        langs = app_langs if field == "app_lang" else wiki_langs
        await callback.message.answer(
            "Выберите язык:",
            reply_markup=lang_choice_keyboard(field, langs),
        )
        return

    if field == "page_len":
        await state.set_state(SettingsEditState.waiting_for_query)
        await state.update_data(edit_field="page_len")
        await callback.message.answer(
            "Введите новую длину страницы (целое число, например: 1024):",
            reply_markup=back_to_settings_keyboard(),
        )
        return

    await callback.message.answer(msg.ERR_UNKNOWN_PARAMETER)


@router.callback_query(F.data.startswith("settings_set_bool:"))
async def settings_set_bool_handler(
    callback: CallbackQuery, settings_service: UserSettingsService, state: FSMContext
) -> None:
    await state.clear()
    await callback.answer()
    if not callback.data or not callback.message:
        return

    _, field, raw = callback.data.split(":", 2)
    value = raw == "1"

    tg_user_id = get_user_id(callback)
    if not tg_user_id:
        await callback.answer(msg.ERR_NO_USERID)
        return

    user_id = await settings_service.ensure_telegram_user(tg_user_id)

    if field == "send_text":
        await settings_service.set_rendering(user_id, send_text=value)
    elif field == "send_image":
        await settings_service.set_rendering(user_id, send_image=value)
    else:
        await callback.message.answer(msg.ERR_UNKNOWN_PARAMETER)
        return

    await show_settings(callback, settings_service)


@router.callback_query(F.data.startswith("settings_set_lang:"))
async def settings_set_lang_handler(
    callback: CallbackQuery, settings_service: UserSettingsService, state: FSMContext
) -> None:
    await state.clear()
    await callback.answer()
    if not callback.data or not callback.message:
        return

    _, field, code = callback.data.split(":", 2)

    tg_user_id = get_user_id(callback)
    if not tg_user_id:
        await callback.answer(msg.ERR_NO_USERID)
        return

    user_id = await settings_service.ensure_telegram_user(tg_user_id)

    if field == "app_lang":
        await settings_service.set_app_lang(user_id, code)
    elif field == "wiki_lang":
        await settings_service.set_wiki_lang(user_id, code)
    else:
        await callback.message.answer(msg.ERR_UNKNOWN_PARAMETER)
        return

    await show_settings(callback, settings_service)


@router.message(SettingsEditState.waiting_for_query, F.text & ~F.text.startswith("/"))
async def settings_input_handler(
    message: Message, settings_service: UserSettingsService, state: FSMContext
) -> None:
    data = await state.get_data()
    if data.get("edit_field") != "page_len":
        await message.answer(
            "Выберите параметр кнопками ниже.", reply_markup=settings_keyboard()
        )
        return

    raw = (message.text or "").strip()
    try:
        page_len = int(raw)
    except ValueError:
        await message.answer("Ожидается целое число. Например: 1024")
        return

    tg_user_id = get_user_id(message)
    if not tg_user_id:
        await message.answer(msg.ERR_NO_USERID)
        return

    user_id = await settings_service.ensure_telegram_user(tg_user_id)

    await settings_service.set_page_len(user_id, page_len)

    await state.clear()
    await show_settings(message, settings_service)
