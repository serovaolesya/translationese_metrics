# -*- coding: utf-8 -*-
"""
МЕТРИКА 7. Эксплицитное называние (explicit naming).

ЧТО ИЗМЕРЯЕТ
    Сколько личных и притяжательных местоимений приходится на каждую
    именованную сущность (имя человека, название места или организации).
    Иначе говоря: как часто текст ссылается на участников местоимением
    («он», «её», «наш») и как часто называет их по имени.

КАК СЧИТАЕТСЯ
    Шаг 1. Находим в тексте местоимения.
           Каждое слово приводим к начальной форме (лемме) и проверяем,
           входит ли лемма в список личных и притяжательных местоимений
           (я, ты, он, она, оно, мы, вы, они, мой, твой, наш, ваш, свой, его,
           её, их). Например, «ему» и «им» дают леммы «он» и «они»,
           поэтому считаются.
    Шаг 2. Находим именованные сущности (за это отвечает файл entities.py).
    Шаг 3. Делим число местоимений на число сущностей и умножаем на 100:

               эксплицитное называние = местоимения / сущности × 100

КАК ЧИТАТЬ РЕЗУЛЬТАТ
    Это отношение, а не доля, поэтому значение может быть больше 100:
        100 %  — в среднем одно местоимение на одну сущность;
        300 %  — три местоимения на одну сущность;
         50 %  — одно местоимение на две сущности.
    Чем выше число, тем больше текст опирается на местоимения;
    чем ниже, тем чаще участники названы по имени.

    Если в тексте нет ни одной сущности, делить не на что,
    и функция возвращает 0. Это значит «посчитать нельзя»,
    а не «местоимений нет».

Запуск (из корневой папки проекта translationese_metrics):
    python metrics/m7_explicit_naming.py                   (учебный пример)
    python metrics/m7_explicit_naming.py texts/text_1.txt  (свой текст)
"""
from collections import Counter

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.common import (
    lemmatize_words,
    text_from_command_line_or_file,
    print_title
)
from data.pronouns import pers_possessive_pronouns_analysis_list
from utils.entities import extract_entities, DEMO_TEXT


def find_pronouns(text: str) -> list:
    """
    Находит в тексте личные и притяжательные местоимения.

    :param text: исходный текст

    :return: список пар (слово в тексте, его начальная форма),
    """
    # lemmatize_words разбирает все слова текста. У каждого разбора есть:
    #   .word        — слово, как оно записано в тексте;
    #   .normal_form — его начальная форма (лемма).
    # Оставляем только те слова, чья лемма входит в список местоимений.
    return [
        (parsed.word, parsed.normal_form)
        for parsed in lemmatize_words(text)
        if parsed.normal_form in pers_possessive_pronouns_analysis_list
    ]


def calculate_explicit_naming_ratio(
        pronouns_count: int,
        entities_count: int
) -> float:
    """
    Считает показатель эксплицитного называния.

    :param pronouns_count: сколько в тексте личных и притяжательных
                           местоимений
    :param entities_count: сколько в тексте именованных сущностей

    :return: число местоимений на 100 сущностей (может быть больше 100);
             0, если сущностей нет
    """
    # Делить на ноль нельзя, поэтому без сущностей возвращаем 0.
    if entities_count > 0:
        return round((pronouns_count / entities_count) * 100, 3)
    return 0


def explicit_naming(text: str) -> float:
    """
    Показатель эксплицитного называния для текста целиком:
    находит местоимения, находит сущности и сразу считает отношение.
    """
    return calculate_explicit_naming_ratio(
        len(find_pronouns(text)), len(extract_entities(text))
    )


if __name__ == "__main__":
    name, text = text_from_command_line_or_file(DEMO_TEXT)

    print_title(f"МЕТРИКА 7. ЭКСПЛИЦИТНОЕ НАЗЫВАНИЕ ({name})")
    print("\nФормула: местоимения / именованные сущности × 100")

    # ----- Шаг 1. Местоимения -----
    found_pronouns = find_pronouns(text)
    pronouns_count = len(found_pronouns)

    print("\n" + "-" * 70)
    print("ШАГ 1. ЛИЧНЫЕ И ПРИТЯЖАТЕЛЬНЫЕ МЕСТОИМЕНИЯ")
    print("-" * 70)

    print(f"\nНайдено местоимений: {pronouns_count}")

    if found_pronouns:
        print(f"\n {'Слово в тексте':<20}{'Начальная форма'}")
        for word, lemma in found_pronouns[:30]:
            print(f"   {word:<20}{lemma}")

        if pronouns_count > 30:
            print(f"   ... и ещё {pronouns_count - 30}")

        # Сколько раз встретилась каждая начальная форма
        lemma_counts = Counter(lemma for _, lemma in found_pronouns)

        print("\n Сколько раз встретилось каждое местоимение (по леммам):")
        for lemma, count in lemma_counts.most_common(10):
            print(f"   {lemma:<20}{count}")

    # ----- Шаг 2. Именованные сущности -----
    found_entities = extract_entities(text)
    entities_count = len(found_entities)

    print("\n" + "-" * 70)
    print("ШАГ 2. ИМЕНОВАННЫЕ СУЩНОСТИ")
    print("-" * 70)

    print("Типы: PER — человек, LOC — место, ORG — организация")

    print(f"\nНайдено сущностей: {entities_count}")

    if found_entities:
        print(f"\n   {'Сущность':<40}{'тип'}")
        for entity, entity_type in found_entities[:30]:
            print(f"   {entity:<40}{entity_type}")
        if entities_count > 30:
            print(f"   ... и ещё {entities_count - 30}")
