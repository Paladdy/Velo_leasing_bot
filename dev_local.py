#!/usr/bin/env python3
"""
Скрипт для локального запуска бота с тестовым токеном.
Использует конфигурацию из .env.local
"""
import os
import sys
from pathlib import Path

# Проверяем наличие .env.local
env_local = Path(__file__).parent / ".env.local"
if not env_local.exists():
    print("❌ Файл .env.local не найден!")
    print("📝 Создайте файл .env.local на основе config.env.example")
    print("⚠️  Используйте ОТДЕЛЬНЫЙ токен тестового бота!")
    sys.exit(1)

# Проверяем, что токен заменен
with open(env_local, "r") as f:
    content = f.read()
    if "your_test_bot_token_here" in content:
        print("❌ Не забудьте заменить BOT_TOKEN в .env.local!")
        print("1. Создайте тестового бота через @BotFather")
        print("2. Скопируйте токен")
        print("3. Замените 'your_test_bot_token_here' в .env.local")
        sys.exit(1)

print("✅ Запуск локального бота...")
print("📝 Используется конфигурация из .env.local")
print("🤖 Это ТЕСТОВЫЙ бот для разработки")
print("-" * 50)

# Запускаем основной скрипт
from main import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())


