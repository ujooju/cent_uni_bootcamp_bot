from aiogram.types import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


def choose_chats(chats):
    markup = InlineKeyboardMarkup()
    for chat in chats:
        markup.add(
            InlineKeyboardButton(
                text=chat["title"], callback_data="CHAT_ID_" + str(chat["chat_id"])
            )
        )
    return markup


def choose_period():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="Завтра", callback_data="period_tomorrow"))
    markup.add(
        InlineKeyboardButton(text="В течение недели", callback_data="period_week")
    )
    markup.add(
        InlineKeyboardButton(text="В течение месяца", callback_data="period_month")
    )
    return markup


def choose_category():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(text="Нетворкинг", callback_data="CATEGORY_networking")
    )
    markup.add(InlineKeyboardButton(text="Досуг", callback_data="CATEGORY_dosug"))
    markup.add(
        InlineKeyboardButton(text="Дедлайны", callback_data="CATEGORY_deadlines")
    )
    return markup
