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
        new_language: Новый язык (ru, tg, uz, ky)
        
    Returns:
        bool: True если успешно изменен, False если ошибка
    """
    print(f"🔄 change_user_language: telegram_id={telegram_id}, new_language={new_language}")
    
    if new_language not in ["ru", "tg", "uz", "ky"]:
        print(f"❌ Неподдерживаемый язык: {new_language}")
        return False
    
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                old_lang = user.language
                user.language = new_language
                await session.commit()
                print(f"✅ Язык изменен: {old_lang} → {new_language} для пользователя {telegram_id}")
                return True
            else:
                print(f"❌ Пользователь {telegram_id} не найден")
                return False
    except Exception as e:
        print(f"❌ Error changing user language: {e}")
        import traceback
        traceback.print_exc()
    
    return False


def get_language_name(language_code: str) -> str:
    """
    Получить название языка по его коду
    
    Args:
        language_code: Код языка (ru, tg, uz, ky)
        
    Returns:
        str: Название языка с флагом
    """
    languages = {
        "ru": "Русский 🇷🇺",
        "tg": "Тоҷикӣ 🇹🇯",
        "uz": "O'zbek 🇺🇿",
        "ky": "Кыргызча 🇰🇬"
    }
    return languages.get(language_code, "Русский 🇷🇺")

