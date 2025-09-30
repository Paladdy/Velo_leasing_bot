from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.base import async_session_factory
from database.models.user import User, UserStatus
from database.models.document import Document, DocumentStatus, DocumentType

router = Router()


@router.message(F.text == "👤 Профиль")
async def show_profile(message: Message, state: FSMContext):
    """Показать профиль пользователя"""
    telegram_id = message.from_user.id
    
    async with async_session_factory() as session:
        # Получаем пользователя с документами
        result = await session.execute(
            select(User)
            .options(selectinload(User.documents))
            .where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer("❌ Пользователь не найден. Пройдите регистрацию командой /start")
            return
        
        # Информация о пользователе
        status_text = {
            UserStatus.PENDING: "⏳ На проверке",
            UserStatus.VERIFIED: "✅ Верифицирован",
            UserStatus.REJECTED: "❌ Отклонен",
            UserStatus.BLOCKED: "🚫 Заблокирован"
        }
        
        registration_date = user.created_at.strftime("%d.%m.%Y") if user.created_at else "Неизвестно"
        verification_date = user.verified_at.strftime("%d.%m.%Y") if user.verified_at else "Не верифицирован"
        
        profile_text = [
            f"👤 **Мой профиль**\n",
            f"📝 **Личные данные:**",
            f"• Имя: {user.full_name}",
            f"• Username: @{user.username or 'не указан'}",
            f"• Телефон: {user.phone or 'не указан'}",
            f"• Email: {user.email or 'не указан'}",
            f"• Роль: {user.role.value}",
            f"",
            f"📊 **Статус аккаунта:**",
            f"• {status_text.get(user.status, 'Неизвестен')}",
            f"• Регистрация: {registration_date}",
            f"• Верификация: {verification_date}",
            f"",
            f"📄 **Документы:**"
        ]
        
        # Информация о документах
        if not user.documents:
            profile_text.append("• Документы не загружены")
        else:
            doc_types = {
                DocumentType.PASSPORT: "📄 Паспорт",
                DocumentType.DRIVER_LICENSE: "🚗 Водительские права",
                DocumentType.SELFIE: "🤳 Селфи"
            }
            
            doc_status_emoji = {
                DocumentStatus.PENDING: "⏳",
                DocumentStatus.APPROVED: "✅",
                DocumentStatus.REJECTED: "❌",
                DocumentStatus.REVISION: "🔄"
            }
            
            for doc in user.documents:
                doc_name = doc_types.get(doc.document_type, "Неизвестный")
                status_emoji = doc_status_emoji.get(doc.status, "❓")
                upload_date = doc.uploaded_at.strftime("%d.%m.%Y") if doc.uploaded_at else "Неизвестно"
                
                profile_text.append(f"• {status_emoji} {doc_name} - {upload_date}")
        
        # Создаем клавиатуру
        keyboard = []
        
        # Кнопки для просмотра документов
        if user.documents:
            keyboard.append([InlineKeyboardButton(text="📄 Мои документы", callback_data="profile_view_documents")])
        
        # Кнопка редактирования профиля
        keyboard.append([InlineKeyboardButton(text="✏️ Редактировать", callback_data="profile_edit")])
        
        # Если есть проблемы с верификацией
        if user.status in [UserStatus.REJECTED, UserStatus.BLOCKED]:
            keyboard.append([InlineKeyboardButton(text="🔄 Повторная подача", callback_data="profile_resubmit")])
        
        inline_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None
        
        await message.answer(
            "\n".join(profile_text),
            reply_markup=inline_keyboard
        )


@router.callback_query(F.data == "profile_view_documents")
async def view_user_documents(callback: CallbackQuery, state: FSMContext):
    """Показать документы пользователя"""
    telegram_id = callback.from_user.id
    
    async with async_session_factory() as session:
        result = await session.execute(
            select(User)
            .options(selectinload(User.documents))
            .where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.documents:
            await callback.answer("❌ Документы не найдены", show_alert=True)
            return
        
        # Создаем кнопки для просмотра каждого документа
        keyboard = []
        
        doc_types = {
            DocumentType.PASSPORT: "📄 Паспорт",
            DocumentType.DRIVER_LICENSE: "🚗 Права", 
            DocumentType.SELFIE: "🤳 Селфи"
        }
        
        doc_status_emoji = {
            DocumentStatus.PENDING: "⏳",
            DocumentStatus.APPROVED: "✅",
            DocumentStatus.REJECTED: "❌",
            DocumentStatus.REVISION: "🔄"
        }
        
        for doc in user.documents:
            doc_name = doc_types.get(doc.document_type, "Документ")
            status_emoji = doc_status_emoji.get(doc.status, "❓")
            
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{status_emoji} {doc_name}",
                    callback_data=f"profile_doc_{doc.id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton(text="◀️ Назад в профиль", callback_data="profile_back")])
        
        status_text = {
            UserStatus.PENDING: "⏳ На проверке",
            UserStatus.VERIFIED: "✅ Верифицирован",
            UserStatus.REJECTED: "❌ Отклонен",
            UserStatus.BLOCKED: "🚫 Заблокирован"
        }
        
        await callback.message.edit_text(
            f"📄 **Мои документы**\n\n"
            f"👤 {user.full_name}\n"
            f"📊 Статус: {status_text.get(user.status, 'Неизвестен')}\n\n"
            f"Нажмите на документ для просмотра:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )


@router.callback_query(F.data.startswith("profile_doc_"))
async def view_profile_document(callback: CallbackQuery, state: FSMContext):
    """Просмотр конкретного документа пользователя"""
    doc_id = int(callback.data.split("_")[-1])
    
    async with async_session_factory() as session:
        result = await session.execute(
            select(Document)
            .options(selectinload(Document.user))
            .where(Document.id == doc_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            await callback.answer("❌ Документ не найден", show_alert=True)
            return
        
        # Проверяем, что это документ текущего пользователя
        if document.user.telegram_id != callback.from_user.id:
            await callback.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        doc_types = {
            DocumentType.PASSPORT: "📄 Паспорт",
            DocumentType.DRIVER_LICENSE: "🚗 Водительские права",
            DocumentType.SELFIE: "🤳 Селфи с документом"
        }
        
        status_text = {
            DocumentStatus.PENDING: "⏳ На проверке",
            DocumentStatus.APPROVED: "✅ Одобрен",
            DocumentStatus.REJECTED: "❌ Отклонен",
            DocumentStatus.REVISION: "🔄 Требует доработки"
        }
        
        upload_date = document.uploaded_at.strftime("%d.%m.%Y %H:%M") if document.uploaded_at else "Неизвестно"
        
        doc_info = (
            f"📄 **{doc_types.get(document.document_type, 'Документ')}**\n\n"
            f"🆔 ID: {document.id}\n"
            f"📊 Статус: {status_text.get(document.status, 'Неизвестен')}\n"
            f"📅 Загружен: {upload_date}"
        )
        
        if document.admin_comment:
            doc_info += f"\n💬 Комментарий администратора:\n{document.admin_comment}"
        
        # Отправляем фото документа
        try:
            photo = FSInputFile(document.file_path)
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад к документам", callback_data="profile_view_documents")]
            ])
            
            await callback.message.answer_photo(
                photo=photo,
                caption=doc_info,
                reply_markup=keyboard
            )
        except Exception as e:
            await callback.message.edit_text(
                f"{doc_info}\n\n❌ Ошибка загрузки файла",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад к документам", callback_data="profile_view_documents")]
                ])
            )


@router.callback_query(F.data == "profile_back")
async def back_to_profile(callback: CallbackQuery, state: FSMContext):
    """Возврат в профиль"""
    # Эмулируем нажатие на кнопку профиля
    fake_message = type('obj', (object,), {
        'answer': callback.message.edit_text,
        'from_user': callback.from_user
    })()
    await show_profile(fake_message, state) 