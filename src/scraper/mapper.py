import re


def extract_number(text: str):
    """Вытаскивает первое число (int или float) из строки."""
    if not text:
        return None
    # Меняем запятые на точки для дробных чисел и ищем цифры
    match = re.search(r"[\d\.,]+", text.replace(",", "."))
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None


def map_apartment_data(raw_json: dict) -> dict:
    item = raw_json.get("item")
    if not item:
        return {}

    apartment = {
        "id": str(item.get("id")),
        "text_description": item.get("title"),
        "price": item.get("price"),
        "rooms": None,  # заполняешь в цикле params
        "total_area": None,  # заполняешь в цикле params
        "floor": None,  # заполняешь в цикле params
        "total_floors": None,  # заполняешь в цикле params
        "deposit": None,  # заполняешь в rent_terms
        "renovation": None,  # заполняешь в цикле params
        # Дефолтные значения для ML-разметки
        "label_is_agency": False,
        "label_is_fake": False,
        "label_hidden_fees": False,
        # Сюда скидываешь всё, что не влезло в колонки
        "metadata_json": {},
    }

    params_items = item.get("paramsDto", {}).get("items", [])

    for param in params_items:
        title = param.get("title")
        desc = param.get("description")

        # Чистим числа для метрик
        if title == "Количество комнат":
            apartment["rooms"] = extract_number(desc)
        elif title == "Общая площадь":
            apartment["total_area"] = extract_number(desc)
        elif title == "Площадь кухни":
            apartment["kitchen_area"] = extract_number(desc)
        elif title == "Жилая площадь":
            apartment["living_area"] = extract_number(desc)
        elif title == "Этаж":
            floors = re.findall(r"\d+", desc) if desc else []
            apartment["floor"] = int(floors[0]) if len(floors) > 0 else None
            apartment["total_floors"] = int(floors[1]) if len(floors) > 1 else None

        # Категориальные признаки оставляем строками, просто чистим пробелы
        elif title in ["Санузел", "Мебель", "Техника"]:
            apartment[title] = desc.replace("\xa0", " ").strip() if desc else None
        elif title == "Ремонт":
            apartment["renovation"] = (
                desc.replace("\xa0", " ").strip() if desc else None
            )

    # Достаем залог и комиссию из условий аренды
    rent_terms = item.get("rentTermsParams", {}).get("data", {}).get("items", [])
    for term in rent_terms:
        title = term.get("title")
        desc = term.get("description")

        if title == "Залог":
            apartment["deposit"] = extract_number(desc)
        elif title == "Комиссия":
            apartment["commission_percent"] = extract_number(desc)

    known_keys = [
        "id",
        "text_description",
        "price",
        "rooms",
        "label_is_agency",
        "label_is_fake",
        "label_hidden_fees",
        "total_area",
        "floor",
        "total_floors",
        "deposit",
        "renovation",
        "metadata_json",
    ]

    metadata = {k: v for k, v in apartment.items() if k not in known_keys}
    apartment["metadata_json"] = metadata

    return apartment
