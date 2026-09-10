from aiogram import Router, Bot, F, types
from aiogram.fsm.context import FSMContext
from keyboards import get_main_menu

router = Router()

# MAXSUS FILTER: Faqat video yoki nomi .mp4/.mkv bilan tugaydigan fayllarni o'tkazadi
def is_video_or_valid_document(message: types.Message):
    if message.video:
        return True
    if message.document:
        name = message.document.file_name
        if name:
            return name.lower().endswith(('.mp4', '.mkv', '.avi', '.mov'))
    return False

@router.message(is_video_or_valid_document)
async def handle_video(message: types.Message, state: FSMContext):
    
    # Nima kelganini to'g'ri o'qib olamiz
    video_obj = message.video if message.video else message.document
    file_name = video_obj.file_name if video_obj.file_name else "video.mp4"

    # Hajmni tekshiramiz
    if video_obj.file_size and video_obj.file_size > 20 * 1024 * 1024:
        await message.answer("Iltimos, 20 MB dan kichik video yuboring.")
        return

    # Agar bot eski holatda qotib qolgan bo'lsa, xotirani tozalaymiz
    await state.clear()
    
    # Video ID sini xotiraga saqlaymiz
    await state.update_data(video_file_id=video_obj.file_id)
    
    # Menyuni ko'rsatamiz
    await message.answer(
        f"Video qabul qilindi ({file_name})! Iltimos, kerakli amalni tanlang 👇",
        reply_markup=get_main_menu()
    )