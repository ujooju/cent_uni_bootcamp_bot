from sqlalchemy import exists
from .DBSM import Chat, sessionmaker, Message, engine
import logging

logger = logging.getLogger(__name__)

# ---------------------- start and save chat ---------------------- #

def create_chat(chat_id):
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as session:
        if not session.query(exists().where(Chat.id == chat_id)).scalar():
            session.add(Chat(chat_id=chat_id))
            session.commit()
            return True
        return False

def save_message_to_db(chat_id: int, user_id: int, message_text: str, link:str=None):
    Session = sessionmaker()
    session = Session(bind=engine)
    db_message = Message(chat_id=chat_id, user_id=user_id, message_text=message_text, link=link)
    session.add(db_message)
    session.commit()
    session.close()

        
# -------------------------- main handlers -------------------------- #




# -------------------------- service handlers ------------------------ #
async def get_chat_ids_from_db():
    try:
        with sessionmaker(bind=engine)() as session:
            return [chat.chat_id for chat in session.query(Chat).all()]
    except Exception as e:
        logger.error(f"Ошибка получения чатов из БД: {str(e)}")
        return []
    