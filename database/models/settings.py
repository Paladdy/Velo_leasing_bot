from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.sql import func
from database.base import Base


class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    
    # Контактная информация
    company_name = Column(String(255), default="Velo Leasing", nullable=False)
    address = Column(String(500), default="г. Химки, ул. Рабочая, д. 2а", nullable=False)
    phone = Column(String(20), default="+7 968 555 55 18", nullable=False)
    email = Column(String(255), nullable=True)
    
    # Часы работы
    working_hours = Column(String(100), default="Пн-Вс: 09:00 - 21:00", nullable=False)
    working_hours_monday = Column(String(20), default="09:00-21:00", nullable=False)
    working_hours_tuesday = Column(String(20), default="09:00-21:00", nullable=False)
    working_hours_wednesday = Column(String(20), default="09:00-21:00", nullable=False)
    working_hours_thursday = Column(String(20), default="09:00-21:00", nullable=False)
    working_hours_friday = Column(String(20), default="09:00-21:00", nullable=False)
    working_hours_saturday = Column(String(20), default="09:00-21:00", nullable=False)
    working_hours_sunday = Column(String(20), default="09:00-21:00", nullable=False)
    
    # Дополнительная информация
    description = Column(Text, nullable=True)
    website = Column(String(255), nullable=True)
    
    # Настройки работы
    is_active = Column(Boolean, default=True, nullable=False)
    maintenance_mode = Column(Boolean, default=False, nullable=False)
    maintenance_message = Column(Text, nullable=True)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<SystemSettings(id={self.id}, company={self.company_name})>"
    
    @property
    def formatted_working_hours(self) -> str:
        """Форматированные часы работы"""
        if self.working_hours:
            return self.working_hours
        
        # Если детальные часы одинаковые, показываем общий формат
        days_hours = [
            self.working_hours_monday, self.working_hours_tuesday, 
            self.working_hours_wednesday, self.working_hours_thursday,
            self.working_hours_friday, self.working_hours_saturday, 
            self.working_hours_sunday
        ]
        
        if all(h == days_hours[0] for h in days_hours):
            return f"Пн-Вс: {days_hours[0]}"
        else:
            return (
                f"Пн: {self.working_hours_monday}\n"
                f"Вт: {self.working_hours_tuesday}\n"
                f"Ср: {self.working_hours_wednesday}\n"
                f"Чт: {self.working_hours_thursday}\n"
                f"Пт: {self.working_hours_friday}\n"
                f"Сб: {self.working_hours_saturday}\n"
                f"Вс: {self.working_hours_sunday}"
            )
