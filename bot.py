import asyncio
import logging
from aiohttp import web

from aiogram import Bot, Dispatcher, types
from aiogram.types import Update
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from dotenv import load_dotenv

from tg_bot.config import load_config, setup_logger
from tg_bot.handlers import register_main_handlers, register_start_handlers

load_dotenv()
logger = setup_logger()


def register_all_handlers(dp: Dispatcher):
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

    webhook_url = f"https://{config.tg_bot.public_url}"
    await bot.set_webhook(
        url=webhook_url,
        #secret_token=config.webhook_secret,
        drop_pending_updates=True
    )
    logger.info(f"Webhook установлен на {webhook_url}")

    app = web.Application()
    app['bot'] = bot
    app['dp'] = dp
    app['config'] = config

    async def webhook_handler(request):
        #secret_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
        #if secret_token != app['config'].webhook_secret:
        #    return web.Response(status=403)
        
        data = await request.json()
        update = Update(**data)
        await app['dp'].process_update(update)
        return web.Response()

    app.router.add_post('/', webhook_handler)


    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=config.tg_bot.local_url, port=config.tg_bot.local_port)
    await site.start()

    logger.info(f"Сервер запущен на {config.tg_bot.local_url}:{config.tg_bot.local_port}")

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Остановка сервера...")
    finally:
        await bot.delete_webhook()
        await dp.storage.close()
        await dp.storage.wait_closed()
        await bot.session.close()
        await runner.cleanup()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped gracefully")
