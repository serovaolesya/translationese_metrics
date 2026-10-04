# -*- coding: utf-8 -*-
"""
Показывает, как Natasha разбирает предложение: у каждого слова часть речи,
тип синтаксической связи, главное слово и морфологические признаки.
В последнем столбце — что решает функция classify_token из m3_m4_clauses.py.

Запуск (из корневой папки проекта translationese_metrics):
    python utils/parse_sents.py                        (примеры из списка SENTENCES)
    python utils/parse_sents.py "Результаты значимы."  (ваше предложение)

"""
import sys

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from metrics.m3_m4_clauses import parse_sentence, classify_token, FINITE_CLAUSE_RELS

# Предложения для разбора, если ничего не указано при запуске.
SENTENCES = [
    "Авторы утверждают, что перевод упрощает текст.",
    "Авторы утверждают, что результаты значимы.",
    "Результаты значимы.",
    "Здесь представлены понятия, заимствованные из работ авторов.",
    "Результаты были значимыми.",
    "Изучив корпус, мы обнаружили различия, которые подтверждают гипотезу.",
    "Исследователи, использовавшие этот метод, получили другие результаты.",
    "Авторы провели анализ и подготовили отчёт.",
]


def show_parse(sentence: str):
    """Печатает таблицу разбора одного предложения."""
    doc = parse_sentence(sentence)

    # Словарь «идентификатор токена -> его текст», чтобы по head_id
    # узнать, от какого слова зависит данное слово.
    # Идентификатор главного слова корня предложения заканчивается на _0,
    # такого токена нет, поэтому для него печатаем «—».
    text_by_id = {token.id: token.text for token in doc.tokens}

    print(f"\nПредложение: {sentence}")
    print(f"{'слово':<16}{'часть речи':<11}{'связь (rel)':<13}"
          f"{'зависит от':<16}{'форма':<8}{'вариант':<9}итог")
    print("-" * 85)

    for token in doc.tokens:
        feats = token.feats or {}
        head_text = text_by_id.get(token.head_id, "—")
        clause_type = classify_token(token)

        # Помечаем слова, которые функция считает вершинами клауз.
        result = clause_type if clause_type else ""
        if clause_type:
            result = "◀ " + clause_type

        print(f"{token.text:<16}{token.pos:<11}{token.rel:<13}"
              f"{head_text:<16}{feats.get('VerbForm', ''):<8}"
              f"{feats.get('Variant', ''):<9}{result}")


if __name__ == "__main__":
    print(f"Связи, дающие финитную клаузу (FINITE_CLAUSE_RELS): "
          f"{sorted(FINITE_CLAUSE_RELS)}")

    # Если предложение указано после имени скрипта — разбираем его,
    # иначе берём примеры из списка SENTENCES.
    sentences = sys.argv[1:] or SENTENCES
    for sentence in sentences:
        show_parse(sentence)



