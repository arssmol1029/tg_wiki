from aiogram.fsm.state import State, StatesGroup


class SearchState(StatesGroup):
    waiting_for_query = State()


class SettingsEditState(StatesGroup):
    waiting_for_query = State()
