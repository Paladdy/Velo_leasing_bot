"""
Утилиты для работы с мультиязычностью (i18n)
"""
from pathlib import Path
from aiogram_i18n import I18nMiddleware
from aiogram_i18n.cores import FluentRuntimeCore
from sqlalchemy import select

from database.base import async_session_factory
from database.models.user import User


# Путь к папке с локализациями
LOCALES_DIR = Path(__file__).parent.parent.parent / "locales"


def setup_i18n() -> I18nMiddleware:
    """
    Настройка i18n middleware
    
    Returns:
        I18nMiddleware: Настроенный middleware для мультиязычности
    """
    i18n_middleware = I18nMiddleware(
        core=FluentRuntimeCore(
            path=LOCALES_DIR,
            raise_key_error=False,  # Не выбрасывать ошибку, если ключ не найден
            locales_map={
                "ru": "ru",  # Русский
                "tg": "tg",  # Таджикский  
                "uz": "uz",  # Узбекский
            }
        ),
        default_locale="ru",
        manager=UserLanguageManager()
    )
    
    return i18n_middleware


class UserLanguageManager:
    """
    Менеджер для получения языка пользователя из базы данных
    """
    
    async def get_locale(self, event_from_user=None, data: dict = None) -> str:
        """
        Получить язык пользователя
        
        Args:
            event_from_user: Объект пользователя от Telegram
            data: Дополнительные данные
            
        Returns:
            str: Код языка (ru, tg, uz)
        """
        if not event_from_user:
            return "ru"
        
        telegram_id = event_from_user.id
        
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(User.language).where(User.telegram_id == telegram_id)
                )
                language = result.scalar_one_or_none()
                
                if language:
                    return language
        except Exception as e:
            print(f"Error getting user language: {e}")
        
        # По умолчанию русский
        return "ru"


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

