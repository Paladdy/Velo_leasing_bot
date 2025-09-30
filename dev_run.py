#!/usr/bin/env python3
"""
Скрипт для запуска бота в режиме разработки с автоперезагрузкой
"""
import os
import sys
import time
import subprocess
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class BotRestartHandler(FileSystemEventHandler):
    """Обработчик изменений файлов для перезапуска бота"""
    
    def __init__(self):
        self.process = None
        self.last_restart = 0
        self.restart_bot()
    
    def on_modified(self, event):
        if event.is_directory:
            return
            
        # Проверяем только Python файлы
        if not event.src_path.endswith('.py'):
            return
            
        # Избегаем слишком частых перезапусков
        current_time = time.time()
        if current_time - self.last_restart < 2:  # Минимум 2 секунды между перезапусками
            return
            
        print(f"🔄 Изменен файл: {event.src_path}")
        self.restart_bot()
        self.last_restart = current_time
    
    def restart_bot(self):
        """Перезапуск процесса бота"""
        if self.process:
            print("🛑 Останавливаем бота...")
            self.process.terminate()
            self.process.wait()
        
        print("🚀 Запускаем бота...")
        self.process = subprocess.Popen([sys.executable, 'main.py'])

def main():
    """Главная функция режима разработки"""
    print("🔧 Режим разработки запущен")
    print("📁 Отслеживаем изменения в Python файлах...")
    print("💡 Для остановки нажмите Ctrl+C")
    
    # Настройка наблюдателя
    event_handler = BotRestartHandler()
    observer = Observer()
    
    # Отслеживаем изменения в основных папках
    watch_paths = ['bot/', 'database/', 'config/', 'services/']
    for path in watch_paths:
        if Path(path).exists():
            observer.schedule(event_handler, path, recursive=True)
            print(f"👁️ Отслеживаем: {path}")
    
    # Отслеживаем main.py
    observer.schedule(event_handler, '.', recursive=False)
    
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Остановка режима разработки...")
        observer.stop()
        if event_handler.process:
            event_handler.process.terminate()
    
    observer.join()

if __name__ == "__main__":
    main() 