import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from dotenv import load_dotenv

# Agar oldingi kodingizda handlers import qilingan bo'lsa, ularni shu yerga qo'shing.
from handlers import router 

load_dotenv()

async def main():
    # 2 GB limitni yechish uchun Local Server sozlamasi
    session = AiohttpSession(
        api=TelegramAPIServer.from_base("http://localhost:8081")
    )
    
    # Botni ishga tushirish (Local Server orqali)
    bot = Bot(token=os.getenv("BOT_TOKEN"), session=session)
    dp = Dispatcher()

    # Routerlarni ulash (agar oldingi bot.py da bo'lgan bo'lsa)
    dp.include_router(router)

    print("Bot muvaffaqiyatli ishga tushdi (Local API)!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())