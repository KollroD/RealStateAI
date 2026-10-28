import json

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


DATABASE_URL = "postgresql+asyncpg://admin:password123@localhost:5432/real_estate"


engine = create_async_engine(
    DATABASE_URL, json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False)
)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_session():
    async with async_session_maker() as session:
        yield session
