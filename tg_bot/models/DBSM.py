from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

engine = create_engine("sqlite:////path/to/file")
Session = sessionmaker()
session = Session(bind=engine)
