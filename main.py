import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from loguru import logger
import redis.asyncio as redis

from config.settings import settings
from database.base import init_db
from bot.handlers.common.start import router as start_router
from bot.handlers.client.rental import router as rental_router
from bot.handlers.client.profile import router as profile_router
from bot.handlers.client.repair import router as repair_router
from bot.handlers.admin.admin_panel import router as admin_panel_router
from bot.handlers.admin.bike_management import router as bike_management_router
from bot.handlers.admin.document_verification import router as document_verification_router
from bot.handlers.admin.settings_management import router as settings_management_router


async def main():
    """Главная функция запуска бота"""
    
    # Настройка логирования
    logger.add(
        "logs/bot.log",
        rotation="1 day",
        retention="7 days",
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    )
    
    logger.info("🚀 Запуск бота...")
    
    # Инициализация бота
    bot = Bot(token=settings.bot_token)
    
    # Выбор хранилища для FSM состояний
    try:
        # Пытаемся подключиться к Redis
        redis_client = redis.from_url(settings.redis_url)
        await redis_client.ping()
        storage = RedisStorage(redis_client)
        logger.info("✅ Подключение к Redis успешно")
    except Exception as e:
        # Если Redis недоступен, используем память
        logger.warning(f"⚠️ Redis недоступен ({e}), используем MemoryStorage")
        storage = MemoryStorage()
    
    dp = Dispatcher(storage=storage)
    
    # Мультиязычность настроена через bot/utils/translations.py (простые JSON переводы)
    logger.info("✅ Мультиязычность (i18n) готова к использованию")
    
    # Регистрация роутеров в правильном порядке
    # 1. Команды (высший приоритет - обработка /start и регистрация)
    dp.include_router(start_router)
    
    # 2. Административные функции (специфичные обработчики)
    dp.include_router(admin_panel_router)
    dp.include_router(bike_management_router)
    dp.include_router(document_verification_router)
    
    # 3. Клиентские функции
    dp.include_router(rental_router)
    dp.include_router(profile_router)
    dp.include_router(repair_router)
    
    # 4. Настройки (могут содержать универсальные обработчики)
    dp.include_router(settings_management_router)
    
    logger.info("✅ Все роутеры зарегистрированы")
    
    try:
        # Инициализация базы данных
        logger.info("🗄️ Инициализация базы данных...")
        await init_db()
        logger.info("✅ База данных инициализирована")
        
        # Запуск бота
        logger.info("🤖 Бот запущен и готов к работе!")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске: {e}")
        raise
    finally:
        await bot.session.close()
        if hasattr(storage, 'close'):
            await storage.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        raise 