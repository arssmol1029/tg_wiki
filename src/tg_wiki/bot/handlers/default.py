from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from tg_wiki.services.wiki_service import search_articles
from tg_wiki.bot.handlers.search import search_handler

router = Router()


@router.message()
async def default_handler(message: Message) -> None:
    if message.quote and message.quote.text:
        query = message.quote.text.strip()
    else:
        return
    
    print(f"Default handler: {query}")
    
    await search_handler(message, query)
