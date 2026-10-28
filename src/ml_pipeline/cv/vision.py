import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image


class ImageVectorizer:
    def __init__(self):
        # Загружаем ResNet50 (веса скачаются автоматически при первом запуске ~100мб)
        # Используем современный метод загрузки весов
        weights = models.ResNet50_Weights.DEFAULT
        full_model = models.resnet50(weights=weights)

        # Отрезаем последний слой (классификатор), чтобы получить вектор (2048 чисел)
        self.model = torch.nn.Sequential(*(list(full_model.children())[:-1]))

        # Переводим модель в режим оценки (отключаем обучение)
        self.model.eval()

        # Стандартные трансформации для ResNet
        self.preprocess = transforms.Compose(
            [
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
                ),
            ]
        )

    def get_embedding(self, image_path: str) -> list:
        try:
            # Открываем и конвертируем в RGB
            img = Image.open(image_path).convert("RGB")

            # Подготавливаем тензор и добавляем размерность батча (batch dimension)
            img_tensor = self.preprocess(img).unsqueeze(0)

            # Прогоняем без вычисления градиентов (экономит память и ускоряет в разы)
            with torch.no_grad():
                features = self.model(img_tensor)

            # Вытягиваем в плоский массив и переводим в обычный list для базы
            embedding = features.flatten().numpy().tolist()
            return embedding

        except Exception as e:
            print(f"❌ Ошибка векторизации {image_path}: {e}")
            return []


# Тестируем локально
if __name__ == "__main__":
    vectorizer = ImageVectorizer()

    vec = vectorizer.get_embedding("src/scraper/media/apartments/117233/0.webp")
    print(f"Размер вектора: {len(vec)}")
    print(f"Первые 5 чисел эмбеддинга: {vec[:5]}")
