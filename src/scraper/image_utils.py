import os
import asyncio
import httpx
from io import BytesIO
from PIL import Image

# Создаем папку, если её нет
os.makedirs("media/apartments", exist_ok=True)


async def download_and_compress_images(image_urls: list, apartment_id: str) -> list:
    """Скачивает картинки, жмет в WebP и возвращает список локальных путей."""
    local_paths = []

    # 1. Путь для сохранения в БД (короткий и красивый)
    db_dir = f"media/apartments/{apartment_id}"

    # 2. Физический путь на твоем диске (с учетом папки src/scraper)
    system_dir = f"src/scraper/{db_dir}"

    if not image_urls:
        return local_paths

    # Создаем папку физически на диске
    os.makedirs(system_dir, exist_ok=True)

    # Используем httpx для скачивания
    async with httpx.AsyncClient(timeout=15.0) as client:
        for i, url in enumerate(image_urls):
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    # Открываем картинку через Pillow
                    try:
                        img = Image.open(BytesIO(response.content))

                        # Конвертируем в RGB (на случай, если попадется PNG
                        # с прозрачностью)
                        if img.mode in ("RGBA", "P"):
                            img = img.convert("RGB")

                            # Физический путь, куда Pillow будет сохранять файл
                            system_file_path = f"{system_dir}/{i}.webp"

                            # Путь, который пойдет в список для базы данных
                            db_file_path = f"{db_dir}/{i}.webp"

                            # Сохраняем файл на диск
                            img.save(system_file_path, "WEBP", quality=80)

                            # А вот в массив для базы добавляем чистый путь!
                            local_paths.append(db_file_path)
                    except Exception:
                        print(f"❌ Картинка битая: {url}. Пропускаю.")
            except Exception as e:
                print(f"⚠️ Ошибка загрузки картинки {url}: {e}")

            # Небольшая пауза, чтобы не дудосить CDN
            await asyncio.sleep(0.5)

    return local_paths
