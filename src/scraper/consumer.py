import asyncio
import json
import os
from aiokafka import AIOKafkaConsumer

from src.scraper.network import HttpClient, load_proxy
from src.scraper.extractor import fetch_apartment_data
from src.scraper.image_utils import download_and_compress_images
from src.scraper.mapper import map_apartment_data
from src.shared.database.database import async_session_maker
from src.shared.database.models import MLDataset

from src.ml_pipeline.cv.detector import AntiFraudDetector

# Ограничиваем количество одновременных задач
CONCURRENCY_LIMIT = 3
semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

print("🤖 Загрузка ML-модели детектора...")
detector = AntiFraudDetector()
print("✅ Нейронка готова к бою!")


async def process_single_apartment(url, session_maker):
    """Эта функция полностью обрабатывает ОДНУ квартиру"""
    async with semaphore:
        print(f"Начал обработку: {url}")

        url = url.split("?")[0]
        # 1. Асинхронный запрос сырых данных
        raw_data = await fetch_apartment_data(client=client, api_url=url)
        if not raw_data:
            return

        # 2. Маппер (работает с CPU, выполняется мгновенно, не тормозит сеть)
        real_url = url.replace("/items/ads/", "/")
        clean_data = map_apartment_data(raw_data, real_url)

        # 3. Асинхронная скачка фоток
        image_urls = clean_data.pop("raw_image_links", [])

        apt_id = clean_data.get("id")

        if image_urls and apt_id:
            print(f"📸 Скачиваю {len(image_urls)} фото для квартиры {apt_id}...")
            # Вызываем твою новую функцию
            clean_data["images_path"] = await download_and_compress_images(
                image_urls, str(apt_id)
            )
        else:
            clean_data["images_path"] = []

        is_fake = False
        current_seller = clean_data.get("seller_id")

        if clean_data["images_path"]:
            print(f"🕵️ Проверка на антифрод для {apt_id}...")
            for img_path in clean_data["images_path"]:
                # Передаем текущего автора в детектор
                orig_apt_id, orig_seller_id = await detector.check_image_for_duplicates(
                    img_path, current_seller
                )

                if orig_apt_id and orig_apt_id != str(apt_id):
                    # Проверяем, кто украл:
                    if current_seller and orig_seller_id == current_seller:
                        print(
                            f"⚠️ Найдено совпадение фото, но автор тот "
                            f"же ({current_seller}). "
                            f"Вероятно, это типовой рендер/агентство."
                        )
                        # Тут можно поставить специальный тег, например
                        # label_is_agency = True
                        clean_data["label_is_agency"] = True
                    else:
                        print(
                            f"🚨 АХТУНГ! Квартира {apt_id} (автор {current_seller}) "
                            f"УКРАЛА фото "
                            f"у {orig_apt_id} (автор {orig_seller_id})!"
                        )
                        is_fake = True
                        break

        clean_data["is_duplicate"] = is_fake

        # 4. Асинхронная запись в БД

        db_data = MLDataset(**clean_data)

        async with session_maker() as session:
            await session.merge(db_data)
            await session.commit()


async def run_worker():
    consumer = AIOKafkaConsumer("avito_apartments", bootstrap_servers="localhost:9092")
    print("Кафка живет, ждем задачи.")
    await consumer.start()

    tasks = set()

    try:
        async for msg in consumer:
            data = json.loads(msg.value.decode("utf-8"))
            url = data["url"]

            task = asyncio.create_task(
                process_single_apartment(url, async_session_maker)
            )
            tasks.add(task)

            task.add_done_callback(tasks.discard)

    finally:
        await consumer.stop()


if __name__ == "__main__":
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))

        proxy_path = os.path.join(base_dir, "proxy.txt")

        proxy = load_proxy(proxy_path)

        client = HttpClient(proxy)

        asyncio.run(run_worker())
    except KeyboardInterrupt:
        print("Воркер остановлен пользователем")
