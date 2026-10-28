import cv2
import numpy as np
import os


class OpenCVFraudDetector:
    def __init__(self):
        pass

    def is_suspicious_interior(self, stats):
        noise = stats["noise_level"]
        lines = stats["total_lines"]
        ratio = stats["perfect_lines_ratio"]

        # 1. Если линий много (> 500), и при этом аномально много идеальных
        # (ratio > 5.0)
        if lines > 500 and ratio > 5.0:
            return True

        # 2. Если линий очень много (> 2000), это почти всегда ИИ/рендер
        if lines > 2000:
            return True

        if noise > 1500:
            return False

        # 3. Высокий шум (> 400) + линии — это типичный шум генерации
        if lines > 500 and noise > 400:
            return True

        return False

    def analyze_image(self, image_path: str):
        if not os.path.exists(image_path):
            print(f"❌ Файл не найден: {image_path}")
            return None

        # OpenCV по умолчанию не умеет читать кириллицу в путях,
        # поэтому читаем через numpy
        stream = open(image_path, "rb")
        bytes = bytearray(stream.read())
        numpyarray = np.asarray(bytes, dtype=np.uint8)
        img = cv2.imdecode(numpyarray, cv2.IMREAD_COLOR)

        if img is None:
            print(f"❌ Ошибка чтения: {image_path}")
            return None

        # Переводим в ЧБ для анализа структуры
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # --- 1. АНАЛИЗ ШУМА (Laplacian Variance) ---
        # Вычисляем дисперсию Лапласиана.
        # Низкое значение = мыльная/сгенерированная картинка без деталей.
        # Высокое = много мелкой текстуры, зерна, реальных деталей.
        noise_level = cv2.Laplacian(gray, cv2.CV_64F).var()

        # --- 2. ПОИСК ИДЕАЛЬНО ПРЯМЫХ ЛИНИЙ (Hough Transform) ---
        # Находим границы объектов
        edges = cv2.Canny(gray, threshold1=50, threshold2=150, apertureSize=3)

        # Ищем длинные прямые линии
        lines = cv2.HoughLines(edges, rho=1, theta=np.pi / 180, threshold=200)

        perfect_lines_count = 0
        total_lines = 0

        if lines is not None:
            total_lines = len(lines)
            for line in lines:
                rho, theta = line[0]
                angle_degrees = theta * (180.0 / np.pi)

                # Ищем строго вертикальные (0, 180) или строго горизонтальные (90) линии
                # Даем погрешность всего в 0.5 градуса
                if (
                    (0 <= angle_degrees <= 0.5)
                    or (179.5 <= angle_degrees <= 180.0)
                    or (89.5 <= angle_degrees <= 90.5)
                ):
                    perfect_lines_count += 1

        # Считаем процент "математически идеальных" линий от всех найденных
        perfect_lines_ratio = (
            (perfect_lines_count / total_lines) * 100 if total_lines > 0 else 0
        )

        return {
            "noise_level": round(noise_level, 2),
            "total_lines": total_lines,
            "perfect_lines_ratio": round(perfect_lines_ratio, 2),
        }
