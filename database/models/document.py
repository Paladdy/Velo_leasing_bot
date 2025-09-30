from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.base import Base
import enum


class DocumentType(enum.Enum):
    PASSPORT = "passport"           # Паспорт
    DRIVER_LICENSE = "driver_license"  # Водительские права
    SELFIE = "selfie"              # Селфи с документом
    OTHER = "other"                # Другое


class DocumentStatus(enum.Enum):
    PENDING = "pending"            # Ожидает проверки
    APPROVED = "approved"          # Одобрен
    REJECTED = "rejected"          # Отклонен
    REVISION = "revision"          # Требует доработки


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    
    # Связи
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Информация о документе
    document_type = Column(Enum(DocumentType), nullable=False)
    file_path = Column(String(500), nullable=False)
    original_filename = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)
    
    # Статус и проверка
    status = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False)
    admin_comment = Column(Text, nullable=True)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Временные метки
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    verified_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    user = relationship("User", back_populates="documents", foreign_keys=[user_id])
    verified_by_admin = relationship("User", foreign_keys=[verified_by], post_update=True)
    
    def __repr__(self):
        return f"<Document(id={self.id}, type={self.document_type.value}, status={self.status.value})>"
    
    @property
    def is_approved(self) -> bool:
        return self.status == DocumentStatus.APPROVED 