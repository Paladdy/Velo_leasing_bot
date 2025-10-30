"""
Сервис для очистки orphaned файлов (файлы без записей в БД).
Запускается периодически как background задача.
"""
import os
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Set

from sqlalchemy import select
from database.base import async_session_factory
from database.models.document import Document
from config.settings import settings


class CleanupService:
    """Сервис для очистки временных и orphaned файлов"""
    
    def __init__(self):
        self.upload_dir = self._get_upload_dir()
    
    def _get_upload_dir(self) -> Path:
        """Получить абсолютный путь к директории загрузок"""
        if os.path.isabs(settings.upload_path):
            return Path(settings.upload_path)
        else:
            # Получаем абсолютный путь от корня проекта
            project_root = Path(__file__).parent.parent
            return project_root / settings.upload_path
    
    async def cleanup_orphaned_files(self, max_age_hours: int = 48) -> dict:
        """
        Удалить файлы, которые:
        1. Не имеют записи в БД
        2. Старше max_age_hours часов
        
        Args:
            max_age_hours: Максимальный возраст файла в часах
            
        Returns:
            dict: Статистика {deleted: int, errors: int, kept: int}
        """
        print(f"\n{'='*60}")
        print(f"🧹 Starting cleanup of orphaned files (age > {max_age_hours}h)")
        print(f"{'='*60}")
        
        if not self.upload_dir.exists():
            print(f"⚠️  Upload directory does not exist: {self.upload_dir}")
            return {"deleted": 0, "errors": 0, "kept": 0}
        
        # Получаем список всех файлов в БД
        async with async_session_factory() as session:
            result = await session.execute(select(Document.file_path))
            db_files = {Path(row[0]) for row in result.all()}
        
        print(f"📊 Files in database: {len(db_files)}")
        
        # Проверяем все файлы в директории uploads
        deleted = 0
        errors = 0
        kept = 0
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        for file_path in self.upload_dir.glob("*"):
            if not file_path.is_file():
                continue
            
            # Пропускаем .gitkeep и другие служебные файлы
            if file_path.name.startswith("."):
                continue
            
            file_absolute = file_path.absolute()
            
            # Проверяем, есть ли файл в БД
            if file_absolute in db_files or str(file_absolute) in {str(f) for f in db_files}:
                kept += 1
                continue
            
            # Файл не в БД - проверяем возраст
            try:
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                
                if file_mtime < cutoff_time:
                    # Файл старше cutoff_time - удаляем
                    file_path.unlink()
                    print(f"🗑️  Deleted orphaned file: {file_path.name} (age: {datetime.now() - file_mtime})")
                    deleted += 1
                else:
                    # Файл новый - оставляем (возможно, регистрация еще не завершена)
                    print(f"⏳ Kept recent orphaned file: {file_path.name} (age: {datetime.now() - file_mtime})")
                    kept += 1
                    
            except Exception as e:
                print(f"❌ Error processing file {file_path.name}: {e}")
                errors += 1
        
        stats = {"deleted": deleted, "errors": errors, "kept": kept}
        
        print(f"\n📊 Cleanup statistics:")
        print(f"   Deleted: {deleted}")
        print(f"   Kept: {kept}")
        print(f"   Errors: {errors}")
        print(f"{'='*60}\n")
        
        return stats
    
    async def cleanup_old_temp_files(self, hours: int = 24) -> int:
        """
        Удалить временные файлы старше заданного времени.
        Временные файлы имеют префикс temp_ или _temp.
        
        Args:
            hours: Возраст файлов в часах
            
        Returns:
            int: Количество удаленных файлов
        """
        if not self.upload_dir.exists():
            return 0
        
        deleted = 0
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        for pattern in ["temp_*", "*_temp.*"]:
            for file_path in self.upload_dir.glob(pattern):
                if not file_path.is_file():
                    continue
                
                try:
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    if file_mtime < cutoff_time:
                        file_path.unlink()
                        print(f"🗑️  Deleted temp file: {file_path.name}")
                        deleted += 1
                        
                except Exception as e:
                    print(f"❌ Error deleting temp file {file_path.name}: {e}")
        
        return deleted


async def run_periodic_cleanup(interval_hours: int = 1, max_file_age_hours: int = 48):
    """
    Запустить периодическую очистку orphaned файлов.
    
    Args:
        interval_hours: Интервал между проверками в часах
        max_file_age_hours: Максимальный возраст файла для удаления
    """
    cleanup_service = CleanupService()
    
    print(f"🔄 Cleanup service started (interval: {interval_hours}h, max_age: {max_file_age_hours}h)")
    
    while True:
        try:
            await cleanup_service.cleanup_orphaned_files(max_age_hours=max_file_age_hours)
            await cleanup_service.cleanup_old_temp_files(hours=24)
        except Exception as e:
            print(f"❌ Cleanup error: {e}")
            import traceback
            traceback.print_exc()
        
        # Ждем следующего запуска
        await asyncio.sleep(interval_hours * 3600)


# Функция для ручного запуска cleanup
async def manual_cleanup():
    """Ручной запуск cleanup для тестирования"""
    cleanup_service = CleanupService()
    stats = await cleanup_service.cleanup_orphaned_files(max_age_hours=48)
    temp_deleted = await cleanup_service.cleanup_old_temp_files(hours=24)
    
    print(f"\n✅ Manual cleanup completed:")
    print(f"   Orphaned files: {stats}")
    print(f"   Temp files deleted: {temp_deleted}")


if __name__ == "__main__":
    # Для тестирования
    asyncio.run(manual_cleanup())

