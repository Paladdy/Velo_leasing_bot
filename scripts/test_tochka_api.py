"""
Скрипт для тестирования доступных методов API Точка Банка
"""
import asyncio
import aiohttp
import json
import os
import sys

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings


async def test_tochka_api():
    """Проверить доступные методы API"""
    
    jwt_token = settings.tochka_jwt_token
    customer_code = settings.tochka_customer_code
    
    if not jwt_token or not customer_code:
        print("❌ TOCHKA_JWT_TOKEN или TOCHKA_CUSTOMER_CODE не настроены в .env")
        return
    
    print(f"📋 Customer Code: {customer_code}")
    print(f"🔑 JWT Token: {jwt_token[:50]}...")
    print("-" * 60)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {jwt_token}"
    }
    
    async with aiohttp.ClientSession() as session:
        
        # 1. Проверяем эквайринг - список торговых точек
        print("\n🏪 Проверка эквайринга (retailers)...")
        url = f"https://enter.tochka.com/uapi/acquiring/v1.0/{customer_code}/retailers"
        async with session.get(url, headers=headers) as resp:
            text = await resp.text()
            print(f"   Status: {resp.status}")
            if resp.status == 200:
                print(f"   ✅ Эквайринг доступен!")
                data = json.loads(text)
                print(f"   Данные: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
            else:
                print(f"   ❌ Эквайринг недоступен: {text[:200]}")
        
        # 2. Проверяем СБП - список юр.лиц
        print("\n💳 Проверка СБП (legal-entity)...")
        url = f"https://enter.tochka.com/uapi/sbp/v1.0/{customer_code}/legal-entity"
        async with session.get(url, headers=headers) as resp:
            text = await resp.text()
            print(f"   Status: {resp.status}")
            if resp.status == 200:
                print(f"   ✅ СБП доступен!")
                data = json.loads(text)
                print(f"   Данные: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
            else:
                print(f"   ❌ СБП недоступен: {text[:200]}")
        
        # 3. Проверяем счета
        print("\n🏦 Проверка счетов (accounts)...")
        url = f"https://enter.tochka.com/uapi/open-banking/v1.0/{customer_code}/accounts"
        async with session.get(url, headers=headers) as resp:
            text = await resp.text()
            print(f"   Status: {resp.status}")
            if resp.status == 200:
                print(f"   ✅ Счета доступны!")
                data = json.loads(text)
                accounts = data.get("Data", {}).get("Account", [])
                for acc in accounts[:3]:
                    print(f"   - {acc.get('accountId')}: {acc.get('currency')} ({acc.get('status')})")
            else:
                print(f"   ❌ Счета недоступны: {text[:200]}")
        
        # 4. Проверяем платежные ссылки (Payment Link) - альтернативный метод
        print("\n🔗 Проверка платежных ссылок...")
        url = f"https://enter.tochka.com/uapi/payment-link/v1.0/{customer_code}/links"
        async with session.get(url, headers=headers) as resp:
            text = await resp.text()
            print(f"   Status: {resp.status}")
            if resp.status == 200:
                print(f"   ✅ Платежные ссылки доступны!")
            else:
                print(f"   ❌ Платежные ссылки недоступны: {text[:200]}")

    print("\n" + "=" * 60)
    print("💡 Рекомендации:")
    print("   - Если СБП доступен - можно использовать QR-коды для оплаты")
    print("   - Если эквайринг недоступен - подключите в ЛК Точки")
    print("   - Если платежные ссылки доступны - это самый простой способ")


if __name__ == "__main__":
    asyncio.run(test_tochka_api())

