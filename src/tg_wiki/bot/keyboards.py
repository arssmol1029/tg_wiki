from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def next_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Следующий пост", callback_data="next")]
        ]
    )
    return keyboard


def nav_keyboard(page: int, total_pages: int, pageid: int) -> InlineKeyboardMarkup:
    if page > 1:
        left_cb = f"select:{page-1}:{pageid}"
        left_text = "❮"
    else:
        left_cb = "noop"
        left_text = "✕"

    if page < total_pages:
        right_cb = f"select:{page+1}:{pageid}"
        right_text = "❯"
    else:
        right_cb = "noop"
        right_text = "✕"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=left_text, callback_data=left_cb),
            InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"),
            InlineKeyboardButton(text=right_text, callback_data=right_cb),
        ]
    ])
    return keyboard


def search_results_keyboard(results: list[dict[str, str]]) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=result["title"],
                    callback_data=f"select:{result['pageid']}"
                )
            ]
            for result in results if result.get("title", None) and result.get("pageid", None)
        ]
    )
    return keyboard
