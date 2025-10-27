from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils.translations import get_text


def get_language_selection_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора языка"""
    keyboard = [
        [InlineKeyboardButton(text="Русский 🇷🇺", callback_data="lang_ru")],
        [InlineKeyboardButton(text="Тоҷикӣ 🇹🇯", callback_data="lang_tg")],
        [InlineKeyboardButton(text="O'zbek 🇺🇿", callback_data="lang_uz")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_main_menu_keyboard(is_staff: bool = False, role: str = None, language: str = "ru") -> ReplyKeyboardMarkup:
    """Главное меню для пользователей"""
    keyboard = [
        [KeyboardButton(text=get_text("menu.rent", language))],
        [KeyboardButton(text=get_text("menu.profile", language))],
        [KeyboardButton(text=get_text("menu.repair", language)), KeyboardButton(text=get_text("menu.extend", language))]
    ]
    
    if is_staff:
        if role == "admin":
            keyboard.append([KeyboardButton(text=get_text("menu.admin_panel", language))])
        else:
            keyboard.append([KeyboardButton(text=get_text("menu.manager_panel", language))])
    
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_phone_request_keyboard(language: str = "ru") -> ReplyKeyboardMarkup:
    """Клавиатура для запроса номера телефона"""
    keyboard = [
        [KeyboardButton(text=get_text("buttons.share_phone", language), request_contact=True)]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)


def get_admin_panel_keyboard(language: str = "ru") -> ReplyKeyboardMarkup:
    """Админская панель (полные права)"""
    keyboard = [
        [KeyboardButton(text=get_text("admin.documents", language))],
        [KeyboardButton(text=get_text("admin.bikes", language))],
        [KeyboardButton(text=get_text("admin.tariffs", language)), KeyboardButton(text=get_text("admin.statistics", language))],
        [KeyboardButton(text=get_text("admin.users", language)), KeyboardButton(text=get_text("admin.settings", language))],
        [KeyboardButton(text=get_text("common.back", language) + " " + get_text("common.main_menu", language).replace("🏠 ", ""))]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_manager_panel_keyboard(language: str = "ru") -> ReplyKeyboardMarkup:
    """Менеджерская панель (ограниченные права)"""
    keyboard = [
        [KeyboardButton(text=get_text("admin.documents", language))],
        [KeyboardButton(text=get_text("admin.bikes", language))],
        [KeyboardButton(text=get_text("admin.tariffs", language)), KeyboardButton(text=get_text("admin.statistics", language))],
        [KeyboardButton(text=get_text("common.back", language) + " " + get_text("common.main_menu", language).replace("🏠 ", ""))]
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


def get_document_choice_keyboard(language: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура для выбора типа документа"""
    keyboard = [
        [InlineKeyboardButton(text=get_text("documents.passport", language), callback_data="doc_choice_passport")],
        [InlineKeyboardButton(text=get_text("documents.driver_license", language), callback_data="doc_choice_license")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard) 