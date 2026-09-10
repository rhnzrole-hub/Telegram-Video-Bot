import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN .env faylida topilmadi!")

MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024