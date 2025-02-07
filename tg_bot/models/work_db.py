from sqlalchemy import exists
from .DBSM import Chat, sessionmaker, Message, engine




def create_chat(chat_id):
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as session:
        if not session.query(exists().where(Chat.id == chat_id)).scalar():
            session.add(Chat(id=chat_id))
            return True
        return False
        