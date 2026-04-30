import asyncio
import logging

from telegram.ext import Application, ApplicationBuilder

from bot.config import settings
from bot.database.db import init_db
from bot.handlers.admin import register_admin_handlers
from bot.handlers.bill import register_bill_handlers
from bot.handlers.display import register_display_handlers
from bot.handlers.settings import register_settings_handlers
from bot.handlers.individual import register_individual_handlers
from bot.handlers.proxy import register_proxy_handlers
from bot.handlers.query import register_query_handlers
from bot.handlers.distribute import register_distribute_handlers

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def main() -> None:
    await init_db()
    logger.info("Database initialized")

    app: Application = ApplicationBuilder().token(settings.BOT_TOKEN).build()

    register_admin_handlers(app)
    register_bill_handlers(app)
    register_display_handlers(app)
    register_settings_handlers(app)
    register_individual_handlers(app)
    register_proxy_handlers(app)
    register_query_handlers(app)
    register_distribute_handlers(app)

    logger.info("All handlers registered")

    if settings.WEBHOOK_URL:
        await app.bot.set_webhook(url=settings.WEBHOOK_URL)
        logger.info(f"Webhook set to {settings.WEBHOOK_URL}")
    else:
        await app.initialize()
        await app.start()
        logger.info("Bot started in polling mode")
        try:
            await app.updater.start_polling()
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            await app.updater.stop()
            await app.stop()
            await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
