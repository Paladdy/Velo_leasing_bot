# 🚴‍♂️ Velo Leasing Bot - Система аренды велосипедов

## 📋 Описание проекта

Telegram-бот для автоматизированного управления арендой велосипедов с поддержкой двух ролей пользователей, интеграцией платежной системы и полным циклом аренды.

## 🏗️ Архитектура проекта

### 📁 Структура файлов

```
velo_leasing_bot/
├── bot/                    # Основной код бота
│   ├── handlers/          # Обработчики команд
│   │   ├── client/        # Хэндлеры для клиентов
│   │   ├── admin/         # Хэндлеры для админов
│   │   └── common/        # Общие хэндлеры
│   ├── keyboards/         # Клавиатуры и кнопки
│   ├── states/            # FSM состояния
│   ├── middlewares/       # Промежуточное ПО
│   └── utils/             # Утилиты
├── database/              # Работа с БД
│   ├── models/            # SQLAlchemy модели
│   │   ├── user.py        # Модель пользователей
│   │   ├── bike.py        # Модели велосипедов и батареек
│   │   ├── rental.py      # Модель аренды
│   │   ├── payment.py     # Модель платежей
│   │   └── document.py    # Модель документов
│   ├── migrations/        # Alembic миграции
│   └── base.py           # Базовая настройка SQLAlchemy
├── services/              # Бизнес-логика
│   ├── payment/           # ЮKassa интеграция
│   ├── document/          # Обработка документов
│   └── rental/            # Логика аренды
├── config/                # Конфигурация
│   └── settings.py        # Настройки приложения
├── requirements.txt       # Зависимости
├── config.env.example     # Пример конфигурации
└── README.md             # Документация
```

## 🛠️ Технологический стек

- **Bot Framework**: aiogram 3.4.1 (асинхронный)
- **Database**: PostgreSQL + SQLAlchemy 2.0 + Alembic
- **State Storage**: Redis
- **Payments**: ЮKassa API
- **Configuration**: pydantic-settings
- **Logging**: loguru

## 👥 Роли пользователей

### 🙋‍♂️ Клиент
- Регистрация и верификация документов
- Выбор и аренда велосипедов
- Оплата через ЮKassa
- Продление аренды
- Заказ ремонтных услуг

### 👨‍💼 Администратор
- Проверка и одобрение документов
- Управление парком велосипедов
- Настройка индивидуальных тарифов
- Мониторинг системы

## 🔄 Основные процессы

### 1. Регистрация клиента
1. Команда `/start`
2. Загрузка документов (паспорт, права)
3. Проверка администратором
4. Одобрение/отклонение

### 2. Аренда велосипеда
1. Выбор велосипеда из каталога
2. Автоматическое формирование договора
3. Генерация ссылки на оплату
4. Подтверждение оплаты
5. Активация аренды

### 3. Управление арендой
- Продление через личный кабинет
- Индивидуальные тарифы
- Заявки на ремонт

## 🗄️ Модели базы данных

### User (Пользователи)
- id, telegram_id, username, full_name
- phone, email, role (client/admin)
- registration_date, is_verified

### Bike (Велосипеды)
- id, number, model, status
- location, rental_price_hour, rental_price_day

### Battery (Батарейки)
- id, number, bike_id, capacity, status

### Rental (Аренды)
- id, user_id, bike_id, start_date, end_date
- total_amount, status, contract_data

### Payment (Платежи)
- id, rental_id, amount, payment_id (ЮKassa)
- status, created_at, paid_at

### Document (Документы)
- id, user_id, document_type, file_path
- status, uploaded_at, verified_at

## 📝 История изменений

### Версия 0.1.0 (Начальная настройка)
- ✅ Создана структура проекта
- ✅ Настроены зависимости (requirements.txt)
- ✅ Создан файл конфигурации (config.env.example)
- ✅ Настроены базовые модули:
  - `config/settings.py` - управление настройками через pydantic
  - `database/base.py` - асинхронная работа с БД через SQLAlchemy
  - `database/models/__init__.py` - импорты основных моделей

### Токен бота
```
8212819884:AAHGedjFU10YpxyCYe-6-OVNi7UIUDjtuUE
```

## 🚀 Запуск проекта

### Требования
- Python 3.8+
- PostgreSQL
- Redis

### Установка
```bash
# Клонирование и установка зависимостей
pip install -r requirements.txt

# Настройка окружения
cp config.env.example .env
# Отредактируйте .env файл

# Миграции БД
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head

# Запуск бота
python main.py
```

## 🔧 Настройка

Основные переменные окружения:
- `BOT_TOKEN` - токен Telegram бота
- `DATABASE_URL` - строка подключения к PostgreSQL
- `REDIS_URL` - строка подключения к Redis
- `YOOKASSA_SHOP_ID` - ID магазина ЮKassa
- `YOOKASSA_SECRET_KEY` - секретный ключ ЮKassa
- `ADMIN_IDS` - список ID администраторов (через запятую)

## 📋 TODO

- [ ] Реализовать базовые хэндлеры для клиентов и админов
- [ ] Настроить базу данных и модели
- [ ] Интегрировать систему платежей ЮKassa
- [ ] Добавить систему управления велосипедами и батарейками
- [ ] Создать FSM состояния для процессов
- [ ] Добавить middleware для авторизации
- [ ] Реализовать систему уведомлений

## 📞 Поддержка

Для вопросов по проекту обращайтесь к разработчикам. 