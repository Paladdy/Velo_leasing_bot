from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from database.base import async_session_factory
from database.models.user import User
from database.models.bike import Bike, Battery, BikeStatus
from bot.keyboards.admin import (
    get_bike_management_keyboard, 
    get_bikes_list_keyboard, 
    get_bike_actions_keyboard,
    get_bike_status_keyboard
)
from bot.keyboards.common import get_admin_panel_keyboard

router = Router()


@router.message(F.text == "🚴‍♂️ Велосипеды")
async def bike_management_menu(message: Message, state: FSMContext):
    """Главное меню управления велосипедами"""
    telegram_id = message.from_user.id
    
    async with async_session_factory() as session:
        # Проверяем права доступа
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.can_manage_bikes:
            await message.answer("❌ У вас нет прав для управления велосипедами")
            return
    
    await message.answer(
        "🚴‍♂️ **Управление парком велосипедов**\n\n"
        "Выберите действие:",
        reply_markup=get_bike_management_keyboard()
    )


@router.callback_query(F.data == "admin_bike_management")
async def bike_management_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка возврата в меню управления велосипедами"""
    await callback.message.edit_text(
        "🚴‍♂️ **Управление парком велосипедов**\n\n"
        "Выберите действие:",
        reply_markup=get_bike_management_keyboard()
    )


@router.callback_query(F.data == "admin_bikes_list")
async def show_bikes_list(callback: CallbackQuery, state: FSMContext):
    """Показать список всех велосипедов"""
    await show_bikes_page(callback, 0)


@router.callback_query(F.data.startswith("admin_bikes_page_"))
async def show_bikes_page_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка пагинации списка велосипедов"""
    page = int(callback.data.split("_")[-1])
    await show_bikes_page(callback, page)


async def show_bikes_page(callback: CallbackQuery, page: int):
    """Показать страницу со списком велосипедов"""
    async with async_session_factory() as session:
        # Получаем все велосипеды с батарейками
        result = await session.execute(
            select(Bike)
            .options(selectinload(Bike.batteries))
            .order_by(Bike.number)
        )
        bikes = result.scalars().all()
        
        if not bikes:
            await callback.message.edit_text(
                "📋 **Список велосипедов**\n\n"
                "В системе пока нет велосипедов.",
                reply_markup=get_bike_management_keyboard()
            )
            return
        
        # Статистика по статусам
        status_counts = {}
        for bike in bikes:
            status_counts[bike.status] = status_counts.get(bike.status, 0) + 1
        
        stats_text = "\n".join([
            f"{'✅ Доступно' if status == BikeStatus.AVAILABLE else '🚴‍♂️ Арендованы' if status == BikeStatus.RENTED else '🔧 На обслуживании' if status == BikeStatus.MAINTENANCE else '❌ Сломаны'}: {count}"
            for status, count in status_counts.items()
        ])
        
        await callback.message.edit_text(
            f"📋 **Список велосипедов**\n\n"
            f"Всего велосипедов: {len(bikes)}\n"
            f"{stats_text}\n\n"
            "Выберите велосипед для управления:",
            reply_markup=get_bikes_list_keyboard(bikes, page)
        )


@router.callback_query(F.data.startswith("admin_bike_view_"))
async def view_bike_details(callback: CallbackQuery, state: FSMContext):
    """Показать детали велосипеда"""
    bike_id = int(callback.data.split("_")[-1])
    
    async with async_session_factory() as session:
        result = await session.execute(
            select(Bike)
            .options(selectinload(Bike.batteries))
            .where(Bike.id == bike_id)
        )
        bike = result.scalar_one_or_none()
        
        if not bike:
            await callback.answer("❌ Велосипед не найден", show_alert=True)
            return
        
        status_text = {
            BikeStatus.AVAILABLE: "✅ Доступен",
            BikeStatus.RENTED: "🚴‍♂️ Арендован", 
            BikeStatus.MAINTENANCE: "🔧 На обслуживании",
            BikeStatus.BROKEN: "❌ Сломан"
        }
        
        battery_info = ""
        if bike.batteries:
            battery_list = []
            for battery in bike.batteries:
                battery_status = "✅" if battery.status.value == "available" else "🔧" if battery.status.value == "charging" else "❌"
                battery_list.append(f"  • {battery.number} ({battery.capacity}) {battery_status}")
            battery_info = "\n🔋 **Батарейки:**\n" + "\n".join(battery_list)
        
        bike_text = (
            f"🚴‍♂️ **Велосипед #{bike.number}**\n\n"
            f"📝 Модель: {bike.model}\n"
            f"📍 Локация: {bike.location or 'Не указана'}\n"
            f"📊 Статус: {status_text.get(bike.status, 'Неизвестен')}\n"
            f"💰 Тарифы: {bike.price_per_hour}₽/час, {bike.price_per_day}₽/день\n"
            f"📄 Описание: {bike.description or 'Не указано'}{battery_info}\n\n"
            f"🕐 Создан: {bike.created_at.strftime('%d.%m.%Y %H:%M') if bike.created_at else 'Неизвестно'}"
        )
        
        await callback.message.edit_text(
            bike_text,
            reply_markup=get_bike_actions_keyboard(bike_id, bike.status)
        )


@router.callback_query(F.data.startswith("bike_set_"))
async def change_bike_status(callback: CallbackQuery, state: FSMContext):
    """Изменить статус велосипеда"""
    parts = callback.data.split("_")
    action = parts[2]  # maintenance, broken, available
    bike_id = int(parts[3])
    
    status_map = {
        "maintenance": BikeStatus.MAINTENANCE,
        "broken": BikeStatus.BROKEN,
        "available": BikeStatus.AVAILABLE
    }
    
    new_status = status_map.get(action)
    if not new_status:
        await callback.answer("❌ Неизвестное действие", show_alert=True)
        return
    
    async with async_session_factory() as session:
        # Обновляем статус велосипеда
        await session.execute(
            update(Bike)
            .where(Bike.id == bike_id)
            .values(status=new_status)
        )
        await session.commit()
        
        status_text = {
            BikeStatus.MAINTENANCE: "🔧 отправлен на обслуживание",
            BikeStatus.BROKEN: "❌ помечен как сломанный",
            BikeStatus.AVAILABLE: "✅ возвращен в работу"
        }
        
        await callback.answer(f"Велосипед {status_text.get(new_status, 'обновлен')}", show_alert=True)
        
        # Обновляем информацию о велосипеде
        await view_bike_details(callback, state)


@router.callback_query(F.data == "admin_bikes_stats")
async def show_bikes_statistics(callback: CallbackQuery, state: FSMContext):
    """Показать статистику по велосипедам"""
    async with async_session_factory() as session:
        result = await session.execute(select(Bike))
        bikes = result.scalars().all()
        
        if not bikes:
            await callback.message.edit_text(
                "📊 **Статистика велосипедов**\n\n"
                "В системе пока нет велосипедов.",
                reply_markup=get_bike_management_keyboard()
            )
            return
        
        # Подсчет статистики
        total = len(bikes)
        available = sum(1 for bike in bikes if bike.status == BikeStatus.AVAILABLE)
        rented = sum(1 for bike in bikes if bike.status == BikeStatus.RENTED)
        maintenance = sum(1 for bike in bikes if bike.status == BikeStatus.MAINTENANCE)
        broken = sum(1 for bike in bikes if bike.status == BikeStatus.BROKEN)
        
        # Расчет процентов
        available_pct = (available / total * 100) if total > 0 else 0
        rented_pct = (rented / total * 100) if total > 0 else 0
        
        # Средние цены
        avg_hour_price = sum(float(bike.price_per_hour) for bike in bikes) / total if total > 0 else 0
        avg_day_price = sum(float(bike.price_per_day) for bike in bikes) / total if total > 0 else 0
        
        stats_text = (
            f"📊 **Статистика велосипедов**\n\n"
            f"📈 **Общая информация:**\n"
            f"• Всего велосипедов: {total}\n"
            f"• ✅ Доступно: {available} ({available_pct:.1f}%)\n"
            f"• 🚴‍♂️ Арендовано: {rented} ({rented_pct:.1f}%)\n"
            f"• 🔧 На обслуживании: {maintenance}\n"
            f"• ❌ Сломано: {broken}\n\n"
            f"💰 **Средние тарифы:**\n"
            f"• Час: {avg_hour_price:.0f}₽\n"
            f"• День: {avg_day_price:.0f}₽"
        )
        
        await callback.message.edit_text(
            stats_text,
            reply_markup=get_bike_management_keyboard()
        )


@router.callback_query(F.data == "admin_bikes_maintenance")
async def show_maintenance_bikes(callback: CallbackQuery, state: FSMContext):
    """Показать велосипеды на обслуживании"""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Bike)
            .options(selectinload(Bike.batteries))
            .where(Bike.status.in_([BikeStatus.MAINTENANCE, BikeStatus.BROKEN]))
            .order_by(Bike.number)
        )
        bikes = result.scalars().all()
        
        if not bikes:
            await callback.message.edit_text(
                "🔧 **Велосипеды на обслуживании**\n\n"
                "Все велосипеды в рабочем состоянии! 👍",
                reply_markup=get_bike_management_keyboard()
            )
            return
        
        bikes_text = []
        for bike in bikes:
            status_emoji = "🔧" if bike.status == BikeStatus.MAINTENANCE else "❌"
            status_text = "На обслуживании" if bike.status == BikeStatus.MAINTENANCE else "Сломан"
            bikes_text.append(f"{status_emoji} #{bike.number} - {bike.model} ({status_text})")
        
        await callback.message.edit_text(
            f"🔧 **Велосипеды на обслуживании**\n\n"
            f"Требуют внимания: {len(bikes)}\n\n" + "\n".join(bikes_text),
            reply_markup=get_bikes_list_keyboard(bikes, 0)
        )


@router.callback_query(F.data == "back_to_admin")
async def back_to_admin_panel(callback: CallbackQuery, state: FSMContext):
    """Возврат в админ панель"""
    await callback.message.edit_text(
        "👨‍💼 **Административная панель**\n\n"
        "Выберите раздел для управления:",
        reply_markup=get_admin_panel_keyboard()
    ) 