from email import message, message_from_binary_file
from hmac import new
from re import S
from aiogram import Dispatcher, Bot, types
from tg_bot.models import Chat, sessionmaker, engine, save_message_to_db
from tg_bot.services import get_user_chats, process_chat_summary
from tg_bot.keyboards import choose_chats, choose_period, choose_category
from datetime import datetime, timedelta
import pytz
from tg_bot.states import SummaryState
from aiogram.dispatcher import FSMContext


async def add_handler(message: types.Message):
    bot_obj = await message.bot.get_me()
    bot_id = bot_obj.id

    for chat_member in message.new_chat_members:
        if chat_member.id == bot_id:
            chat_id = message.chat.id
            Session = sessionmaker()
            session = Session(bind=engine)
            chat = session.query(Chat).filter(Chat.id == chat_id).all()
            if chat == []:
                try:
                    new_chat = Chat(chat_id=chat_id)
                    try:
                        await message.delete()
                    except:
                        pass
                    await message.answer(
                        "Приветствую вас! 😊 Спасибо, что добавили меня в этот канал! Я очень рад быть здесь!\n\nЧто я могу для вас сделать? 🤔\n\nСоставить краткий и структурированный пересказ данных за любой период.\nНапомнить о ближайших дедлайнах ⏰.\nПодсказать, чем можно заняться в течение следующего месяца 📅.\nРассказать о волонтерских движениях и мероприятиях, которые стоит учесть 🤝.\nЕсли вам нужно что-то из этого — просто обратитесь! 😊"
                    )
                    session.add(new_chat)
                    session.commit()
                except Exception as e:
                    print(e)
            session.close()


async def start_handler(message: types.Message):
    if message.chat.id < 0:
        return
    chats = await get_user_chats(target_user_id=message.from_user.id, bot=message.bot)
    print(chats, " - CHATS")
    if chats != []:
        keyboard = choose_chats(chats)
        await message.answer("Выберите чат:", reply_markup=keyboard)
    else:
        await message.answer(
            "Вы не добавили меня ни в один чат. 😕\n\nИли я не могу читать сообщения  😕 Назначьте меня пожалуйтста админом группы! Тогда я смогу читать все сообщения и делать краткую выжимку)"
        )
        
    await SummaryState.choosing_chat.set()


# Обработчик для сохранения сообщений в базу данных
async def save_message_handler(message: types.Message):
    if message.chat.id < 0:
        try:
            print(message.as_json())
            save_message_to_db(message.chat.id, message.from_user.id, message.text, f"https://t.me/{message.chat.username}/{message.message_id}")
            print("SAVE MESSAGE", message.chat.id, message.from_user.id, message.text, f"https://t.me/{message.chat.username}/{message.message_id}")
        except:
            print(message.as_json())
            save_message_to_db(message.chat.id, message.from_user.id, message.text)
            print("SAVE MESSAGE", message.chat.id, message.from_user.id, message.text)
        return
    chats = await get_user_chats(target_user_id=message.from_user.id, bot=message.bot)
    print(chats, " - CHATS")
    if chats != []:
        keyboard = choose_chats(chats)
        await message.answer("Выберите чат:", reply_markup=keyboard)
    else:

        await message.answer("У вас не хватает прав доступа :( , ничё поделать не могу)")
        # await message.answer(
        #     "Вы не добавили меня ни в один чат, или я не могу читать сообщения😕\nНазначьте меня пожалуйтста админом группы! Тогда я смогу читать все сообщения и делать краткую выжимку)"
        # )
        
    # await SummaryState.choosing_chat.set()


async def get_messages(chat_id, start_date, bot: Bot):
    messages = []
    async for message in bot.get_chat_history(chat_id, limit=1000):
        if message.date >= start_date:
            messages.append(message.text)
        else:
            break
    return messages


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


def register_main_handlers(dp: Dispatcher):
    dp.register_message_handler(
        save_message_handler, content_types=types.ContentType.TEXT
    )
    dp.register_message_handler(add_handler, content_types=["new_chat_members"])
    dp.register_message_handler(start_handler, commands=["start"])
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
