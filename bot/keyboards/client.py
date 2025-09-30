from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from typing import List
from database.models.bike import Bike


def get_rental_type_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа аренды"""
    keyboard = [
        [
            InlineKeyboardButton(text="⏰ Почасовая", callback_data="rental_type_hourly"),
            InlineKeyboardButton(text="📅 Посуточная", callback_data="rental_type_daily")
        ],
        [
            InlineKeyboardButton(text="🛒 Выкуп с рассрочкой", callback_data="rental_type_installment"),
            InlineKeyboardButton(text="🎯 Индивидуальная", callback_data="rental_type_custom")
        ],
        [InlineKeyboardButton(text="🏪 Выбор на месте", callback_data="rental_onsite")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_bikes_keyboard(bikes: List[Bike]) -> InlineKeyboardMarkup:
    """Клавиатура со списком доступных велосипедов"""
    keyboard = []
    
    for bike in bikes:
        battery_count = len(bike.batteries) if bike.batteries else 0
        bike_text = f"🚴‍♂️ #{bike.number} - {bike.model}"
        if battery_count > 0:
            bike_text += f" (🔋×{battery_count})"
        
        keyboard.append([
            InlineKeyboardButton(
                text=bike_text, 
                callback_data=f"select_bike_{bike.id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_duration_keyboard(rental_type: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора продолжительности аренды"""
    keyboard = []
    
    if rental_type == "hourly":
        durations = [
            ("1 час", "1h"), ("3 часа", "3h"), ("6 часов", "6h"), 
            ("12 часов", "12h"), ("24 часа", "24h")
        ]
    else:  # daily
        durations = [
            ("1 день", "1d"), ("3 дня", "3d"), ("7 дней", "7d"),
            ("14 дней", "14d"), ("30 дней", "30d")
        ]
    
    for text, value in durations:
        keyboard.append([InlineKeyboardButton(text=text, callback_data=f"duration_{value}")])
    
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_rental_type")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_rental_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения аренды"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Подтвердить и оплатить", callback_data="confirm_rental"),
            InlineKeyboardButton(text="✏️ Изменить", callback_data="edit_rental")
        ],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_rental")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard) 