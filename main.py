import logging
import sys
import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from config import settings
from parsers.tg_parser import TGParser
from utils import format_results, safe_format_query

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Проверка токена
if not settings.BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не установлен! Проверьте переменные окружения на Render.")
    sys.exit(1)
else:
    logger.info(f"✅ Token loaded: {settings.BOT_TOKEN[:10]}...")

# Инициализация
bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()
tg_parser = TGParser()


@dp.message(Command("start"))
async def cmd_start(message: Message):
    logger.info(f"📩 /start от {message.from_user.id}")
    await message.answer(
        "👋 <b>Бот поиска вакансий</b>\n\n"
        "Используй команду:\n"
        "<code>/search &lt;должность&gt;</code>\n\n"
        "<b>Примеры:</b>\n"
        "<code>/search маркетолог</code>\n"
        "<code>/search SMM</code>\n"
        "<code>/search контент-менеджер</code>\n"
        "<code>/search PR</code>\n\n"
        "<b>📡 Источники:</b>\n"
        "• @vacanciesbest\n"
        "• @pstmarketing\n"
        "• @yojob",
        parse_mode="HTML"
    )


@dp.message(Command("search"))
async def cmd_search(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "❌ <b>Неверный формат</b>\n"
            "Используй: <code>/search маркетолог</code>",
            parse_mode="HTML"
        )
        return

    query = safe_format_query(args[1])
    logger.info(f"🔍 Поиск от {message.from_user.id}: '{query}'")
    
    status_msg = await message.answer(
        f"🔎 <b>Ищу вакансии:</b> <code>{query}</code>\n"
        f"⏳ Секундочку, проверяю каналы...",
        parse_mode="HTML"
    )

    try:
        results = await tg_parser.search(
            channels=settings.CHANNELS,
            query=query,
            limit=settings.MAX_RESULTS
        )
    except Exception as e:
        logger.error(f"❌ Ошибка поиска: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ <b>Ошибка:</b> <code>{e}</code>",
            parse_mode="HTML"
        )
        return

    if not results:
        await status_msg.edit_text(
            "😔 <b>Ничего не найдено</b>\n\n"
            "Попробуйте:\n"
            "• Другую формулировку\n"
            "• Более общее слово (например, <code>маркетинг</code>)",
            parse_mode="HTML"
        )
        return

    formatted = format_results(results)
    await status_msg.edit_text(
        formatted,
        parse_mode="HTML",
        disable_web_page_preview=True
    )


@dp.message()
async def echo_handler(message: Message):
    await message.answer(
        "🤔 Используй команду <code>/search</code>\n"
        "Например: <code>/search маркетолог</code>",
        parse_mode="HTML"
    )


async def main():
    # HTTP-сервер для Render (чтобы сервис считался активным)
    async def handle(request):
        return web.Response(text="✅ Bot is alive")

    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"🌐 HTTP server running on port {port}")

    # Запуск Telegram-бота
    logger.info("🤖 Starting Telegram bot polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
