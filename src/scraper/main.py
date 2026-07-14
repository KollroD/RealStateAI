import asyncio
from random import uniform
from network import load_proxy, HttpClient  # load_proxies
from crawler import fetch_catalog_urls
from extractor import fetch_apartment_data
from mapper import map_apartment_data
from src.shared.database.database import async_session_maker
from src.shared.database.models import MLDataset
from image_utils import download_and_compress_images


async def main():
    # 1. Загружаем твои 50 прокси из файла
    """proxies = load_proxies("proxies.txt")
    print(f"Успешно загружено прокси: {len(proxies)} шт.")

    if not proxies:
        print("Список прокси пуст. Проверь файл proxies.txt")
        return
    """
    proxy = load_proxy("proxy.txt")
    # 2. Инициализируем сетевой движок
    client = HttpClient(proxy)

    # 3. Запускаем краулер (он сам пройдет по всем страницам)
    # 24 = Квартиры, 640860 = Нижний Новгород
    api_urls = await fetch_catalog_urls(client, category_id=24, location_id=640860)
    print(f"Итого собрано уникальных ссылок на API квартир: {len(api_urls)}")

    # 4. Проходимся по каждой собранной ссылке
    for i in api_urls:
        url = i.split("?")[0]
        raw_data = await fetch_apartment_data(client, url)

        if raw_data:
            real_url = url.replace("/items/ads/", "/")
            clean_data = map_apartment_data(raw_data, real_url)

            if not clean_data or clean_data.get("id") is None:
                print(f"Пропуск записи: нет данных или id для {url}")
                continue

            image_urls_to_download = clean_data.pop("raw_image_links", [])
            apt_id = clean_data["id"]

            # 2. СКАЧИВАЕМ КАРТИНКИ
            if image_urls_to_download:
                print(f"📸 Качаем фото для квартиры {apt_id}...")
                local_images = await download_and_compress_images(
                    image_urls_to_download, apt_id
                )
            else:
                local_images = []

            # 3. Записываем локальные пути в словарь для БД
            clean_data["images_path"] = local_images

            # Создаем объект модели
            listing = MLDataset(**clean_data)

            # Записываем в БД
            async with async_session_maker() as session:
                # .merge() делает "upsert": если id уже есть, он обновит поля,
                # если нет — создаст новую запись. Это спасет от ошибок дубликатов.
                await session.merge(listing)
                await session.commit()

            print(f"✅ Записано в БД: {clean_data.get('id')}")

        # Обязательный джиттер (рандомизированная пауза) между запросами к карточкам
        await asyncio.sleep(uniform(5, 10))


if __name__ == "__main__":
    asyncio.run(main())
