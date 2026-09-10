import os
from dotenv import load_dotenv

# .env faylini o'qiymiz
load_dotenv()

# BOT_TOKEN ni o'zgaruvchiga olamiz
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN .env faylida topilmadi!")

# Fayl hajmi limiti (Kelajak uchun 2 GB qilib belgilaymiz)
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024