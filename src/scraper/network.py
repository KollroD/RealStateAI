import asyncio
import random
from curl_cffi.requests import AsyncSession


def load_proxy(filepath: str) -> str:
    """Берет одну строку конфига прокси."""
    with open(filepath, "r") as f:
        line = f.readline().strip()
        host, port, user, password = line.split(":")
        return f"http://{user}:{password}@{host}:{port}"


class HttpClient:
    def __init__(self, proxy_url: str):
        self.proxy = proxy_url
        # Куки не нужны! Мы притворяемся свежим юзером каждый раз
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.avito.ru/",
        }

    async def get_json(self, url: str, max_retries: int = 5) -> dict:
        for attempt in range(max_retries):
            try:
                # impersonate="chrome120" делает TLS-отпечаток 1 в 1 как у Хрома
                async with AsyncSession(
                    proxy=self.proxy, impersonate="chrome120", timeout=30.0
                ) as client:
                    response = await client.get(url, headers=self.headers)

                    if response.status_code == 200:
                        return response.json()
                    elif response.status_code == 429:
                        wait_time = (attempt + 1) * 20
                        print(f"[429] Авито притормозил. Ждем {wait_time} сек...")
                        await asyncio.sleep(wait_time)
                        continue
                    elif response.status_code == 404:
                        print("Объявление, видимо, снято с продажи, пропускаем...")
                        return {}
                    else:
                        print(f"Статус {response.status_code} при запросе {url}")

            except Exception as e:
                print(f"Ошибка [{type(e).__name__}]: {str(e)}")

            await asyncio.sleep(random.uniform(2.0, 8.0))
        return {}
