import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.base import async_session_factory, init_db
from database.models.bike import Bike, Battery, BikeStatus, BatteryStatus
from sqlalchemy import select, text


async def add_test_bikes():
    """Добавить тестовые велосипеды в базу данных"""
    await init_db()
    
    async with async_session_factory() as session:
        # Проверяем, есть ли уже велосипеды
        existing_bikes = await session.execute(text("SELECT COUNT(*) FROM bikes"))
        count = existing_bikes.scalar()
        
        if count > 0:
            print(f"В базе уже есть {count} велосипедов. Пропускаем добавление.")
            return
        
        # Создаем тестовые велосипеды
        bikes_data = [
            {
                "number": "VL001",
                "model": "Urban Cruiser",
                "description": "Удобный городской велосипед",
                "location": "Центральная точка",
                "price_per_hour": 150.00,
                "price_per_day": 800.00,
                "battery_count": 1
            },
            {
                "number": "VL002", 
                "model": "Mountain Explorer",
                "description": "Горный велосипед для активного отдыха",
                "location": "Парк Горького",
                "price_per_hour": 200.00,
                "price_per_day": 1200.00,
                "battery_count": 2
            },
            {
                "number": "VL003",
                "model": "Speed Demon",
                "description": "Спортивный велосипед для быстрой езды",
                "location": "Центральная точка",
                "price_per_hour": 180.00,
                "price_per_day": 1000.00,
                "battery_count": 1
            },
            {
                "number": "VL004",
                "model": "Family Comfort",
                "description": "Семейный велосипед с корзиной",
                "location": "Детский парк",
                "price_per_hour": 120.00,
                "price_per_day": 600.00,
                "battery_count": 3
            },
            {
                "number": "VL005",
                "model": "Electric Power",
                "description": "Электровелосипед с мощным мотором",
                "location": "Центральная точка",
                "price_per_hour": 300.00,
                "price_per_day": 1800.00,
                "battery_count": 2
            }
        ]
        
        for bike_data in bikes_data:
            # Создаем велосипед
            bike = Bike(
                number=bike_data["number"],
                model=bike_data["model"],
                description=bike_data["description"],
                location=bike_data["location"],
                price_per_hour=bike_data["price_per_hour"],
                price_per_day=bike_data["price_per_day"],
                status=BikeStatus.AVAILABLE
            )
            session.add(bike)
            await session.flush()  # Получаем ID велосипеда
            
            # Создаем батарейки для велосипеда
            for i in range(bike_data["battery_count"]):
                battery = Battery(
                    number=f"{bike_data['number']}-BAT{i+1:02d}",
                    bike_id=bike.id,
                    capacity="48V 15Ah",
                    size="Standard",
                    status=BatteryStatus.AVAILABLE
                )
                session.add(battery)
        
        await session.commit()
        print(f"✅ Добавлено {len(bikes_data)} тестовых велосипедов с батарейками")
        
        # Выводим информацию о созданных велосипедах
        print("\n📋 Созданные велосипеды:")
        for bike_data in bikes_data:
            print(f"🚴‍♂️ {bike_data['number']} - {bike_data['model']} ({bike_data['battery_count']} батареек)")


if __name__ == "__main__":
    asyncio.run(add_test_bikes()) 