from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu():
    # Tugmalarni qatorlarga ajratib joylaymiz
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎵 Videoga Audio qo'shish", callback_data="action_add_audio")],
        [InlineKeyboardButton(text="💬 Subtitr qo'shish", callback_data="action_add_subtitle")],
        [InlineKeyboardButton(text="📝 Metadata Editor", callback_data="action_edit_metadata")],
        [InlineKeyboardButton(text="🎞 Letterboxing (16:9)", callback_data="action_letterbox")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="action_cancel")]
    ])
    return keyboard

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎵 Videoga Audio qo'shish", callback_data="action_add_audio")],
        [InlineKeyboardButton(text="💬 Subtitr qo'shish", callback_data="action_add_subtitle")],
        [InlineKeyboardButton(text="📝 Metadata Editor", callback_data="action_edit_metadata")],
        [InlineKeyboardButton(text="🎞 Letterboxing (16:9)", callback_data="action_letterbox")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="action_cancel")]
    ])
    return keyboard

def get_streams_keyboard(streams: list, changes: dict = None):
    if changes is None:
        changes = {}
        
    keyboard = []
    for stream in streams:
        codec_type = stream.get('codec_type')
        index = str(stream.get('index')) # Indexni matn (string) sifatida olamiz
        tags = stream.get('tags', {})
        
        # Agar xotirada o'zgarish bo'lsa o'shani olamiz, bo'lmasa videodagi originalini
        lang = changes.get(index, {}).get('language', tags.get('language', 'N/A'))
        title = changes.get(index, {}).get('title', tags.get('title', 'N/A'))
        
        icon = "🎵 Audio" if codec_type == "audio" else "💬 Subtitr"
        
        # O'zgarganligini bildirib turish uchun qalamchani qo'shamiz
        changed_mark = "✏️ " if index in changes else ""
        btn_text = f"{changed_mark}{icon} #{index} | Til: {lang} | Nom: {title}"
        
        keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"stream_{index}")])
        
    # YAKUNLASH TUGMASI
    keyboard.append([InlineKeyboardButton(text="✅ Yakunlash (Yuklash)", callback_data="meta_finish")])
    keyboard.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="action_cancel")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_metadata_action_keyboard(stream_index: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Nomini (Title) o'zgartirish", callback_data=f"meta_{stream_index}_title")],
        [InlineKeyboardButton(text="🌐 Tilini (Language) o'zgartirish", callback_data=f"meta_{stream_index}_language")],
        [InlineKeyboardButton(text="🔙 Ortga", callback_data="action_edit_metadata")]
    ])