from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    choosing_language = State()
    waiting_for_name = State()
    waiting_for_phone = State()
    choosing_document_type = State()
    waiting_for_main_document = State()
    waiting_for_selfie = State()
    registration_complete = State() 