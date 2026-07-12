import math


async def fetch_catalog_urls(client, category_id: int, location_id: int) -> list:
    urls = []
    current_page = 1
    max_page = 1

    while current_page <= 1:
        print(f"Парсим страницу каталога {current_page} из {max_page}...")

        url = f"https://www.avito.ru/web/1/js/items?categoryId={category_id}&locationId={location_id}&p={current_page}&params%5B201%5D=1060&params%5B504%5D=5256&params%5B349941936%5D=129623&verticalCategoryId=1&rootCategoryId=4&localPriority=0&updateListOnly=true"
        data = await client.get_json(url)

        if not data:
            print("Данные каталога не получены, прерываем сбор.")
            break

        # На первой странице вычисляем реальное количество страниц
        if current_page == 1:
            total_elements = data.get("totalElements", 0)
            items_on_page = data.get("itemsOnPage", 50)
            if items_on_page > 0:
                max_page = math.ceil(total_elements / items_on_page)
                print(
                    f"Найдено {total_elements} объявлений. "
                    f"Всего страниц для парсинга: {max_page}"
                )

        # Собираем ссылки на API квартир
        items = data.get("catalog", {}).get("items", [])
        for item in items:
            if item.get("type") == "item":
                url_path = item.get("urlPath")
                if url_path:
                    # Конструируем сразу ссылку для экстрактора!
                    urls.append(f"https://www.avito.ru/items/ads{url_path}")

        current_page += 1

    return list(set(urls))
