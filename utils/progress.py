import time
import aiohttp
import os
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.exceptions import TelegramBadRequest

CANCEL_TASKS = {}

def get_progress_keyboard(task_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Jarayonni ko'rish", callback_data=f"prog_refresh_{task_id}")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"prog_cancel_{task_id}")]
    ])

def format_progress_bar(filename, action, current, total, start_time):
    if total == 0: total = 1
    percent = current / total * 100
    filled = int(percent / 10)
    bar = "■" * filled + "□" * (10 - filled)
    
    elapsed_time = time.time() - start_time
    speed = current / elapsed_time if elapsed_time > 0 else 0
    time_left = (total - current) / speed if speed > 0 else 0
        
    curr_mb = current / (1024 * 1024)
    tot_mb = total / (1024 * 1024)
    speed_mb = speed / (1024 * 1024)
    mins, secs = divmod(int(time_left), 60)
    
    text = f"**{action}**: `{filename}`\n\n"
    text += f"[{bar}] {percent:.2f}%\n\n"
    text += f"=> {curr_mb:.2f} MB Of {tot_mb:.2f} MB\n"
    text += f"=> Speed: {speed_mb:.2f} MB/s\n"
    text += f"=> Time Left: {mins}m {secs}s"
    return text

class ProgressTracker:
    def __init__(self, message, action, filename, task_id):
        self.message = message
        self.action = action
        self.filename = filename
        self.task_id = task_id
        self.start_time = time.time()
        self.last_update_time = 0
        
    async def update(self, current, total, force=False):
        if CANCEL_TASKS.get(self.task_id):
            raise Exception("TaskCancelled")
            
        now = time.time()
        if force or (now - self.last_update_time > 5):
            self.last_update_time = now
            text = format_progress_bar(self.filename, self.action, current, total, self.start_time)
            try:
                await self.message.edit_text(text, reply_markup=get_progress_keyboard(self.task_id), parse_mode="Markdown")
            except TelegramBadRequest:
                pass

    async def update_ffmpeg(self, current_sec, total_sec, force=False):
        if CANCEL_TASKS.get(self.task_id):
            raise Exception("TaskCancelled")
            
        now = time.time()
        if force or (now - self.last_update_time > 5):
            self.last_update_time = now
            text = format_ffmpeg_progress(self.filename, self.action, current_sec, total_sec, self.start_time)
            try:
                await self.message.edit_text(text, reply_markup=get_progress_keyboard(self.task_id), parse_mode="Markdown")
            except TelegramBadRequest:
                pass

async def download_with_progress(bot, file_id, destination, tracker):
    file = await bot.get_file(file_id)
    file_path = file.file_path
    total_size = file.file_size
    
    # DIQQAT: Faqat o'zimizning Docker serverimizdan (8081) tortamiz!
    url = f"http://localhost:8081/file/bot{bot.token}/{file_path}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Yuklab olishda xato: HTTP {response.status}")
            with open(destination, 'wb') as f:
                read_bytes = 0
                async for chunk in response.content.iter_chunked(1024 * 1024): 
                    if CANCEL_TASKS.get(tracker.task_id): raise Exception("TaskCancelled")
                    f.write(chunk)
                    read_bytes += len(chunk)
                    await tracker.update(read_bytes, total_size)
    await tracker.update(total_size, total_size, force=True)

class ProgressFSInputFile(FSInputFile):
    def __init__(self, path, tracker):
        super().__init__(path, chunk_size=1024 * 1024)
        self.tracker = tracker
        self.total_size = os.path.getsize(path)

    async def read(self, bot):
        read_bytes = 0
        async for chunk in super().read(bot):
            if CANCEL_TASKS.get(self.tracker.task_id):
                raise Exception("TaskCancelled")
            read_bytes += len(chunk)
            await self.tracker.update(read_bytes, self.total_size)
            yield chunk

def format_ffmpeg_progress(filename, action, current_sec, total_sec, start_time):
    if total_sec == 0: total_sec = 1
    percent = (current_sec / total_sec) * 100
    percent = min(percent, 100.0)
    filled = int(percent / 10)
    bar = "■" * filled + "□" * (10 - filled)
    
    elapsed_time = time.time() - start_time
    speed = current_sec / elapsed_time if elapsed_time > 0 else 0
    time_left = (total_sec - current_sec) / speed if speed > 0 else 0
        
    def fmt_time(seconds):
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0: return f"{h}h {m}m {s}s"
        return f"{m}m {s}s"
    
    text = f"**{action}**: `{filename}`\n\n[{bar}] {percent:.2f}%\n\n=> Vaqt: {fmt_time(current_sec)} / {fmt_time(total_sec)}\n=> Tezlik: {speed:.2f}x\n=> Qolgan vaqt: {fmt_time(time_left)}"
    return text