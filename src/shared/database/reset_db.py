import asyncio
from src.shared.database.database import engine
from src.shared.database.models import Base


async def reset():
    print("Начинаю удаление таблиц...")
    async with engine.begin() as conn:
        # Сносит ВСЕ таблицы, описанные в Base (models.py)
        await conn.run_sync(Base.metadata.drop_all)
        print("Старые таблицы удалены.")

        # Создает новые таблицы с учетом колонки avito_url
        await conn.run_sync(Base.metadata.create_all)
        print("Новые таблицы успешно созданы!")


if __name__ == "__main__":
    asyncio.run(reset())
