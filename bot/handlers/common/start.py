from aiogram import Router, F
from aiogram.types import Message, PhotoSize, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import os
from pathlib import Path

from database.base import async_session_factory
from database.models.user import User, UserRole, UserStatus
from database.models.document import Document, DocumentType, DocumentStatus
from bot.keyboards.common import get_main_menu_keyboard, get_phone_request_keyboard, get_document_choice_keyboard, get_language_selection_keyboard
from bot.states.registration import RegistrationStates
from config.settings import settings
from bot.utils.i18n import change_user_language, get_language_name
from bot.utils.translations import get_text, get_user_language
from bot.utils.redis_storage import get_registration_storage
from services.registration_service import RegistrationService

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    telegram_id = message.from_user.id
    username = message.from_user.username
    
    # Временное логирование для определения ID администратора
    print(f"🆔 User info: ID={telegram_id}, Username=@{username}, Name={message.from_user.full_name}")
    
    # Отладка - логируем все входящие сообщения
    print(f"📨 Получено сообщение: '{message.text}'")
    
    async with async_session_factory() as session:
        # Проверяем, есть ли пользователь в базе
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Пользователь уже зарегистрирован
            await state.clear()
            lang = get_user_language(user)
            
            # Автоматически назначаем роль админа, если telegram_id в ADMIN_IDS
            if telegram_id in settings.admin_ids and user.role != UserRole.ADMIN:
                user.role = UserRole.ADMIN
                user.status = UserStatus.VERIFIED
                await session.commit()
                print(f"✅ Автоматически назначен администратором: {user.full_name} (ID: {telegram_id})")
            
            keyboard = get_main_menu_keyboard(is_staff=user.is_staff, role=user.role.value, language=lang)
            
            welcome_text = get_text("start.welcome_back", lang, name=user.full_name)
            if user.is_admin:
                welcome_text += get_text("start.admin_rights", lang)
            elif user.is_manager:
                welcome_text += get_text("start.manager_rights", lang)
            
            await message.answer(welcome_text, reply_markup=keyboard)
        else:
            # Проверяем, есть ли незавершенная регистрация в Redis
            storage = get_registration_storage()
            registration_data = await storage.get_all_registration_data(telegram_id)
            
            if registration_data:
                # Есть незавершенная регистрация
                lang = registration_data.get('language', 'ru')
                missing = await storage.get_missing_data(telegram_id, lang)
                
                print(f"📋 Incomplete registration found for {telegram_id}: {missing}")
                
                # Продлеваем TTL
                await storage.extend_ttl(telegram_id)
                
                await message.answer(
                    get_text("registration.continue_registration", lang),
                    reply_markup=get_document_choice_keyboard(lang)
                )
                await state.update_data(language=lang, telegram_id=telegram_id, username=username)
                await state.set_state(RegistrationStates.choosing_document_type)
            else:
                # Новый пользователь - начинаем регистрацию с выбора языка
                await message.answer(
                    get_text("language_selection.choose", "ru"),
                    reply_markup=get_language_selection_keyboard(for_registration=True)
                )
                # Сохраняем telegram_id для последующего использования
                await state.update_data(telegram_id=telegram_id, username=username)
                await state.set_state(RegistrationStates.choosing_language)


@router.callback_query(F.data.startswith("register_lang_"))
async def process_language_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора языка ПРИ РЕГИСТРАЦИИ"""
    language = callback.data.split("_")[2]  # register_lang_ru -> ru
    
    # Сохраняем выбранный язык в состояние
    await state.update_data(language=language)
    
    # Получаем название языка и приветственное сообщение на выбранном языке
    language_selected = get_text("language_selection.changed", language)
    
    welcome_msg = f"{language_selected}\n\n{get_text('start.welcome_new', language)}"
    
    # Пытаемся отредактировать caption (если это фото) или text (если текст)
    try:
        if callback.message.photo:
            await callback.message.edit_caption(
                caption=welcome_msg,
                reply_markup=None
            )
        else:
            await callback.message.edit_text(
                welcome_msg,
                reply_markup=None
            )
    except Exception as e:
        # Если не получилось отредактировать, отправляем новое сообщение
        print(f"Не удалось отредактировать сообщение: {e}")
        await callback.message.answer(welcome_msg)
    
    await state.set_state(RegistrationStates.waiting_for_name)


@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    """Обработка ввода имени"""
    telegram_id = message.from_user.id
    
    # ВАЖНО: Проверяем, не зарегистрирован ли пользователь уже
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            # Пользователь уже зарегистрирован - очищаем состояние и игнорируем
            await state.clear()
            print(f"⚠️ Пользователь {telegram_id} уже зарегистрирован, игнорируем ввод имени")
            return
    
    data = await state.get_data()
    lang = data.get('language', 'ru')
    
    if not message.text or len(message.text.strip()) < 2:
        await message.answer(get_text("registration.name_error", lang))
        return
    
    # Игнорируем тексты кнопок меню (содержат эмодзи транспорта)
    name = message.text.strip()
    if any(emoji in name for emoji in ['🚴', '👤', '🔧', '💳', '👨‍💼']):
        await message.answer(get_text("registration.name_error", lang))
        await state.clear()  # Очищаем состояние
        return
    
    await state.update_data(full_name=name)
    
    await message.answer(
        get_text("registration.enter_phone", lang),
        reply_markup=get_phone_request_keyboard(lang)
    )
    await state.set_state(RegistrationStates.waiting_for_phone)


@router.message(RegistrationStates.waiting_for_phone, F.contact)
async def process_phone_contact(message: Message, state: FSMContext):
    """Обработка получения номера телефона через контакт"""
    telegram_id = message.from_user.id
    
    # ВАЖНО: Проверяем, не зарегистрирован ли пользователь уже
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            # Пользователь уже зарегистрирован - очищаем состояние и игнорируем
            await state.clear()
            print(f"⚠️ Пользователь {telegram_id} уже зарегистрирован, игнорируем телефон")
            return
    
    phone = message.contact.phone_number
    await process_phone_number(message, state, phone)


@router.message(RegistrationStates.waiting_for_phone)
async def process_phone_text(message: Message, state: FSMContext):
    """Обработка ввода номера телефона текстом"""
    telegram_id = message.from_user.id
    
    # ВАЖНО: Проверяем, не зарегистрирован ли пользователь уже
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            # Пользователь уже зарегистрирован - очищаем состояние и игнорируем
            await state.clear()
            print(f"⚠️ Пользователь {telegram_id} уже зарегистрирован, игнорируем текст телефона")
            return
    
    data = await state.get_data()
    lang = data.get('language', 'ru')
    
    if not message.text:
        await message.answer(get_text("registration.phone_error", lang))
        return
    
    phone = message.text.strip()
    await process_phone_number(message, state, phone)


async def process_phone_number(message: Message, state: FSMContext, phone: str):
    """
    Общая обработка номера телефона.
    НОВАЯ ЛОГИКА: Сохраняем данные в Redis, не создаем пользователя в БД сразу.
    """
    telegram_id = message.from_user.id
    username = message.from_user.username
    data = await state.get_data()
    language = data.get('language', 'ru')
    full_name = data.get('full_name', '')
    
    # Проверяем, не зарегистрирован ли пользователь уже в PostgreSQL
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            # Пользователь уже в БД - это повторная регистрация или обновление
            print(f"ℹ️ Пользователь {telegram_id} уже существует в БД")
            
            # Если это админ - просто обновляем данные
            if telegram_id in settings.admin_ids:
                existing_user.username = username
                existing_user.full_name = full_name
                existing_user.phone = phone
                existing_user.language = language
                existing_user.role = UserRole.ADMIN
                existing_user.status = UserStatus.VERIFIED
                await session.commit()
                
                await message.answer(
                    get_text("start.welcome_back", language, name=full_name),
                    reply_markup=get_main_menu_keyboard(is_staff=True, role="ADMIN", language=language)
                )
                await state.clear()
                return
            
            # Для обычных пользователей - проверяем документы
            doc_result = await session.execute(
                select(Document).where(
                    Document.user_id == existing_user.id,
                    Document.status == DocumentStatus.PENDING
                )
            )
            pending_docs = doc_result.scalars().all()
            
            if pending_docs:
                await message.answer(
                    get_text("registration.documents_pending", language),
                    reply_markup=get_main_menu_keyboard(is_staff=False, language=language)
                )
                await state.clear()
                return
    
    # НОВАЯ ЛОГИКА: Сохраняем данные в Redis (staging area)
    storage = get_registration_storage()
    
    user_data = {
        "full_name": full_name,
        "phone": phone,
        "username": username,
        "email": data.get('email')  # Опционально
    }
    
    await storage.set_user_data(telegram_id, user_data)
    print(f"✅ User data saved to Redis: {telegram_id} -> {full_name}")
    
    # Проверяем, есть ли уже документы в Redis (незавершенная регистрация)
    documents = await storage.get_documents(telegram_id)
    if documents and len(documents) >= 2:
        await message.answer(
            get_text("registration.resume_registration", language),
            reply_markup=get_document_choice_keyboard(language)
        )
    else:
        await message.answer(
            get_text("registration.registration_complete", language),
            reply_markup=get_document_choice_keyboard(language)
        )
    
    await state.set_state(RegistrationStates.choosing_document_type)


@router.callback_query(F.data == "doc_choice_passport")
async def choose_passport(callback: CallbackQuery, state: FSMContext):
    """Выбор паспорта для загрузки"""
    telegram_id = callback.from_user.id
    data = await state.get_data()
    lang = data.get('language', 'ru')
    
    # Проверяем, нет ли уже документов на проверке
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            doc_result = await session.execute(
                select(Document).where(
                    Document.user_id == user.id,
                    Document.status == DocumentStatus.PENDING
                )
            )
            pending_docs = doc_result.scalars().all()
            
            if pending_docs:
                await callback.answer(
                    get_text("registration.documents_already_pending", lang),
                    show_alert=True
                )
                return
    
    await state.update_data(chosen_document_type="passport")
    await callback.message.edit_text(
        get_text("documents.upload_passport", lang),
        reply_markup=None
    )
    await state.set_state(RegistrationStates.waiting_for_main_document)


@router.callback_query(F.data == "doc_choice_license")
async def choose_license(callback: CallbackQuery, state: FSMContext):
    """Выбор водительских прав для загрузки"""
    telegram_id = callback.from_user.id
    data = await state.get_data()
    lang = data.get('language', 'ru')
    
    # Проверяем, нет ли уже документов на проверке
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            doc_result = await session.execute(
                select(Document).where(
                    Document.user_id == user.id,
                    Document.status == DocumentStatus.PENDING
                )
            )
            pending_docs = doc_result.scalars().all()
            
            if pending_docs:
                await callback.answer(
                    get_text("registration.documents_already_pending", lang),
                    show_alert=True
                )
                return
    
    await state.update_data(chosen_document_type="driver_license")
    await callback.message.edit_text(
        get_text("documents.upload_license", lang),
        reply_markup=None
    )
    await state.set_state(RegistrationStates.waiting_for_main_document)


@router.message(RegistrationStates.waiting_for_main_document, F.photo)
async def process_main_document_photo(message: Message, state: FSMContext):
    """Обработка фото основного документа (паспорт или права)"""
    data = await state.get_data()
    lang = data.get('language', 'ru')
    doc_type_str = data.get('chosen_document_type', 'passport')
    
    # Преобразуем строку в enum
    doc_type = DocumentType.PASSPORT if doc_type_str == 'passport' else DocumentType.DRIVER_LICENSE
    
    if doc_type == DocumentType.PASSPORT:
        response_text = get_text("documents.passport_received", lang)
    else:
        response_text = get_text("documents.license_received", lang)
    
    await save_document_photo(message, state, doc_type, response_text)
    await state.set_state(RegistrationStates.waiting_for_selfie)


@router.message(RegistrationStates.waiting_for_selfie, F.photo)
async def process_selfie_photo(message: Message, state: FSMContext):
    """Обработка селфи с документом"""
    data = await state.get_data()
    lang = data.get('language', 'ru')
    
    await save_document_photo(message, state, DocumentType.SELFIE,
                             get_text("documents.selfie_received", lang))
    
    await message.answer(
        get_text("registration.thank_you", lang),
        reply_markup=get_main_menu_keyboard(is_staff=False, language=lang)
    )
    await state.set_state(RegistrationStates.registration_complete)


async def save_document_photo(message: Message, state: FSMContext, doc_type: DocumentType, response_text: str):
    """
    Сохранение фото документа.
    НОВАЯ ЛОГИКА: Сохраняем file_id в Redis, а не скачиваем файл сразу.
    Атомарное сохранение в БД происходит после загрузки ВСЕХ документов.
    """
    telegram_id = message.from_user.id
    data = await state.get_data()
    lang = data.get('language', 'ru')
    
    # Получаем самое большое фото
    photo = message.photo[-1]
    file_id = photo.file_id
    
    try:
        # Сохраняем file_id в Redis
        storage = get_registration_storage()
        doc_type_str = doc_type.value  # "passport", "driver_license" или "selfie"
        
        await storage.set_document(telegram_id, doc_type_str, file_id)
        print(f"✅ Document file_id saved to Redis: {telegram_id} -> {doc_type_str} (file_id: {file_id[:20]}...)")
        
        await message.answer(response_text)
        
        # Проверяем, загружены ли все обязательные документы
        is_complete = await storage.is_registration_complete(telegram_id)
        
        if is_complete:
            print(f"🎉 All documents collected! Starting atomic registration for {telegram_id}")
            
            # Получаем все данные из Redis
            registration_data = await storage.get_all_registration_data(telegram_id)
            
            if not registration_data:
                await message.answer(get_text("documents.save_error", lang))
                return
            
            # Атомарно создаем пользователя + все документы в PostgreSQL
            try:
                async with async_session_factory() as session:
                    async with session.begin():  # Открываем транзакцию
                        registration_service = RegistrationService(message.bot)
                        
                        user = await registration_service.register_user_with_documents(
                            session=session,
                            telegram_id=telegram_id,
                            user_data=registration_data['user_data'],
                            documents_file_ids=registration_data['documents'],
                            language=registration_data['language']
                        )
                        
                        # Если всё прошло успешно, commit произойдет автоматически при выходе из async with
                        print(f"✅ Atomic registration completed for user {user.id}")
                
                # Очищаем Redis после успешной регистрации
                await storage.clear_registration_data(telegram_id)
                print(f"🧹 Redis data cleared for {telegram_id}")
                
                # Уведомляем пользователя об успешной регистрации
                await message.answer(
                    get_text("registration.thank_you", lang),
                    reply_markup=get_main_menu_keyboard(is_staff=False, language=lang)
                )
                await state.clear()
                
                print(f"{'='*60}")
                print(f"🎉 Registration complete for user {telegram_id}")
                print(f"{'='*60}\n")
                
            except Exception as e:
                # При ошибке транзакция откатится автоматически
                print(f"❌ Atomic registration failed: {e}")
                import traceback
                traceback.print_exc()
                
                await message.answer(
                    get_text("documents.save_error", lang) + "\n\n" +
                    "⚠️ Ваши данные сохранены. Попробуйте отправить команду /start и продолжить регистрацию."
                )
                # Данные остаются в Redis, пользователь может повторить попытку
        else:
            # Не все документы загружены - продолжаем
            missing = await storage.get_missing_data(telegram_id, lang)
            print(f"ℹ️ Missing documents for {telegram_id}: {missing}")
        
    except Exception as e:
        print(f"❌ Error saving document to Redis: {e}")
        import traceback
        traceback.print_exc()
        await message.answer(get_text("documents.save_error", lang))


@router.message(F.text.in_(["◀️ Главное меню", "◀️ Бозгашт", "◀️ Orqaga", "◀️ Артка"]))
async def back_to_main_menu(message: Message, state: FSMContext):
    # Очищаем состояние, чтобы не было конфликта с регистрацией
    await state.clear()
    """Возврат в главное меню"""
    telegram_id = message.from_user.id
    
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            await state.clear()
            lang = get_user_language(user)
            keyboard = get_main_menu_keyboard(is_staff=user.is_staff, role=user.role.value, language=lang)
            await message.answer(get_text("common.main_menu", lang), reply_markup=keyboard)


@router.message(RegistrationStates.waiting_for_main_document)
@router.message(RegistrationStates.waiting_for_selfie)
async def handle_non_photo_in_document_states(message: Message, state: FSMContext):
    """Обработка не-фото сообщений в состояниях загрузки документов"""
    data = await state.get_data()
    lang = data.get('language', 'ru')
    current_state = await state.get_state()
    
    doc_names = {
        "ru": {"passport": "паспорта", "license": "водительских прав", "selfie": "селфи с документом"},
        "tg": {"passport": "шиносномаи гражданӣ", "license": "иҷозатномаи ронандагӣ", "selfie": "селфӣ бо ҳуҷҷат"},
        "uz": {"passport": "pasport", "license": "haydovchilik guvohnomasi", "selfie": "hujjat bilan selfi"}
    }
    
    if current_state == RegistrationStates.waiting_for_main_document:
        doc_type_str = data.get('chosen_document_type', 'passport')
        doc_key = "passport" if doc_type_str == 'passport' else "license"
    else:
        doc_key = "selfie"
    
    doc_name = doc_names.get(lang, doc_names["ru"]).get(doc_key, "")
    await message.answer(get_text("documents.photo_required", lang, doc_name=doc_name))


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Команда /admin для отладки"""
    print(f"🚨 ADMIN COMMAND: Команда /admin вызвана!")
    
    telegram_id = message.from_user.id
    print(f"🔍 User ID: {telegram_id}")
    
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            lang = "ru"
            await message.answer(get_text("start.user_not_found", lang))
            return
            
        lang = get_user_language(user)
        print(f"🔍 User found: {user.full_name}, role: {user.role.value}, is_admin: {user.is_admin}")
        
        if not user.is_admin:
            await message.answer(get_text("admin.no_permissions", lang))
            return
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Документы", callback_data="admin_documents")],
            [InlineKeyboardButton(text="🚴‍♂️ Велосипеды", callback_data="admin_bikes")],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")]
        ])
        
        await message.answer(
            f"👨‍💼 **Админ панель (через команду)**\n\n"
            f"Добро пожаловать, {user.full_name}!\n"
            f"Ваша роль: {user.role.value}",
            reply_markup=admin_keyboard
        ) 