from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


class SearchState(StatesGroup):
    waiting_for_query = State()