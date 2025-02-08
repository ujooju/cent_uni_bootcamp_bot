import datetime
from urllib.parse import quote_plus

from sqlalchemy import BigInteger, Column, DateTime, Integer, Text, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from tg_bot.config import load_config

config = load_config(".env")
engine = create_engine(
    f"postgresql://{config.db_config.user}:%s@{config.db_config.host}/{config.db_config.database}"
    % quote_plus(f"{config.db_config.password}", encoding="utf8")
)

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
    link = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.now())


Base.metadata.create_all(bind=engine)
