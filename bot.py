import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from handlers import video, audio, actions, subtitle, metadata, progress

from config import BOT_TOKEN
from handlers import video, audio, actions, subtitle, metadata


logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, base_url="http://localhost:8081", base_file_url="http://localhost:8081/file/bot")
dp = Dispatcher()

dp.include_router(video.router)
dp.include_router(actions.router)
dp.include_router(audio.router)
dp.include_router(subtitle.router)
dp.include_router(metadata.router)
dp.include_router(progress.router)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Salom! Menga qayta ishlash uchun video yuboring.")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer("Menga ixtiyoriy video yuboring, men sizga menyu ko'rsataman.")

async def main():
    if not os.path.exists("temp"):
        os.makedirs("temp")
        
    print("Bot ishga tushmoqda...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot to'xtatildi! 🛑")