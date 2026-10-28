from sqlalchemy import select
from src.shared.database.database import async_session_maker
from src.shared.database.models import ApartmentImage, MLDataset  # Добавили MLDataset
from src.ml_pipeline.cv.vision import ImageVectorizer


class AntiFraudDetector:
    def __init__(self):
        self.vectorizer = ImageVectorizer()

    async def check_image_for_duplicates(
        self,
        image_path: str,
        current_seller_id: str,
        similarity_threshold: float = 0.95,
    ):
        embedding = self.vectorizer.get_embedding(image_path)
        if not embedding:
            return None, None  # Возвращаем два None (нет дубля, нет автора)

        async with async_session_maker() as session:
            distance_expr = ApartmentImage.embedding.cosine_distance(embedding).label(
                "distance"
            )

            # ДЕЛАЕМ JOIN, чтобы достать seller_id оригинальной квартиры избегая N+1
            query = (
                select(ApartmentImage, MLDataset.seller_id, distance_expr)
                .join(MLDataset, ApartmentImage.apartment_id == MLDataset.id)
                .order_by(distance_expr)
                .limit(1)
            )

            result = await session.execute(query)
            row = result.first()

            if row:
                closest_match = row[0]
                original_seller_id = row[1]  # ID автора оригинальной фотки
                distance = row.distance
                similarity = 1.0 - distance

                if similarity >= similarity_threshold:
                    return closest_match.apartment_id, original_seller_id

            return None, None
