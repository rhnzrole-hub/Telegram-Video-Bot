import os
import uuid
from aiogram import Router, Bot, F, types
from aiogram.fsm.context import FSMContext
from states import ProcessState
from keyboards import get_main_menu, get_streams_keyboard
from services.ffmpeg_service import get_video_streams, apply_letterbox, get_video_duration
from utils.progress import ProgressTracker, download_with_progress, ProgressFSInputFile, CANCEL_TASKS
from utils.cleanup import remove_temp_files

router = Router()

@router.callback_query(F.data == "action_cancel")
async def action_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Amal bekor qilindi ❌. Boshqa video yuborishingiz mumkin.")
    await callback.answer()

async def download_video_if_needed(bot, video_file_id, video_path, state, status_msg, task_id):
    if not video_path or not os.path.exists(video_path):
        save_path = os.path.join("temp", f"{uuid.uuid4()}.mp4")
        tracker = ProgressTracker(status_msg, "Yuklab olinmoqda (Video)", "video.mp4", task_id)
        await download_with_progress(bot, video_file_id, save_path, tracker)
        await state.update_data(video_path=save_path)
        return save_path
    return video_path

@router.callback_query(F.data == "action_add_audio")
async def action_add_audio(callback: types.CallbackQuery, bot: Bot, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    video_file_id = data.get("video_file_id")
    video_path = data.get("video_path")

    if not video_file_id:
        return await callback.message.edit_text("Video topilmadi. Qaytadan yuboring.")

    status_msg = await callback.message.edit_text("Video yuklab olinmoqda ⏳...")
    task_id = str(uuid.uuid4())[:8]

    try:
        await download_video_if_needed(bot, video_file_id, video_path, state, status_msg, task_id)
        await state.set_state(ProcessState.waiting_for_audio)
        await status_msg.edit_text("Video yuklab olindi! ✅\n\nEndi menga bu videoga qo'shmoqchi bo'lgan **AUDIO** faylini yuboring.")
    except Exception as e:
        if CANCEL_TASKS.get(task_id): await status_msg.edit_text("Yuklab olish bekor qilindi ❌")
        else: await status_msg.edit_text(f"Yuklab olishda xatolik: {e}")

@router.callback_query(F.data == "action_add_subtitle")
async def action_add_subtitle(callback: types.CallbackQuery, bot: Bot, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    video_file_id = data.get("video_file_id")
    video_path = data.get("video_path")

    if not video_file_id:
        return await callback.message.edit_text("Video topilmadi. Qaytadan yuboring.")

    status_msg = await callback.message.edit_text("Video yuklab olinmoqda ⏳...")
    task_id = str(uuid.uuid4())[:8]

    try:
        await download_video_if_needed(bot, video_file_id, video_path, state, status_msg, task_id)
        await state.set_state(ProcessState.waiting_for_subtitle)
        await status_msg.edit_text("Video yuklab olindi! ✅\n\nEndi menga **.srt** yoki **.ass** formatidagi Subtitr faylini yuboring.")
    except Exception as e:
        if CANCEL_TASKS.get(task_id): await status_msg.edit_text("Yuklab olish bekor qilindi ❌")
        else: await status_msg.edit_text(f"Yuklab olishda xatolik: {e}")

@router.callback_query(F.data == "action_edit_metadata")
async def action_edit_metadata(callback: types.CallbackQuery, bot: Bot, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    video_file_id = data.get("video_file_id")
    video_path = data.get("video_path")

    if not video_file_id:
        return await callback.message.edit_text("Video topilmadi. Qaytadan yuboring.")

    status_msg = await callback.message.edit_text("Tahlil uchun video yuklab olinmoqda ⏳...")
    task_id = str(uuid.uuid4())[:8]

    try:
        video_path = await download_video_if_needed(bot, video_file_id, video_path, state, status_msg, task_id)
    except Exception as e:
        if CANCEL_TASKS.get(task_id): await status_msg.edit_text("Yuklab olish bekor qilindi ❌")
        else: await status_msg.edit_text(f"Yuklab olishda xatolik: {e}")
        return

    streams = await get_video_streams(video_path)
    target_streams = [s for s in streams if s.get("codec_type") in ["audio", "subtitle"]]
    
    if not target_streams:
        return await status_msg.edit_text("Bu videoda o'zgartirish mumkin bo'lgan audio yoki subtitr topilmadi.")

    await state.update_data(metadata_changes={})
    await status_msg.edit_text(
        "Mavjud oqimlar (Streams) topildi! Qaysi birini o'zgartirmoqchisiz? 👇",
        reply_markup=get_streams_keyboard(target_streams, changes={})
    )

@router.callback_query(F.data == "action_letterbox")
async def action_letterbox(callback: types.CallbackQuery, bot: Bot, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    video_file_id = data.get("video_file_id")
    video_path = data.get("video_path")

    if not video_file_id:
        return await callback.message.edit_text("Video topilmadi.")

    status_msg = await callback.message.edit_text("Video tayyorlanmoqda ⏳...")
    task_id = str(uuid.uuid4())[:8]
    output_path = None

    try:
        video_path = await download_video_if_needed(bot, video_file_id, video_path, state, status_msg, task_id)
        
        await status_msg.edit_text("Videoning davomiyligi aniqlanmoqda ⏳...")
        total_duration = await get_video_duration(video_path)
        
        ffmpeg_task_id = str(uuid.uuid4())[:8]
        ffmpeg_tracker = ProgressTracker(status_msg, "Qayta ishlanmoqda (Letterbox)", "video", ffmpeg_task_id)
        
        output_path = os.path.join("temp", f"{uuid.uuid4()}_16x9.mkv")
        
        success = await apply_letterbox(
            video_path=video_path, 
            output_path=output_path, 
            tracker=ffmpeg_tracker,
            total_duration=total_duration
        )
        
        if success:
            upload_task_id = str(uuid.uuid4())[:8]
            upload_tracker = ProgressTracker(status_msg, "Yuklanmoqda (Upload)", "16x9_video.mkv", upload_task_id)
            result = ProgressFSInputFile(output_path, upload_tracker)
            
            await callback.message.answer_document(document=result, caption="Videongiz 16:9 formatga muvaffaqiyatli o'tkazildi! 🎬")
            await status_msg.delete()
        else:
            await status_msg.edit_text("Letterboxing jarayonida xatolik yuz berdi ❌ (Terminalni tekshiring)")
            
    except Exception as e:
        if CANCEL_TASKS.get(task_id) or CANCEL_TASKS.get(ffmpeg_task_id) or CANCEL_TASKS.get(upload_task_id, False): 
            await status_msg.edit_text("Jarayon foydalanuvchi tomonidan bekor qilindi ❌")
        else: 
            await status_msg.edit_text(f"Xatolik yuz berdi: {e}")
            
    finally:
        remove_temp_files(video_path, output_path)
        await state.clear()