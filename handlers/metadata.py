import os
import uuid
from aiogram import Router, Bot, F, types
from aiogram.fsm.context import FSMContext
from states import ProcessState
from keyboards import get_streams_keyboard
from services.ffmpeg_service import apply_multiple_metadata, get_video_streams
from utils.progress import ProgressTracker, ProgressFSInputFile, CANCEL_TASKS
from utils.cleanup import remove_temp_files

router = Router()

@router.callback_query(F.data == "meta_finish")
async def finish_metadata(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    changes = data.get("metadata_changes", {})
    video_path = data.get("video_path")
    
    if not changes:
        return await callback.answer("Hech qanday o'zgarish qilinmadi!", show_alert=True)
        
    status_msg = await callback.message.edit_text("Barcha o'zgarishlar bittada qo'llanilmoqda ⚙️...")
    output_path = os.path.join("temp", f"{uuid.uuid4()}_meta.mkv")
    upload_task_id = str(uuid.uuid4())[:8]
    
    try:
        success = await apply_multiple_metadata(video_path, changes, output_path)
        
        if success:
            upload_tracker = ProgressTracker(status_msg, "Yuklanmoqda (Upload)", "metadata_ready.mkv", upload_task_id)
            result = ProgressFSInputFile(output_path, upload_tracker)
            await callback.message.answer_document(document=result, caption="Barcha metadata o'zgarishlari muvaffaqiyatli saqlandi! ✅")
            await status_msg.delete()
        else:
            await status_msg.edit_text("Xatolik yuz berdi ❌")
            
    except Exception as e:
        if CANCEL_TASKS.get(upload_task_id): 
            await status_msg.edit_text("Yuklash bekor qilindi ❌")
        else: 
            await status_msg.edit_text(f"Yuklashda xatolik: {e}")
            
    finally:
        remove_temp_files(video_path, output_path)
        await state.clear()

@router.callback_query(F.data.startswith("stream_"))
async def select_stream(callback: types.CallbackQuery, state: FSMContext):
    stream_index = callback.data.split("_")[1]
    await state.update_data(meta_stream_index=stream_index)
    await state.set_state(ProcessState.waiting_for_metadata_value)
    
    text = (
        f"Tanlandi: **Oqim #{stream_index}**\n\n"
        "✶ Nomini VA Tilini o'zgartirish uchun `|` belgisidan foydalaning.\n"
        "Format: `Nom | til_kodi`\n"
        "M-n: `O'zbekcha Tarjima | uzb`\n\n"
        "Yangi qiymatni yuboring 👇"
    )
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()

@router.message(ProcessState.waiting_for_metadata_value)
async def process_metadata_value(message: types.Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    
    changes = data.get("metadata_changes", {})
    stream_index = str(data.get("meta_stream_index"))
    
    if stream_index not in changes: changes[stream_index] = {}
        
    if "|" in text:
        parts = text.split("|")
        changes[stream_index]['title'] = parts[0].strip()
        changes[stream_index]['language'] = parts[1].strip()
    else:
        changes[stream_index]['title'] = text
        
    await state.update_data(metadata_changes=changes)
    
    video_path = data.get("video_path")
    streams = await get_video_streams(video_path)
    target_streams = [s for s in streams if s.get("codec_type") in ["audio", "subtitle"]]
    
    await message.answer(
        f"Oqim #{stream_index} xotiraga saqlandi! ✏️ Yana nimanidir o'zgartirasizmi yoki yakunlaymizmi? 👇",
        reply_markup=get_streams_keyboard(target_streams, changes)
    )
    await state.set_state(None)