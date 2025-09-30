from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from typing import List
from database.models.bike import Bike, BikeStatus
from database.models.user import User
from database.models.document import Document


def get_bike_management_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления велосипедами"""
    keyboard = [
        [InlineKeyboardButton(text="📋 Список", callback_data="admin_bikes_list")],
        [
            InlineKeyboardButton(text="🔧 Обслуживание", callback_data="admin_bikes_maintenance"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_bikes_stats")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_bikes_list_keyboard(bikes: List[Bike], page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    """Клавиатура со списком велосипедов для админа"""
    keyboard = []
    
    start = page * per_page
    end = start + per_page
    bikes_page = bikes[start:end]
    
    for bike in bikes_page:
        status_emoji = {
            BikeStatus.AVAILABLE: "✅",
            BikeStatus.RENTED: "🚴‍♂️", 
            BikeStatus.MAINTENANCE: "🔧",
            BikeStatus.BROKEN: "❌"
        }
        
        bike_text = f"{status_emoji.get(bike.status, '❓')} #{bike.number} - {bike.model}"
        keyboard.append([
            InlineKeyboardButton(text=bike_text, callback_data=f"admin_bike_view_{bike.id}")
        ])
    
    # Пагинация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_bikes_page_{page-1}"))
    
    nav_buttons.append(InlineKeyboardButton(text=f"📄 {page+1}", callback_data="current_page"))
    
    if end < len(bikes):
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_bikes_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_bike_management")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_bike_actions_keyboard(bike_id: int, current_status: BikeStatus) -> InlineKeyboardMarkup:
    """Клавиатура действий с велосипедом"""
    keyboard = []
    
    # Действия в зависимости от статуса
    if current_status == BikeStatus.AVAILABLE:
        keyboard.extend([
            [InlineKeyboardButton(text="🔧 Отправить на обслуживание", callback_data=f"bike_set_maintenance_{bike_id}")],
            [InlineKeyboardButton(text="❌ Пометить как сломанный", callback_data=f"bike_set_broken_{bike_id}")]
        ])
    elif current_status == BikeStatus.MAINTENANCE:
        keyboard.extend([
            [InlineKeyboardButton(text="✅ Вернуть в работу", callback_data=f"bike_set_available_{bike_id}")],
            [InlineKeyboardButton(text="❌ Пометить как сломанный", callback_data=f"bike_set_broken_{bike_id}")]
        ])
    elif current_status == BikeStatus.BROKEN:
        keyboard.extend([
            [InlineKeyboardButton(text="🔧 Отправить на обслуживание", callback_data=f"bike_set_maintenance_{bike_id}")],
            [InlineKeyboardButton(text="✅ Отремонтирован", callback_data=f"bike_set_available_{bike_id}")]
        ])
    elif current_status == BikeStatus.RENTED:
        keyboard.append([InlineKeyboardButton(text="🏁 Завершить аренду", callback_data=f"bike_end_rental_{bike_id}")])
    
    # Общие действия
    keyboard.extend([
        [
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"bike_edit_{bike_id}"),
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"bike_delete_{bike_id}")
        ],
        [InlineKeyboardButton(text="◀️ Назад к списку", callback_data="admin_bikes_list")]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_bike_status_keyboard(bike_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для изменения статуса велосипеда"""
    keyboard = [
        [InlineKeyboardButton(text="✅ Доступен", callback_data=f"bike_status_{bike_id}_available")],
        [InlineKeyboardButton(text="🔧 На обслуживании", callback_data=f"bike_status_{bike_id}_maintenance")],
        [InlineKeyboardButton(text="❌ Сломан", callback_data=f"bike_status_{bike_id}_broken")],
        [InlineKeyboardButton(text="◀️ Отмена", callback_data=f"admin_bike_view_{bike_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_document_verification_keyboard(document_id: int, user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для проверки документов"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"doc_approve_{document_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"doc_reject_{document_id}")
        ],
        [InlineKeyboardButton(text="🔄 Требует доработки", callback_data=f"doc_revision_{document_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_user_docs_{user_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard) 