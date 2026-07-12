async def fetch_apartment_data(client, api_url: str) -> dict:
    print(f"Тянем данные карточки: {api_url}")
    return await client.get_json(api_url)
