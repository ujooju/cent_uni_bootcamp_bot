import logging

from sqlalchemy import exists
from sqlalchemy.orm import Session

from .DBSM import Chat, Message, engine, sessionmaker

logger = logging.getLogger(__name__)


# ---------------------- Chat management ---------------------- #


def create_chat(chat_id: int) -> bool:
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as session:
        if not session.query(exists().where(Chat.id == chat_id)).scalar():
            session.add(Chat(chat_id=chat_id))
            session.commit()
            return True
        return False


def save_message_to_db(
    chat_id: int, user_id: int, message_text: str, link: str = None
) -> None:
    Session = sessionmaker(bind=engine)
    with Session() as session:
        db_message = Message(
            chat_id=chat_id, user_id=user_id, message_text=message_text, link=link
        )
        session.add(db_message)
        session.commit()


# ---------------------- Service functions ---------------------- #


def get_chat_ids_from_db() -> list[int]:
    try:
        Session = sessionmaker(bind=engine)
        with Session() as session:
            return [chat.chat_id for chat in session.query(Chat).all()]
    except Exception as e:
        logger.error(f"Ошибка получения чатов из БД: {e}", exc_info=True)
        return []
