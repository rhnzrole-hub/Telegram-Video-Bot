import os
import uuid
from aiogram import Router, Bot, F, types
from aiogram.fsm.context import FSMContext
from states import ProcessState
from services.ffmpeg_service import add_subtitle_to_video
from utils.progress import ProgressTracker, download_with_progress, CANCEL_TASKS
from utils.cleanup import remove_temp_files

router = Router()

@router.message(ProcessState.waiting_for_subtitle, F.document)
async def handle_subtitle(message: types.Message, bot: Bot, state: FSMContext):
    document = message.document
    
    if not (document.file_name.endswith('.srt') or document.file_name.endswith('.ass')):
        return await message.answer("Iltimos, faqat **.srt** yoki **.ass** formatini yuboring.")

    status_msg = await message.answer("Subtitr yuklab olinmoqda ⏳...")
    
    task_id = str(uuid.uuid4())[:8]
    sub_ext = os.path.splitext(document.file_name)[1]
    subtitle_path = os.path.join("temp", f"{uuid.uuid4()}{sub_ext}")
    output_path = os.path.join("temp", f"{uuid.uuid4()}_ready.mkv")
    
    data = await state.get_data()
    video_path = data.get("video_path")

    try:
        tracker = ProgressTracker(status_msg, "Yuklab olinmoqda (Subtitr)", document.file_name, task_id)
        await download_with_progress(bot, document.file_id, subtitle_path, tracker)
        
        await status_msg.edit_text("Subtitr videoga biriktirilmoqda (MKV formatida) ⚙️...")
        success = await add_subtitle_to_video(video_path, subtitle_path, output_path)

        if success:
            await status_msg.edit_text("Fayl Telegramga yuklanmoqda 🚀 (Local API)...")
            result_file = types.FSInputFile(output_path)
            await message.answer_document(document=result_file, caption="Sizning videongiz tayyor (MKV formatida)!")
            await status_msg.delete()
        else:
            await status_msg.edit_text("Birlashtirishda xatolik yuz berdi ❌")
            
    except Exception as e:
        if CANCEL_TASKS.get(task_id): 
            await status_msg.edit_text("Jarayon bekor qilindi ❌")
        else: 
            await status_msg.edit_text(f"Xatolik yuz berdi: {e}")
            
    finally:
        remove_temp_files(subtitle_path, output_path)
        CANCEL_TASKS.pop(task_id, None)
        await state.set_state(None)