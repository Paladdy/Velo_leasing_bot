#!/usr/bin/env python3
"""
Скрипт для проверки документов в базе данных
"""
import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.base import async_session_factory
from database.models.user import User
from database.models.document import Document
from sqlalchemy import select
from sqlalchemy.orm import selectinload


async def check_documents():
    """Проверить документы в базе данных"""
    
    async with async_session_factory() as session:
        # Получаем всех пользователей с документами
        result = await session.execute(
            select(User)
            .options(selectinload(User.documents))
            .order_by(User.id)
        )
        users = result.scalars().all()
        
        print(f"{'='*80}")
        print(f"📊 ПРОВЕРКА ДОКУМЕНТОВ В БАЗЕ ДАННЫХ")
        print(f"{'='*80}\n")
        
        if not users:
            print("❌ Пользователи не найдены")
            return
        
        for user in users:
            print(f"👤 Пользователь ID: {user.id}")
            print(f"   Имя: {user.full_name}")
            print(f"   Telegram ID: {user.telegram_id}")
            print(f"   Статус: {user.status.value}")
            print(f"   Документов: {len(user.documents)}")
            
            if user.documents:
                print(f"\n   📄 Документы:")
                for doc in user.documents:
                    file_exists = "✅" if Path(doc.file_path).exists() else "❌"
                    print(f"      • ID: {doc.id}")
                    print(f"        Тип: {doc.document_type.value}")
                    print(f"        Статус: {doc.status.value}")
                    print(f"        Путь: {doc.file_path}")
                    print(f"        Файл существует: {file_exists}")
                    if doc.uploaded_at:
                        print(f"        Загружен: {doc.uploaded_at.strftime('%d.%m.%Y %H:%M:%S')}")
                    print()
            else:
                print(f"   ⚠️  Документов нет\n")
            
            print(f"{'-'*80}\n")


async def check_specific_user(telegram_id: int):
    """Проверить документы конкретного пользователя"""
    
    async with async_session_factory() as session:
        result = await session.execute(
            select(User)
            .options(selectinload(User.documents))
            .where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"❌ Пользователь с Telegram ID {telegram_id} не найден")
            return
        
        print(f"{'='*80}")
        print(f"👤 {user.full_name} (Telegram ID: {telegram_id})")
        print(f"{'='*80}\n")
        print(f"User ID в БД: {user.id}")
        print(f"Статус: {user.status.value}")
        print(f"Роль: {user.role.value}")
        print(f"Документов в БД: {len(user.documents)}\n")
        
        if user.documents:
            print(f"📄 Список документов:\n")
            for i, doc in enumerate(user.documents, 1):
                file_exists = Path(doc.file_path).exists()
                print(f"{i}. Документ ID: {doc.id}")
                print(f"   Тип: {doc.document_type.value}")
                print(f"   Статус: {doc.status.value}")
                print(f"   Путь: {doc.file_path}")
                print(f"   Файл существует: {'✅ Да' if file_exists else '❌ Нет'}")
                if not file_exists:
                    print(f"   ⚠️  ВНИМАНИЕ: Файл не найден на диске!")
                if doc.uploaded_at:
                    print(f"   Загружен: {doc.uploaded_at.strftime('%d.%m.%Y %H:%M:%S')}")
                if doc.verified_at:
                    print(f"   Проверен: {doc.verified_at.strftime('%d.%m.%Y %H:%M:%S')}")
                print()
        else:
            print("⚠️  У пользователя НЕТ документов в базе данных!\n")
            print("Возможные причины:")
            print("  1. Документы не были загружены")
            print("  2. Произошла ошибка при сохранении")
            print("  3. Документы были удалены")


async def main():
    """Главная функция"""
    if len(sys.argv) > 1:
        try:
            telegram_id = int(sys.argv[1])
            await check_specific_user(telegram_id)
        except ValueError:
            print("❌ Ошибка: Telegram ID должен быть числом")
            print("Использование: python check_documents.py [TELEGRAM_ID]")
    else:
        await check_documents()


if __name__ == "__main__":
    asyncio.run(main())

