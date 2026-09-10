from aiogram.fsm.state import StatesGroup, State

class ProcessState(StatesGroup):
    waiting_for_audio = State()
    waiting_for_subtitle = State()
    waiting_for_metadata_value = State()