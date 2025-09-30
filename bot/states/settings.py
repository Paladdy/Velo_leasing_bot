from aiogram.fsm.state import State, StatesGroup


class SettingsStates(StatesGroup):
    editing_general_hours = State()
    editing_address = State()
    editing_phone = State()
    editing_email = State()
