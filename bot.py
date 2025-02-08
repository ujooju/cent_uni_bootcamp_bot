import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from dotenv import load_dotenv

from tg_bot.config import load_config, setup_logger
from tg_bot.handlers import register_main_handlers, register_start_handlers

load_dotenv()
logger = logging.getLogger(__name__)



logger = setup_logger()

def register_all_handlers(dp):
    logger.debug("Registering handlers...")
    register_main_handlers(dp)
    register_start_handlers(dp)


async def main():
    config = load_config(".env")

    bot = Bot(token=config.tg_bot.token, parse_mode="HTML")
    storage = MemoryStorage()
    dp = Dispatcher(bot, storage=storage)
    bot["config"] = config

    register_all_handlers(dp)

    try:
        logger.info("Starting bot...")
        await dp.start_polling()
        
    finally:
        await dp.storage.close()
        await dp.storage.wait_closed()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Bot stopped!")
