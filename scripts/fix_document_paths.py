#!/usr/bin/env python3
"""
Скрипт для исправления путей к документам в базе данных.
Конвертирует относительные пути в абсолютные.
"""

import asyncio
import os
from pathlib import Path
from sqlalchemy import select, update

# Добавляем корневую директорию проекта в путь
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.base import async_session_factory
from database.models.document import Document


async def fix_document_paths():
    """Исправить пути к документам в базе данных"""
    
    # Получаем абсолютный путь к корню проекта
    project_root = Path(__file__).parent.parent
    
    async with async_session_factory() as session:
        # Получаем все документы
        result = await session.execute(select(Document))
        documents = result.scalars().all()
        
        print(f"📄 Найдено документов в базе данных: {len(documents)}")
        
        updated_count = 0
        for doc in documents:
            old_path = doc.file_path
            
            # Проверяем, является ли путь относительным
            if not os.path.isabs(old_path):
                # Конвертируем в абсолютный путь
                new_path = (project_root / old_path).absolute()
                
                # Проверяем, существует ли файл
                if new_path.exists():
                    doc.file_path = str(new_path)
                    updated_count += 1
                    print(f"✅ Обновлен путь для документа ID {doc.id}:")
                    print(f"   Старый: {old_path}")
                    print(f"   Новый:  {new_path}")
                else:
                    print(f"⚠️  Файл не найден для документа ID {doc.id}: {new_path}")
            else:
                # Путь уже абсолютный, проверяем существование файла
                if not Path(old_path).exists():
                    print(f"⚠️  Файл не найден для документа ID {doc.id}: {old_path}")
        
        if updated_count > 0:
            await session.commit()
            print(f"\n✅ Обновлено записей: {updated_count}")
        else:
            print(f"\n✅ Все пути уже корректны")


async def main():
    """Главная функция"""
    print("🔧 Исправление путей к документам в базе данных...\n")
    try:
        await fix_document_paths()
        print("\n✅ Готово!")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

