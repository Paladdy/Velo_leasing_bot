from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Numeric, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.base import Base
import enum


class PaymentStatus(enum.Enum):
    PENDING = "pending"         # Ожидает оплаты
    PROCESSING = "processing"   # В процессе
    SUCCEEDED = "succeeded"     # Успешно
    CANCELLED = "cancelled"     # Отменен
    FAILED = "failed"          # Ошибка


class PaymentType(enum.Enum):
    RENTAL = "rental"          # Оплата аренды
    EXTENSION = "extension"    # Продление аренды
    REPAIR = "repair"          # Ремонт
    INSTALLMENT = "installment" # Рассрочка


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    
    # Связи
    rental_id = Column(Integer, ForeignKey("rentals.id"), nullable=True)  # Может быть null для ремонта
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Платежная информация
    external_payment_id = Column(String(255), unique=True, nullable=True, index=True)  # ID платежа в Точка Банк
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="RUB", nullable=False)
    
    # Типы и статусы
    payment_type = Column(Enum(PaymentType), nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    
    # Описание и метаданные
    description = Column(String(500), nullable=True)
    payment_metadata = Column(Text, nullable=True)  # JSON строка для дополнительных данных
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    rental = relationship("Rental", back_populates="payments")
    user = relationship("User")
    
    def __repr__(self):
        return f"<Payment(id={self.id}, amount={self.amount}, status={self.status.value})>"
    
    @property
    def is_paid(self) -> bool:
        return self.status == PaymentStatus.SUCCEEDED 