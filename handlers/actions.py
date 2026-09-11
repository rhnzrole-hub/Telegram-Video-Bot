import os
import uuid
from aiogram import Router, Bot, F, types
from aiogram.fsm.context import FSMContext
from states import ProcessState
from keyboards import get_main_menu, get_streams_keyboard
from services.ffmpeg_service import get_video_streams, apply_letterbox, get_video_duration
from utils.progress import ProgressTracker, download_with_progress, CANCEL_TASKS
from utils.cleanup import remove_temp_files

router = Router()

@router.callback_query(F.data == "action_cancel")
async def action_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await callback.message.edit_text("Amal bekor qilindi ❌. Boshqa amalni tanlashingiz yoki yangi video yuborishingiz mumkin.")
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
        await status_msg.edit_text("Video tayyor! ✅\n\nEndi menga bu videoga qo'shmoqchi bo'lgan **AUDIO** faylini yuboring.")
    except Exception as e:
        if CANCEL_TASKS.get(task_id): await status_msg.edit_text("Yuklab olish bekor qilindi ❌")
        else: await status_msg.edit_text(f"Yuklab olishda xatolik: {e}")
    finally:
        CANCEL_TASKS.pop(task_id, None)

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
        await status_msg.edit_text("Video tayyor! ✅\n\nEndi menga **.srt** yoki **.ass** formatidagi Subtitr faylini yuboring.")
    except Exception as e:
        if CANCEL_TASKS.get(task_id): await status_msg.edit_text("Yuklab olish bekor qilindi ❌")
        else: await status_msg.edit_text(f"Yuklab olishda xatolik: {e}")
    finally:
        CANCEL_TASKS.pop(task_id, None)

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
        CANCEL_TASKS.pop(task_id, None)
        return

    CANCEL_TASKS.pop(task_id, None)
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
async def ask_letterbox_split(callback: types.CallbackQuery):
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🎞 Butun videoni qayta ishlash", callback_data="lb_process_whole")],
        [types.InlineKeyboardButton(text="✂️ Vaqt oralig'ida qirqish", callback_data="lb_process_trim")],
        [types.InlineKeyboardButton(text="❌ Bekor qilish", callback_data="action_cancel")]
    ])
    await callback.message.edit_text("Letterboxing jarayoni uchun amalni tanlang 👇", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "lb_process_whole")
async def process_whole_video(callback: types.CallbackQuery, bot: Bot, state: FSMContext):
    await callback.answer()
    status_msg = await callback.message.edit_text("Video tayyorlanmoqda ⏳...")
    await start_letterbox_task(status_msg, bot, state, 0.0, None)

@router.callback_query(F.data == "lb_process_trim")
async def ask_trim_time(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ProcessState.waiting_for_trim_time)
    text = (
        "Iltimos, qirqmoqchi bo'lgan vaqt oralig'ingizni kiriting.\n\n"
        "Format: `Boshlanish_vaqti - Tugash_vaqti` (HH:MM:SS)\n"
        "Masalan: `00:00:00 - 00:09:09`\n"
    )
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()

@router.message(ProcessState.waiting_for_trim_time)
async def process_trim_time(message: types.Message, bot: Bot, state: FSMContext):
    text = message.text.strip()
    try:
        if "-" not in text:
            raise ValueError
            
        start_str, end_str = text.split("-")
        
        def parse_time(t_str):
            parts = t_str.strip().split(":")
            if len(parts) == 3: return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            elif len(parts) == 2: return float(parts[0]) * 60 + float(parts[1])
            return float(parts[0])
        
        start_sec = parse_time(start_str)
        end_sec = parse_time(end_str)
        
        if start_sec >= end_sec:
            return await message.answer("❌ Tugash vaqti boshlanish vaqtidan katta bo'lishi kerak. Qaytadan kiriting:")
        
        duration = end_sec - start_sec
        await state.set_state(None)
        
        status_msg = await message.answer("Vaqt qabul qilindi ✅ Video tayyorlanmoqda ⏳...")
        await start_letterbox_task(status_msg, bot, state, start_sec, duration)
        
    except Exception:
        await message.answer("❌ Xato format! Iltimos, `00:00:00 - 00:09:09` formatida kiriting.")

async def start_letterbox_task(status_msg: types.Message, bot: Bot, state: FSMContext, start_sec: float, duration: float = None):
    data = await state.get_data()
    video_file_id = data.get("video_file_id")
    video_path = data.get("video_path")

    if not video_file_id:
        return await status_msg.edit_text("Video topilmadi.")

    task_id = str(uuid.uuid4())[:8]
    output_path = None

    try:
        video_path = await download_video_if_needed(bot, video_file_id, video_path, state, status_msg, task_id)
        await status_msg.edit_text("Videoning davomiyligi aniqlanmoqda ⏳...")
        
        if duration is None:
            duration = await get_video_duration(video_path)
            
        ffmpeg_task_id = str(uuid.uuid4())[:8]
        ffmpeg_tracker = ProgressTracker(status_msg, "Qayta ishlanmoqda (Letterbox)", "video.mkv", ffmpeg_task_id)
        output_path = os.path.join("temp", f"{uuid.uuid4()}_16x9.mkv")
        
        success = await apply_letterbox(video_path=video_path, output_path=output_path, tracker=ffmpeg_tracker, total_duration=duration, start_time=start_sec, duration=duration)
        
        if success:
            await status_msg.edit_text("Fayl Telegramga yuklanmoqda 🚀 (Local API)...")
            result = types.FSInputFile(output_path)
            await status_msg.answer_document(document=result, caption="Videongiz 16:9 formatga muvaffaqiyatli o'tkazildi! 🎬")
            await status_msg.delete()
        else:
            await status_msg.edit_text("Xatolik yuz berdi ❌ (Terminalni tekshiring)")
    
    except Exception as e:
        if CANCEL_TASKS.get(task_id) or CANCEL_TASKS.get(ffmpeg_task_id): 
            await status_msg.edit_text("Jarayon foydalanuvchi tomonidan bekor qilindi ❌")
        else: 
            await status_msg.edit_text(f"Xatolik yuz berdi: {e}")
    finally:
        remove_temp_files(output_path)
        CANCEL_TASKS.pop(task_id, None)
        CANCEL_TASKS.pop(ffmpeg_task_id, None)
        await state.set_state(None)