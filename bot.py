import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from httpx import get
from tg_bot.config import load_config
from os import getenv
from tg_bot.handlers import register_main_handlers

logger = logging.getLogger(__name__)
getenv.load_dotenv()

def register_all_filters(dp):
    return None


def register_all_handlers(dp):
    register_main_handlers(dp)


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s",
    )
    config = load_config(".env")

    bot = Bot(token=config.tg_bot.token, parse_mode="HTML")
    storage = MemoryStorage()
    dp = Dispatcher(bot, storage=storage)
    bot["config"] = config

    register_all_filters(dp)
    register_all_handlers(dp)

    try:
        await dp.start_polling()
    finally:
        await dp.storager.close()
        await dp.storage.wait_closed()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Bot stopped!")
