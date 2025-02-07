import asyncio
from aiogram import Bot
from tg_bot.models import sessionmaker, engine, Chat
from tg_bot.models.DBSM import Session


async def get_user_chats(target_user_id: int, bot: Bot) -> list:
    chats_with_user = []

    updates = await bot.get_updates(limit=10000, offset=-1)
    Session = sessionmaker()
    session = Session(bind=engine)
    unique_chat_ids = session.query(Chat).all()
    session.close()

    for chat_id in unique_chat_ids:
        try:
            member = await bot.get_chat_member(
                chat_id=chat_id.chat_id, user_id=target_user_id
            )

            if member.status not in ["left", "kicked"]:
                chat = await bot.get_chat(chat_id.chat_id)
                chats_with_user.append(
                    {
                        "chat_id": chat_id.chat_id,
                        "title": chat.title if chat.title else "Private Chat",
                        "type": chat.type,
                    }
                )
        except Exception as e:
            print(e)
            continue

    return chats_with_user
