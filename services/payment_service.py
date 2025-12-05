"""
Сервис интеграции с Точка Банком для обработки платежей
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


class TochkaService:
    """Сервис для работы с API Точка Банка (СБП + эквайринг)"""
    
    # API URL для эквайринга Точка Банка
    ACQUIRING_URL = "https://enter.tochka.com/uapi/acquiring/v1.0"
    # API URL для СБП (Система быстрых платежей)
    SBP_URL = "https://enter.tochka.com/uapi/sbp/v1.0"
    
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
        self.jwt_token = settings.tochka_jwt_token
        self.customer_code = settings.tochka_customer_code
        self.merchant_id = settings.tochka_merchant_id
    
    def _get_headers(self) -> Dict[str, str]:
        """Получить заголовки для запросов"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.jwt_token}",
            "X-Request-Id": str(uuid.uuid4())
        }
    
    async def get_retailers(self) -> Optional[Dict[str, Any]]:
        """
        Получить список торговых точек (retailers) для эквайринга.
        Используется для получения merchantId если он не указан.
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = self._get_headers()
                url = f"{self.ACQUIRING_URL}/{self.customer_code}/retailers"
                
                logger.info(f"Запрос списка торговых точек: {url}")
                
                async with session.get(url, headers=headers) as response:
                    response_text = await response.text()
                    logger.debug(f"Retailers response: {response.status}, {response_text}")
                    
                    if response.status == 200:
                        return json.loads(response_text)
                    else:
                        logger.error(f"Ошибка получения retailers: {response.status} - {response_text}")
                        return None
        except Exception as e:
            logger.error(f"Ошибка при получении retailers: {e}")
            return None
    
    async def get_sbp_legal_entities(self) -> Optional[Dict[str, Any]]:
        """
        Получить список юр.лиц зарегистрированных в СБП.
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = self._get_headers()
                url = f"{self.SBP_URL}/{self.customer_code}/legal-entity"
                
                logger.info(f"Запрос юр.лиц СБП: {url}")
                
                async with session.get(url, headers=headers) as response:
                    response_text = await response.text()
                    logger.debug(f"SBP legal entities response: {response.status}, {response_text}")
                    
                    if response.status == 200:
                        return json.loads(response_text)
                    else:
                        logger.error(f"Ошибка получения юр.лиц СБП: {response.status} - {response_text}")
                        return None
        except Exception as e:
            logger.error(f"Ошибка при получении юр.лиц СБП: {e}")
            return None
    
    async def create_sbp_qr(
        self,
        amount: Decimal,
        description: str,
        user_id: int,
        rental_id: Optional[int] = None,
        payment_type: PaymentType = PaymentType.RENTAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Создать динамический QR-код для оплаты через СБП
        
        Args:
            amount: Сумма платежа
            description: Описание платежа
            user_id: ID пользователя
            rental_id: ID аренды
            payment_type: Тип платежа
            metadata: Дополнительные данные
            
        Returns:
            Данные с QR-кодом или None
        """
        try:
            payment_id = str(uuid.uuid4())
            
            # Сумма в копейках для СБП
            amount_kopeks = int(amount * 100)
            
            # Формат запроса для создания динамического QR-кода СБП
            payload = {
                "Data": {
                    "amount": amount_kopeks,
                    "currency": "RUB",
                    "paymentPurpose": description,
                    "qrcType": "02",  # 02 = динамический QR
                    "sourceAccount": self.customer_code  # Счёт для зачисления
                }
            }
            
            async with aiohttp.ClientSession() as session:
                headers = self._get_headers()
                url = f"{self.SBP_URL}/{self.customer_code}/qr-codes"
                
                logger.info(f"Создание СБП QR-кода: {url}")
                logger.debug(f"SBP Payload: {json.dumps(payload, ensure_ascii=False)}")
                
                async with session.post(url, json=payload, headers=headers) as response:
                    response_text = await response.text()
                    logger.debug(f"SBP Response: {response.status}, {response_text}")
                    
                    if response.status in [200, 201]:
                        data = json.loads(response_text)
                        
                        # Извлекаем данные QR-кода
                        qr_data = data.get("Data", {})
                        qr_id = qr_data.get("qrcId") or qr_data.get("id") or payment_id
                        qr_url = qr_data.get("payload") or qr_data.get("qrUrl") or qr_data.get("url")
                        qr_image = qr_data.get("image") or qr_data.get("qrImage")
                        
                        # Сохраняем в БД
                        await self._save_payment_to_db(
                            tochka_payment_id=qr_id,
                            amount=amount,
                            user_id=user_id,
                            rental_id=rental_id,
                            payment_type=payment_type,
                            description=description,
                            metadata=metadata
                        )
                        
                        return {
                            "id": qr_id,
                            "status": "pending",
                            "confirmation": {
                                "confirmation_url": qr_url,
                                "qr_image": qr_image
                            },
                            "amount": {
                                "value": str(amount),
                                "currency": "RUB"
                            },
                            "type": "sbp"
                        }
                    else:
                        logger.error(f"Ошибка создания СБП QR: {response.status} - {response_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Ошибка при создании СБП QR: {e}")
            return None
    
    async def create_payment_link(
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
        Создать платёж через Точка Банк.
        Сначала пробует СБП, если не получится - эквайринг.
        
        Args:
            amount: Сумма платежа
            description: Описание платежа
            user_id: ID пользователя в нашей системе
            rental_id: ID аренды (опционально)
            payment_type: Тип платежа
            return_url: URL для возврата после оплаты
            metadata: Дополнительные данные
        
        Returns:
            Данные платежа или None при ошибке
        """
        # Сначала пробуем СБП
        logger.info("Пробуем создать платёж через СБП...")
        sbp_result = await self.create_sbp_qr(
            amount=amount,
            description=description,
            user_id=user_id,
            rental_id=rental_id,
            payment_type=payment_type,
            metadata=metadata
        )
        
        if sbp_result:
            logger.info("СБП QR-код успешно создан")
            return sbp_result
        
        # Если СБП не сработал - пробуем эквайринг
        logger.info("СБП не доступен, пробуем эквайринг...")
        return await self._create_acquiring_payment(
            amount=amount,
            description=description,
            user_id=user_id,
            rental_id=rental_id,
            payment_type=payment_type,
            return_url=return_url,
            metadata=metadata
        )
    
    async def _create_acquiring_payment(
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
        Создать платёжную ссылку через интернет-эквайринг Точка Банк
        """
        try:
            payment_id = str(uuid.uuid4())
            amount_value = int(amount)
            
            payload = {
                "Data": {
                    "Operation": [
                        {
                            "amount": amount_value,
                            "paymentMode": ["card", "sbp"],
                            "redirectUrl": return_url,
                            "failRedirectUrl": return_url,
                            "purpose": description,
                            "ttl": 1440
                        }
                    ]
                }
            }
            
            if self.merchant_id:
                payload["Data"]["Operation"][0]["merchantId"] = self.merchant_id
            
            async with aiohttp.ClientSession() as session:
                headers = self._get_headers()
                url = f"{self.ACQUIRING_URL}/{self.customer_code}/payment-operation"
                
                logger.info(f"Создание платёжной ссылки эквайринг: {url}")
                logger.debug(f"Payload: {json.dumps(payload, ensure_ascii=False)}")
                
                async with session.post(url, json=payload, headers=headers) as response:
                    response_text = await response.text()
                    logger.debug(f"Response: {response.status}, {response_text}")
                    
                    if response.status in [200, 201]:
                        data = json.loads(response_text)
                        operations = data.get("Data", {}).get("Operation", [])
                        payment_url = None
                        tochka_operation_id = None
                        
                        if operations:
                            payment_url = operations[0].get("paymentLink") or operations[0].get("link")
                            tochka_operation_id = operations[0].get("operationId") or operations[0].get("id")
                        
                        final_payment_id = tochka_operation_id or payment_id
                        
                        await self._save_payment_to_db(
                            tochka_payment_id=final_payment_id,
                            amount=amount,
                            user_id=user_id,
                            rental_id=rental_id,
                            payment_type=payment_type,
                            description=description,
                            metadata=metadata
                        )
                        
                        return {
                            "id": final_payment_id,
                            "status": "pending",
                            "confirmation": {
                                "confirmation_url": payment_url
                            },
                            "amount": {
                                "value": str(amount),
                                "currency": "RUB"
                            },
                            "type": "acquiring"
                        }
                    else:
                        logger.error(f"Ошибка эквайринга: {response.status} - {response_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Ошибка при создании платежа эквайринг: {e}")
            return None
    
    async def get_payment_status(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить статус платежа по ID
        
        Args:
            payment_id: ID платежа
            
        Returns:
            Данные платежа или None
        """
        try:
            # Сначала проверяем статус в нашей БД
            from sqlalchemy import select
            
            async with async_session_factory() as session:
                result = await session.execute(
                    select(Payment).where(Payment.external_payment_id == payment_id)
                )
                payment = result.scalar_one_or_none()
                
                if payment:
                    # Преобразуем статус к формату API
                    status_map = {
                        PaymentStatus.PENDING: "pending",
                        PaymentStatus.PROCESSING: "processing",
                        PaymentStatus.SUCCEEDED: "succeeded",
                        PaymentStatus.CANCELLED: "canceled",
                        PaymentStatus.FAILED: "failed"
                    }
                    return {
                        "id": payment_id,
                        "status": status_map.get(payment.status, "unknown"),
                        "amount": {
                            "value": str(payment.amount),
                            "currency": payment.currency
                        }
                    }
            
            # Если в БД нет - пытаемся запросить у Точки
            async with aiohttp.ClientSession() as session:
                headers = self._get_headers()
                url = f"{self.ACQUIRING_URL}/{self.customer_code}/operations/{payment_id}"
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Преобразуем статус Точки в наш формат
                        tochka_status = data.get("Data", {}).get("status", "").lower()
                        status_map = {
                            "completed": "succeeded",
                            "paid": "succeeded",
                            "success": "succeeded",
                            "cancelled": "canceled",
                            "canceled": "canceled",
                            "failed": "failed",
                            "pending": "pending",
                            "processing": "processing"
                        }
                        return {
                            "id": payment_id,
                            "status": status_map.get(tochka_status, "pending")
                        }
                    else:
                        logger.warning(f"Статус платежа не найден в Точке: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Ошибка при получении статуса платежа: {e}")
            return None
    
    async def _save_payment_to_db(
        self,
        tochka_payment_id: str,
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
                    external_payment_id=tochka_payment_id,
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
        Обработать webhook от Точка Банка
        
        Args:
            data: Данные webhook
            
        Returns:
            True если успешно обработано
        """
        try:
            # Формат webhook от Точки может быть разным
            # Проверяем событие acquiringInternetPayment
            event_type = data.get("eventType") or data.get("event")
            payment_data = data.get("Data", {})
            
            # Получаем ID операции
            operation_id = (
                payment_data.get("operationId") or 
                payment_data.get("paymentId") or
                payment_data.get("id")
            )
            status = (payment_data.get("status") or "").lower()
            
            logger.info(f"Получен webhook Точка: {event_type}, статус {status} для операции {operation_id}")
            
            if status in ["succeeded", "completed", "paid", "success"]:
                await self._handle_payment_succeeded(operation_id, payment_data)
            elif status in ["canceled", "cancelled", "failed", "rejected"]:
                await self._handle_payment_canceled(operation_id, payment_data)
            
            return True
        except Exception as e:
            logger.error(f"Ошибка обработки webhook: {e}")
            return False
    
    async def _handle_payment_succeeded(self, payment_id: str, payment_data: Dict[str, Any]):
        """Обработать успешный платёж"""
        from sqlalchemy import select
        
        async with async_session_factory() as session:
            # Находим платёж в БД
            result = await session.execute(
                select(Payment).where(Payment.external_payment_id == payment_id)
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
    
    async def _handle_payment_canceled(self, payment_id: str, payment_data: Dict[str, Any]):
        """Обработать отменённый платёж"""
        from sqlalchemy import select
        
        async with async_session_factory() as session:
            result = await session.execute(
                select(Payment).where(Payment.external_payment_id == payment_id)
            )
            payment = result.scalar_one_or_none()
            
            if payment:
                payment.status = PaymentStatus.CANCELLED
                await session.commit()
                logger.info(f"Платёж {payment_id} помечен как отменённый")


class RentalExtensionService:
    """Сервис для продления аренды"""
    
    def __init__(self):
        self.tochka = TochkaService()
    
    @staticmethod
    def get_tariffs() -> Dict[str, Dict[str, Any]]:
        """Получить доступные тарифы"""
        return TochkaService.TARIFFS
    
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
        
        tariff = TochkaService.TARIFFS.get(tariff_key)
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
        
        payment_data = await self.tochka.create_payment_link(
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
        payment_data = await self.tochka.get_payment_status(payment_id)
        if payment_data:
            return payment_data.get("status")
        return None


# Глобальные экземпляры сервисов
tochka_service = TochkaService()
rental_extension_service = RentalExtensionService()
