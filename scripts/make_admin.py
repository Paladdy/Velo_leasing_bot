import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.base import async_session_factory, init_db
from database.models.user import User, UserRole, UserStatus
from sqlalchemy import select


async def make_admin(telegram_id: int):
    """Назначить пользователя администратором"""
    await init_db()
    
    async with async_session_factory() as session:
        # Находим пользователя по telegram_id
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"❌ Пользователь с ID {telegram_id} не найден в базе данных")
            print("💡 Сначала зарегистрируйтесь в боте командой /start")
            return
        
        # Назначаем роль администратора и верифицируем
        old_role = user.role.value
        user.role = UserRole.ADMIN
        user.status = UserStatus.VERIFIED  # Админы автоматически верифицированы
        
        await session.commit()
        
        print(f"✅ Пользователь {user.full_name} (ID: {telegram_id}) назначен администратором")
        print(f"🔄 Роль изменена: {old_role} → {user.role.value}")
        print(f"✅ Статус: {user.status.value}")


if __name__ == "__main__":
    # ID администратора
    admin_id = 6080737314
    asyncio.run(make_admin(admin_id)) 