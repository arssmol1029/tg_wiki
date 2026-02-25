from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from tg_wiki.domain.article import ArticleMeta


def next_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Следующий пост", callback_data="next")]
        ]
    )


def nav_keyboard(
    page: int, total_pages: int, pageid: int, page_len: int
) -> InlineKeyboardMarkup:
    if page > 1:
        left_cb = f"select:{page-1}:{page_len}:{pageid}"
        left_text = "❮"
    else:
        left_cb = "noop"
        left_text = "✕"

    if page < total_pages:
        right_cb = f"select:{page+1}:{page_len}:{pageid}"
        right_text = "❯"
    else:
        right_cb = "noop"
        right_text = "✕"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=left_text, callback_data=left_cb),
                InlineKeyboardButton(
                    text=f"{page}/{total_pages}", callback_data="noop"
                ),
                InlineKeyboardButton(text=right_text, callback_data=right_cb),
            ]
        ]
    )


def search_results_keyboard(results: list[ArticleMeta]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=result.title, callback_data=f"select:{result.pageid}"
                )
            ]
            for result in results
            if result.title and result.pageid
        ]
    )


def settings_keyboard() -> InlineKeyboardMarkup:
    settings = [
        ("Длина страницы", "page_len"),
        ("Получать краткое содержание", "send_text"),
        ("Получать изображение", "send_image"),
        ("Язык интерфейса", "app_lang"),
        ("Язык википедии", "wiki_lang"),
    ]

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, callback_data=f"settings:{field}")]
            for text, field in settings
        ]
    )


def back_to_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings:back")]
        ]
    )


def bool_choice_keyboard(field: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Вкл", callback_data=f"settings_set_bool:{field}:1"
                ),
                InlineKeyboardButton(
                    text="❌ Выкл", callback_data=f"settings_set_bool:{field}:0"
                ),
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings:back")],
        ]
    )


def lang_choice_keyboard(field: str, langs: dict[str, str]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=name, callback_data=f"settings_set_lang:{field}:{code}"
            )
        ]
        for code, name in langs.items()
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="settings:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
