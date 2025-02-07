from dataclasses import dataclass
from environs import Env
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

@dataclass
class TgBot:
    token: str



@dataclass
class Config:
    tg_bot: TgBot


def load_config(path: str = None):
    env = Env()
    env.read_env(path)

    return Config(
        tg_bot=TgBot(
            token=env.str("BOT_TOKEN")
        )
    )



Path("logs").mkdir(exist_ok=True)

def setup_logger(name: str = "bot") -> logging.Logger:
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)


    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)


    file_handler = RotatingFileHandler(
        filename="logs/bot.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger