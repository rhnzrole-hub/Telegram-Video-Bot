import os
import uuid
from aiogram import Router, Bot, F, types
from aiogram.fsm.context import FSMContext
from states import ProcessState
from services.ffmpeg_service import add_audio_to_video
from utils.progress import ProgressTracker, download_with_progress, CANCEL_TASKS
from utils.cleanup import remove_temp_files
from config import MAX_FILE_SIZE

router = Router()

@router.message(ProcessState.waiting_for_audio, F.audio | F.voice | F.document)
async def handle_audio(message: types.Message, bot: Bot, state: FSMContext):
    audio_obj = message.audio or message.voice or message.document
    
    if audio_obj.file_size and audio_obj.file_size > MAX_FILE_SIZE:
        return await message.answer("Iltimos, 2 GB dan kichik audio yuboring.")

    status_msg = await message.answer("Audio yuklab olinmoqda ⏳...")
    
    task_id = str(uuid.uuid4())[:8]
    ext = ".tmp"
    if hasattr(audio_obj, 'file_name') and audio_obj.file_name:
        ext = os.path.splitext(audio_obj.file_name)[1]
        
    audio_path = os.path.join("temp", f"{uuid.uuid4()}{ext}")
    output_path = os.path.join("temp", f"{uuid.uuid4()}_ready.mp4")
    
    data = await state.get_data()
    video_path = data.get("video_path")

    try:
        tracker = ProgressTracker(status_msg, "Yuklab olinmoqda (Audio)", "audio_file", task_id)
        await download_with_progress(bot, audio_obj.file_id, audio_path, tracker)
        
        await status_msg.edit_text("Video va Audio birlashtirilmoqda ⚙️ (Bu biroz vaqt olishi mumkin)...")
        success = await add_audio_to_video(video_path, audio_path, output_path)

        if success:
            await status_msg.edit_text("Fayl Telegramga yuklanmoqda 🚀 (Local API)...")
            result_file = types.FSInputFile(output_path)
            await message.answer_document(document=result_file, caption="Sizning videongiz tayyor! Yangi audio asosiy qilib belgilandi.")
            await status_msg.delete()
        else:
            await status_msg.edit_text("Birlashtirishda xatolik yuz berdi ❌")
            
    except Exception as e:
        if CANCEL_TASKS.get(task_id): 
            await status_msg.edit_text("Audio jarayoni bekor qilindi ❌")
        else: 
            await status_msg.edit_text(f"Xatolik: {e}")
            
    finally:
        remove_temp_files(audio_path, output_path)
        CANCEL_TASKS.pop(task_id, None)
        await state.set_state(None)