from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu_keyboard(is_staff: bool = False, role: str = None) -> ReplyKeyboardMarkup:
    """Главное меню для пользователей"""
    keyboard = [
        [KeyboardButton(text="🚴‍♂️ Арендовать")],
        [KeyboardButton(text="👤 Профиль")],  # Убрали "Мои аренды"
        [KeyboardButton(text="🔧 Ремонт"), KeyboardButton(text="💳 Продлить")]
    ]
    
    if is_staff:
        if role == "admin":
            keyboard.append([KeyboardButton(text="👨‍💼 Админ панель")])
        else:
            keyboard.append([KeyboardButton(text="👨‍💼 Менеджер панель")])
    
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_phone_request_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для запроса номера телефона"""
    keyboard = [
        [KeyboardButton(text="📱 Поделиться номером", request_contact=True)]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)


def get_admin_panel_keyboard() -> ReplyKeyboardMarkup:
    """Админская панель (полные права)"""
    keyboard = [
        [KeyboardButton(text="📋 Документы")],
        [KeyboardButton(text="🚴‍♂️ Велосипеды")],
        [KeyboardButton(text="💰 Тарифы"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="👥 Пользователи"), KeyboardButton(text="⚙️ Настройки")],
        [KeyboardButton(text="◀️ Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_manager_panel_keyboard() -> ReplyKeyboardMarkup:
    """Менеджерская панель (ограниченные права)"""
    keyboard = [
        [KeyboardButton(text="📋 Документы")],
        [KeyboardButton(text="🚴‍♂️ Велосипеды")],
        [KeyboardButton(text="💰 Тарифы"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="◀️ Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_document_verification_keyboard(document_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для проверки документов"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_doc_{document_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_doc_{document_id}")
        ],
        [InlineKeyboardButton(text="🔄 Требует доработки", callback_data=f"revision_doc_{document_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_document_choice_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора типа документа"""
    keyboard = [
        [InlineKeyboardButton(text="📄 Паспорт", callback_data="doc_choice_passport")],
        [InlineKeyboardButton(text="🚗 Водительские права", callback_data="doc_choice_license")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard) 