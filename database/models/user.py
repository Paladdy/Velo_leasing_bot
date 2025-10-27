from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Boolean, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.base import Base
import enum


class UserRole(enum.Enum):
    CLIENT = "client"
    MANAGER = "manager"
    ADMIN = "admin"


class UserStatus(enum.Enum):
    PENDING = "pending"          # Ожидает верификации
    VERIFIED = "verified"        # Верифицирован
    REJECTED = "rejected"        # Отклонен
    BLOCKED = "blocked"          # Заблокирован


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    
    # Язык интерфейса (ru, tg, uz)
    language = Column(String(5), default="ru", nullable=False)
    
    # Роли и статусы
    role = Column(Enum(UserRole), default=UserRole.CLIENT, nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.PENDING, nullable=False)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Связи
    documents = relationship("Document", back_populates="user", foreign_keys="Document.user_id")
    rentals = relationship("Rental", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, role={self.role.value})>"
    
    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN
    
    @property
    def is_manager(self) -> bool:
        return self.role == UserRole.MANAGER
    
    @property
    def is_staff(self) -> bool:
        """Проверка, является ли пользователь сотрудником (менеджер или админ)"""
        return self.role in (UserRole.MANAGER, UserRole.ADMIN)
    
    @property
    def is_verified(self) -> bool:
        return self.status == UserStatus.VERIFIED
    
    @property
    def can_verify_documents(self) -> bool:
        """Может ли пользователь проверять документы"""
        return self.is_staff
    
    @property
    def can_manage_bikes(self) -> bool:
        """Может ли пользователь управлять велосипедами"""
        return self.is_staff
    
    @property
    def can_manage_users(self) -> bool:
        """Может ли пользователь управлять пользователями"""
        return self.is_admin 