"""
Утилиты для работы с мультиязычностью (i18n)
Упрощенная версия без FluentRuntimeCore
"""
from sqlalchemy import select

from database.base import async_session_factory
from database.models.user import User


def setup_i18n():
    """
    Заглушка для совместимости
    В этом проекте мы используем простую систему переводов через JSON
    См. bot/utils/translations.py
    """
    # Middleware не нужен, так как мы используем прямые вызовы get_text()
    return None


async def change_user_language(telegram_id: int, new_language: str) -> bool:
    """
    Изменить язык пользователя в базе данных
    
    Args:
        telegram_id: Telegram ID пользователя
        new_language: Новый язык (ru, tg, uz)
        
    Returns:
        bool: True если успешно изменен, False если ошибка
    """
    if new_language not in ["ru", "tg", "uz"]:
        return False
    
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                user.language = new_language
                await session.commit()
                return True
    except Exception as e:
        print(f"Error changing user language: {e}")
    
    return False


def get_language_name(language_code: str) -> str:
    """
    Получить название языка по его коду
    
    Args:
        language_code: Код языка (ru, tg, uz)
        
    Returns:
        str: Название языка с флагом
    """
    languages = {
        "ru": "Русский 🇷🇺",
        "tg": "Тоҷикӣ 🇹🇯",
        "uz": "O'zbek 🇺🇿"
    }
    return languages.get(language_code, "Русский 🇷🇺")

