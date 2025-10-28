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
            # Новый пользователь - начинаем регистрацию с выбора языка
            await message.answer(
                get_text("language_selection.choose", "ru"),
                reply_markup=get_language_selection_keyboard()
            )
            # Сохраняем telegram_id для последующего использования
            await state.update_data(telegram_id=telegram_id, username=username)
            await state.set_state(RegistrationStates.choosing_language)


@router.callback_query(F.data.startswith("lang_"))
async def process_language_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора языка"""
    language = callback.data.split("_")[1]  # lang_ru -> ru
    
    # Сохраняем выбранный язык в состояние
    await state.update_data(language=language)
    
    # Получаем название языка и приветственное сообщение на выбранном языке
    lang_name = get_language_name(language)
    language_selected = get_text("language_selection.changed", language).replace(
        get_language_name("ru") if language == "ru" else 
        get_language_name("tg") if language == "tg" else 
        get_language_name("uz"),
        lang_name
    )
    
    welcome_msg = f"{language_selected}\n\n{get_text('start.welcome_new', language)}"
    
    await callback.message.edit_text(
        welcome_msg,
        reply_markup=None
    )
    await state.set_state(RegistrationStates.waiting_for_name)


@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    """Обработка ввода имени"""
    data = await state.get_data()
    lang = data.get('language', 'ru')
    
    if not message.text or len(message.text.strip()) < 2:
        await message.answer(get_text("registration.name_error", lang))
        return
    
    await state.update_data(full_name=message.text.strip())
    
    await message.answer(
        get_text("registration.enter_phone", lang),
        reply_markup=get_phone_request_keyboard(lang)
    )
    await state.set_state(RegistrationStates.waiting_for_phone)


@router.message(RegistrationStates.waiting_for_phone, F.contact)
async def process_phone_contact(message: Message, state: FSMContext):
    """Обработка получения номера телефона через контакт"""
    phone = message.contact.phone_number
    await process_phone_number(message, state, phone)


@router.message(RegistrationStates.waiting_for_phone)
async def process_phone_text(message: Message, state: FSMContext):
    """Обработка ввода номера телефона текстом"""
    data = await state.get_data()
    lang = data.get('language', 'ru')
    
    if not message.text:
        await message.answer(get_text("registration.phone_error", lang))
        return
    
    phone = message.text.strip()
    await process_phone_number(message, state, phone)


async def process_phone_number(message: Message, state: FSMContext, phone: str):
    """Общая обработка номера телефона"""
    await state.update_data(phone=phone)
    
    # Создаем пользователя в базе данных
    telegram_id = message.from_user.id
    username = message.from_user.username
    data = await state.get_data()
    
    # Получаем выбранный язык (по умолчанию русский)
    language = data.get('language', 'ru')
    
    # Определяем роль и статус на основе ADMIN_IDS
    role = UserRole.ADMIN if telegram_id in settings.admin_ids else UserRole.CLIENT
    status = UserStatus.VERIFIED if telegram_id in settings.admin_ids else UserStatus.PENDING
    
    async with async_session_factory() as session:
        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=data['full_name'],
            phone=phone,
            role=role,
            status=status,
            language=language
        )
        session.add(user)
        await session.commit()
        
        if role == UserRole.ADMIN:
            print(f"✅ Новый администратор зарегистрирован: {user.full_name} (ID: {telegram_id})")
    
    await message.answer(
        get_text("registration.registration_complete", language),
        reply_markup=get_document_choice_keyboard(language)
    )
    await state.set_state(RegistrationStates.choosing_document_type)


@router.callback_query(F.data == "doc_choice_passport")
async def choose_passport(callback: CallbackQuery, state: FSMContext):
    """Выбор паспорта для загрузки"""
    data = await state.get_data()
    lang = data.get('language', 'ru')
    
    await state.update_data(chosen_document_type="passport")
    await callback.message.edit_text(
        get_text("documents.upload_passport", lang),
        reply_markup=None
    )
    await state.set_state(RegistrationStates.waiting_for_main_document)


@router.callback_query(F.data == "doc_choice_license")
async def choose_license(callback: CallbackQuery, state: FSMContext):
    """Выбор водительских прав для загрузки"""
    data = await state.get_data()
    lang = data.get('language', 'ru')
    
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
    """Сохранение фото документа"""
    telegram_id = message.from_user.id
    
    # Создаем папку для загрузок, если её нет
    upload_dir = Path(settings.upload_path)
    upload_dir.mkdir(exist_ok=True)
    
    # Получаем самое большое фото
    photo = message.photo[-1]
    
    # Генерируем имя файла
    file_extension = "jpg"
    filename = f"{telegram_id}_{doc_type.value}_{photo.file_id}.{file_extension}"
    file_path = upload_dir / filename
    
    try:
        # Скачиваем файл
        file_info = await message.bot.get_file(photo.file_id)
        await message.bot.download_file(file_info.file_path, file_path)
        
        # Сохраняем в базу данных
        async with async_session_factory() as session:
            # Находим пользователя
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                # Создаем запись документа
                document = Document(
                    user_id=user.id,
                    document_type=doc_type,
                    file_path=str(file_path),
                    original_filename=filename,
                    file_size=photo.file_size,
                    status=DocumentStatus.PENDING
                )
                session.add(document)
                await session.commit()
        
        await message.answer(response_text)
        
    except Exception as e:
        # Пытаемся получить язык из состояния
        data = await state.get_data()
        lang = data.get('language', 'ru')
        await message.answer(get_text("documents.save_error", lang))
        print(f"Error saving document: {e}")


@router.message(F.text.in_(["◀️ Главное меню", "◀️ Бозгашт", "◀️ Orqaga"]))
async def back_to_main_menu(message: Message, state: FSMContext):
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