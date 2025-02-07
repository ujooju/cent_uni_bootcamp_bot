from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine

engine = create_engine("sqlite:///sqlite.db")
Session = sessionmaker()
session = Session(bind=engine)

Base = declarative_base()

class Chat(Base):
    __tablename__ = 'chats_active'

    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, unique=True, nullable=False)


Base.metadata.create_all(bind=engine)
