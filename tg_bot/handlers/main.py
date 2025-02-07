from aiogram import Dispatcher, Bot, types
from tg_bot import keyboards
from tg_bot.models import Chat, sessionmaker, engine, save_message_to_db
from tg_bot.models import create_chat
import asyncio
from tg_bot.services import get_user_chats, process_chat_summary
from tg_bot.keyboards import choose_chats, choose_period, choose_category, check_again_keyboard
from datetime import datetime, timedelta
from aiogram.utils.exceptions import MessageToDeleteNotFound, TelegramAPIError
import pytz
from typing import Optional
from tg_bot.states import SummaryState
from aiogram.dispatcher import FSMContext
import logging

logger = logging.getLogger(__name__)




async def chat_chosen_handler(callback_query: types.CallbackQuery, state: FSMContext):
    chat_id = int(callback_query.data.replace("CHAT_ID_", ""))
    await state.update_data(chat_id=chat_id)
    keyboard = choose_category()
    await callback_query.message.delete()
    await callback_query.message.answer(
        "🔹 <b>Отлично!</b> Теперь выберите категорию: 🎭🤝⏳", reply_markup=keyboard
    )
    await state.set_state(SummaryState.choosing_category)


# ---- Обработчик выбора категории ----
async def category_chosen_handler(
    callback_query: types.CallbackQuery, state: FSMContext
):
    category = callback_query.data.replace("CATEGORY_", "")
    await state.update_data(category=category)
    keyboard = choose_period()
    await callback_query.message.delete()
    await callback_query.message.answer(
        "📅 <b>Супер!</b> Теперь укажите период: 🔜📆", reply_markup=keyboard
    )
    await state.set_state(SummaryState.choosing_period)


# ---- Обработчик выбора периода ----
async def period_chosen_handler(callback_query: types.CallbackQuery, state: FSMContext):
    period_key = callback_query.data
    periods = {
        "period_tomorrow": timedelta(days=1),
        "period_week": timedelta(days=7),
        "period_month": timedelta(days=30),
    }
    user_data = await state.get_data()
    category = user_data.get("category")
    if period_key not in periods:
        await callback_query.answer(
            "<b>⚠️ Ой! Что-то не так.</b> Пожалуйста, выберите корректный период. ❌"
        )
        return
    days = period_key
    type_text = ""
    if days == "period_month":
        type_text = "Месяц"
    if days == "period_week":
        type_text = "Неделя"
    if days == "period_day":
        type_text = "День"
    type = category
    type2_text = "Всё"
    if type == "deadlines":
        type2_text = "Дедлайны"
    if type == "dosug":
        type2_text = "Досуг"
    if type == "networking":
        type2_text = "Нетворкинг"
    
    chat_id = user_data.get("chat_id")

    start_date = datetime.now(pytz.UTC) - periods[period_key]
    await callback_query.message.delete()
    await callback_query.message.answer(
        f"🔍 Чат: {chat_id}\n📂 Категория: {type2_text}\n📅 Период: {type_text}\n\nСкоро всё будет готово!"
    )
    result = await process_chat_summary(
        chat_id, callback_query.from_user.id, period_key, type, callback_query.bot
    )
    await state.finish()

async def help_adding_handler(callback: types.CallbackQuery):
    
    help_text = (
        "🛠 <b>Как добавить бота в чат:</b>\n\n"
        "1. Откройте настройки чата\n"
        "2. Выберите 'Добавить участника'\n"
        "3. Найдите @username_бота\n"
        "4. Назначьте права администратора\n"
        "5. Сохраните изменения\n\n"
        "✅ После этих действий бот появится в списке!"
    )
    keyboard = check_again_keyboard()
    await callback.message.answer(help_text, reply_markup=keyboard)
    await callback.message.delete()

def register_main_handlers(dp: Dispatcher):

    dp.register_callback_query_handler(
        chat_chosen_handler,
        lambda c: c.data.startswith("CHAT_ID_"),
        state=SummaryState.choosing_chat,
    )
    dp.register_callback_query_handler(
        category_chosen_handler,
        lambda c: c.data.startswith("CATEGORY_"),
        state=SummaryState.choosing_category,
    )
    dp.register_callback_query_handler(
        period_chosen_handler,
        lambda c: c.data.startswith("period_"),
        state=SummaryState.choosing_period,
    )
    dp.register_callback_query_handler(help_adding_handler, text="HELP_ADDING_TO_CHAT")
    dp.register_callback_query_handler(help_adding_handler, text="HELP_ADDING_TO_CHAT", state="*")
