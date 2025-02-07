from datetime import datetime, timedelta
import pytz
from aiogram import Bot
from aiogram.types import Message

async def get_messages(chat_id, period, bot: Bot):

    now = datetime.now(pytz.UTC)
    if period == "Завтра":
        start_date = now + timedelta(days=1)
    elif period == "В течение недели":
        start_date = now - timedelta(weeks=1)
    elif period == "В течение месяца":
        start_date = now - timedelta(days=30)
    else:
        return []

    messages = []
    async for message in bot.get_chat_history(chat_id, limit=10000):  
        if message.date >= start_date:
            messages.append(message)
        else:
            break

    return messages
