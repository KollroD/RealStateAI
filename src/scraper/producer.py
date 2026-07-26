import asyncio
import json
import math
import os
import redis.asyncio as aioredis
from aiokafka import AIOKafkaProducer
from src.scraper.network import HttpClient, load_proxy


async def start_crawling(client, category_id: int, location_id: int):
    # Подключаемся к Кафке
    producer = AIOKafkaProducer(bootstrap_servers="localhost:9092")
    await producer.start()

    redis_client = await aioredis.from_url(
        "redis://localhost:6379", decode_responses=True
    )
    current_page = 1
    max_page = 1

    try:
        while current_page <= max_page:
            print(f"Парсим страницу каталога {current_page} из {max_page}...")

            url = (
                f"https://www.avito.ru/web/1/js/items?"
                f"categoryId={category_id}&locationId={location_id}&p={current_page}"
                f"&params[201]=1060&params[504]=5256&params[349941936]=129623"
                f"&verticalCategoryId=1&rootCategoryId=4&localPriority=0&updateListOnly=true"
            )

            data = await client.get_json(url)
            if not data:
                continue

            # Вычисляем лимит страниц один раз
            if current_page == 1:
                total_elements = data.get("totalElements", 0)
                items_on_page = data.get("itemsOnPage", 50)
                if items_on_page > 0:
                    max_page = math.ceil(total_elements / items_on_page)
                    print(
                        f"Найдено {total_elements} объявлений. "
                        f"Всего страниц: {max_page}"
                    )

            # Ищем данные в правильном месте (API может отдавать в 'items')
            items = data.get("items") or data.get("catalog", {}).get("items", [])

            for item in items:
                if item.get("type") == "item":
                    apt_id = item.get("id")
                    url_path = item.get("urlPath")
                    if not apt_id and url_path:
                        apt_id = url_path.split("_")[-1]

                    if apt_id and url_path:
                        redis_key = f"avito:parsed:{apt_id}"
                        is_parsed = await redis_client.exists(redis_key)

                        if is_parsed:
                            continue

                        full_url = f"https://www.avito.ru/items/ads{url_path}"

                        # ПУЛЯЕМ В КАФКУ СРАЗУ
                        message = json.dumps({"url": full_url}).encode("utf-8")
                        await producer.send("avito_apartments", message)
                        await redis_client.set(redis_key, "1", ex=2592000)

            current_page += 1
            # Небольшая пауза, чтобы не дудосить Авито
            await asyncio.sleep(1)

    finally:
        await producer.stop()
        print("Краулинг завершен, все ссылки в Кафке.")


if __name__ == "__main__":
    # Получаем путь к папке, где лежит сам producer.py
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Склеиваем его с именем файла
    proxy_path = os.path.join(base_dir, "proxy.txt")

    proxy = load_proxy(proxy_path)

    client = HttpClient(proxy)

    asyncio.run(start_crawling(client, category_id=24, location_id=634930))
