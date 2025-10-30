# 🎯 Рефакторинг системы регистрации

## Проблема

**Старая архитектура (некорректная):**
```
1. Пользователь вводит данные → PostgreSQL (статус: PENDING)
2. Загружает документ 1 → попытка сохранить (может провалиться)
3. Загружает документ 2 → попытка сохранить (может провалиться)
❌ Результат: Пользователь в БД без документов (inconsistent state)
```

**Проблемы:**
- Ошибка `Permission denied` оставляла пользователя в состоянии PENDING без документов
- Администратор видел "Документы не загружены", хотя пользователь их отправлял
- Невозможность продолжить регистрацию после ошибки
- Мусор в базе данных

---

## Решение: Redis Staging + Атомарная транзакция

**Новая архитектура:**
```
1. Пользователь вводит данные → Redis (TTL 24ч)
2. Загружает документ 1 → file_id в Redis
3. Загружает документ 2 → file_id в Redis
4. Все готово? → Атомарная транзакция:
   ✅ Создать User в PostgreSQL
   ✅ Скачать все файлы
   ✅ Создать все Documents
   ✅ Commit (если ошибка → rollback всего)
5. Очистить Redis
```

**Преимущества:**
- ✅ PostgreSQL всегда консистентный
- ✅ Откат при любых ошибках
- ✅ Возможность продолжить регистрацию
- ✅ Автоматическая очистка (TTL 24ч)
- ✅ Нет мусора в БД

---

## Архитектура

### 1. Redis Storage (`bot/utils/redis_storage.py`)
```python
registration:{telegram_id}:language = "ru"       # TTL: 24h
registration:{telegram_id}:data = {              # TTL: 24h
    "full_name": "...",
    "phone": "...",
    "username": "...",
    "email": "..."
}
registration:{telegram_id}:documents = {         # TTL: 24h
    "passport": "AgACAgIAAxkBAANE...",  # file_id от Telegram
    "selfie": "AgACAgIAAxkBAANJ..."
}
```

**Методы:**
- `set_language()`, `get_language()`
- `set_user_data()`, `get_user_data()`
- `set_document()`, `get_documents()`
- `is_registration_complete()` - проверка всех данных
- `clear_registration_data()` - очистка после регистрации
- `extend_ttl()` - продление времени жизни

### 2. Registration Service (`services/registration_service.py`)
**Атомарная регистрация:**
```python
async with session.begin():  # Транзакция
    # 1. Создать пользователя
    user = User(...)
    session.add(user)
    await session.flush()  # Получить user.id
    
    # 2. Скачать и сохранить ВСЕ документы
    for file_id in documents:
        file_path = await download_from_telegram(file_id)
        doc = Document(user_id=user.id, file_path=file_path)
        session.add(doc)
    
    # 3. Commit (или rollback при ошибке)
    await session.commit()
```

**При ошибке:**
- Автоматический rollback транзакции
- Удаление скачанных файлов
- Данные остаются в Redis
- Пользователь может повторить попытку

### 3. Cleanup Service (`services/cleanup_service.py`)
**Background задача (каждый час):**
- Находит файлы без записей в БД (orphaned files)
- Удаляет файлы старше 48 часов
- Удаляет временные файлы старше 24 часов

---

## Процесс регистрации

### Шаг 1: Выбор языка
```
/start → Выбор языка → Redis: language
```

### Шаг 2: Ввод данных
```
Имя → Телефон → Redis: user_data
```

### Шаг 3: Загрузка документов
```
Паспорт/Права → Redis: documents.passport
Селфи → Redis: documents.selfie
```

### Шаг 4: Атомарная регистрация
```python
if all_documents_uploaded:
    try:
        async with transaction:
            user = create_user()
            for doc in documents:
                download_and_save(doc)
            commit()
        
        # Успех
        clear_redis()
        notify_user("Регистрация завершена!")
    except Exception:
        # Ошибка - данные остаются в Redis
        rollback()
        notify_user("Ошибка. Попробуйте /start")
```

### Продолжение регистрации
```
/start → Проверка Redis → Есть данные?
    → Да: "Продолжить регистрацию?"
    → Нет: "Начать новую регистрацию"
```

---

## Тестирование

### 1. Успешная регистрация
```bash
1. Отправить /start боту
2. Выбрать язык
3. Ввести имя
4. Отправить телефон
5. Загрузить паспорт
6. Загрузить селфи
7. Проверить в PostgreSQL:
   SELECT * FROM users WHERE telegram_id = YOUR_ID;
   SELECT * FROM documents WHERE user_id = (SELECT id FROM users WHERE telegram_id = YOUR_ID);
```

**Ожидаемый результат:**
- ✅ Пользователь создан в БД
- ✅ Все документы сохранены
- ✅ Файлы существуют на диске
- ✅ Redis очищен

### 2. Прерванная регистрация
```bash
1. Начать регистрацию (/start)
2. Ввести данные
3. Загрузить ОДИН документ
4. Закрыть бота
5. Через час отправить /start снова
```

**Ожидаемый результат:**
- ✅ Бот предлагает продолжить
- ✅ Уже загруженный документ не нужно загружать снова
- ✅ После загрузки всех документов - регистрация завершается

### 3. Ошибка при регистрации
```bash
1. Начать регистрацию
2. Загрузить все документы
3. (Симулировать ошибку - например, отключить диск)
4. Проверить PostgreSQL
```

**Ожидаемый результат:**
- ✅ Пользователь НЕ создан в БД
- ✅ Документы НЕ созданы в БД
- ✅ Данные остаются в Redis
- ✅ Можно попробовать снова через /start

### 4. Cleanup задача
```bash
# Создать orphaned файл
echo "test" > uploads/test_orphaned.jpg

# Подождать 2 дня или изменить mtime
touch -t 202310011200 uploads/test_orphaned.jpg

# Запустить cleanup вручную
python services/cleanup_service.py
```

**Ожидаемый результат:**
- ✅ Orphaned файлы удалены
- ✅ Файлы из БД сохранены
- ✅ Логи показывают статистику

---

## Мониторинг и логирование

### Логи регистрации
```
✅ Language saved to Redis: 123456 -> ru
✅ User data saved to Redis: 123456 -> John Doe
✅ Document file_id saved to Redis: 123456 -> passport
🎉 All documents collected! Starting atomic registration for 123456
✅ User created: ID=1, Name=John Doe
📥 Downloading passport (file_id: AgACAgIAAxkBAANE...)
✅ Document downloaded: passport -> 123456_passport_AgAC...jpg
✅ Document saved: passport
✅ Atomic registration completed for user 1
🧹 Redis data cleared for 123456
🎉 Registration complete for user 123456
```

### Логи cleanup
```
🧹 Starting cleanup of orphaned files (age > 48h)
📊 Files in database: 15
🗑️  Deleted orphaned file: 123_passport_old.jpg (age: 3 days)
⏳ Kept recent orphaned file: 456_selfie_new.jpg (age: 1 hour)
📊 Cleanup statistics:
   Deleted: 1
   Kept: 2
   Errors: 0
```

---

## Миграция старых пользователей

Для пользователей, которые застряли в состоянии PENDING без документов:

```bash
# Вариант 1: Удалить из БД (они смогут зарегистрироваться заново)
docker exec -it velo-postgres psql -U velo_user -d velo_bot -c "
DELETE FROM users WHERE status = 'PENDING' AND id NOT IN (SELECT DISTINCT user_id FROM documents);
"

# Вариант 2: Исправить пути для существующих документов
docker exec -it velo-bot python3 scripts/fix_document_paths.py
```

---

## Конфигурация

### Redis TTL
```python
# bot/utils/redis_storage.py
REGISTRATION_TTL = 24 * 60 * 60  # 24 часа
```

### Cleanup интервалы
```python
# main.py
cleanup_task = asyncio.create_task(
    run_periodic_cleanup(
        interval_hours=1,        # Проверка каждый час
        max_file_age_hours=48    # Удалять файлы старше 48 часов
    )
)
```

---

## FAQ

**Q: Что если Redis упадет во время регистрации?**  
A: Данные пропадут, пользователь начнет регистрацию заново. PostgreSQL останется чистым.

**Q: Что если файл очень большой и загрузка займет много времени?**  
A: Транзакция подождет. При ошибке - rollback, файлы удалятся, данные останутся в Redis.

**Q: Как долго хранятся данные в Redis?**  
A: 24 часа с автоматическим продлением при /start.

**Q: Можно ли использовать без Redis?**  
A: Нет. Redis критичен для новой архитектуры.

---

## Технические детали

### Зависимости
- Redis (обязательно)
- PostgreSQL + asyncpg
- aiogram 3.x
- SQLAlchemy 2.x (async)

### Файлы изменений
- ✅ `bot/utils/redis_storage.py` - новый
- ✅ `services/registration_service.py` - новый
- ✅ `services/cleanup_service.py` - новый
- ✅ `bot/handlers/common/start.py` - переписан
- ✅ `main.py` - добавлена инициализация и cleanup
- ✅ `locales/ru/messages.json` - добавлены переводы

---

## Коммит

```bash
git add bot/utils/redis_storage.py
git add services/registration_service.py
git add services/cleanup_service.py
git add bot/handlers/common/start.py
git add main.py
git add locales/ru/messages.json
git add REGISTRATION_REFACTORING.md

git commit -m "Рефакторинг регистрации: Redis staging + атомарные транзакции

- Реализован Redis staging для временных данных регистрации (TTL 24ч)
- Атомарная транзакция: User + все Documents создаются вместе
- Автоматический rollback при ошибках
- Продолжение незавершенной регистрации
- Cleanup service для orphaned файлов
- Консистентность PostgreSQL гарантирована

Fixes: Permission denied при сохранении документов
Fixes: Пользователи без документов в БД"
```

---

**Автор**: AI Assistant (Сеньор разработчик режим 🚀)  
**Дата**: 2025-10-30

