from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from datetime import datetime

from database.base import async_session_factory
from database.models.user import User, UserStatus, UserRole
from database.models.document import Document, DocumentStatus, DocumentType
from bot.keyboards.admin import get_document_verification_keyboard
from bot.keyboards.common import get_admin_panel_keyboard

router = Router()





@router.message(F.text == "📋 Документы")
@router.callback_query(F.data == "admin_documents")
async def documents_menu(message_or_callback, state: FSMContext):
    """Главное меню проверки документов"""
    # Определяем тип события (message или callback)
    if hasattr(message_or_callback, 'message'):
        # Это callback
        message = message_or_callback.message
        telegram_id = message_or_callback.from_user.id
        send_method = message.edit_text
    else:
        # Это обычное сообщение
        message = message_or_callback
        telegram_id = message.from_user.id
        send_method = message.answer
    
    async with async_session_factory() as session:
        # Проверяем права доступа
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.can_verify_documents:
            await send_method("❌ У вас нет прав для проверки документов")
            return
        
        # Получаем пользователей по статусам
        unverified_users = await session.execute(
            select(User)
            .where(User.status == UserStatus.PENDING)
            .where(User.role == UserRole.CLIENT)
        )
        unverified_count = len(unverified_users.scalars().all())
        
        verified_users = await session.execute(
            select(User)
            .where(User.status == UserStatus.VERIFIED)
            .where(User.role == UserRole.CLIENT)
        )
        verified_count = len(verified_users.scalars().all())
    
    stats_text = (
        f"📋 **Проверка документов**\n\n"
        f"📊 **Статистика пользователей:**\n"
        f"• ❌ Не прошли верификацию: {unverified_count}\n"
        f"• ✅ Прошли верификацию: {verified_count}\n\n"
        "Выберите категорию:"
    )
    
    keyboard = [
        [InlineKeyboardButton(text=f"❌ Не прошли ({unverified_count})", callback_data="admin_users_unverified")],
        [InlineKeyboardButton(text=f"✅ Прошли ({verified_count})", callback_data="admin_users_verified")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")]
    ]
    
    inline_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await send_method(stats_text, reply_markup=inline_keyboard)


@router.callback_query(F.data == "admin_users_unverified")
async def show_unverified_users(callback: CallbackQuery, state: FSMContext):
    """Показать пользователей, ожидающих верификацию"""
    async with async_session_factory() as session:
        # Получаем пользователей с документами на проверке
        result = await session.execute(
            select(User)
            .options(selectinload(User.documents))
                         .where(User.status == UserStatus.PENDING)
             .where(User.role == UserRole.CLIENT)
            .order_by(User.created_at.desc())
        )
        users = result.scalars().all()
        
        if not users:
            await callback.message.edit_text(
                "✅ **Список пуст**\n\n"
                "Нет пользователей, ожидающих верификацию документов.\n"
                "Все зарегистрированные пользователи уже прошли проверку! 🎉",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_users_pending")],
                        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_documents")]
                    ]
                )
            )
            return
        
        users_text = ["👥 **Пользователи на верификации:**\n"]
        keyboard = []
        
        for user in users:
            # Подсчет документов по статусам
            pending_docs = [d for d in user.documents if d.status == DocumentStatus.PENDING]
            approved_docs = [d for d in user.documents if d.status == DocumentStatus.APPROVED]
            
            registration_date = user.created_at.strftime("%d.%m.%Y") if user.created_at else "Неизвестно"
            
            user_info = (
                f"👤 **{user.full_name}**\n"
                f"📱 @{user.username or 'без username'}\n"
                f"📞 {user.phone or 'не указан'}\n"
                f"📅 Регистрация: {registration_date}\n"
                f"📄 Документов: {len(pending_docs)} на проверке, {len(approved_docs)} одобрено\n"
            )
            users_text.append(user_info)
            
            keyboard.append([
                InlineKeyboardButton(
                    text=f"👤 {user.full_name[:20]}{'...' if len(user.full_name) > 20 else ''}",
                    callback_data=f"admin_user_docs_{user.id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_documents")])
        
        await callback.message.edit_text(
            "\n\n".join(users_text),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )


@router.callback_query(F.data == "admin_users_verified")
async def show_verified_users(callback: CallbackQuery, state: FSMContext):
    """Показать верифицированных пользователей"""
    async with async_session_factory() as session:
        # Получаем верифицированных пользователей с документами
        result = await session.execute(
            select(User)
            .options(selectinload(User.documents))
            .where(User.status == UserStatus.VERIFIED)
            .where(User.role == UserRole.CLIENT)
            .order_by(User.verified_at.desc())
        )
        users = result.scalars().all()
        
        if not users:
            await callback.message.edit_text(
                "✅ **Список пуст**\n\n"
                "Пока нет верифицированных пользователей.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_users_verified")],
                        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_documents")]
                    ]
                )
            )
            return
        
        users_text = ["✅ **Верифицированные пользователи:**\n"]
        keyboard = []
        
        for user in users:
            approved_docs = [d for d in user.documents if d.status == DocumentStatus.APPROVED]
            verification_date = user.verified_at.strftime("%d.%m.%Y") if user.verified_at else "Неизвестно"
            
            user_info = (
                f"👤 **{user.full_name}**\n"
                f"📱 @{user.username or 'без username'}\n"
                f"📞 {user.phone or 'не указан'}\n"
                f"✅ Верифицирован: {verification_date}\n"
                f"📄 Документов одобрено: {len(approved_docs)}\n"
            )
            users_text.append(user_info)
            
            keyboard.append([
                InlineKeyboardButton(
                    text=f"👤 {user.full_name[:20]}{'...' if len(user.full_name) > 20 else ''}",
                    callback_data=f"admin_user_docs_{user.id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_documents")])
        
        await callback.message.edit_text(
            "\n\n".join(users_text),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )


@router.callback_query(F.data.startswith("admin_user_docs_"))
async def show_user_documents(callback: CallbackQuery, state: FSMContext):
    """Показать документы конкретного пользователя"""
    print(f"🔍 DEBUG: show_user_documents вызван с callback: {callback.data}")
    user_id = int(callback.data.split("_")[-1])
    print(f"🔍 DEBUG: Извлеченный User ID: {user_id}")
    
    async with async_session_factory() as session:
        # Получаем пользователя с документами
        result = await session.execute(
            select(User)
            .options(selectinload(User.documents))
            .where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        if not user.documents:
            await callback.message.edit_text(
                f"👤 **{user.full_name}**\n\n"
                "📄 Пользователь еще не загрузил документы",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="admin_users_pending")]]
                )
            )
            return
        
        # Группируем документы по типам
        doc_types = {
            DocumentType.PASSPORT: "📄 Паспорт",
            DocumentType.DRIVER_LICENSE: "🚗 Водительские права", 
            DocumentType.SELFIE: "🤳 Селфи с документом"
        }
        
        status_emoji = {
            DocumentStatus.PENDING: "⏳",
            DocumentStatus.APPROVED: "✅",
            DocumentStatus.REJECTED: "❌",
            DocumentStatus.REVISION: "🔄"
        }
        
        docs_text = [
            f"👤 **{user.full_name}**",
            f"📱 @{user.username or 'без username'}",
            f"📞 {user.phone or 'не указан'}",
            f"📧 {user.email or 'не указан'}\n",
            "📄 **Документы:**"
        ]
        
        keyboard = []
        
        for doc in user.documents:
            doc_type_name = doc_types.get(doc.document_type, "Неизвестный тип")
            status_text = status_emoji.get(doc.status, "❓")
            upload_date = doc.uploaded_at.strftime("%d.%m.%Y") if doc.uploaded_at else "Неизвестно"
            
            docs_text.append(
                f"{status_text} {doc_type_name} (ID: {doc.id}) - 📅 {upload_date}"
            )
            
            # Кнопка для просмотра документа
            keyboard.append([
                InlineKeyboardButton(
                    text=f"👁️ {doc_type_name}",
                    callback_data=f"admin_view_doc_{doc.id}"
                )
            ])
        
        # Кнопки массовых действий
        pending_docs = [d for d in user.documents if d.status == DocumentStatus.PENDING]
        if pending_docs:
            keyboard.append([
                InlineKeyboardButton(text="✅ Одобрить все", callback_data=f"admin_approve_all_{user.id}"),
                InlineKeyboardButton(text="❌ Отклонить все", callback_data=f"admin_reject_all_{user.id}")
            ])
        
        keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_users_unverified")])
        
        # Если это callback с фото, удаляем сообщение и отправляем новое
        try:
            await callback.message.edit_text(
                "\n".join(docs_text),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except Exception as e:
            # Если не можем редактировать (например, сообщение с фото), отправляем новое
            try:
                await callback.message.delete()
            except:
                pass
            
            await callback.bot.send_message(
                callback.from_user.id,
                "\n".join(docs_text),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )


@router.callback_query(F.data.startswith("admin_view_doc_"))
async def view_document(callback: CallbackQuery, state: FSMContext):
    """Просмотр конкретного документа"""
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
            f"📄 **{doc_types.get(document.document_type, 'Неизвестный тип')}**\n\n"
            f"🆔 ID документа: {document.id}\n"
            f"👤 Пользователь: {document.user.full_name}\n"
            f"📱 Username: @{document.user.username or 'без username'}\n"
            f"📊 Статус: {status_text.get(document.status, 'Неизвестен')}\n"
            f"📅 Загружен: {upload_date}"
        )
        
        if document.admin_comment:
            doc_info += f"\n💬 Комментарий: {document.admin_comment}"
        
        # Отправляем фото документа
        try:
            photo = FSInputFile(document.file_path)
            await callback.message.answer_photo(
                photo=photo,
                caption=doc_info,
                reply_markup=get_document_verification_keyboard(document.id, document.user_id)
            )
        except Exception as e:
            # Если не удалось отправить фото, отправляем только текст
            await callback.message.edit_text(
                f"{doc_info}\n\n❌ Ошибка загрузки файла: {str(e)}",
                reply_markup=get_document_verification_keyboard(document.id, document.user_id)
            )


@router.callback_query(F.data.startswith("doc_approve_"))
async def approve_document(callback: CallbackQuery, state: FSMContext):
    """Одобрить документ"""
    doc_id = int(callback.data.split("_")[-1])
    await process_document_verification(callback, doc_id, DocumentStatus.APPROVED, "✅ Документ одобрен", state)


@router.callback_query(F.data.startswith("doc_reject_"))
async def reject_document(callback: CallbackQuery, state: FSMContext):
    """Отклонить документ"""
    doc_id = int(callback.data.split("_")[-1])
    await process_document_verification(callback, doc_id, DocumentStatus.REJECTED, "❌ Документ отклонен", state)


@router.callback_query(F.data.startswith("doc_revision_"))
async def revision_document(callback: CallbackQuery, state: FSMContext):
    """Отправить на доработку"""
    doc_id = int(callback.data.split("_")[-1])
    await process_document_verification(callback, doc_id, DocumentStatus.REVISION, "🔄 Документ отправлен на доработку", state)


async def process_document_verification(callback: CallbackQuery, doc_id: int, new_status: DocumentStatus, success_message: str, state: FSMContext):
    """Обработать верификацию документа"""
    async with async_session_factory() as session:
        # Обновляем статус документа
        admin_result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        admin = admin_result.scalar_one_or_none()
        
        await session.execute(
            update(Document)
            .where(Document.id == doc_id)
            .values(
                status=new_status,
                verified_at=datetime.utcnow(),
                verified_by=admin.id if admin else None
            )
        )
        
        # Получаем документ и пользователя
        doc_result = await session.execute(
            select(Document)
            .options(selectinload(Document.user))
            .where(Document.id == doc_id)
        )
        document = doc_result.scalar_one_or_none()
        
        if document:
            # Проверяем, все ли документы пользователя одобрены
            user_docs = await session.execute(
                select(Document).where(Document.user_id == document.user_id)
            )
            all_docs = user_docs.scalars().all()
            
            # Если все документы одобрены, верифицируем пользователя
            if all(doc.status == DocumentStatus.APPROVED for doc in all_docs):
                await session.execute(
                    update(User)
                    .where(User.id == document.user_id)
                    .values(status=UserStatus.VERIFIED)
                )
                
                # Уведомляем пользователя
                try:
                    bot = callback.bot
                    await bot.send_message(
                        document.user.telegram_id,
                        "🎉 **Поздравляем!**\n\n"
                        "✅ Все ваши документы прошли проверку!\n"
                        "🚴‍♂️ Теперь вы можете арендовать велосипеды.\n\n"
                        "Используйте кнопку \"🚴‍♂️ Арендовать\" в главном меню."
                    )
                except:
                    pass  # Игнорируем ошибки отправки уведомлений
        
        await session.commit()
        
        await callback.answer(success_message, show_alert=True)
        
        # Возвращаемся к списку документов пользователя
        try:
            await callback.message.delete()
        except:
            pass  # Игнорируем ошибки удаления
            
        fake_callback = type('obj', (object,), {
            'data': f"admin_user_docs_{document.user_id}",
            'message': callback.message,
            'from_user': callback.from_user,
            'bot': callback.bot
        })()
        await show_user_documents(fake_callback, state)


@router.callback_query(F.data == "admin_documents_menu")
async def back_to_documents_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в меню документов"""
    # Эмулируем нажатие на кнопку "Документы"
    fake_message = type('obj', (object,), {
        'answer': callback.message.edit_text,
        'from_user': callback.from_user
    })()
    await documents_menu(fake_message, state)


@router.callback_query(F.data == "admin_documents_refresh")
async def refresh_documents_menu(callback: CallbackQuery, state: FSMContext):
    """Обновить меню документов"""
    fake_message = type('obj', (object,), {
        'answer': callback.message.edit_text,
        'from_user': callback.from_user
    })()
    await documents_menu(fake_message, state) 