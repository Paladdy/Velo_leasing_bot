"""
Сервис интеграции с ЮKassa для обработки платежей
"""
import aiohttp
import json
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from loguru import logger

from config.settings import settings
from database.base import async_session_factory
from database.models.payment import Payment, PaymentStatus, PaymentType
from database.models.rental import Rental, RentalStatus


class YooKassaService:
    """Сервис для работы с API ЮKassa"""
    
    BASE_URL = "https://api.yookassa.ru/v3"
    
    # Тарифы аренды
    TARIFFS = {
        "biweekly": {
            "name": "2 недели",
            "days": 14,
            "price": Decimal("6500.00"),
            "description": "Аренда велосипеда на 2 недели"
        },
        "monthly": {
            "name": "Месяц",
            "days": 30,
            "price": Decimal("12600.00"),
            "description": "Аренда велосипеда на месяц"
        }
    }
    
    def __init__(self):
        self.shop_id = settings.yookassa_shop_id
        self.secret_key = settings.yookassa_secret_key
        self.oauth_token = settings.yookassa_oauth_token
    
    def _get_auth(self) -> Optional[aiohttp.BasicAuth]:
        """Получить авторизацию для запросов к API (Basic Auth)"""
        if self.shop_id and self.secret_key:
            return aiohttp.BasicAuth(self.shop_id, self.secret_key)
        return None
    
    def _get_headers(self) -> Dict[str, str]:
        """Получить заголовки для запросов"""
        headers = {
            "Content-Type": "application/json",
            "Idempotence-Key": str(uuid.uuid4())
        }
        
        # Если есть OAuth токен - используем его
        if self.oauth_token:
            headers["Authorization"] = f"Bearer {self.oauth_token}"
        
        return headers
    
    async def create_payment(
        self,
        amount: Decimal,
        description: str,
        user_id: int,
        rental_id: Optional[int] = None,
        payment_type: PaymentType = PaymentType.RENTAL,
        return_url: str = "https://t.me/VeloLeasingBot",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Создать платёж в ЮKassa
        
        Args:
            amount: Сумма платежа
            description: Описание платежа
            user_id: ID пользователя в нашей системе
            rental_id: ID аренды (опционально)
            payment_type: Тип платежа
            return_url: URL для возврата после оплаты
            metadata: Дополнительные данные
        
        Returns:
            Данные платежа от ЮKassa или None при ошибке
        """
        try:
            payload = {
                "amount": {
                    "value": str(amount),
                    "currency": "RUB"
                },
                "capture": True,  # Автоматический захват платежа
                "confirmation": {
                    "type": "redirect",
                    "return_url": return_url
                },
                "description": description,
                "metadata": {
                    "user_id": user_id,
                    "rental_id": rental_id,
                    "payment_type": payment_type.value,
                    **(metadata or {})
                }
            }
            
            async with aiohttp.ClientSession() as session:
                auth = self._get_auth()
                headers = self._get_headers()
                
                async with session.post(
                    f"{self.BASE_URL}/payments",
                    json=payload,
                    auth=auth,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Создан платёж ЮKassa: {data.get('id')}")
                        
                        # Сохраняем платёж в БД
                        await self._save_payment_to_db(
                            yookassa_payment_id=data.get("id"),
                            amount=amount,
                            user_id=user_id,
                            rental_id=rental_id,
                            payment_type=payment_type,
                            description=description,
                            metadata=metadata
                        )
                        
                        return data
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка создания платежа ЮKassa: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Ошибка при создании платежа: {e}")
            return None
    
    async def get_payment_status(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить статус платежа по ID
        
        Args:
            payment_id: ID платежа в ЮKassa
            
        Returns:
            Данные платежа или None
        """
        try:
            async with aiohttp.ClientSession() as session:
                auth = self._get_auth()
                headers = self._get_headers()
                
                async with session.get(
                    f"{self.BASE_URL}/payments/{payment_id}",
                    auth=auth,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Ошибка получения статуса платежа: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Ошибка при получении статуса платежа: {e}")
            return None
    
    async def cancel_payment(self, payment_id: str) -> bool:
        """
        Отменить платёж
        
        Args:
            payment_id: ID платежа в ЮKassa
            
        Returns:
            True если успешно отменён
        """
        try:
            async with aiohttp.ClientSession() as session:
                auth = self._get_auth()
                headers = self._get_headers()
                
                async with session.post(
                    f"{self.BASE_URL}/payments/{payment_id}/cancel",
                    auth=auth,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        logger.info(f"Платёж {payment_id} отменён")
                        return True
                    else:
                        logger.error(f"Ошибка отмены платежа: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Ошибка при отмене платежа: {e}")
            return False
    
    async def _save_payment_to_db(
        self,
        yookassa_payment_id: str,
        amount: Decimal,
        user_id: int,
        rental_id: Optional[int],
        payment_type: PaymentType,
        description: str,
        metadata: Optional[Dict[str, Any]]
    ) -> Optional[Payment]:
        """Сохранить платёж в базу данных"""
        try:
            async with async_session_factory() as session:
                payment = Payment(
                    yookassa_payment_id=yookassa_payment_id,
                    amount=amount,
                    user_id=user_id,
                    rental_id=rental_id,
                    payment_type=payment_type,
                    status=PaymentStatus.PENDING,
                    description=description,
                    payment_metadata=json.dumps(metadata) if metadata else None
                )
                session.add(payment)
                await session.commit()
                await session.refresh(payment)
                return payment
        except Exception as e:
            logger.error(f"Ошибка сохранения платежа в БД: {e}")
            return None
    
    async def process_webhook(self, data: Dict[str, Any]) -> bool:
        """
        Обработать webhook от ЮKassa
        
        Args:
            data: Данные webhook
            
        Returns:
            True если успешно обработано
        """
        try:
            event_type = data.get("event")
            payment_data = data.get("object", {})
            payment_id = payment_data.get("id")
            
            logger.info(f"Получен webhook ЮKassa: {event_type} для платежа {payment_id}")
            
            if event_type == "payment.succeeded":
                await self._handle_payment_succeeded(payment_data)
            elif event_type == "payment.canceled":
                await self._handle_payment_canceled(payment_data)
            elif event_type == "payment.waiting_for_capture":
                # Для автозахвата не требуется действий
                pass
            
            return True
        except Exception as e:
            logger.error(f"Ошибка обработки webhook: {e}")
            return False
    
    async def _handle_payment_succeeded(self, payment_data: Dict[str, Any]):
        """Обработать успешный платёж"""
        from sqlalchemy import select
        
        payment_id = payment_data.get("id")
        
        async with async_session_factory() as session:
            # Находим платёж в БД
            result = await session.execute(
                select(Payment).where(Payment.yookassa_payment_id == payment_id)
            )
            payment = result.scalar_one_or_none()
            
            if payment:
                payment.status = PaymentStatus.SUCCEEDED
                payment.paid_at = datetime.utcnow()
                
                # Если это платёж за продление аренды
                if payment.rental_id and payment.payment_type == PaymentType.EXTENSION:
                    rental_result = await session.execute(
                        select(Rental).where(Rental.id == payment.rental_id)
                    )
                    rental = rental_result.scalar_one_or_none()
                    
                    if rental:
                        # Получаем информацию о продлении из метаданных
                        metadata = json.loads(payment.payment_metadata) if payment.payment_metadata else {}
                        extension_days = metadata.get("extension_days", 14)
                        
                        # Продлеваем аренду
                        rental.end_date = rental.end_date + timedelta(days=extension_days)
                        rental.paid_amount = rental.paid_amount + payment.amount
                        
                        logger.info(f"Аренда {rental.id} продлена на {extension_days} дней")
                
                await session.commit()
                logger.info(f"Платёж {payment_id} помечен как успешный")
    
    async def _handle_payment_canceled(self, payment_data: Dict[str, Any]):
        """Обработать отменённый платёж"""
        from sqlalchemy import select
        
        payment_id = payment_data.get("id")
        
        async with async_session_factory() as session:
            result = await session.execute(
                select(Payment).where(Payment.yookassa_payment_id == payment_id)
            )
            payment = result.scalar_one_or_none()
            
            if payment:
                payment.status = PaymentStatus.CANCELLED
                await session.commit()
                logger.info(f"Платёж {payment_id} помечен как отменённый")


class RentalExtensionService:
    """Сервис для продления аренды"""
    
    def __init__(self):
        self.yookassa = YooKassaService()
    
    @staticmethod
    def get_tariffs() -> Dict[str, Dict[str, Any]]:
        """Получить доступные тарифы"""
        return YooKassaService.TARIFFS
    
    async def get_active_rental(self, user_id: int) -> Optional[Rental]:
        """Получить активную аренду пользователя по telegram_id"""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from database.models.user import User
        
        async with async_session_factory() as session:
            # Сначала находим пользователя
            user_result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                return None
            
            # Ищем активную аренду
            result = await session.execute(
                select(Rental)
                .options(selectinload(Rental.bike))
                .where(
                    Rental.user_id == user.id,
                    Rental.status == RentalStatus.ACTIVE
                )
                .order_by(Rental.end_date.desc())
            )
            return result.scalar_one_or_none()
    
    async def get_user_rentals(self, user_id: int) -> list:
        """Получить все аренды пользователя"""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from database.models.user import User
        
        async with async_session_factory() as session:
            user_result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                return []
            
            result = await session.execute(
                select(Rental)
                .options(selectinload(Rental.bike))
                .where(Rental.user_id == user.id)
                .order_by(Rental.created_at.desc())
            )
            return result.scalars().all()
    
    async def create_extension_payment(
        self,
        rental_id: int,
        tariff_key: str,
        telegram_user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Создать платёж для продления аренды
        
        Args:
            rental_id: ID аренды
            tariff_key: Ключ тарифа ('biweekly' или 'monthly')
            telegram_user_id: Telegram ID пользователя
            
        Returns:
            Данные платежа с URL для оплаты
        """
        from sqlalchemy import select
        from database.models.user import User
        
        tariff = YooKassaService.TARIFFS.get(tariff_key)
        if not tariff:
            logger.error(f"Неизвестный тариф: {tariff_key}")
            return None
        
        async with async_session_factory() as session:
            # Получаем пользователя
            user_result = await session.execute(
                select(User).where(User.telegram_id == telegram_user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                return None
            
            # Проверяем аренду
            rental_result = await session.execute(
                select(Rental).where(
                    Rental.id == rental_id,
                    Rental.user_id == user.id,
                    Rental.status == RentalStatus.ACTIVE
                )
            )
            rental = rental_result.scalar_one_or_none()
            
            if not rental:
                logger.error(f"Активная аренда {rental_id} не найдена для пользователя {user.id}")
                return None
        
        # Создаём платёж
        description = f"Продление аренды велосипеда на {tariff['name']}"
        
        payment_data = await self.yookassa.create_payment(
            amount=tariff["price"],
            description=description,
            user_id=user.id,
            rental_id=rental_id,
            payment_type=PaymentType.EXTENSION,
            metadata={
                "tariff": tariff_key,
                "extension_days": tariff["days"],
                "telegram_user_id": telegram_user_id
            }
        )
        
        return payment_data
    
    async def check_payment_status(self, payment_id: str) -> Optional[str]:
        """Проверить статус платежа"""
        payment_data = await self.yookassa.get_payment_status(payment_id)
        if payment_data:
            return payment_data.get("status")
        return None


# Глобальные экземпляры сервисов
yookassa_service = YooKassaService()
rental_extension_service = RentalExtensionService()

