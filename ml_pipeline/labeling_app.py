"""Модуль автоматической разметки объявлений о недвижимости.

Классифицирует авторов объявлений на 3 класса:
    0 - Собственник (Owner)
    1 - Риелтор / Агентство (Realtor)
    2 - Робот / LLM (Generated)
"""

import argparse
import re
from typing import Optional, Tuple
import pandas as pd


# Словарь подмены визуально похожих латинских букв на кириллические
# Используется агентствами для обхода спам-фильтров и стоп-слов
LOOKALIKE_MAPPING = {
    "A": "А",
    "a": "а",
    "B": "В",
    "E": "Е",
    "e": "е",
    "K": "К",
    "k": "к",
    "M": "М",
    "H": "Н",
    "O": "О",
    "o": "о",
    "P": "Р",
    "p": "р",
    "C": "С",
    "c": "с",
    "T": "Т",
    "X": "Х",
    "x": "х",
    "y": "у",
}

EMOJI_PATTERN = re.compile(
    r"[\U0001F300-\U0001F64F\U0001F680-\U0001F6FF\U0001F900-\U0001F9FF\u2600-\u26FF\u2700-\u27BF]"
)

LLM_PHRASES = [
    "идеальный выбор",
    "в самом сердце",
    "потрясающий",
    "не упустите шанс",
    "ваш идеальный дом",
    "клубная атмосфера",
    "дизайнерский ремонт",
    "продуманное пространство",
]

REALTOR_PATTERNS = [
    r"комисси",
    r"агент",
    r"риэлтор",
    r"арт\.",
    r"номер объекта",
    r"мы являемся партнерами",
    r"деятельность агентства застрахована",
    r"оформление ипотеки",
    r"залог",
]

OWNER_PATTERNS = [
    r"от собственника",
    r"я собственник",
    r"без комиссии",
    r"риелторам не беспокоить",
    r"агентам не звонить",
    r"сдаю свою",
    r"без посредников",
]


def normalize_text(text: str) -> str:
    """Нормализует текст: заменяет латинские омоглифы на кириллицу и приводит к нижнему регистру."""
    if not isinstance(text, str):
        return ""
    for lat, cyr in LOOKALIKE_MAPPING.items():
        text = text.replace(lat, cyr)
    return text.lower()


def evaluate_listing(
    commission: float,
    description: str,
    seller_offers_count: Optional[int] = 1,
) -> Tuple[int, str, str]:
    """Оценивает объявление и возвращает (target_id, target_name, reason).

    Args:
        commission: Размер комиссии в процентах или рублях.
        description: Исходный текст описания объявления.
        seller_offers_count: Число активных предложений у автора объявления.

    Returns:
        tuple (target, label_name, reason):
            target: 0 (Собственник), 1 (Риелтор), 2 (Робот/LLM)
    """
    raw_text = str(description) if description is not None else ""
    text_lower = normalize_text(raw_text)

    # 1. Проверка на признаки LLM / робота
    emoji_count = len(EMOJI_PATTERN.findall(raw_text))
    bullet_points = len(re.findall(r"(\n- |\n\* |✅|✨|•|—)", raw_text))
    has_llm_phrases = any(p in text_lower for p in LLM_PHRASES)

    if emoji_count > 5 or (bullet_points > 5 and len(raw_text) > 250) or (has_llm_phrases and bullet_points >= 3):
        return (
            2,
            "Робот (LLM)",
            "Множество эмодзи, списки с буллетами или рекламные клише LLM.",
        )

    # 2. Проверка комиссии: ненулевая комиссия - 100% Риелтор
    try:
        comm_val = float(commission) if pd.notna(commission) else 0.0
    except (ValueError, TypeError):
        comm_val = 0.0

    if comm_val > 0:
        return 1, "Риелтор", f"Указана комиссия агентства ({comm_val}%), это 100% риелтор."

    # 3. Большое число предложений у продавца
    try:
        offers = int(seller_offers_count) if pd.notna(seller_offers_count) else 1
    except (ValueError, TypeError):
        offers = 1

    if offers > 3:
        return 1, "Риелтор", f"У продавца более {offers} активных объявлений (профессиональный аккаунт)."

    # 4. Текстовые маркеры риелтора (включая скрытую латиницу)
    if any(re.search(p, text_lower) for p in REALTOR_PATTERNS):
        return (
            1,
            "Риелтор",
            "Присутствуют текстовые маркеры агентства (номер объекта, арт., ипотека, залог и т.д.).",
        )

    # 5. Текстовые маркеры собственника
    if any(re.search(p, text_lower) for p in OWNER_PATTERNS):
        return (
            0,
            "Собственник",
            "Явно указано 'от собственника', 'без комиссии' или просьба не беспокоить агентов.",
        )

    # 6. Fallback к собственнику при отсутствии признаков агента
    return (
        0,
        "Собственник",
        "Простое бытовое описание без маркеров агентства при нулевой комиссии.",
    )


def label_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Размечает датафрейм объявлений и формирует аудит-лог разметки.

    Ожидает колонки: 'real_description' (или 'description'), 'commission',
    опционально 'seller_offers_count'.
    """
    df = df.copy()

    desc_col = "real_description" if "real_description" in df.columns else "description"
    comm_col = "commission" if "commission" in df.columns else None
    offers_col = "seller_offers_count" if "seller_offers_count" in df.columns else None

    targets = []
    labels = []
    reasons = []

    for _, row in df.iterrows():
        desc = row.get(desc_col, "")
        comm = row.get(comm_col, 0.0) if comm_col else 0.0
        offers = row.get(offers_col, 1) if offers_col else 1

        target, label, reason = evaluate_listing(comm, desc, offers)
        targets.append(target)
        labels.append(label)
        reasons.append(reason)

    df["target"] = targets

    audit_df = pd.DataFrame(
        {
            "row_index": range(2, len(df) + 2),
            "target": targets,
            "target_name": labels,
            "reason": reasons,
        }
    )

    return df, audit_df


def main():
    parser = argparse.ArgumentParser(description="Автоматическая разметка объявлений недвижимости")
    parser.add_argument("--input", "-i", default="data/for_model.csv", help="Путь к исходному CSV файлу")
    parser.add_argument("--output", "-o", default="data/target_dataset.csv", help="Путь для сохранения размеченного CSV")
    parser.add_argument("--audit-log", "-a", default="data/manual_evaluations.csv", help="Путь для сохранения журнала обоснований")

    args = parser.parse_args()

    print(f"Загрузка данных из: {args.input}...")
    df = pd.read_csv(args.input)

    print("Применение правил классификации...")
    labeled_df, audit_df = label_dataframe(df)

    print("\n--- Распределение классов ---")
    print(labeled_df["target"].value_counts().rename({0: "0 (Собственник)", 1: "1 (Риелтор)", 2: "2 (Робот/LLM)"}))

    print(f"\nСохранение размеченного датасета в {args.output}...")
    labeled_df.to_csv(args.output, index=False)

    if args.audit_log:
        print(f"Сохранение журнала разметки в {args.audit_log}...")
        audit_df.to_csv(args.audit_log, index=False)

    print("Разметка успешно завершена!")


if __name__ == "__main__":
    main()
