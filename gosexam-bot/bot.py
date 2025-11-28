import asyncio
import os
from pathlib import Path
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from app.handlers import register_handlers

ENV_PATH = Path(__file__).with_name(".env")
loaded = load_dotenv(dotenv_path=ENV_PATH, override=True)

# Fallback на случай скрытого BOM в ключе
TOKEN = os.getenv("BOT_TOKEN") or os.environ.get("\ufeffBOT_TOKEN")

async def main():
    # Диагностика — временно
    print("cwd:", os.getcwd())
    print(".env path:", ENV_PATH)
    print(".env exists:", ENV_PATH.exists())
    print("dotenv loaded:", loaded)
    print("TOKEN present:", bool(TOKEN))
    assert TOKEN, "BOT_TOKEN не найден. Проверь .env рядом с bot.py"
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    register_handlers(dp)
    print("✅ Бот запущен. Нажми Ctrl+C для остановки.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())