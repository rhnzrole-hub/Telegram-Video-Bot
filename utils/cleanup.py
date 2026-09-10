import os

def remove_temp_files(*filepaths):
    """ Berilgan fayl yo'llarini kompyuterdan xavfsiz o'chiradi """
    for path in filepaths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
                print(f"🗑 Tozalandi: {path}")
            except Exception as e:
                print(f"⚠️ O'chirishda xatolik ({path}): {e}")