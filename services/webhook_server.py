"""
Webhook сервер для приёма уведомлений от ЮKassa
"""
import asyncio
from aiohttp import web
from loguru import logger

from services.payment_service import yookassa_service


async def handle_yookassa_webhook(request: web.Request) -> web.Response:
    """
    Обработчик webhook от ЮKassa
    
    ЮKassa отправляет POST запросы с JSON данными о событиях платежей
    """
    try:
        # Получаем данные из запроса
        data = await request.json()
        
        logger.info(f"Получен webhook от ЮKassa: {data.get('event', 'unknown')}")
        
        # Обрабатываем событие
        success = await yookassa_service.process_webhook(data)
        
        if success:
            return web.Response(status=200, text="OK")
        else:
            return web.Response(status=500, text="Processing error")
            
    except Exception as e:
        logger.error(f"Ошибка обработки webhook: {e}")
        return web.Response(status=500, text=str(e))


async def health_check(request: web.Request) -> web.Response:
    """Health check endpoint"""
    return web.Response(status=200, text="OK")


def create_webhook_app() -> web.Application:
    """Создать приложение для webhook сервера"""
    app = web.Application()
    
    # Маршруты
    app.router.add_post("/webhook/yookassa", handle_yookassa_webhook)
    app.router.add_get("/health", health_check)
    
    return app


async def run_webhook_server(host: str = "0.0.0.0", port: int = 8080):
    """
    Запустить webhook сервер
    
    Args:
        host: Хост для прослушивания
        port: Порт для прослушивания
    """
    app = create_webhook_app()
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    logger.info(f"🌐 Webhook сервер запущен на http://{host}:{port}")
    logger.info(f"   - ЮKassa webhook: POST http://{host}:{port}/webhook/yookassa")
    logger.info(f"   - Health check: GET http://{host}:{port}/health")
    
    # Держим сервер запущенным
    while True:
        await asyncio.sleep(3600)

