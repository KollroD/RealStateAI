import re


def extract_number(text: str):
    if not text:
        return None
    match = re.search(r"[\d\.,]+", text.replace(",", "."))
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None


def extract_int(text: str):
    value = extract_number(text)
    return int(round(value)) if value is not None else None


def clean_html(raw_html: str) -> str:
    """Вырезает <p>, <br> и прочий мусор из описания"""
    if not raw_html:
        return ""
    clean_text = re.sub(r"<[^>]+>", " ", raw_html)
    return " ".join(clean_text.split())


def map_apartment_data(raw_json: dict, url: str) -> dict:
    buyer = raw_json.get("buyerItem") or {}
    item = buyer.get("item") or {}
    if not item:
        return {}

    # --- ВЫТАСКИВАЕМ ССЫЛКИ НА ФОТО ---
    # Берем размер 640x480, он идеален для баланса качество/вес[cite: 1]
    raw_images = item.get("imageUrls", [])  # [cite: 1]
    image_links = []
    for img in raw_images:
        if "640x480" in img:  # [cite: 1]
            image_links.append(img["640x480"])  # [cite: 1]

    apartment = {
        "id": str(item.get("id")),
        "avito_url": url,  # <--- Пойдет в отдельную колонку
        "text_description": item.get("title"),  # <--- Короткий заголовок
        "price": item.get("price"),
        "rooms": None,
        "total_area": None,
        "floor": None,
        "total_floors": None,
        "deposit": None,
        "renovation": None,
        "label_is_agency": False,
        "label_is_fake": False,
        "label_hidden_fees": False,
        "raw_image_links": image_links,
        "metadata_json": {},
        "Описание": clean_html(item.get("description", "")),
    }

    # 1. Параметры квартиры (Интернет и ТВ и т.д.)
    params_items = buyer.get("paramsDto", {}).get("items", []) or item.get(
        "paramsDto", {}
    ).get("items", [])
    for param in params_items:
        title = param.get("title")
        desc = param.get("description")
        if not title or not desc:
            continue

        if title == "Количество комнат":
            apartment["rooms"] = extract_int(desc)
        elif title == "Общая площадь":
            apartment["total_area"] = extract_number(desc)
        elif title == "Площадь кухни":
            apartment["kitchen_area"] = extract_number(desc)
        elif title == "Жилая площадь":
            apartment["living_area"] = extract_number(desc)
        elif title == "Этаж":
            floors = re.findall(r"\d+", desc)
            apartment["floor"] = int(floors[0]) if len(floors) > 0 else None
            apartment["total_floors"] = int(floors[1]) if len(floors) > 1 else None
        elif title == "Ремонт":
            apartment["renovation"] = desc.replace("\xa0", " ").strip()
        else:
            apartment[title] = desc.replace("\xa0", " ").strip()

    # 2. Условия аренды
    rent_terms = item.get("rentTermsParams", {}).get("data", {}).get("items", [])
    for term in rent_terms:
        title = term.get("title")
        desc = term.get("description")
        if not title or not desc:
            continue

        if title == "Залог":
            apartment["deposit"] = extract_int(desc)
        elif title == "Комиссия":
            apartment["commission_percent"] = extract_number(desc)
        else:
            apartment[title] = desc.replace("\xa0", " ").strip()

    # 3. Правила
    rules_items = item.get("rulesParams", {}).get("data", {}).get("items", [])
    for rule in rules_items:
        title = rule.get("title")
        desc = rule.get("description")
        if title and desc:
            apartment[title] = desc.replace("\xa0", " ").strip()

    # 4. О доме
    house_items = item.get("houseParams", {}).get("data", {}).get("items", [])
    for house_param in house_items:
        title = house_param.get("title")
        desc = house_param.get("description")
        if title and desc:
            apartment[f"Дом: {title}"] = desc.replace("\xa0", " ").strip()

    # ДОБАВИЛИ avito_url В ИЗВЕСТНЫЕ КЛЮЧИ КОЛОНОК БД
    known_keys = [
        "id",
        "avito_url",
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
        "raw_image_links",
    ]

    metadata = {k: v for k, v in apartment.items() if k not in known_keys}

    # Фикс кодировки: кириллица запишется читаемым текстом
    apartment["metadata_json"] = metadata

    return {k: apartment.get(k) for k in known_keys}
