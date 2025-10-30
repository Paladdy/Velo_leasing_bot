-- SQL скрипт для обновления относительных путей к документам на абсолютные
-- Используйте этот скрипт, если документы были сохранены с относительными путями

-- Сначала посмотрим, какие пути есть в базе
SELECT id, user_id, document_type, file_path 
FROM documents 
WHERE file_path NOT LIKE '/%'
ORDER BY id;

-- Обновляем относительные пути на абсолютные
-- ВАЖНО: Замените /Users/daniilramkulov/Velo_leasing_bot на ваш реальный путь к проекту
UPDATE documents 
SET file_path = REPLACE(file_path, 'uploads/', '/Users/daniilramkulov/Velo_leasing_bot/uploads/')
WHERE file_path LIKE 'uploads/%';

UPDATE documents 
SET file_path = REPLACE(file_path, './uploads/', '/Users/daniilramkulov/Velo_leasing_bot/uploads/')
WHERE file_path LIKE './uploads/%';

-- Проверяем результат
SELECT id, user_id, document_type, file_path 
FROM documents 
ORDER BY id;

