from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from database.base import async_session_factory
from database.models.settings import SystemSettings


class SettingsService:
    """Сервис для работы с настройками системы"""
    
    @staticmethod
    async def get_settings() -> SystemSettings:
        """Получить текущие настройки системы"""
        async with async_session_factory() as session:
            result = await session.execute(select(SystemSettings))
            settings = result.scalar_one_or_none()
            
            if not settings:
                # Создаем настройки по умолчанию
                settings = SystemSettings()
                session.add(settings)
                await session.commit()
                await session.refresh(settings)
            
            return settings
    
    @staticmethod
    async def update_contact_info(address: str = None, phone: str = None, email: str = None) -> bool:
        """Обновить контактную информацию"""
        async with async_session_factory() as session:
            try:
                # Получаем настройки
                result = await session.execute(select(SystemSettings))
                settings = result.scalar_one_or_none()
                
                if not settings:
                    settings = SystemSettings()
                    session.add(settings)
                    await session.flush()
                
                # Обновляем только переданные поля
                update_data = {}
                if address is not None:
                    update_data['address'] = address
                if phone is not None:
                    update_data['phone'] = phone
                if email is not None:
                    update_data['email'] = email
                
                if update_data:
                    await session.execute(
                        update(SystemSettings)
                        .where(SystemSettings.id == settings.id)
                        .values(**update_data)
                    )
                
                await session.commit()
                return True
                
            except Exception as e:
                await session.rollback()
                print(f"Error updating contact info: {e}")
                return False
    
    @staticmethod
    async def update_working_hours(general_hours: str = None, **day_hours) -> bool:
        """Обновить часы работы"""
        async with async_session_factory() as session:
            try:
                # Получаем настройки
                result = await session.execute(select(SystemSettings))
                settings = result.scalar_one_or_none()
                
                if not settings:
                    settings = SystemSettings()
                    session.add(settings)
                    await session.flush()
                
                # Обновляем часы работы
                update_data = {}
                
                if general_hours is not None:
                    update_data['working_hours'] = general_hours
                
                # Обновляем часы по дням недели
                day_mapping = {
                    'monday': 'working_hours_monday',
                    'tuesday': 'working_hours_tuesday',
                    'wednesday': 'working_hours_wednesday',
                    'thursday': 'working_hours_thursday',
                    'friday': 'working_hours_friday',
                    'saturday': 'working_hours_saturday',
                    'sunday': 'working_hours_sunday'
                }
                
                for day, value in day_hours.items():
                    if day in day_mapping and value is not None:
                        update_data[day_mapping[day]] = value
                
                if update_data:
                    await session.execute(
                        update(SystemSettings)
                        .where(SystemSettings.id == settings.id)
                        .values(**update_data)
                    )
                
                await session.commit()
                return True
                
            except Exception as e:
                await session.rollback()
                print(f"Error updating working hours: {e}")
                return False
    
    @staticmethod
    async def set_maintenance_mode(enabled: bool, message: str = None) -> bool:
        """Включить/выключить режим технических работ"""
        async with async_session_factory() as session:
            try:
                result = await session.execute(select(SystemSettings))
                settings = result.scalar_one_or_none()
                
                if not settings:
                    settings = SystemSettings()
                    session.add(settings)
                    await session.flush()
                
                await session.execute(
                    update(SystemSettings)
                    .where(SystemSettings.id == settings.id)
                    .values(
                        maintenance_mode=enabled,
                        maintenance_message=message
                    )
                )
                
                await session.commit()
                return True
                
            except Exception as e:
                await session.rollback()
                print(f"Error setting maintenance mode: {e}")
                return False
