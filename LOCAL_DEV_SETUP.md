# 🔵 Локальная разработка

## Как запускать локально И на сервере

У вас 2 окружения:
- 🟢 **Продакшн** (сервер) - основной бот
- 🔵 **Dev** (локально) - тестовый бот

## 🚀 Быстрый старт для локальной разработки

### 1. Создайте тестового бота

```
Telegram → @BotFather
/newbot
Название: Velo Leasing TEST
Username: velo_leasing_test_bot (или другой)
```

Скопируйте токен тестового бота.

### 2. Настройте .env.local

```bash
# Откройте файл
nano .env.local

# Замените строку:
BOT_TOKEN=ВАШ_ТЕСТОВЫЙ_ТОКЕН_ОТ_BOTFATHER

# Также укажите ваш Telegram ID:
ADMIN_IDS=ваш_telegram_id

# Сохраните: Ctrl+O, Enter, Ctrl+X
```

### 3. Скопируйте конфиг для Docker (если используете Docker)

```bash
# Локально используем .env.local
cp .env.local config/test.env
```

### 4. Запустите локально

```bash
docker compose down
docker compose build --no-cache bot
docker compose up -d
docker compose logs bot -f
```

### 5. Тестируйте!

Откройте вашего **ТЕСТОВОГО** бота в Telegram и отправьте `/start`

---

## 🟢 Продакшн (На сервере)

### На сервере используйте .env.prod

```bash
# На сервере
cd ~/dev/velo-leasing-bot

# Создайте .env.prod с настройками продакшена
nano .env.prod
# Вставьте содержимое из .env.prod (токен основного бота)

# Скопируйте в config
cp .env.prod config/test.env

# Запустите
docker-compose down
docker-compose build --no-cache bot
docker-compose up -d
```

---

## 📋 Структура файлов

```
.env.local      # 🔵 Локальная разработка (не в git) - используется автоматически
.env            # 🟢 Продакшн сервер (не в git)
.gitignore      # Игнорирует .env*
config/test.env # Для Docker (копия .env.local)
```

---

## 🔄 Рабочий процесс

### Локально (разработка):

```bash
# 1. Вносим изменения в код
nano bot/handlers/...

# 2. Тестируем (Python напрямую)
python dev_local.py

# Или через Docker:
cp .env.local config/test.env
docker compose restart bot
docker compose logs bot -f

# 3. Коммитим
git add .
git commit -m "feat: новая фича"
git push github main
```

### На сервере (деплой):

```bash
# 1. Подключаемся
ssh root@сервер

# 2. Обновляем код
cd ~/dev/velo-leasing-bot
git pull origin main  # или git pull github main

# 3. Используем prod конфиг (убедитесь что .env существует на сервере)
cp .env config/test.env

# 4. Перезапускаем
docker-compose build bot
docker-compose restart bot
docker-compose logs bot -f
```

---

## ⚠️ Важно

- **НЕ комитьте** файлы `.env.local` и `.env` в git (там токены!)
- **Всегда используйте** разные токены для dev и prod
- **Тестовый бот** только для разработки
- **Основной бот** только на продакшн сервере
- `.env.local` **автоматически** используется при запуске локально

---

## 🎯 Преимущества

✅ Можно тестировать локально без остановки продакшн бота  
✅ Разные БД для dev и prod  
✅ Безопасно экспериментировать  
✅ Быстрая разработка

---

**Готово к использованию!** 🚀


