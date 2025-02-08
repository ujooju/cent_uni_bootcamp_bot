import logging

from aiogram import Bot

from tg_bot.models import get_chat_ids_from_db


logger = logging.getLogger(__name__)

async def get_user_chats(target_user_id: int, bot: Bot):
    try:
        chat_ids = await get_chat_ids_from_db()
        
        chats_with_user = []
        
        for chat_id in chat_ids:
            try:
                if not await is_bot_admin(chat_id, bot):
                    logger.debug(f"Бот не админ в чате {chat_id}, пропускаем")
                    continue
                if await is_user_in_chat(chat_id, target_user_id, bot):
                    chat_info = await get_chat_info(chat_id, bot)
                    chats_with_user.append(chat_info)
                    
            except Exception as e:
                logger.error(f"Ошибка обработки чата {chat_id}: {str(e)}", exc_info=True)
        
        return chats_with_user

    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}", exc_info=True)
        return []

async def is_bot_admin(chat_id: int, bot: Bot):
    try:
        bot_member = await bot.get_chat_member(chat_id, (await bot.get_me()).id)
        return bot_member.status in ["administrator", "creator"]
    except Exception as e:
        logger.warning(f"Ошибка проверки прав бота в чате {chat_id}: {str(e)}.")
        return False

async def is_user_in_chat(chat_id: int, user_id: int, bot: Bot):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status not in ["left", "kicked"]
    except Exception as e:
        logger.debug(f"Пользователь {user_id} отсутствует в чате {chat_id}: {str(e)}")
        return False

async def get_chat_info(chat_id: int, bot: Bot):
    try:
        chat = await bot.get_chat(chat_id)
        return {
            "chat_id": chat_id,
            "title": chat.title or "Private Chat",
            "type": chat.type,
            "username": chat.username
        }
    except Exception as e:
        logger.error(f"Ошибка получения информации о чате {chat_id}: {str(e)}")
        return {"chat_id": chat_id, "error": str(e)}
    