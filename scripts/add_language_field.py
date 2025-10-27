"""
Скрипт для добавления поля language в таблицу users
"""
import asyncio
from sqlalchemy import text
from database.base import async_session_factory, engine


async def add_language_field():
    """Добавляет поле language в таблицу users"""
    
    async with engine.begin() as conn:
        # Проверяем, существует ли уже поле language
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='language'
        """)
        
        result = await conn.execute(check_query)
        exists = result.fetchone()
        
        if exists:
            print("✅ Поле 'language' уже существует в таблице 'users'")
            return
        
        # Добавляем поле language
        alter_query = text("""
            ALTER TABLE users 
            ADD COLUMN language VARCHAR(5) NOT NULL DEFAULT 'ru'
        """)
        
        await conn.execute(alter_query)
        print("✅ Поле 'language' успешно добавлено в таблицу 'users'")


async def main():
    """Главная функция"""
    try:
        print("🔄 Начало миграции: добавление поля language...")
        await add_language_field()
        print("✅ Миграция завершена успешно!")
    except Exception as e:
        print(f"❌ Ошибка при выполнении миграции: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

