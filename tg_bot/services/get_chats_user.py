import logging

from aiogram import Bot
from aiogram.types import ChatMemberStatus, ChatType

from tg_bot.models import get_chat_ids_from_db

logger = logging.getLogger(__name__)


async def get_user_chats(target_user_id: int, bot: Bot) -> list[dict]:
    try:
        chat_ids = await get_chat_ids_from_db()
        chats_with_user = []

        for chat_id in chat_ids:
            try:
                if not await is_bot_admin(chat_id, bot):
                    logger.debug("Бот не админ в чате %d, пропускаем", chat_id)
                    continue

                if await is_user_in_chat(chat_id, target_user_id, bot):
                    chat_info = await get_chat_info(chat_id, bot)
                    chats_with_user.append(chat_info)

            except Exception as e:
                logger.error("Ошибка обработки чата %d: %s", chat_id, e, exc_info=True)

        return chats_with_user

    except Exception as e:
        logger.critical("Критическая ошибка: %s", e, exc_info=True)
        return []


async def is_bot_admin(chat_id: int, bot: Bot) -> bool:
    try:
        bot_id = (await bot.get_me()).id
        bot_member = await bot.get_chat_member(chat_id, bot_id)
        return bot_member.status in {
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR,
        }
    except Exception as e:
        logger.warning("Ошибка проверки прав бота в чате %d: %s", chat_id, e)
        return False


async def is_user_in_chat(chat_id: int, user_id: int, bot: Bot) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status not in {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}
    except Exception as e:
        logger.debug("Пользователь %d отсутствует в чате %d: %s", user_id, chat_id, e)
        return False


async def get_chat_info(chat_id: int, bot: Bot) -> dict:
    try:
        chat = await bot.get_chat(chat_id)
        return {
            "chat_id": chat_id,
            "title": chat.title or "Private Chat",
            "type": chat.type if chat.type else ChatType.PRIVATE,
            "username": chat.username,
        }
    except Exception as e:
        logger.error("Ошибка получения информации о чате %d: %s", chat_id, e)
        return {"chat_id": chat_id, "error": str(e)}
