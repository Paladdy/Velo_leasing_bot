-- Добавление поля language в таблицу users
-- Выполните этот скрипт вручную или через psql

-- Проверяем, существует ли уже поле
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'language'
    ) THEN
        ALTER TABLE users 
        ADD COLUMN language VARCHAR(5) NOT NULL DEFAULT 'ru';
        
        RAISE NOTICE 'Поле language успешно добавлено в таблицу users';
    ELSE
        RAISE NOTICE 'Поле language уже существует в таблице users';
    END IF;
END $$;

