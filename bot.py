import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from dotenv import load_dotenv
from handlers.actions import router as actions_router
from handlers.audio import router as audio_router
from handlers.metadata import router as metadata_router
from handlers.subtitle import router as subtitle_router
from handlers.video import router as video_router
from handlers.progress import router as progress_router

load_dotenv()

async def main():
    os.makedirs("temp", exist_ok=True)
    
    session = AiohttpSession(
        api=TelegramAPIServer.from_base("http://localhost:8081", is_local=True)
    )
    
    bot = Bot(token=os.getenv("BOT_TOKEN"), session=session)
    dp = Dispatcher()

    dp.include_routers(
        actions_router,
        audio_router,
        metadata_router,
        subtitle_router,
        video_router,
        progress_router
    )

    print("Bot muvaffaqiyatli ishga tushdi (Local API)!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())