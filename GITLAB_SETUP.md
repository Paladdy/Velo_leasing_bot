# 🚀 Инструкция по загрузке проекта на GitLab

## 📋 Подготовка проекта

### 1. Инициализация Git репозитория
```bash
cd /Users/daniilramkulov/Velo_leasing_bot
git init
git add .
git commit -m "Initial commit: Velo Leasing Bot project"
```

### 2. Создание репозитория на GitLab

1. Зайдите на ваш GitLab (gitlab.com или корпоративный)
2. Нажмите "New Project" → "Create blank project"
3. Заполните данные:
   - **Project name**: `velo-leasing-bot`
   - **Project slug**: `velo-leasing-bot`
   - **Visibility**: Private (рекомендуется)
   - **Initialize repository**: оставьте пустым ❌
4. Нажмите "Create project"

### 3. Подключение локального репозитория к GitLab
```bash
# Замените YOUR_GITLAB_URL и YOUR_USERNAME на ваши данные
git remote add origin https://gitlab.com/YOUR_USERNAME/velo-leasing-bot.git

# Или если используете SSH:
# git remote add origin git@gitlab.com:YOUR_USERNAME/velo-leasing-bot.git

# Отправляем код
git branch -M main
git push -u origin main
```

## ⚠️ ВАЖНО: Безопасность

### Файлы, которые НЕ должны попасть в репозиторий:
- ✅ `.env` - уже исключен в .gitignore
- ✅ `uploads/` - папка с документами пользователей  
- ✅ `logs/` - логи приложения
- ✅ `.idea/` - настройки IDE
- ✅ `__pycache__/` - кэш Python

### Настройка переменных окружения в GitLab CI/CD:

1. Перейдите в Settings → CI/CD → Variables
2. Добавьте следующие переменные:

| Ключ | Значение | Тип | Защищено |
|------|----------|-----|----------|
| `BOT_TOKEN` | Токен вашего бота | Variable | ✅ |
| `DATABASE_URL` | URL базы данных | Variable | ✅ |
| `YOOKASSA_SHOP_ID` | ID магазина ЮKassa | Variable | ✅ |
| `YOOKASSA_SECRET_KEY` | Секретный ключ ЮKassa | Variable | ✅ |
| `ADMIN_IDS` | ID администраторов | Variable | ❌ |
| `REDIS_URL` | URL Redis | Variable | ❌ |

## 🔧 Настройка GitLab CI/CD (опционально)

Создайте файл `.gitlab-ci.yml` для автоматического деплоя:

```yaml
# См. следующий раздел в этом файле
```

## 📁 Структура проекта для Git

```
velo-leasing-bot/
├── .gitignore              ✅ Создан
├── .gitlab-ci.yml          🔄 Создадим отдельно
├── README.md               ✅ Есть
├── requirements.txt        ✅ Есть
├── docker-compose.yml      ✅ Есть
├── Dockerfile             ✅ Есть
├── config.env.example     ✅ Есть (шаблон)
├── bot/                   ✅ Код бота
├── database/              ✅ Модели БД
├── services/              ✅ Бизнес-логика
├── config/                ✅ Настройки
├── scripts/               ✅ Утилиты
├── logs/.gitkeep          ✅ Создан
└── uploads/.gitkeep       ✅ Создан
```

## 🚀 Команды для первоначальной загрузки

```bash
# 1. Перейдите в папку проекта
cd /Users/daniilramkulov/Velo_leasing_bot

# 2. Инициализируйте Git
git init

# 3. Добавьте все файлы (кроме исключенных в .gitignore)
git add .

# 4. Создайте первый коммит
git commit -m "🚀 Initial commit: Velo Leasing Bot

✅ Базовая структура проекта
✅ Модели базы данных
✅ Система регистрации и верификации
✅ Административная панель
✅ Docker конфигурация
🔄 В разработке: платежи, AI-интеграция"

# 5. Добавьте remote (замените URL на ваш)
git remote add origin https://gitlab.com/YOUR_USERNAME/velo-leasing-bot.git

# 6. Отправьте код
git branch -M main
git push -u origin main
```

## 📋 Checklist перед загрузкой

- [ ] Создан .gitignore файл
- [ ] Удален .env из отслеживания Git
- [ ] Проверены секреты в коде (токены, пароли)
- [ ] Создан GitLab репозиторий
- [ ] Настроены переменные окружения в GitLab
- [ ] Обновлен README.md с актуальной информацией
- [ ] Добавлены .gitkeep файлы для пустых папок

## 🔄 Дальнейшая работа

После загрузки используйте стандартный Git workflow:

```bash
# Создание новой ветки для функционала
git checkout -b feature/payment-integration

# Коммиты изменений
git add .
git commit -m "feat: добавлена интеграция с ЮKassa"

# Отправка в GitLab
git push origin feature/payment-integration

# Создание Merge Request в GitLab UI
```

## 📞 Поддержка

При возникновении проблем проверьте:
1. Правильность URL репозитория
2. Права доступа к GitLab
3. SSH ключи (если используете SSH)
4. Настройки .gitignore
