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
    save_dir = f"media/apartments/{apartment_id}"

    if not image_urls:
        return local_paths

    os.makedirs(save_dir, exist_ok=True)

    # Используем httpx для скачивания
    # (без всяких прокси, картинки Авито отдает CDN без защиты)
    async with httpx.AsyncClient(timeout=15.0) as client:
        for i, url in enumerate(image_urls):
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    # Открываем картинку через Pillow
                    img = Image.open(BytesIO(response.content))

                    # Конвертируем в RGB (на случай, если попадется PNG с прозрачностью)
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")

                    # Сохраняем в WebP с качеством 80 (весить будет копейки)
                    file_path = f"{save_dir}/{i}.webp"
                    img.save(file_path, "WEBP", quality=80)
                    local_paths.append(file_path)
            except Exception as e:
                print(f"⚠️ Ошибка загрузки картинки {url}: {e}")

            # Небольшая пауза, чтобы не дудосить CDN
            await asyncio.sleep(0.5)

    return local_paths
