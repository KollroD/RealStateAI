"""Модуль обучения модели классификации объявлений о недвижимости.

Использует:
  1. Эмбеддинги RuBERT-tiny2 (312 признаков)
  2. Статистические и структурные признаки текста (длина, капс, эмодзи, списки)
  3. Числовые признаки объявления (цена, залог, комиссия)
  4. Градиентный бустинг CatBoostClassifier с подбором оптимального порога для редкого класса LLM.
"""

import argparse
import json
import os
import re
from typing import Dict, List, Tuple
from catboost import CatBoostClassifier
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import train_test_split
import torch
from transformers import AutoModel, AutoTokenizer


MODEL_NAME = "cointegrated/rubert-tiny2"


def get_device() -> torch.device:
    """Определяет оптимальное доступное устройство (MPS для macOS, CUDA или CPU)."""
    if torch.backends.mps.is_available():
        return torch.device("mps")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def extract_embeddings(
    texts: np.ndarray,
    tokenizer: AutoTokenizer,
    model: AutoModel,
    device: torch.device,
    batch_size: int = 64,
) -> np.ndarray:
    """Извлекает нормализованные эмбеддинги CLS-токенов модели RuBERT-tiny2."""
    model.eval()
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i : i + batch_size].astype(str).tolist()
        encoded = tokenizer(
            batch_texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        )
        encoded = {k: v.to(device) for k, v in encoded.items()}

        with torch.no_grad():
            model_output = model(**encoded)
            # CLS-токен (позиция 0) обобщает смысл всего предложения
            cls_emb = model_output.last_hidden_state[:, 0, :]
            norm_emb = torch.nn.functional.normalize(cls_emb)
            all_embeddings.append(norm_emb.cpu().numpy())

    return np.vstack(all_embeddings)


def extract_advanced_text_features(df_src: pd.DataFrame, text_col: str = "real_description") -> pd.DataFrame:
    """Вычисляет статистические и стилистические признаки текста для детекции LLM и риелторов."""
    feats = pd.DataFrame(index=df_src.index)
    text_s = df_src[text_col].fillna("").astype(str)

    # Длина текста и слов
    feats["char_len"] = text_s.apply(len)
    feats["word_count"] = text_s.apply(lambda x: len(x.split()))
    feats["avg_word_len"] = feats["char_len"] / (feats["word_count"] + 1e-5)

    # Пунктуация и списки (типичные маркеры ИИ)
    feats["exclamation_mark_count"] = text_s.apply(lambda x: x.count("!"))
    feats["bullet_count"] = text_s.apply(lambda x: len(re.findall(r"[\bullet\-\*\d+\.]", x)))
    feats["has_emoji"] = text_s.apply(lambda x: int(bool(re.search(r"[\U00010000-\U0010ffff]", x))))

    # Капс, структура абзацев и цифры
    feats["caps_ratio"] = text_s.apply(lambda x: sum(1 for c in x if c.isupper()) / (len(x) + 1e-5))
    feats["paragraph_count"] = text_s.apply(lambda x: x.count("\n") + 1)
    feats["digits_count"] = text_s.apply(lambda x: sum(1 for c in x if c.isdigit()))

    return feats


def tune_llm_threshold(
    probabilities: np.ndarray,
    y_true: pd.Series,
    threshold_range: np.ndarray = np.arange(0.15, 0.50, 0.05),
) -> Tuple[float, float]:
    """Подбирает оптимальный порог вероятности для класса 2 (LLM), максимизирующий F1-меру."""
    best_threshold = 0.33
    best_llm_f1 = 0.0

    print("\n--- Поиск оптимального порога вероятности для LLM (класс 2) ---")
    for threshold in threshold_range:
        custom_preds = []
        for proba in probabilities:
            p_owner, p_realtor, p_llm = proba
            if p_llm >= threshold:
                custom_preds.append(2)
            else:
                custom_preds.append(0 if p_owner >= p_realtor else 1)

        f1_scores = f1_score(y_true, custom_preds, average=None, zero_division=0)
        current_f1 = f1_scores[2] if len(f1_scores) > 2 else 0.0
        print(f"Порог P(LLM) >= {threshold:.2f} | F1-Score (LLM): {current_f1:.4f}")

        if current_f1 > best_llm_f1:
            best_llm_f1 = current_f1
            best_threshold = float(threshold)

    print(f"Выбран лучший порог: {best_threshold:.2f} (F1: {best_llm_f1:.4f})")
    return best_threshold, best_llm_f1


def train_pipeline(
    data_path: str,
    output_dir: str = "models",
    iterations: int = 700,
    learning_rate: float = 0.05,
    depth: int = 6,
) -> None:
    """Полный цикл обучения: извлечение фичей -> обучение CatBoost -> подбор порога -> сохранение."""
    os.makedirs(output_dir, exist_ok=True)

    print(f"1. Загрузка данных из: {data_path}...")
    df = pd.read_csv(data_path)

    text_col = "real_description" if "real_description" in df.columns else "description"
    if text_col not in df.columns:
        raise ValueError(f"Колонка текста '{text_col}' не найдена в датасете!")

    # 2. Извлечение эмбеддингов
    device = get_device()
    print(f"2. Инициализация трансформера {MODEL_NAME} на устройстве: {device}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    transformer = AutoModel.from_pretrained(MODEL_NAME).to(device)

    print("Извлечение эмбеддингов RuBERT...")
    raw_texts = df[text_col].fillna("").values
    embeddings = extract_embeddings(raw_texts, tokenizer, transformer, device)
    emb_cols = [f"emb_{i}" for i in range(embeddings.shape[1])]
    df_embeddings = pd.DataFrame(embeddings, columns=emb_cols, index=df.index)

    # 3. Извлечение текстовых признаков
    print("3. Расчет структурных и статистических признаков текста...")
    df_text_feats = extract_advanced_text_features(df, text_col=text_col)

    # 4. Числовые признаки
    numeric_features = ["price", "deposit", "commission"]
    for col in numeric_features:
        if col not in df.columns:
            df[col] = 0.0
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df_num = df[numeric_features]

    # Сборка финальной матрицы признаков
    X = pd.concat([df_num, df_text_feats, df_embeddings], axis=1)
    y = df["target"].astype(int)

    print(f"Размерность матрицы признаков X: {X.shape}, целевой вектор y: {y.shape}")

    # 5. Разделение выборки
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train выборка: {X_train.shape[0]} строк | Test выборка: {X_test.shape[0]} строк")

    # 6. Обучение CatBoost с кастомными весами классов
    print(f"4. Обучение CatBoost (iterations={iterations}, lr={learning_rate}, depth={depth})...")
    # Увеличиваем штраф за ошибки на редком классе LLM (класс 2)
    class_weights = [1.0, 1.0, 4.5]

    model = CatBoostClassifier(
        iterations=iterations,
        learning_rate=learning_rate,
        depth=depth,
        class_weights=class_weights,
        random_seed=42,
        verbose=100,
    )
    model.fit(X_train, y_train)

    # 7. Подбор порога вероятностей для класса LLM
    probabilities = model.predict_proba(X_test)
    best_threshold, best_f1 = tune_llm_threshold(probabilities, y_test)

    # 8. Финальная оценка с подобранным порогом
    final_preds = []
    for proba in probabilities:
        p_owner, p_realtor, p_llm = proba
        if p_llm >= best_threshold:
            final_preds.append(2)
        else:
            final_preds.append(0 if p_owner >= p_realtor else 1)

    print("\n--- Финальный отчет по качеству модели (Test выборка) ---")
    target_names = ["Собственник (0)", "Риелтор (1)", "LLM (2)"]
    print(classification_report(y_test, final_preds, target_names=target_names))

    # Топ-10 признаков
    feature_importances = pd.Series(model.get_feature_importance(), index=X.columns).sort_values(ascending=False)
    print("\n--- ТОП-10 ключевых признаков модели ---")
    print(feature_importances.head(10))

    # 9. Сохранение артефактов
    model_save_path = os.path.join(output_dir, "catboost_classifier.cbm")
    config_save_path = os.path.join(output_dir, "model_config.json")

    print(f"\n5. Сохранение модели CatBoost в: {model_save_path}...")
    model.save_model(model_save_path)

    config_data = {
        "transformer_model": MODEL_NAME,
        "llm_probability_threshold": best_threshold,
        "class_mapping": {
            0: "Собственник",
            1: "Риелтор",
            2: "Робот (LLM)",
        },
        "numeric_features": numeric_features,
        "text_feature_names": list(df_text_feats.columns),
        "embedding_dimensions": embeddings.shape[1],
        "catboost_params": {
            "iterations": iterations,
            "learning_rate": learning_rate,
            "depth": depth,
            "class_weights": class_weights,
        },
    }

    with open(config_save_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)

    print(f"Конфигурация модели сохранена в: {config_save_path}")
    print("Пайплайн обучения успешно завершен!")


def main():
    parser = argparse.ArgumentParser(description="Обучение модели классификации авторов объявлений")
    parser.add_argument("--data", "-d", default="data/target_dataset.csv", help="Путь к размеченному датасету CSV")
    parser.add_argument("--output-dir", "-o", default="models", help="Директория для сохранения модели и конфигов")
    parser.add_argument("--iterations", type=int, default=700, help="Число итераций CatBoost")
    parser.add_argument("--lr", type=float, default=0.05, help="Learning rate")
    parser.add_argument("--depth", type=int, default=6, help="Глубина деревьев CatBoost")

    args = parser.parse_args()
    train_pipeline(
        data_path=args.data,
        output_dir=args.output_dir,
        iterations=args.iterations,
        learning_rate=args.lr,
        depth=args.depth,
    )


if __name__ == "__main__":
    main()
