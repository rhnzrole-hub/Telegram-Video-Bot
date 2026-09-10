from aiogram import Router, F, types
from utils.progress import CANCEL_TASKS

router = Router()

@router.callback_query(F.data.startswith("prog_refresh_"))
async def refresh_progress(callback: types.CallbackQuery):
    # Orqa fondagi jarayon shundoq ham o'zini yangilab turadi
    await callback.answer("Jarayon yangilanmoqda 🔄...", show_alert=False)

@router.callback_query(F.data.startswith("prog_cancel_"))
async def cancel_progress(callback: types.CallbackQuery):
    task_id = callback.data.split("_")[2]
    # Bekor qilish tugmasi bosilganda xotiraga True yozib qo'yamiz
    CANCEL_TASKS[task_id] = True
    await callback.answer("Jarayon to'xtatilmoqda ❌...", show_alert=True)