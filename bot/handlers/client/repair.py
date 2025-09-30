from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from database.base import async_session_factory
from database.models.user import User, UserStatus
from database.models.rental import Rental, RentalStatus

router = Router()


@router.message(F.text == "🔧 Ремонт")
async def repair_menu(message: Message, state: FSMContext):
    """Главное меню заявок на ремонт"""
    telegram_id = message.from_user.id
    
    async with async_session_factory() as session:
        # Проверяем пользователя
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer("❌ Пользователь не найден. Пройдите регистрацию командой /start")
            return
            
        if user.status != UserStatus.VERIFIED:
            await message.answer(
                "❌ Для подачи заявки на ремонт необходимо пройти верификацию.\n"
                "📄 Загрузите документы и дождитесь их одобрения администратором."
            )
            return
        
        # Получаем активные аренды пользователя
        rentals_result = await session.execute(
            select(Rental)
            .where(Rental.user_id == user.id)
            .where(Rental.status == RentalStatus.ACTIVE)
        )
        active_rentals = rentals_result.scalars().all()
    
    repair_text = (
        "🔧 **Заявка на ремонт**\n\n"
        "Если у вас возникли проблемы с велосипедом во время аренды, "
        "вы можете подать заявку на ремонт.\n\n"
        "📋 **Процесс:**\n"
        "1. Опишите проблему\n"
        "2. Прикрепите фото (при необходимости)\n"
        "3. Администратор оценит стоимость\n"
        "4. Вы получите ссылку на оплату\n\n"
    )
    
    keyboard = []
    
    if active_rentals:
        repair_text += f"🚴‍♂️ **У вас есть {len(active_rentals)} активных аренд**\n"
        keyboard.append([InlineKeyboardButton(text="🔧 Подать заявку на ремонт", callback_data="repair_create")])
    else:
        repair_text += "ℹ️ У вас нет активных аренд.\nДля подачи заявки на ремонт сначала арендуйте велосипед."
    
    # Кнопка истории заявок
    keyboard.append([InlineKeyboardButton(text="📋 История заявок", callback_data="repair_history")])
    keyboard.append([InlineKeyboardButton(text="❓ Частые вопросы", callback_data="repair_faq")])
    
    inline_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None
    
    await message.answer(repair_text, reply_markup=inline_keyboard)


@router.callback_query(F.data == "repair_create")
async def create_repair_request(callback: CallbackQuery, state: FSMContext):
    """Создать заявку на ремонт"""
    await callback.message.edit_text(
        "🔧 **Новая заявка на ремонт**\n\n"
        "📝 Пожалуйста, опишите проблему с велосипедом:\n"
        "• Что именно сломалось?\n"
        "• При каких обстоятельствах?\n"
        "• Насколько серьезная проблема?\n\n"
        "Напишите подробное описание проблемы:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="repair_cancel")]
        ])
    )
    await state.set_state(RepairStates.waiting_repair_description)


@router.callback_query(F.data == "repair_history")
async def repair_history(callback: CallbackQuery, state: FSMContext):
    """История заявок на ремонт"""
    await callback.message.edit_text(
        "📋 **История заявок на ремонт**\n\n"
        "🚧 Раздел в разработке\n\n"
        "Здесь будет отображаться история ваших заявок на ремонт:\n"
        "• Статус заявок\n"
        "• Стоимость ремонта\n"
        "• Дата подачи и выполнения\n"
        "• Комментарии администратора",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="repair_back")]
        ])
    )


@router.callback_query(F.data == "repair_faq")
async def repair_faq(callback: CallbackQuery, state: FSMContext):
    """Частые вопросы по ремонту"""
    faq_text = (
        "❓ **Частые вопросы - Ремонт**\n\n"
        "**Q: Кто оплачивает ремонт?**\n"
        "A: Ремонт оплачивается арендатором, если поломка произошла по его вине.\n\n"
        "**Q: Сколько стоит ремонт?**\n"
        "A: Стоимость оценивается администратором индивидуально в зависимости от характера поломки.\n\n"
        "**Q: Как долго длится ремонт?**\n"
        "A: Обычно от 1 до 7 дней, в зависимости от сложности.\n\n"
        "**Q: Что если поломка не по моей вине?**\n"
        "A: Обратитесь к администратору - ремонт может быть бесплатным.\n\n"
        "**Q: Можно ли продолжить аренду другого велосипеда?**\n"
        "A: Да, вы можете арендовать другой велосипед, пока идет ремонт."
    )
    
    await callback.message.edit_text(
        faq_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔧 Подать заявку", callback_data="repair_create")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="repair_back")]
        ])
    )


@router.callback_query(F.data == "repair_back")
async def back_to_repair_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в меню ремонта"""
    fake_message = type('obj', (object,), {
        'answer': callback.message.edit_text,
        'from_user': callback.from_user
    })()
    await repair_menu(fake_message, state)


@router.callback_query(F.data == "repair_cancel")
async def cancel_repair_request(callback: CallbackQuery, state: FSMContext):
    """Отмена создания заявки"""
    await state.clear()
    await back_to_repair_menu(callback, state)


# Обработчик для описания проблемы
# Создаем состояние для ремонта
from aiogram.fsm.state import State, StatesGroup

class RepairStates(StatesGroup):
    waiting_repair_description = State()

@router.message(RepairStates.waiting_repair_description, F.text)
async def process_repair_description(message: Message, state: FSMContext):
    """Обработка описания проблемы для ремонта"""
    
    if not message.text or len(message.text.strip()) < 10:
        await message.answer(
            "❌ Пожалуйста, опишите проблему более подробно (минимум 10 символов).\n"
            "Это поможет администратору точнее оценить стоимость ремонта."
        )
        return
    
    description = message.text.strip()
    
    await message.answer(
        f"✅ **Заявка принята!**\n\n"
        f"📝 **Описание проблемы:**\n{description}\n\n"
        f"⏳ Ваша заявка отправлена администратору для оценки стоимости.\n"
        f"📱 Мы уведомим вас, когда будет готова смета.\n\n"
        f"🕐 Обычно оценка занимает до 2 часов в рабочее время.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 История заявок", callback_data="repair_history")]
        ])
    )
    
    await state.clear()
    
    # TODO: Здесь нужно сохранить заявку в базу данных и уведомить администратора
    print(f"🔧 Новая заявка на ремонт от {message.from_user.full_name}: {description}") 