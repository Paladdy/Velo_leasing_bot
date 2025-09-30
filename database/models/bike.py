from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, ForeignKey, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.base import Base
import enum


class BikeStatus(enum.Enum):
    AVAILABLE = "available"      # Доступен
    RENTED = "rented"           # Арендован
    MAINTENANCE = "maintenance"  # На обслуживании
    BROKEN = "broken"           # Сломан


class BatteryStatus(enum.Enum):
    AVAILABLE = "available"      # Доступна
    IN_USE = "in_use"           # Используется
    CHARGING = "charging"        # Заряжается
    BROKEN = "broken"           # Сломана


class Bike(Base):
    __tablename__ = "bikes"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(50), unique=True, nullable=False, index=True)
    model = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    
    # Статус и местоположение
    status = Column(Enum(BikeStatus), default=BikeStatus.AVAILABLE, nullable=False)
    location = Column(String(255), nullable=True)
    
    # Тарифы
    price_per_hour = Column(Numeric(10, 2), nullable=False, default=0)
    price_per_day = Column(Numeric(10, 2), nullable=False, default=0)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    batteries = relationship("Battery", back_populates="bike")
    rentals = relationship("Rental", back_populates="bike")
    
    def __repr__(self):
        return f"<Bike(id={self.id}, number={self.number}, status={self.status.value})>"
    
    @property
    def is_available(self) -> bool:
        return self.status == BikeStatus.AVAILABLE


class Battery(Base):
    __tablename__ = "batteries"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(50), unique=True, nullable=False, index=True)
    bike_id = Column(Integer, ForeignKey("bikes.id"), nullable=False)
    
    # Характеристики
    capacity = Column(String(50), nullable=True)  # Например "48V 20Ah"
    size = Column(String(50), nullable=True)      # Размер батарейки
    
    # Статус
    status = Column(Enum(BatteryStatus), default=BatteryStatus.AVAILABLE, nullable=False)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    bike = relationship("Bike", back_populates="batteries")
    
    def __repr__(self):
        return f"<Battery(id={self.id}, number={self.number}, bike_id={self.bike_id})>" 