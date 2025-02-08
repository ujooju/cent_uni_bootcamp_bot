from pydoc import text
import stat
from aiogram import types, Dispatcher
from tg_bot.models import save_message_to_db
from tg_bot.models import create_chat
import asyncio
from tg_bot.services import get_user_chats
from tg_bot.keyboards import choose_chats, get_help_markup, choose_category, generate_chats_keyboard
from datetime import datetime, timedelta
from aiogram.utils.exceptions import MessageToDeleteNotFound, TelegramAPIError
from typing import Optional
from aiogram.dispatcher import FSMContext
from tg_bot.states import SummaryState
import logging

logger = logging.getLogger(__name__)


async def add_handler(message: types.Message):
    bot = message.bot
    bot_id = (await bot.get_me()).id
    new_members = message.new_chat_members
    
    welcome_text = (
        "Приветствую вас! 😊 Спасибо, что добавили меня в этот канал! "
        "Я очень рад быть здесь!\n\nЧто я могу для вас сделать? 🤔\n\n"
        "- Составить краткий и структурированный пересказ данных за любой период\n"
        "- Напомнить о ближайших дедлайнах ⏰\n"
        "- Подсказать, чем можно заняться в течение следующего месяца 📅\n"
        "- Рассказать о волонтерских движениях и мероприятиях 🤝\n\n"
        "Просто обратитесь - и я помогу!"
    )
    if any(member.id == bot_id for member in new_members):
        chat_id = message.chat.id
        
        try:
            if create_chat(chat_id):
                await asyncio.gather(
                    message.answer(welcome_text)
                )
            else:
                logger.info(f"Бот повторно добавлен в чат {chat_id}")
        except MessageToDeleteNotFound:
            logger.warning(f"Сообщение уже удалено в чате {chat_id}")
        except TelegramAPIError as e:
            logger.error(f"Ошибка Telegram API в чате {chat_id}: {e}")
        except Exception as e:
            logger.exception(f"Неожиданная ошибка в чате {chat_id}:")


async def save_message_handler(message: types.Message) -> None:
    try:
        if message.chat.id > 0:
            await handle_private_chat(message)
            return

        if not await process_group_message(message):
            logger.warning(f"Не удалось сохранить сообщение из чата {message.chat.id}")

    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {str(e)}", exc_info=True)
        await handle_error(message)

async def handle_private_chat(message: types.Message) -> None:
    await message.answer(
        "⚠️ Вы выбрали не ту команду. Для старта используйте: /start\n\n"
        "Для работы с ботом в групповых чатах:\n"
        "1. Добавьте бота в группу\n"
        "2. Выдайте права администратора\n"
        "3. Напишите любое сообщение в группе"
    )

async def process_group_message(message: types.Message) -> bool:
    message_link = generate_message_link(message)
    message_text = message.text or ""

    try:
        save_message_to_db(
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            message_text=message_text,
            link=message_link
        )
        
        log_message_details(message, message_link)
        return True

    except Exception as e:
        logger.error(f"Ошибка сохранения сообщения: {str(e)}", exc_info=True)
        return False

def generate_message_link(message: types.Message) -> Optional[str]:
    try:
        if message.chat.username:
            return f"https://t.me/{message.chat.username}/{message.message_id}"
        return None
    except AttributeError:
        logger.warning(f"Чат {message.chat.id} не имеет username")
        return None

def log_message_details(message: types.Message, link: Optional[str]) -> None:
    log_data = {
        "chat_id": message.chat.id,
        "user_id": message.from_user.id,
        "message_id": message.message_id,
        "text": message.text,
        "link": link
    }
    logger.info("Сообщение сохранено: %s", log_data)

async def handle_error(message: types.Message) -> None:
    """Отправляет пользователю сообщение об ошибке."""
    error_text = (
        "⚠️ Произошла ошибка при обработке сообщения. "
        "Попробуйте повторить позже или обратитесь в поддержку."
    )
    
    try:
        await message.answer(error_text)
    except TelegramAPIError as e:
        logger.error(f"Не удалось отправить сообщение об ошибке: {str(e)}")


async def start_handler(message: types.Message, state: FSMContext, user_id: int = None):
    welcome_text = (
        "👋 *Привет, {user_name}!*\n\n"
        "Я твой цифровой помощник для работы с чатами! Вот что я умею:\n\n"
        "📝 *Делать краткие выжимки* из обсуждений за любой период\n"
        "⏰ *Напоминать о дедлайнах* и важных событиях\n"
        "📅 *Планировать активности* на ближайший месяц\n"
        "🤝 *Рекомендовать волонтерские мероприятия*\n\n"
        "Выбери чаты для работы:"
    ).format(user_name=message.from_user.full_name)

    no_chats_text = (
        "😢 *Упс! Кажется, вы еще не добавили меня ни в один чат.*\n\n"
        "Чтобы я смог работать, сделайте несколько простых шагов:\n\n"
        "1. 👉 Добавьте меня в группу/канал\n"
        "2. 👑 Назначьте администратором с правом просмотра сообщений\n"
        "3. 💬 Напишите любое сообщение в чате\n\n"
        "После этого я смогу анализировать переписки и помогать вам!"
    )

    if message.chat.id < 0:
        return
    
    target_user = user_id or message.from_user.id
    chats = await get_user_chats(target_user_id=target_user, bot=message.bot)
    async with state.proxy() as data:
        data['selected_chats'] = data.get('selected_chats', [])
        
        if len(chats) == 1:
            data['selected_chats'] = chats
            await show_category_selection(message, chats, state)
            return

        if chats:
            keyboard = await generate_chats_keyboard(chats, data['selected_chats'])
            try:
                await message.edit_text(welcome_text, parse_mode="Markdown", reply_markup=keyboard)
            except:
                await message.answer(welcome_text, parse_mode="Markdown", reply_markup=keyboard)
        else:
            keyboard = get_help_markup()
            try:
                await message.edit_text(no_chats_text, parse_mode="Markdown", reply_markup=keyboard)
            except:
                await message.answer(no_chats_text, parse_mode="Markdown", reply_markup=keyboard)
    
    await SummaryState.choosing_chats.set()
    
async def show_category_selection(message: types.Message, chats, state: FSMContext):
    keyboard = choose_category()
    welcome_text = (
        "👋 *Привет, {user_name}!*\n\n"
        "Я твой цифровой помощник для работы с чатами! Вот что я умею:\n\n"
        "📝 *Делать краткие выжимки* из обсуждений за любой период\n"
        "⏰ *Напоминать о дедлайнах* и важных событиях\n"
        "📅 *Планировать активности* на ближайший месяц\n"
        "🤝 *Рекомендовать волонтерские мероприятия*\n\n"
    ).format(user_name=message.from_user.full_name)
  
    selected_chats = chats
    chat_count = len(selected_chats)
    chat_text = "чат" if chat_count == 1 else "чата" if 2 <= chat_count <= 4 else "чатов"
    async with state.proxy() as data:
        data['selected_chats'] = selected_chats[0]["chat_id"]
    
    text = welcome_text + (
        f"У Вас есть единственный чат: *{selected_chats[0]['title']}*\n"
        "Теперь выберите категорию:"
    )
    
    try:
        await message.edit_text(text, reply_markup=keyboard)
    except:
        await message.answer(text, reply_markup=keyboard)

    await SummaryState.choosing_category.set()

async def start_query_handler(callback: types.CallbackQuery, state: FSMContext):
    return await start_handler(callback.message, state, callback.from_user.id)

def register_start_handlers(dp: Dispatcher):
    dp.register_message_handler(start_handler, commands=["start"])
    dp.register_message_handler(start_handler, commands=["start"], state="*")
    dp.register_callback_query_handler(start_query_handler, text="CHECK_BOT")
    dp.register_callback_query_handler(start_query_handler, text="CHECK_BOT", state="*")
    dp.register_message_handler(save_message_handler, content_types=types.ContentType.TEXT)
    dp.register_message_handler(add_handler, content_types=["new_chat_members"])
    
    