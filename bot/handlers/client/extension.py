"""
Обработчики продления аренды велосипеда онлайн
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from loguru import logger

from database.base import async_session_factory
from database.models.user import User, UserStatus
from database.models.rental import Rental, RentalStatus
from services.payment_service import rental_extension_service, TochkaService
from bot.utils.translations import get_text, get_user_language
from sqlalchemy import select


router = Router()


def get_extension_tariffs_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура выбора тарифа для продления"""
    tariffs = TochkaService.TARIFFS
    
    buttons = []
    for key, tariff in tariffs.items():
        buttons.append([
            InlineKeyboardButton(
                text=f"📅 {tariff['name']} — {tariff['price']:,.0f}₽",
                callback_data=f"extend_tariff_{key}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="cancel_extension"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_extension_confirm_keyboard(tariff_key: str, rental_id: int, lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура подтверждения продления"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Оплатить",
                callback_data=f"confirm_extend_{tariff_key}_{rental_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ Назад к тарифам",
                callback_data="back_to_tariffs"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="cancel_extension"
            )
        ]
    ])


def get_my_rentals_keyboard(rentals: list, lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура со списком аренд для продления"""
    buttons = []
    
    for rental in rentals:
        if rental.status == RentalStatus.ACTIVE:
            bike_info = rental.bike.number if rental.bike else "N/A"
            end_date = rental.end_date.strftime("%d.%m.%Y")
            buttons.append([
                InlineKeyboardButton(
                    text=f"🚴 #{bike_info} | до {end_date}",
                    callback_data=f"extend_rental_{rental.id}"
                )
            ])
    
    if not buttons:
        buttons.append([
            InlineKeyboardButton(
                text="📋 У вас нет активных аренд",
                callback_data="no_active_rentals"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="back_to_main_menu"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(F.text.in_(["📋 Мои аренды", "📋 Ижараҳои ман", "📋 Mening ijaralarim", "📋 Менин ижараларым"]))
async def show_my_rentals(message: Message, state: FSMContext):
    """Показать аренды пользователя"""
    await state.clear()
    telegram_id = message.from_user.id
    
    async with async_session_factory() as session:
        # Получаем пользователя
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer("❌ Пользователь не найден. Используйте /start")
            return
        
        lang = get_user_language(user)
        
        if user.status != UserStatus.VERIFIED:
            await message.answer(get_text("rental.verification_required", lang))
            return
    
    # Получаем аренды пользователя
    rentals = await rental_extension_service.get_user_rentals(telegram_id)
    
    active_rentals = [r for r in rentals if r.status == RentalStatus.ACTIVE]
    
    if not active_rentals:
        await message.answer(
            "📋 **Мои аренды**\n\n"
            "У вас пока нет активных аренд.\n\n"
            "🚴 Чтобы арендовать велосипед, приезжайте к нам в офис!",
            parse_mode="Markdown"
        )
        return
    
    # Формируем текст с информацией об арендах
    text = "📋 **Ваши активные аренды:**\n\n"
    
    for rental in active_rentals:
        bike_info = f"#{rental.bike.number} {rental.bike.model}" if rental.bike else "N/A"
        end_date = rental.end_date.strftime("%d.%m.%Y")
        days_left = (rental.end_date - datetime.now(rental.end_date.tzinfo)).days
        
        status_emoji = "🟢" if days_left > 3 else "🟡" if days_left > 0 else "🔴"
        
        text += (
            f"{status_emoji} **Велосипед:** {bike_info}\n"
            f"   📅 Окончание: {end_date}\n"
            f"   ⏰ Осталось: {days_left} дн.\n\n"
        )
    
    text += "💡 Выберите аренду для продления:"
    
    await message.answer(
        text,
        reply_markup=get_my_rentals_keyboard(active_rentals, lang),
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("extend_rental_"))
async def select_rental_for_extension(callback: CallbackQuery, state: FSMContext):
    """Выбор аренды для продления"""
    rental_id = int(callback.data.split("_")[2])
    
    await state.update_data(rental_id=rental_id)
    
    # Показываем тарифы
    text = (
        "📅 **Выберите период продления:**\n\n"
        "• **2 недели** — 6 500 ₽\n"
        "• **Месяц** — 12 600 ₽\n\n"
        "💳 Оплата онлайн через Точка Банк"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_extension_tariffs_keyboard(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("extend_tariff_"))
async def select_tariff(callback: CallbackQuery, state: FSMContext):
    """Выбор тарифа продления"""
    tariff_key = callback.data.split("_")[2]  # extend_tariff_biweekly -> biweekly
    
    data = await state.get_data()
    rental_id = data.get("rental_id")
    
    if not rental_id:
        await callback.answer("❌ Ошибка: аренда не выбрана", show_alert=True)
        return
    
    tariff = TochkaService.TARIFFS.get(tariff_key)
    if not tariff:
        await callback.answer("❌ Неизвестный тариф", show_alert=True)
        return
    
    await state.update_data(tariff_key=tariff_key)
    
    # Показываем подтверждение
    text = (
        f"✅ **Подтверждение продления**\n\n"
        f"📅 Период: {tariff['name']}\n"
        f"💰 Стоимость: **{tariff['price']:,.0f} ₽**\n\n"
        f"После оплаты аренда будет автоматически продлена на {tariff['days']} дней.\n\n"
        f"Нажмите «Оплатить» для перехода к оплате."
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_extension_confirm_keyboard(tariff_key, rental_id),
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("confirm_extend_"))
async def confirm_extension(callback: CallbackQuery, state: FSMContext):
    """Подтверждение и создание платежа"""
    parts = callback.data.split("_")
    tariff_key = parts[2]  # confirm_extend_biweekly_123
    rental_id = int(parts[3])
    
    telegram_id = callback.from_user.id
    
    await callback.answer("⏳ Создаём платёж...", show_alert=False)
    
    # Создаём платёж
    payment_data = await rental_extension_service.create_extension_payment(
        rental_id=rental_id,
        tariff_key=tariff_key,
        telegram_user_id=telegram_id
    )
    
    if not payment_data:
        await callback.message.edit_text(
            "❌ **Ошибка создания платежа**\n\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору.",
            parse_mode="Markdown"
        )
        return
    
    # Получаем URL для оплаты
    confirmation_url = payment_data.get("confirmation", {}).get("confirmation_url")
    payment_id = payment_data.get("id")
    
    if not confirmation_url:
        await callback.message.edit_text(
            "❌ **Ошибка получения ссылки на оплату**\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode="Markdown"
        )
        return
    
    tariff = TochkaService.TARIFFS.get(tariff_key)
    
    # Показываем ссылку на оплату
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="💳 Перейти к оплате",
                url=confirmation_url
            )
        ],
        [
            InlineKeyboardButton(
                text="✅ Я оплатил",
                callback_data=f"check_payment_{payment_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отменить",
                callback_data=f"cancel_payment_{payment_id}"
            )
        ]
    ])
    
    await callback.message.edit_text(
        f"💳 **Оплата продления аренды**\n\n"
        f"📅 Период: {tariff['name']}\n"
        f"💰 Сумма: **{tariff['price']:,.0f} ₽**\n\n"
        f"Нажмите кнопку ниже для перехода к оплате.\n"
        f"После оплаты нажмите «Я оплатил» для проверки статуса.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    
    await state.clear()


@router.callback_query(F.data.startswith("check_payment_"))
async def check_payment_status(callback: CallbackQuery, state: FSMContext):
    """Проверка статуса платежа"""
    payment_id = callback.data.split("_")[2]
    
    await callback.answer("⏳ Проверяем статус платежа...")
    
    status = await rental_extension_service.check_payment_status(payment_id)
    
    if status == "succeeded":
        await callback.message.edit_text(
            "✅ **Платёж успешно завершён!**\n\n"
            "Ваша аренда продлена. Спасибо за оплату!\n\n"
            "📋 Используйте «Мои аренды» чтобы посмотреть новую дату окончания.",
            parse_mode="Markdown"
        )
    elif status == "pending":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Проверить ещё раз",
                    callback_data=f"check_payment_{payment_id}"
                )
            ]
        ])
        await callback.message.edit_text(
            "⏳ **Платёж в обработке**\n\n"
            "Оплата ещё не подтверждена. Это может занять несколько минут.\n"
            "Нажмите кнопку ниже чтобы проверить снова.",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    elif status == "canceled":
        await callback.message.edit_text(
            "❌ **Платёж отменён**\n\n"
            "Вы можете создать новый платёж через «Мои аренды».",
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text(
            f"⚠️ **Статус платежа: {status or 'неизвестно'}**\n\n"
            "Если у вас возникли проблемы, обратитесь к администратору.",
            parse_mode="Markdown"
        )


@router.callback_query(F.data.startswith("cancel_payment_"))
async def cancel_payment(callback: CallbackQuery, state: FSMContext):
    """Отмена платежа"""
    await callback.message.edit_text(
        "❌ **Оплата отменена**\n\n"
        "Вы можете создать новый платёж в любое время через «Мои аренды».",
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "back_to_tariffs")
async def back_to_tariffs(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору тарифов"""
    text = (
        "📅 **Выберите период продления:**\n\n"
        "• **2 недели** — 6 500 ₽\n"
        "• **Месяц** — 12 600 ₽\n\n"
        "💳 Оплата онлайн через Точка Банк"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_extension_tariffs_keyboard(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "cancel_extension")
async def cancel_extension(callback: CallbackQuery, state: FSMContext):
    """Отмена продления"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Продление отменено.\n\n"
        "Используйте «📋 Мои аренды» чтобы продлить позже."
    )


@router.callback_query(F.data == "back_to_main_menu")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await callback.message.delete()


@router.callback_query(F.data == "no_active_rentals")
async def no_active_rentals(callback: CallbackQuery, state: FSMContext):
    """Обработка нажатия когда нет активных аренд"""
    await callback.answer(
        "У вас нет активных аренд для продления.\n"
        "Приезжайте к нам в офис для оформления аренды!",
        show_alert=True
    )

