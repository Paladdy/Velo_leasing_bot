"""
Redis storage для временных данных регистрации.
Данные хранятся с TTL 24 часа и автоматически удаляются.
"""
import json
from typing import Optional, Dict, Any
from redis.asyncio import Redis
from config.settings import settings


# TTL для данных регистрации (24 часа)
REGISTRATION_TTL = 24 * 60 * 60  # 86400 секунд


class RegistrationStorage:
    """Хранилище для временных данных регистрации в Redis"""
    
    def __init__(self, redis: Redis):
        self.redis = redis
    
    def _key(self, telegram_id: int, suffix: str) -> str:
        """Генерирует ключ для Redis"""
        return f"registration:{telegram_id}:{suffix}"
    
    async def set_language(self, telegram_id: int, language: str) -> None:
        """Сохранить выбранный язык"""
        key = self._key(telegram_id, "language")
        await self.redis.setex(key, REGISTRATION_TTL, language)
    
    async def get_language(self, telegram_id: int) -> Optional[str]:
        """Получить выбранный язык"""
        key = self._key(telegram_id, "language")
        value = await self.redis.get(key)
        return value.decode() if value else None
    
    async def set_user_data(self, telegram_id: int, data: Dict[str, Any]) -> None:
        """
        Сохранить данные пользователя (ФИО, телефон, email)
        
        Args:
            telegram_id: Telegram ID пользователя
            data: Словарь с данными (full_name, phone, email, username)
        """
        key = self._key(telegram_id, "data")
        json_data = json.dumps(data, ensure_ascii=False)
        await self.redis.setex(key, REGISTRATION_TTL, json_data)
    
    async def get_user_data(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получить данные пользователя"""
        key = self._key(telegram_id, "data")
        value = await self.redis.get(key)
        return json.loads(value) if value else None
    
    async def set_document(self, telegram_id: int, doc_type: str, file_id: str) -> None:
        """
        Сохранить file_id документа от Telegram
        
        Args:
            telegram_id: Telegram ID пользователя
            doc_type: Тип документа (passport/driver_license/selfie)
            file_id: File ID от Telegram
        """
        key = self._key(telegram_id, "documents")
        
        # Получаем текущий словарь документов
        documents = await self.get_documents(telegram_id) or {}
        documents[doc_type] = file_id
        
        # Сохраняем обновленный словарь
        json_data = json.dumps(documents, ensure_ascii=False)
        await self.redis.setex(key, REGISTRATION_TTL, json_data)
    
    async def get_documents(self, telegram_id: int) -> Optional[Dict[str, str]]:
        """
        Получить все file_id документов
        
        Returns:
            Словарь {doc_type: file_id} или None
        """
        key = self._key(telegram_id, "documents")
        value = await self.redis.get(key)
        return json.loads(value) if value else None
    
    async def get_all_registration_data(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить все данные регистрации (язык, данные, документы)
        
        Returns:
            Словарь с полными данными или None если нет данных
        """
        language = await self.get_language(telegram_id)
        user_data = await self.get_user_data(telegram_id)
        documents = await self.get_documents(telegram_id)
        
        if not user_data:
            return None
        
        return {
            "language": language or "ru",
            "user_data": user_data,
            "documents": documents or {}
        }
    
    async def is_registration_complete(self, telegram_id: int) -> bool:
        """
        Проверить, завершена ли регистрация
        (все данные заполнены и все обязательные документы загружены)
        """
        data = await self.get_all_registration_data(telegram_id)
        if not data:
            return False
        
        user_data = data.get("user_data", {})
        documents = data.get("documents", {})
        
        # Проверяем наличие обязательных полей
        required_fields = ["full_name", "phone"]
        if not all(user_data.get(field) for field in required_fields):
            return False
        
        # Проверяем наличие обязательных документов (паспорт или права + селфи)
        has_id_document = "passport" in documents or "driver_license" in documents
        has_selfie = "selfie" in documents
        
        return has_id_document and has_selfie
    
    async def clear_registration_data(self, telegram_id: int) -> None:
        """Удалить все данные регистрации пользователя"""
        keys = [
            self._key(telegram_id, "language"),
            self._key(telegram_id, "data"),
            self._key(telegram_id, "documents")
        ]
        await self.redis.delete(*keys)
    
    async def extend_ttl(self, telegram_id: int) -> None:
        """Продлить TTL всех ключей регистрации"""
        keys = [
            self._key(telegram_id, "language"),
            self._key(telegram_id, "data"),
            self._key(telegram_id, "documents")
        ]
        for key in keys:
            if await self.redis.exists(key):
                await self.redis.expire(key, REGISTRATION_TTL)
    
    async def get_missing_data(self, telegram_id: int, language: str = "ru") -> Dict[str, bool]:
        """
        Проверить, какие данные отсутствуют
        
        Returns:
            Словарь с флагами отсутствующих данных
        """
        data = await self.get_all_registration_data(telegram_id)
        
        if not data:
            return {
                "user_data": True,
                "id_document": True,
                "selfie": True
            }
        
        user_data = data.get("user_data", {})
        documents = data.get("documents", {})
        
        return {
            "full_name": not user_data.get("full_name"),
            "phone": not user_data.get("phone"),
            "id_document": not ("passport" in documents or "driver_license" in documents),
            "selfie": not documents.get("selfie")
        }


# Глобальный экземпляр (будет инициализирован при старте бота)
_registration_storage: Optional[RegistrationStorage] = None


def init_registration_storage(redis: Redis) -> RegistrationStorage:
    """Инициализировать глобальное хранилище"""
    global _registration_storage
    _registration_storage = RegistrationStorage(redis)
    return _registration_storage


def get_registration_storage() -> RegistrationStorage:
    """Получить глобальный экземпляр хранилища"""
    if _registration_storage is None:
        raise RuntimeError("RegistrationStorage not initialized. Call init_registration_storage first.")
    return _registration_storage

