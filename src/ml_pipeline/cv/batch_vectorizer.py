from sqlalchemy import select
from src.shared.database.database import async_session_maker
from src.shared.database.models import ApartmentImage
from src.ml_pipeline.cv.vision import ImageVectorizer


class AntiFraudDetector:
    def __init__(self):
        self.vectorizer = ImageVectorizer()

    async def check_image_for_duplicates(
        self, image_path: str, similarity_threshold: float = 0.95
    ):
        """
        Проверяет одну картинку на дубликаты в базе.
        Возвращает ID оригинальной квартиры, если найден дубль, иначе None.
        """
        # 1. Делаем вектор из новой фотки с помощью ImageVectorizer
        embedding = self.vectorizer.get_embedding(image_path)

        # Если векторизатор вернул пустой список из-за ошибки (как прописано в твоем
        # блоке except)
        if not embedding:
            return None

        # 2. Ищем похожие векторы в базе
        async with async_session_maker() as session:
            # Высчитываем дистанцию и выносим ее как отдельное поле 'distance'
            distance_expr = ApartmentImage.embedding.cosine_distance(embedding).label(
                "distance"
            )

            query = (
                select(ApartmentImage, distance_expr)
                .order_by(distance_expr)
                .limit(1)  # Берем только самое близкое совпадение
            )

            result = await session.execute(query)
            row = result.first()

            if row:
                closest_match = row[0]
                distance = row.distance

                # В pgvector cosine_distance возвращает от 0 (идентичны) до 2
                # (противоположны)
                # Переводим дистанцию в процент сходства
                similarity = 1.0 - distance

                # Если сходство превышает наш порог (например, 0.95)
                if similarity >= similarity_threshold:
                    print(
                        f"🚨 Найден дубликат! Сходство: {similarity:.2f}. "
                        f"Оригинал: {closest_match.apartment_id}"
                    )
                    return closest_match.apartment_id

            return None
