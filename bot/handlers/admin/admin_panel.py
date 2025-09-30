from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from database.base import async_session_factory
from database.models.user import User
from bot.keyboards.common import get_admin_panel_keyboard, get_manager_panel_keyboard

router = Router()




@router.message(F.text == "👨‍💼 Админ панель")
async def admin_panel(message: Message, state: FSMContext):
    """Вход в административную панель"""
    print(f"🚨 ADMIN PANEL: Обработчик вызван!")
    
    telegram_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name
    
    print(f"🔍 DEBUG: Нажатие на админ панель от пользователя:")
    print(f"   - ID: {telegram_id}")
    print(f"   - Username: @{username}")
    print(f"   - Name: {full_name}")
    
    async with async_session_factory() as session:
        # Проверяем права доступа
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        print(f"🔍 DEBUG: Найден пользователь в БД: {user is not None}")
        if user:
            print(f"   - Роль: {user.role.value}")
            print(f"   - is_admin: {user.is_admin}")
            print(f"   - Статус: {user.status.value}")
        
        if not user or not user.is_admin:
            print(f"❌ DEBUG: Доступ запрещен - user: {user is not None}, is_admin: {user.is_admin if user else False}")
            await message.answer("❌ У вас нет прав администратора")
            return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    # Создаем inline-клавиатуру для админ панели
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Документы", callback_data="admin_documents")],
        [InlineKeyboardButton(text="🚴‍♂️ Велосипеды", callback_data="admin_bikes")],
        [
            InlineKeyboardButton(text="💰 Тарифы", callback_data="admin_tariffs"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")
        ]
    ])
    
    print(f"✅ DEBUG: Отправляем админ панель пользователю {user.full_name}")
    
    await message.answer(
        "👨‍💼 **Административная панель**\n\n"
        f"Добро пожаловать, {user.full_name}!\n"
        "Выберите раздел для управления:",
        reply_markup=admin_keyboard
    )
    
    print(f"✅ DEBUG: Админ панель отправлена успешно")


@router.message(F.text == "👨‍💼 Менеджер панель") 
async def manager_panel(message: Message, state: FSMContext):
    """Вход в менеджерскую панель"""
    telegram_id = message.from_user.id
    
    async with async_session_factory() as session:
        # Проверяем права доступа
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_staff:
            await message.answer("❌ У вас нет прав менеджера")
            return
    
    await message.answer(
        "👨‍💼 **Менеджерская панель**\n\n"
        f"Добро пожаловать, {user.full_name}!\n"
        "Выберите раздел для управления:",
        reply_markup=get_manager_panel_keyboard()
    )


@router.callback_query(F.data == "admin_documents")
async def admin_documents_callback(callback: CallbackQuery, state: FSMContext):
    """Переход в раздел документов"""
    # Эмулируем нажатие на кнопку "Документы"
    from bot.handlers.admin.document_verification import documents_menu
    fake_message = type('obj', (object,), {
        'answer': callback.message.edit_text,
        'from_user': callback.from_user
    })()
    await documents_menu(fake_message, state)


@router.callback_query(F.data == "admin_bikes")
async def admin_bikes_callback(callback: CallbackQuery, state: FSMContext):
    """Переход в раздел велосипедов"""
    from bot.keyboards.admin import get_bike_management_keyboard
    await callback.message.edit_text(
        "🚴‍♂️ **Управление парком велосипедов**\n\n"
        "Выберите действие:",
        reply_markup=get_bike_management_keyboard()
    )


@router.callback_query(F.data == "back_to_admin")
async def back_to_admin_callback(callback: CallbackQuery, state: FSMContext):
    """Возврат в админ панель через callback"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Документы", callback_data="admin_documents")],
        [InlineKeyboardButton(text="🚴‍♂️ Велосипеды", callback_data="admin_bikes")],
        [
            InlineKeyboardButton(text="💰 Тарифы", callback_data="admin_tariffs"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")
        ]
    ])
    
    await callback.message.edit_text(
        "👨‍💼 **Административная панель**\n\n"
        "Выберите раздел для управления:",
        reply_markup=admin_keyboard
    )


@router.callback_query(F.data == "admin_settings")
async def admin_settings_callback(callback: CallbackQuery, state: FSMContext):
    """Переход в раздел настроек"""
    from bot.handlers.admin.settings_management import settings_menu
    fake_message = type('obj', (object,), {
        'answer': callback.message.edit_text,
        'from_user': callback.from_user
    })()
    await settings_menu(fake_message, state)


# Обработчики для текстовых кнопок из ReplyKeyboard админ панели
@router.message(F.text == "📋 Документы")
async def admin_documents_text(message: Message, state: FSMContext):
    """Обработка текстовой кнопки Документы"""
    telegram_id = message.from_user.id
    
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.can_verify_documents:
            await message.answer("❌ У вас нет прав для проверки документов")
            return
    
    from bot.handlers.admin.document_verification import documents_menu
    await documents_menu(message, state)


@router.message(F.text == "🚴‍♂️ Велосипеды")
async def admin_bikes_text(message: Message, state: FSMContext):
    """Обработка текстовой кнопки Велосипеды"""
    telegram_id = message.from_user.id
    
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.can_manage_bikes:
            await message.answer("❌ У вас нет прав для управления велосипедами")
            return
    
    # Используем существующую функцию из bike_management
    from bot.keyboards.admin import get_bike_management_keyboard
    await message.answer(
        "🚴‍♂️ **Управление парком велосипедов**\n\n"
        "Выберите действие:",
        reply_markup=get_bike_management_keyboard()
    )


@router.message(F.text == "⚙️ Настройки")
async def admin_settings_text(message: Message, state: FSMContext):
    """Обработка текстовой кнопки Настройки"""
    telegram_id = message.from_user.id
    
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_staff:
            await message.answer("❌ У вас нет прав для изменения настроек")
            return
    
    from bot.handlers.admin.settings_management import settings_menu
    await settings_menu(message, state) 