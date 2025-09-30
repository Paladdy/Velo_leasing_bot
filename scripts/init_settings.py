import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.base import async_session_factory, init_db
from database.models.settings import SystemSettings
from sqlalchemy import select


async def init_default_settings():
    """Инициализировать настройки по умолчанию"""
    await init_db()
    
    async with async_session_factory() as session:
        # Проверяем, есть ли уже настройки
        result = await session.execute(select(SystemSettings))
        existing_settings = result.scalar_one_or_none()
        
        if existing_settings:
            print(f"✅ Настройки уже существуют (ID: {existing_settings.id})")
            print(f"📍 Адрес: {existing_settings.address}")
            print(f"📞 Телефон: {existing_settings.phone}")
            print(f"🕐 Часы работы: {existing_settings.working_hours}")
            return
        
        # Создаем настройки по умолчанию
        settings = SystemSettings(
            company_name="Velo Leasing",
            address="г. Химки, Московская область, ул. Рабочая, д. 2а",
            phone="+7 968 555 55 18",
            working_hours="Пн-Вс: 09:00 - 21:00",
            description="Прокат велосипедов в Химках",
            is_active=True,
            maintenance_mode=False
        )
        
        session.add(settings)
        await session.commit()
        
        print("✅ Настройки по умолчанию созданы!")
        print(f"📍 Адрес: {settings.address}")
        print(f"📞 Телефон: {settings.phone}")
        print(f"🕐 Часы работы: {settings.working_hours}")


if __name__ == "__main__":
    asyncio.run(init_default_settings())
