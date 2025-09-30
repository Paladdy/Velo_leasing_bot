from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Numeric, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.base import Base
import enum


class RentalType(enum.Enum):
    HOURLY = "hourly"           # Почасовая
    DAILY = "daily"             # Посуточная
    INSTALLMENT = "installment" # Рассрочка/выкуп
    CUSTOM = "custom"           # Индивидуальная


class RentalStatus(enum.Enum):
    PENDING = "pending"         # Ожидает оплаты
    ACTIVE = "active"           # Активная аренда
    COMPLETED = "completed"     # Завершена
    CANCELLED = "cancelled"     # Отменена
    OVERDUE = "overdue"         # Просрочена


class Rental(Base):
    __tablename__ = "rentals"

    id = Column(Integer, primary_key=True, index=True)
    
    # Связи
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bike_id = Column(Integer, ForeignKey("bikes.id"), nullable=False)
    
    # Тип и статус аренды
    rental_type = Column(Enum(RentalType), nullable=False)
    status = Column(Enum(RentalStatus), default=RentalStatus.PENDING, nullable=False)
    
    # Временные рамки
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    actual_end_date = Column(DateTime(timezone=True), nullable=True)
    
    # Финансы
    total_amount = Column(Numeric(10, 2), nullable=False)
    paid_amount = Column(Numeric(10, 2), default=0, nullable=False)
    
    # Данные договора (JSON для гибкости)
    contract_data = Column(JSON, nullable=True)
    
    # Дополнительная информация
    notes = Column(Text, nullable=True)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    user = relationship("User", back_populates="rentals")
    bike = relationship("Bike", back_populates="rentals")
    payments = relationship("Payment", back_populates="rental")
    
    def __repr__(self):
        return f"<Rental(id={self.id}, user_id={self.user_id}, bike_id={self.bike_id}, status={self.status.value})>"
    
    @property
    def is_active(self) -> bool:
        return self.status == RentalStatus.ACTIVE
    
    @property
    def is_paid(self) -> bool:
        return self.paid_amount >= self.total_amount 