from aiogram import Router, F
from aiogram.types import Message, PhotoSize, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import os
from pathlib import Path

from database.base import async_session_factory
from database.models.user import User, UserRole
from database.models.document import Document, DocumentType, DocumentStatus
from bot.keyboards.common import get_main_menu_keyboard, get_phone_request_keyboard, get_document_choice_keyboard
from bot.states.registration import RegistrationStates
from config.settings import settings

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
            keyboard = get_main_menu_keyboard(is_staff=user.is_staff, role=user.role.value)
            
            welcome_text = f"👋 Добро пожаловать обратно, {user.full_name}!"
            if user.is_admin:
                welcome_text += "\n\n👨‍💼 У вас есть права администратора"
            elif user.is_manager:
                welcome_text += "\n\n👨‍💼 У вас есть права менеджера"
            
            await message.answer(welcome_text, reply_markup=keyboard)
        else:
            # Новый пользователь - начинаем регистрацию
            await message.answer(
                "👋 Добро пожаловать в систему аренды велосипедов!\n\n"
                "Для начала работы необходимо пройти регистрацию.\n"
                "Пожалуйста, введите ваше полное имя:",
                reply_markup=None
            )
            await state.set_state(RegistrationStates.waiting_for_name)


@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    """Обработка ввода имени"""
    if not message.text or len(message.text.strip()) < 2:
        await message.answer("❌ Пожалуйста, введите корректное имя (минимум 2 символа)")
        return
    
    await state.update_data(full_name=message.text.strip())
    
    await message.answer(
        "📱 Отлично! Теперь поделитесь своим номером телефона:",
        reply_markup=get_phone_request_keyboard()
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
    if not message.text:
        await message.answer("📱 Пожалуйста, поделитесь номером телефона или введите его вручную")
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
    
    async with async_session_factory() as session:
        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=data['full_name'],
            phone=phone,
            role=UserRole.CLIENT
        )
        session.add(user)
        await session.commit()
    
    await message.answer(
        "✅ Отлично! Регистрация завершена.\n\n"
        "📄 Для аренды велосипеда необходимо загрузить документы:\n"
        "• Паспорт ИЛИ Водительские права (на выбор)\n"
        "• Селфи с выбранным документом\n\n"
        "Выберите, какой документ вы хотите загрузить:",
        reply_markup=get_document_choice_keyboard()
    )
    await state.set_state(RegistrationStates.choosing_document_type)


@router.callback_query(F.data == "doc_choice_passport")
async def choose_passport(callback: CallbackQuery, state: FSMContext):
    """Выбор паспорта для загрузки"""
    await state.update_data(chosen_document_type="passport")  # Сохраняем строку вместо enum
    await callback.message.edit_text(
        "📄 **Загрузка паспорта**\n\n"
        "Пожалуйста, отправьте четкое фото вашего паспорта.\n"
        "Убедитесь, что все данные хорошо видны.",
        reply_markup=None
    )
    await state.set_state(RegistrationStates.waiting_for_main_document)


@router.callback_query(F.data == "doc_choice_license")
async def choose_license(callback: CallbackQuery, state: FSMContext):
    """Выбор водительских прав для загрузки"""
    await state.update_data(chosen_document_type="driver_license")  # Сохраняем строку вместо enum
    await callback.message.edit_text(
        "🚗 **Загрузка водительских прав**\n\n"
        "Пожалуйста, отправьте четкое фото ваших водительских прав.\n"
        "Убедитесь, что все данные хорошо видны.",
        reply_markup=None
    )
    await state.set_state(RegistrationStates.waiting_for_main_document)


@router.message(RegistrationStates.waiting_for_main_document, F.photo)
async def process_main_document_photo(message: Message, state: FSMContext):
    """Обработка фото основного документа (паспорт или права)"""
    data = await state.get_data()
    doc_type_str = data.get('chosen_document_type', 'passport')
    
    # Преобразуем строку в enum
    doc_type = DocumentType.PASSPORT if doc_type_str == 'passport' else DocumentType.DRIVER_LICENSE
    
    if doc_type == DocumentType.PASSPORT:
        response_text = "📄 Паспорт получен! Теперь отправьте селфи с паспортом:"
    else:
        response_text = "🚗 Водительские права получены! Теперь отправьте селфи с правами:"
    
    await save_document_photo(message, state, doc_type, response_text)
    await state.set_state(RegistrationStates.waiting_for_selfie)


@router.message(RegistrationStates.waiting_for_selfie, F.photo)
async def process_selfie_photo(message: Message, state: FSMContext):
    """Обработка селфи с документом"""
    await save_document_photo(message, state, DocumentType.SELFIE,
                             "🤳 Селфи получено!")
    
    await message.answer(
        "✅ Все документы загружены!\n\n"
        "📋 Ваши документы отправлены на проверку администратору.\n"
        "⏰ Обычно проверка занимает до 24 часов.\n"
        "📱 Мы уведомим вас, как только документы будут проверены.\n\n"
        "Спасибо за регистрацию! 🚴‍♂️",
        reply_markup=get_main_menu_keyboard(is_staff=False)
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
        await message.answer("❌ Произошла ошибка при сохранении документа. Попробуйте еще раз.")
        print(f"Error saving document: {e}")


@router.message(F.text == "◀️ Главное меню")
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
            keyboard = get_main_menu_keyboard(is_staff=user.is_staff, role=user.role.value)
            await message.answer("🏠 Главное меню", reply_markup=keyboard)


@router.message(RegistrationStates.waiting_for_main_document)
@router.message(RegistrationStates.waiting_for_selfie)
async def handle_non_photo_in_document_states(message: Message, state: FSMContext):
    """Обработка не-фото сообщений в состояниях загрузки документов"""
    current_state = await state.get_state()
    
    if current_state == RegistrationStates.waiting_for_main_document:
        data = await state.get_data()
        doc_type_str = data.get('chosen_document_type', 'passport')
        doc_name = "паспорта" if doc_type_str == 'passport' else "водительских прав"
    else:
        doc_name = "селфи с документом"
    
    await message.answer(f"📷 Пожалуйста, отправьте фото {doc_name}, а не текст.")


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
            await message.answer("❌ Пользователь не найден")
            return
            
        print(f"🔍 User found: {user.full_name}, role: {user.role.value}, is_admin: {user.is_admin}")
        
        if not user.is_admin:
            await message.answer("❌ У вас нет прав администратора")
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