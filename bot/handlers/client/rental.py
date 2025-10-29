from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.base import async_session_factory
from database.models.user import User, UserStatus
from database.models.bike import Bike, BikeStatus
from bot.keyboards.client import get_rental_type_keyboard, get_bikes_keyboard, get_duration_keyboard, get_rental_confirmation_keyboard
from bot.states.rental import RentalStates
from services.settings_service import SettingsService
from bot.utils.translations import get_text, get_user_language

router = Router()


# СТАРЫЙ КОД ДИСТАНЦИОННОЙ АРЕНДЫ - ЗАКОММЕНТИРОВАН ПО ТРЕБОВАНИЮ ЗАКАЗЧИКА
# @router.message(F.text == "🚴‍♂️ Арендовать")
# async def start_rental_process(message: Message, state: FSMContext):
#     """Начало процесса аренды велосипеда"""
#     telegram_id = message.from_user.id
#     
#     async with async_session_factory() as session:
#         # Проверяем статус пользователя
#         result = await session.execute(
#             select(User).where(User.telegram_id == telegram_id)
#         )
#         user = result.scalar_one_or_none()
#         
#         if not user:
#             await message.answer("❌ Пользователь не найден. Пожалуйста, пройдите регистрацию командой /start")
#             return
#             
#         if user.status != UserStatus.VERIFIED:
#             status_text = {
#                 UserStatus.PENDING: "⏳ Ваши документы находятся на проверке",
#                 UserStatus.REJECTED: "❌ Ваши документы были отклонены. Обратитесь к администратору",
#                 UserStatus.BLOCKED: "🚫 Ваш аккаунт заблокирован. Обратитесь к администратору"
#             }
#             await message.answer(
#                 f"{status_text.get(user.status, 'Неизвестный статус')}\n\n"
#                 "📄 Для аренды велосипеда необходимо пройти верификацию документов."
#             )
#             return
#     
#     # Пользователь верифицирован - показываем варианты аренды
#     await message.answer(
#         "🚴‍♂️ **Аренда велосипеда**\n\n"
#         "Выберите тип аренды:",
#         reply_markup=get_rental_type_keyboard()
#     )
#     await state.set_state(RentalStates.choosing_rental_type)

# НОВЫЙ КОД - ТОЛЬКО ОЧНАЯ АРЕНДА
@router.message(F.text.in_(["🚴‍♂️ Арендовать", "🚴‍♂️ Иҷора кардан", "🚴‍♂️ Ijaraga olish", "🚴‍♂️ Ижарага алуу"]))
async def show_rental_contacts(message: Message, state: FSMContext):
    # Очищаем состояние, чтобы не было конфликта с регистрацией
    await state.clear()
    """Показать контакты для очной аренды велосипеда"""
    telegram_id = message.from_user.id
    
    async with async_session_factory() as session:
        # Проверяем статус пользователя
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            lang = "ru"
            await message.answer(get_text("start.user_not_found", lang))
            return
        
        lang = get_user_language(user)
            
        if user.status != UserStatus.VERIFIED:
            status_key = {
                UserStatus.PENDING: "rental.status_pending",
                UserStatus.REJECTED: "rental.status_rejected",
                UserStatus.BLOCKED: "rental.status_blocked"
            }
            status_msg = get_text(status_key.get(user.status, "status.unknown"), lang)
            await message.answer(
                f"{status_msg}\n\n"
                f"{get_text('rental.verification_required', lang)}"
            )
            return
    
    # Получаем настройки из базы данных
    settings = await SettingsService.get_settings()
    
    # Показываем контакты для очной аренды
    contact_text = (
        f"{get_text('rental.title', lang)}\n\n"
        f"{get_text('rental.our_address', lang, address=settings.address)}\n\n"
        f"{get_text('rental.our_phone', lang, phone=settings.phone)}\n\n"
        f"{get_text('rental.working_hours', lang, hours=settings.formatted_working_hours)}\n\n"
        f"{get_text('rental.how_to_rent', lang)}\n\n"
        f"{get_text('rental.see_you', lang)}"
    )
    
    # Клавиатура с дополнительными действиями
    # Формируем ссылку для звонка (убираем пробелы и спецсимволы)
    phone_clean = settings.phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    # Формируем точную ссылку для карты Химки с координатами центра города
    # Координаты центра Химок: 55.8970, 37.4297
    map_url = "https://yandex.ru/maps/?text=улица+Рабочая+2а+Химки&ll=37.4297%2C55.8970&z=16"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text("rental.show_on_map", lang), url=map_url)]
        # [InlineKeyboardButton(text="📋 Мои аренды", callback_data="my_rentals")]  # Закомментировано - не нужно при очной аренде
    ])
    
    await message.answer(contact_text, reply_markup=keyboard)


# ЗАКОММЕНТИРОВАНО - НЕ НУЖНО ПРИ ОЧНОЙ МОДЕЛИ АРЕНДЫ
# @router.callback_query(F.data == "my_rentals")
# async def show_my_rentals(callback: CallbackQuery, state: FSMContext):
#     """Показать аренды пользователя"""
#     await callback.message.edit_text(
#         "📋 **Мои аренды**\n\n"
#         "🚧 Раздел в разработке\n\n"
#         "Здесь будет отображаться:\n"
#         "• Текущие аренды\n"
#         "• История аренд\n"
#         "• Возможность продления\n"
#         "• Статус платежей\n\n"
#         "💡 Пока что все аренды оформляются только в офисе.",
#         reply_markup=InlineKeyboardMarkup(inline_keyboard=[
#             [InlineKeyboardButton(text="🚴‍♂️ Арендовать", callback_data="rental_contacts")]
#         ])
#     )
# 
# 
# @router.callback_query(F.data == "rental_contacts")
# async def show_contacts_callback(callback: CallbackQuery, state: FSMContext):
#     """Показать контакты через callback"""
#     fake_message = type('obj', (object,), {
#         'answer': callback.message.edit_text,
#         'from_user': callback.from_user
#     })()
#     await show_rental_contacts(fake_message, state)


# ==================================================================================
# СТАРЫЙ КОД ДИСТАНЦИОННОЙ АРЕНДЫ - ЗАКОММЕНТИРОВАН ПО ТРЕБОВАНИЮ ЗАКАЗЧИКА
# ==================================================================================
# 
# @router.callback_query(F.data.startswith("rental_type_"))
# async def process_rental_type(callback: CallbackQuery, state: FSMContext):
#     """Обработка выбора типа аренды"""
#     rental_type = callback.data.split("_", 2)[2]  # rental_type_hourly -> hourly
#     
#     await state.update_data(rental_type=rental_type)
#     
#     if rental_type == "custom":
#         await callback.message.edit_text(
#             "🎯 **Индивидуальная сделка**\n\n"
#             "Для индивидуальных условий аренды обратитесь к администратору.\n"
#             "📞 Контакты: @admin_username",
#             reply_markup=None
#         )
#         await state.clear()
#         return
#     elif rental_type == "installment":
#         await callback.message.edit_text(
#             "🛒 **Выкуп с рассрочкой**\n\n"
#             "Для оформления рассрочки обратитесь к администратору.\n"
#             "📞 Контакты: @admin_username",
#             reply_markup=None
#         )
#         await state.clear()
#         return
#     
#     # Показываем доступные велосипеды
#     await show_available_bikes(callback.message, state)
# 
# 
# @router.callback_query(F.data == "rental_onsite")
# async def process_onsite_rental(callback: CallbackQuery, state: FSMContext):
#     """Обработка выбора на месте"""
#     await callback.message.edit_text(
#         "🏪 **Выбор велосипеда на месте**\n\n"
#         "📍 **Адрес точки выдачи:**\n"
#         "ул. Примерная, д. 123\n\n"
#         "🕐 **Время работы:**\n"
#         "Пн-Вс: 09:00 - 21:00\n\n"
#         "📞 **Телефон:**\n"
#         "+7 (999) 123-45-67\n\n"
#         "💡 Приезжайте к нам, и администратор поможет выбрать велосипед!",
#         reply_markup=None
#     )
#     await state.clear()
# 
# 
# async def show_available_bikes(message: Message, state: FSMContext):
#     """Показать доступные велосипеды"""
#     async with async_session_factory() as session:
#         # Получаем доступные велосипеды с батарейками
#         result = await session.execute(
#             select(Bike)
#             .options(selectinload(Bike.batteries))
#             .where(Bike.status == BikeStatus.AVAILABLE)
#             .order_by(Bike.number)
#         )
#         bikes = result.scalars().all()
#         
#         if not bikes:
#             await message.edit_text(
#                 "😔 **К сожалению, сейчас нет доступных велосипедов**\n\n"
#                 "Попробуйте позже или обратитесь к администратору.",
#                 reply_markup=None
#             )
#             await state.clear()
#             return
#         
#         data = await state.get_data()
#         rental_type = data.get("rental_type", "hourly")
#         
#         type_text = {
#             "hourly": "⏰ Почасовая аренда",
#             "daily": "📅 Посуточная аренда"
#         }
#         
#         await message.edit_text(
#             f"🚴‍♂️ **{type_text.get(rental_type)}**\n\n"
#             f"Доступно велосипедов: {len(bikes)}\n"
#             "Выберите велосипед:",
#             reply_markup=get_bikes_keyboard(bikes)
#         )
#         await state.set_state(RentalStates.choosing_bike)
# 
# 
# @router.callback_query(F.data.startswith("select_bike_"))
# async def process_bike_selection(callback: CallbackQuery, state: FSMContext):
#     """Обработка выбора велосипеда"""
#     bike_id = int(callback.data.split("_")[2])
#     
#     async with async_session_factory() as session:
#         result = await session.execute(
#             select(Bike)
#             .options(selectinload(Bike.batteries))
#             .where(Bike.id == bike_id)
#         )
#         bike = result.scalar_one_or_none()
#         
#         if not bike or bike.status != BikeStatus.AVAILABLE:
#             await callback.answer("❌ Велосипед недоступен", show_alert=True)
#             return
#         
#         await state.update_data(bike_id=bike_id, bike=bike)
#         
#         # Показываем варианты продолжительности
#         data = await state.get_data()
#         rental_type = data.get("rental_type")
#         
#         battery_info = ""
#         if bike.batteries:
#             battery_numbers = [b.number for b in bike.batteries]
#             battery_info = f"\n🔋 Батарейки: {', '.join(battery_numbers)}"
#         
#         await callback.message.edit_text(
#             f"✅ **Выбран велосипед:**\n"
#             f"🚴‍♂️ #{bike.number} - {bike.model}\n"
#             f"📍 {bike.location or 'Основная точка'}{battery_info}\n\n"
#             "⏱️ Выберите продолжительность аренды:",
#             reply_markup=get_duration_keyboard(rental_type)
#         )
#         await state.set_state(RentalStates.choosing_duration)
# 
# 
# @router.callback_query(F.data.startswith("duration_"))
# async def process_duration_selection(callback: CallbackQuery, state: FSMContext):
#     """Обработка выбора продолжительности"""
#     duration = callback.data.split("_")[1]  # duration_3h -> 3h
#     
#     await state.update_data(duration=duration)
#     
#     # Показываем итоговую информацию и подтверждение
#     await show_rental_confirmation(callback.message, state)
# 
# 
# async def show_rental_confirmation(message: Message, state: FSMContext):
#     """Показать подтверждение аренды"""
#     data = await state.get_data()
#     bike = data.get("bike")
#     rental_type = data.get("rental_type")
#     duration = data.get("duration")
#     
#     # Парсим продолжительность
#     if duration.endswith("h"):
#         hours = int(duration[:-1])
#         duration_text = f"{hours} час(ов)"
#         if rental_type == "hourly":
#             total_cost = hours * float(bike.price_per_hour)
#         else:
#             total_cost = float(bike.price_per_day)  # За день
#     else:  # days
#         days = int(duration[:-1])
#         duration_text = f"{days} день(дней)"
#         total_cost = days * float(bike.price_per_day)
#     
#     type_text = {
#         "hourly": "⏰ Почасовая",
#         "daily": "📅 Посуточная"
#     }
#     
#     battery_info = ""
#     if bike.batteries:
#         battery_numbers = [b.number for b in bike.batteries]
#         battery_info = f"\n🔋 Батарейки: {', '.join(battery_numbers)}"
#     
#     confirmation_text = (
#         f"📋 **Подтверждение аренды**\n\n"
#         f"🚴‍♂️ Велосипед: #{bike.number} - {bike.model}\n"
#         f"📍 Локация: {bike.location or 'Основная точка'}{battery_info}\n"
#         f"📅 Тип аренды: {type_text.get(rental_type)}\n"
#         f"⏱️ Продолжительность: {duration_text}\n"
#         f"💰 **Стоимость: {total_cost:.2f} ₽**\n\n"
#         f"Подтверждаете аренду?"
#     )
#     
#     await message.edit_text(
#         confirmation_text,
#         reply_markup=get_rental_confirmation_keyboard()
#     )
#     await state.set_state(RentalStates.confirming_rental)
# 
# 
# # Обработчики навигации
# @router.callback_query(F.data == "back_to_rental_type")
# async def back_to_rental_type(callback: CallbackQuery, state: FSMContext):
#     """Возврат к выбору типа аренды"""
#     await callback.message.edit_text(
#         "🚴‍♂️ **Аренда велосипеда**\n\n"
#         "Выберите тип аренды:",
#         reply_markup=get_rental_type_keyboard()
#     )
#     await state.set_state(RentalStates.choosing_rental_type)
# 
# 
# @router.callback_query(F.data == "back_to_main")
# async def back_to_main(callback: CallbackQuery, state: FSMContext):
#     """Возврат в главное меню"""
#     await callback.message.delete()
#     await callback.message.answer("Возвращаемся в главное меню")
#     await state.clear()
# 
# 
# @router.callback_query(F.data == "cancel_rental")
# async def cancel_rental(callback: CallbackQuery, state: FSMContext):
#     """Отмена аренды"""
#     await callback.message.edit_text("❌ Аренда отменена")
#     await state.clear()
# 
# ================================================================================== 