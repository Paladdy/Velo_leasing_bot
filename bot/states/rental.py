from aiogram.fsm.state import State, StatesGroup


class RentalStates(StatesGroup):
    choosing_bike = State()
    choosing_rental_type = State()
    choosing_duration = State()
    confirming_rental = State()
    waiting_payment = State()
    rental_active = State() 