from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
import datetime

engine = create_engine("sqlite:///sqlite.db")
Session = sessionmaker()
session = Session(bind=engine)

Base = declarative_base()


class Chat(Base):
    __tablename__ = "chats_active"

    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, unique=True, nullable=False)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, index=True)
    user_id = Column(Integer)
    message_text = Column(Text)
    timestamp = Column(DateTime, default=datetime.datetime.now())


Base.metadata.create_all(bind=engine)


def save_message_to_db(chat_id: int, user_id: int, message_text: str):
    Session = sessionmaker()
    session = Session(bind=engine)
    db_message = Message(chat_id=chat_id, user_id=user_id, message_text=message_text)
    session.add(db_message)
    session.commit()
    session.close()


Base.metadata.create_all(bind=engine)
