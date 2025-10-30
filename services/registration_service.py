"""
Сервис для атомарной регистрации пользователя с документами.
Гарантирует консистентность: либо создается пользователь со всеми документами, либо ничего.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models.user import User, UserRole, UserStatus
from database.models.document import Document, DocumentType, DocumentStatus
from config.settings import settings


class RegistrationService:
    """Сервис для регистрации пользователей"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
    
    def _get_upload_dir(self) -> Path:
        """Получить абсолютный путь к директории загрузок"""
        if os.path.isabs(settings.upload_path):
            upload_dir = Path(settings.upload_path)
        else:
            # Получаем абсолютный путь от корня проекта
            project_root = Path(__file__).parent.parent
            upload_dir = project_root / settings.upload_path
        
        # Создаем директорию, если её нет
        upload_dir.mkdir(parents=True, exist_ok=True)
        return upload_dir
    
    async def _download_document_from_telegram(
        self, 
        file_id: str, 
        telegram_id: int, 
        doc_type: str
    ) -> Path:
        """
        Скачать документ из Telegram и сохранить на диск
        
        Args:
            file_id: File ID от Telegram
            telegram_id: Telegram ID пользователя
            doc_type: Тип документа
            
        Returns:
            Path: Путь к сохраненному файлу
            
        Raises:
            Exception: Если не удалось скачать файл
        """
        upload_dir = self._get_upload_dir()
        
        # Получаем информацию о файле
        file_info = await self.bot.get_file(file_id)
        
        # Генерируем имя файла
        file_extension = "jpg"
        filename = f"{telegram_id}_{doc_type}_{file_id}.{file_extension}"
        file_path = upload_dir / filename
        
        # Скачиваем файл
        await self.bot.download_file(file_info.file_path, file_path)
        
        print(f"✅ Document downloaded: {file_path.absolute()}")
        return file_path
    
    async def register_user_with_documents(
        self,
        session: AsyncSession,
        telegram_id: int,
        user_data: Dict[str, Any],
        documents_file_ids: Dict[str, str],
        language: str = "ru"
    ) -> User:
        """
        Атомарно создать пользователя и все его документы в рамках одной транзакции.
        
        Args:
            session: Сессия SQLAlchemy (должна быть в транзакции)
            telegram_id: Telegram ID пользователя
            user_data: Данные пользователя (full_name, phone, email, username)
            documents_file_ids: Словарь {doc_type: file_id}
            language: Язык интерфейса
            
        Returns:
            User: Созданный пользователь
            
        Raises:
            Exception: Если что-то пошло не так (транзакция откатится)
        """
        print(f"\n{'='*60}")
        print(f"🔄 Starting atomic registration for user {telegram_id}")
        print(f"{'='*60}")
        
        # 1. Проверяем, не существует ли уже пользователь
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise ValueError(f"User with telegram_id {telegram_id} already exists")
        
        # 2. Создаем пользователя
        user = User(
            telegram_id=telegram_id,
            username=user_data.get("username"),
            full_name=user_data.get("full_name"),
            phone=user_data.get("phone"),
            email=user_data.get("email"),
            language=language,
            role=UserRole.CLIENT,
            status=UserStatus.PENDING  # Статус "на проверке"
        )
        
        session.add(user)
        await session.flush()  # Получаем user.id
        
        print(f"✅ User created: ID={user.id}, Name={user.full_name}")
        
        # 3. Скачиваем и сохраняем все документы
        downloaded_files: List[Path] = []
        created_documents: List[Document] = []
        
        try:
            for doc_type, file_id in documents_file_ids.items():
                # Преобразуем строку в enum
                if doc_type == "passport":
                    document_type = DocumentType.PASSPORT
                elif doc_type == "driver_license":
                    document_type = DocumentType.DRIVER_LICENSE
                elif doc_type == "selfie":
                    document_type = DocumentType.SELFIE
                else:
                    raise ValueError(f"Unknown document type: {doc_type}")
                
                # Скачиваем файл
                print(f"📥 Downloading {doc_type} (file_id: {file_id[:20]}...)")
                file_path = await self._download_document_from_telegram(
                    file_id, telegram_id, doc_type
                )
                downloaded_files.append(file_path)
                
                # Создаем запись в БД
                document = Document(
                    user_id=user.id,
                    document_type=document_type,
                    file_path=str(file_path.absolute()),
                    original_filename=file_path.name,
                    file_size=file_path.stat().st_size,
                    status=DocumentStatus.PENDING,
                    uploaded_at=datetime.utcnow()
                )
                
                session.add(document)
                created_documents.append(document)
                
                print(f"✅ Document saved: {doc_type} -> {file_path.name}")
            
            # 4. Commit в рамках транзакции вызывающего кода
            # (не делаем commit здесь, чтобы вызывающий код мог откатить при необходимости)
            
            print(f"✅ Registration complete: {len(created_documents)} documents")
            print(f"{'='*60}\n")
            
            return user
            
        except Exception as e:
            # При ошибке удаляем скачанные файлы
            print(f"❌ Error during registration: {e}")
            print(f"🗑️  Rolling back and cleaning up {len(downloaded_files)} files...")
            
            for file_path in downloaded_files:
                try:
                    if file_path.exists():
                        file_path.unlink()
                        print(f"   Deleted: {file_path.name}")
                except Exception as cleanup_error:
                    print(f"   ⚠️  Failed to delete {file_path.name}: {cleanup_error}")
            
            # Пробрасываем ошибку дальше для rollback транзакции
            raise
    
    async def check_user_exists(self, session: AsyncSession, telegram_id: int) -> Optional[User]:
        """Проверить, существует ли пользователь в БД"""
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

