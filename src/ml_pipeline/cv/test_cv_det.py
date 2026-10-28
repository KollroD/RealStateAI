import os
from src.ml_pipeline.cv.cv_detector import OpenCVFraudDetector


def run_test():
    detector = OpenCVFraudDetector()

    # Список путей к папкам (5 папок с реальными фото + 1 с ИИ)
    folders_to_test = [
        "src/scraper/media/apartments/117233",  # Реальные
        "src/scraper/media/apartments/959390328",
        "src/scraper/media/apartments/1285060035",
        "src/scraper/media/apartments/820694585",
        "src/scraper/media/apartments/1447283151",
        "src/scraper/media/test/1",  # ИИ/Рендеры
    ]

    for folder in folders_to_test:
        print(f"\n📂 ПРОВЕРКА ПАПКИ: {folder}")
        if not os.path.exists(folder):
            print(f"❌ Папка не найдена: {folder}")
            continue

        files = [
            f
            for f in os.listdir(folder)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
        ]

        for file in files:
            file_path = os.path.join(folder, file)
            stats = detector.analyze_image(file_path)

            if stats:
                # Наша логика подозрения
                is_suspicious = detector.is_suspicious_interior(stats)
                status = "🚨 ПОДОЗРИТЕЛЬНО" if is_suspicious else "✅ НОРМА"

                print(
                    f"   📄 {file}: Шум={stats['noise_level']}, "
                    f"Линий={stats['total_lines']} -> {status}"
                )


if __name__ == "__main__":
    run_test()
