from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.base import async_session_factory
from database.models.user import User, UserStatus
from database.models.document import Document, DocumentStatus, DocumentType
from bot.keyboards.common import get_language_selection_keyboard
from bot.utils.i18n import change_user_language, get_language_name
from bot.utils.translations import get_text, get_user_language

router = Router()


@router.message(F.text.in_(["👤 Профиль", "👤 Профил"]))
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
            lang = "ru"
            await message.answer(get_text("start.user_not_found", lang))
            return
        
        lang = get_user_language(user)
        
        # Информация о пользователе
        status_key = {
            UserStatus.PENDING: "profile.status_pending",
            UserStatus.VERIFIED: "profile.status_verified",
            UserStatus.REJECTED: "profile.status_rejected",
            UserStatus.BLOCKED: "profile.status_blocked"
        }
        
        registration_date = user.created_at.strftime("%d.%m.%Y") if user.created_at else get_text("status.unknown", lang)
        verification_date = user.verified_at.strftime("%d.%m.%Y") if user.verified_at else get_text("profile.not_verified", lang)
        
        username_text = get_text("profile.username", lang, username=user.username) if user.username else get_text("profile.username_not_set", lang)
        phone_text = get_text("profile.phone", lang, phone=user.phone) if user.phone else get_text("profile.phone_not_set", lang)
        email_text = get_text("profile.email", lang, email=user.email) if user.email else get_text("profile.email_not_set", lang)
        
        profile_text = [
            get_text("profile.title", lang) + "\n",
            get_text("profile.personal_data", lang),
            get_text("profile.name", lang, name=user.full_name),
            username_text,
            phone_text,
            email_text,
            get_text("profile.role", lang, role=user.role.value),
            get_text("profile.language", lang, language=get_language_name(user.language)),
            "",
            get_text("profile.account_status", lang),
            get_text(status_key.get(user.status, "status.unknown"), lang),
            get_text("profile.registration_date", lang, date=registration_date),
            get_text("profile.verification_date", lang, date=verification_date),
            "",
            get_text("profile.documents_title", lang)
        ]
        
        # Информация о документах
        if not user.documents:
            profile_text.append(get_text("profile.no_documents", lang))
        else:
            doc_status_emoji = {
                DocumentStatus.PENDING: "⏳",
                DocumentStatus.APPROVED: "✅",
                DocumentStatus.REJECTED: "❌",
                DocumentStatus.REVISION: "🔄"
            }
            
            for doc in user.documents:
                # Получаем название документа из переводов
                doc_name = get_text(f"documents.{doc.document_type.value}", lang)
                status_emoji = doc_status_emoji.get(doc.status, "❓")
                upload_date = doc.uploaded_at.strftime("%d.%m.%Y") if doc.uploaded_at else get_text("status.unknown", lang)
                
                profile_text.append(f"• {status_emoji} {doc_name} - {upload_date}")
        
        # Создаем клавиатуру
        keyboard = []
        
        # Кнопки для просмотра документов
        if user.documents:
            keyboard.append([InlineKeyboardButton(text=get_text("profile.view_documents", lang), callback_data="profile_view_documents")])
        
        # Кнопка редактирования профиля
        keyboard.append([InlineKeyboardButton(text=get_text("profile.edit_profile", lang), callback_data="profile_edit")])
        
        # Кнопка изменения языка
        keyboard.append([InlineKeyboardButton(text=get_text("profile.change_language", lang), callback_data="profile_change_language")])
        
        # Если есть проблемы с верификацией
        if user.status in [UserStatus.REJECTED, UserStatus.BLOCKED]:
            keyboard.append([InlineKeyboardButton(text=get_text("profile.resubmit", lang), callback_data="profile_resubmit")])
        
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


@router.callback_query(F.data == "profile_change_language")
async def change_language(callback: CallbackQuery, state: FSMContext):
    """Изменить язык интерфейса"""
    telegram_id = callback.from_user.id
    
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        current_lang = get_language_name(user.language)
        
        messages = {
            "ru": f"🌐 **Изменение языка**\n\nТекущий язык: {current_lang}\n\nВыберите новый язык:",
            "tg": f"🌐 **Иваз кардани забон**\n\nЗабони ҷорӣ: {current_lang}\n\nЗабони навро интихоб кунед:",
            "uz": f"🌐 **Tilni o'zgartirish**\n\nJoriy til: {current_lang}\n\nYangi tilni tanlang:"
        }
        
        await callback.message.edit_text(
            messages.get(user.language, messages["ru"]),
            reply_markup=get_language_selection_keyboard()
        )


@router.callback_query(F.data.startswith("lang_"))
async def process_language_change(callback: CallbackQuery, state: FSMContext):
    """Обработка изменения языка"""
    # Проверяем, что это не регистрация (у зарегистрированных пользователей нет active state)
    current_state = await state.get_state()
    if current_state is not None:
        # Это регистрация, не обрабатываем здесь
        return
    
    language = callback.data.split("_")[1]  # lang_ru -> ru
    telegram_id = callback.from_user.id
    
    # Изменяем язык в базе данных
    success = await change_user_language(telegram_id, language)
    
    if success:
        lang_name = get_language_name(language)
        
        success_messages = {
            "ru": f"✅ Язык успешно изменен на {lang_name}",
            "tg": f"✅ Забон ба {lang_name} иваз карда шуд",
            "uz": f"✅ Til {lang_name}ga o'zgartirildi"
        }
        
        await callback.answer(success_messages.get(language, success_messages["ru"]), show_alert=True)
        
        # Возвращаемся к профилю
        fake_message = type('obj', (object,), {
            'answer': callback.message.edit_text,
            'from_user': callback.from_user
        })()
        await show_profile(fake_message, state)
    else:
        await callback.answer("❌ Ошибка при изменении языка", show_alert=True)


@router.callback_query(F.data == "profile_back")
async def back_to_profile(callback: CallbackQuery, state: FSMContext):
    """Возврат в профиль"""
    # Эмулируем нажатие на кнопку профиля
    fake_message = type('obj', (object,), {
        'answer': callback.message.edit_text,
        'from_user': callback.from_user
    })()
    await show_profile(fake_message, state) 