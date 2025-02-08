from aiogram.dispatcher.filters.state import State, StatesGroup


class SummaryState(StatesGroup):
    choosing_chats = State()
    choosing_chat = State()
    choosing_period = State()
    summarizing = State()
    choosing_category = State()
    get_query = State()
