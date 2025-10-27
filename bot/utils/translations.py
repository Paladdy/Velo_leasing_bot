"""
Утилиты для работы с переводами
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional


# Кэш для загруженных переводов
_translations_cache: Dict[str, Dict[str, Any]] = {}


def load_translations(language: str = "ru") -> Dict[str, Any]:
    """
    Загрузить переводы для указанного языка
    
    Args:
        language: Код языка (ru, tg, uz)
        
    Returns:
        Dict с переводами
    """
    if language in _translations_cache:
        return _translations_cache[language]
    
    locales_dir = Path(__file__).parent.parent.parent / "locales"
    translation_file = locales_dir / language / "messages.json"
    
    try:
        with open(translation_file, "r", encoding="utf-8") as f:
            translations = json.load(f)
            _translations_cache[language] = translations
            return translations
    except Exception as e:
        print(f"Error loading translations for {language}: {e}")
        # Fallback к русскому
        if language != "ru":
            return load_translations("ru")
        return {}


def get_text(key: str, language: str = "ru", **kwargs) -> str:
    """
    Получить переведенный текст по ключу
    
    Args:
        key: Ключ в формате "section.subsection.key" или "section.key"
        language: Код языка
        **kwargs: Параметры для форматирования (например, name="John")
        
    Returns:
        Переведенный текст
        
    Examples:
        >>> get_text("start.welcome_back", "ru", name="Иван")
        "👋 Добро пожаловать обратно, Иван!"
    """
    translations = load_translations(language)
    
    # Разбираем ключ (например, "start.welcome_back")
    keys = key.split(".")
    value = translations
    
    try:
        for k in keys:
            value = value[k]
        
        # Если есть параметры для форматирования
        if kwargs and isinstance(value, str):
            return value.format(**kwargs)
        
        return str(value)
    except (KeyError, TypeError) as e:
        # Если ключ не найден, возвращаем сам ключ (для отладки)
        print(f"Translation key not found: {key} for language {language}")
        
        # Пробуем fallback к русскому
        if language != "ru":
            return get_text(key, "ru", **kwargs)
        
        return f"[{key}]"


def get_texts(keys: Dict[str, str], language: str = "ru", **kwargs) -> Dict[str, str]:
    """
    Получить несколько переводов сразу
    
    Args:
        keys: Словарь {alias: key_path}
        language: Код языка
        **kwargs: Параметры для форматирования
        
    Returns:
        Dict с переводами {alias: translated_text}
        
    Example:
        >>> get_texts({
        ...     "welcome": "start.welcome_back",
        ...     "error": "common.error"
        ... }, "ru", name="Иван")
        {"welcome": "👋 Добро пожаловать обратно, Иван!", "error": "❌ Произошла ошибка"}
    """
    return {
        alias: get_text(key, language, **kwargs)
        for alias, key in keys.items()
    }


class TranslationHelper:
    """
    Хелпер для работы с переводами в обработчиках
    """
    
    def __init__(self, language: str = "ru"):
        self.language = language
        self._translations = load_translations(language)
    
    def get(self, key: str, **kwargs) -> str:
        """Получить перевод по ключу"""
        return get_text(key, self.language, **kwargs)
    
    def multiple(self, keys: Dict[str, str], **kwargs) -> Dict[str, str]:
        """Получить несколько переводов"""
        return get_texts(keys, self.language, **kwargs)
    
    @property
    def lang(self) -> str:
        """Получить код текущего языка"""
        return self.language


def get_translation_for_languages(key: str, languages: list = None, **kwargs) -> Dict[str, str]:
    """
    Получить перевод для нескольких языков сразу
    
    Args:
        key: Ключ перевода
        languages: Список языков (по умолчанию ["ru", "tg", "uz"])
        **kwargs: Параметры для форматирования
        
    Returns:
        Dict {language: translated_text}
        
    Example:
        >>> get_translation_for_languages("start.welcome_back", name="Иван")
        {
            "ru": "👋 Добро пожаловать обратно, Иван!",
            "tg": "👋 Хуш омадед, Иван!",
            "uz": "👋 Xush kelibsiz, Иван!"
        }
    """
    if languages is None:
        languages = ["ru", "tg", "uz"]
    
    return {
        lang: get_text(key, lang, **kwargs)
        for lang in languages
    }


# Константы для часто используемых языков
LANGUAGES = {
    "ru": {"code": "ru", "name": "Русский", "flag": "🇷🇺"},
    "tg": {"code": "tg", "name": "Тоҷикӣ", "flag": "🇹🇯"},
    "uz": {"code": "uz", "name": "O'zbek", "flag": "🇺🇿"}
}


def get_user_language(user) -> str:
    """
    Безопасно получить язык пользователя
    
    Args:
        user: Объект User из БД
        
    Returns:
        Код языка или "ru" по умолчанию
    """
    if user and hasattr(user, 'language'):
        return user.language or "ru"
    return "ru"

