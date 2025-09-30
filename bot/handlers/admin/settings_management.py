from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from database.base import async_session_factory
from database.models.user import User
from services.settings_service import SettingsService

router = Router()


@router.message(F.text == "⚙️ Настройки")
async def settings_menu(message: Message, state: FSMContext):
    """Главное меню настроек системы"""
    telegram_id = message.from_user.id
    
    async with async_session_factory() as session:
        # Проверяем права доступа
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_staff:
            await message.answer("❌ У вас нет прав для изменения настроек")
            return
    
    # Получаем текущие настройки
    settings = await SettingsService.get_settings()
    
    settings_text = (
        f"⚙️ **Настройки системы**\n\n"
        f"🏢 **Компания:** {settings.company_name}\n"
        f"📍 **Адрес:** {settings.address}\n"
        f"📞 **Телефон:** {settings.phone}\n"
        f"📧 **Email:** {settings.email or 'не указан'}\n\n"
        f"🕐 **Часы работы:**\n{settings.formatted_working_hours}\n\n"
        f"🔧 **Статус:** {'🚧 Техработы' if settings.maintenance_mode else '✅ Работаем'}"
    )
    
    keyboard = [
        [InlineKeyboardButton(text="📞 Изменить контакты", callback_data="settings_contacts")],
        [InlineKeyboardButton(text="🕐 Изменить часы работы", callback_data="settings_hours")],
        [InlineKeyboardButton(text="🔧 Режим техработ", callback_data="settings_maintenance")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")]
    ]
    
    await message.answer(
        settings_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@router.callback_query(F.data == "settings_contacts")
async def edit_contacts(callback: CallbackQuery, state: FSMContext):
    """Редактирование контактной информации"""
    settings = await SettingsService.get_settings()
    
    contact_text = (
        f"📞 **Редактирование контактов**\n\n"
        f"📍 **Текущий адрес:**\n{settings.address}\n\n"
        f"📞 **Текущий телефон:**\n{settings.phone}\n\n"
        f"📧 **Email:**\n{settings.email or 'не указан'}\n\n"
        "Выберите, что изменить:"
    )
    
    keyboard = [
        [InlineKeyboardButton(text="📍 Изменить адрес", callback_data="edit_address")],
        [InlineKeyboardButton(text="📞 Изменить телефон", callback_data="edit_phone")],
        [InlineKeyboardButton(text="📧 Изменить email", callback_data="edit_email")],
        [InlineKeyboardButton(text="◀️ Назад к настройкам", callback_data="settings_back")]
    ]
    
    await callback.message.edit_text(
        contact_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@router.callback_query(F.data == "settings_hours")
async def edit_working_hours(callback: CallbackQuery, state: FSMContext):
    """Редактирование часов работы"""
    settings = await SettingsService.get_settings()
    
    hours_text = (
        f"🕐 **Редактирование часов работы**\n\n"
        f"**Текущие часы:**\n{settings.formatted_working_hours}\n\n"
        "Выберите режим редактирования:"
    )
    
    keyboard = [
        [InlineKeyboardButton(text="📅 Общие часы (Пн-Вс)", callback_data="edit_general_hours")],
        [InlineKeyboardButton(text="📋 По дням недели", callback_data="edit_daily_hours")],
        [InlineKeyboardButton(text="🚀 Быстрые настройки", callback_data="quick_hours")],
        [InlineKeyboardButton(text="◀️ Назад к настройкам", callback_data="settings_back")]
    ]
    
    await callback.message.edit_text(
        hours_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@router.callback_query(F.data == "quick_hours")
async def quick_hours_setup(callback: CallbackQuery, state: FSMContext):
    """Быстрая настройка часов работы"""
    quick_text = (
        "🚀 **Быстрые настройки часов работы**\n\n"
        "Выберите готовый вариант:"
    )
    
    keyboard = [
        [InlineKeyboardButton(text="🌅 09:00 - 18:00", callback_data="quick_set_09-18")],
        [InlineKeyboardButton(text="🌞 10:00 - 20:00", callback_data="quick_set_10-20")],
        [InlineKeyboardButton(text="🌙 09:00 - 21:00", callback_data="quick_set_09-21")],
        [InlineKeyboardButton(text="🌃 11:00 - 22:00", callback_data="quick_set_11-22")],
        [InlineKeyboardButton(text="🕐 Круглосуточно", callback_data="quick_set_24-7")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="settings_hours")]
    ]
    
    await callback.message.edit_text(
        quick_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@router.callback_query(F.data.startswith("quick_set_"))
async def apply_quick_hours(callback: CallbackQuery, state: FSMContext):
    """Применить быструю настройку часов"""
    hours_type = callback.data.split("_")[-1]  # quick_set_09-18 -> 09-18
    
    hours_map = {
        "09-18": "Пн-Вс: 09:00 - 18:00",
        "10-20": "Пн-Вс: 10:00 - 20:00", 
        "09-21": "Пн-Вс: 09:00 - 21:00",
        "11-22": "Пн-Вс: 11:00 - 22:00",
        "24-7": "Пн-Вс: Круглосуточно"
    }
    
    new_hours = hours_map.get(hours_type, "Пн-Вс: 09:00 - 21:00")
    
    # Обновляем настройки
    success = await SettingsService.update_working_hours(general_hours=new_hours)
    
    if success:
        await callback.answer("✅ Часы работы обновлены!", show_alert=True)
        
        # Показываем обновленную информацию
        await edit_working_hours(callback, state)
    else:
        await callback.answer("❌ Ошибка при обновлении", show_alert=True)


@router.callback_query(F.data == "edit_general_hours")
async def start_edit_general_hours(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование общих часов работы"""
    await callback.message.edit_text(
        "🕐 **Изменение общих часов работы**\n\n"
        "Введите новые часы работы в формате:\n"
        "**Пн-Вс: ЧЧ:ММ - ЧЧ:ММ**\n\n"
        "Примеры:\n"
        "• Пн-Вс: 09:00 - 21:00\n"
        "• Пн-Пт: 10:00 - 19:00, Сб-Вс: 11:00 - 18:00\n"
        "• Пн-Вс: Круглосуточно\n\n"
        "Напишите новые часы работы:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="settings_hours")]
        ])
    )
    await state.set_state(SettingsStates.editing_general_hours)


@router.callback_query(F.data == "edit_address")
async def start_edit_address(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование адреса"""
    settings = await SettingsService.get_settings()
    
    await callback.message.edit_text(
        f"📍 **Изменение адреса**\n\n"
        f"**Текущий адрес:**\n{settings.address}\n\n"
        "Введите новый адрес:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="settings_contacts")]
        ])
    )
    await state.set_state(SettingsStates.editing_address)


@router.callback_query(F.data == "edit_phone")
async def start_edit_phone(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование телефона"""
    settings = await SettingsService.get_settings()
    
    await callback.message.edit_text(
        f"📞 **Изменение телефона**\n\n"
        f"**Текущий телефон:**\n{settings.phone}\n\n"
        "Введите новый номер телефона в формате:\n"
        "+7 XXX XXX XX XX",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="settings_contacts")]
        ])
    )
    await state.set_state(SettingsStates.editing_phone)


@router.callback_query(F.data == "settings_back")
async def back_to_settings(callback: CallbackQuery, state: FSMContext):
    """Возврат к настройкам"""
    fake_message = type('obj', (object,), {
        'answer': callback.message.edit_text,
        'from_user': callback.from_user
    })()
    await settings_menu(fake_message, state)


# Специфичные обработчики для состояний настроек
from bot.states.settings import SettingsStates

@router.message(SettingsStates.editing_general_hours, F.text)
async def process_general_hours_input(message: Message, state: FSMContext):
    """Обработка ввода общих часов работы"""
    if not message.text or len(message.text.strip()) < 5:
        await message.answer("❌ Пожалуйста, введите корректные часы работы")
        return
    
    new_hours = message.text.strip()
    
    # Обновляем настройки
    success = await SettingsService.update_working_hours(general_hours=new_hours)
    
    if success:
        await message.answer(
            f"✅ **Часы работы обновлены!**\n\n"
            f"**Новые часы:**\n{new_hours}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings_back")]
            ])
        )
    else:
        await message.answer("❌ Ошибка при обновлении часов работы")
    
    await state.clear()


@router.message(SettingsStates.editing_address, F.text)
async def process_address_input(message: Message, state: FSMContext):
    """Обработка ввода нового адреса"""
    if not message.text or len(message.text.strip()) < 10:
        await message.answer("❌ Пожалуйста, введите корректный адрес (минимум 10 символов)")
        return
    
    new_address = message.text.strip()
    
    # Обновляем настройки
    success = await SettingsService.update_contact_info(address=new_address)
    
    if success:
        await message.answer(
            f"✅ **Адрес обновлен!**\n\n"
            f"**Новый адрес:**\n{new_address}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings_back")]
            ])
        )
    else:
        await message.answer("❌ Ошибка при обновлении адреса")
    
    await state.clear()


@router.message(SettingsStates.editing_phone, F.text)
async def process_phone_input(message: Message, state: FSMContext):
    """Обработка ввода нового телефона"""
    if not message.text or len(message.text.strip()) < 10:
        await message.answer("❌ Пожалуйста, введите корректный номер телефона")
        return
    
    new_phone = message.text.strip()
    
    # Обновляем настройки
    success = await SettingsService.update_contact_info(phone=new_phone)
    
    if success:
        await message.answer(
            f"✅ **Телефон обновлен!**\n\n"
            f"**Новый телефон:**\n{new_phone}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings_back")]
            ])
        )
    else:
        await message.answer("❌ Ошибка при обновлении телефона")
    
    await state.clear()


# Дублирующие функции удалены - используем обработчики выше
