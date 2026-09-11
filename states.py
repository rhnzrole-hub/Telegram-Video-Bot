from aiogram.fsm.state import State, StatesGroup

class ProcessState(StatesGroup):
    waiting_for_audio = State()
    waiting_for_subtitle = State()
    waiting_for_metadata_value = State()
    waiting_for_trim_time = State()