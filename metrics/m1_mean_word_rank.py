# -*- coding: utf-8 -*-
"""
МЕТРИКА 1. Средний ранг лексики (mean word rank, MWR).

Идея: чем ниже средний ранг слов текста, тем больше более
частотной лексики языка используется в тексте.


Как считается MWR:
  1) все слова текста приводятся к леммам;
  2) для каждой леммы ищется её ранг в частотном списке
     (и — 1, в — 2, не — 3);
  3) слово, которого нет в списке:
       MWR1 — получает ранг 6000,
       MWR2 — пропускается, исключается из расчета вовсе;
  4) считается среднее арифметическое рангов.

Запуск (из корневой папки проекта translationese_metrics):
    python metrics/m1_mean_word_rank.py                   (учебный пример)
    python metrics/m1_mean_word_rank.py texts/text_1.txt  (свой текст)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.common import (get_lemmas, text_from_command_line_or_file,
                          print_title, DEMO_TEXT)
from data.word_frequencies import words_by_freq

# Ранг для слов, которых нет в частотном списке (только для MWR1)
DEFAULT_RANK = 6000


def calculate_mean_word_rank(lemmas: list) -> tuple:
    """
    :param lemmas: список лемм всех слов текста
    :return: (MWR1, MWR2), округлённые до целого
    """
    total_rank_1 = 0   # сумма рангов для MWR1
    total_rank_2 = 0   # сумма рангов для MWR2
    word_count_1 = 0   # сколько слов учтено в MWR1 (все)
    word_count_2 = 0   # сколько слов учтено в MWR2 (только найденные)

    for word in lemmas:
        rank = words_by_freq.get(word)   # ранг или None, если слова нет
        if rank:
            total_rank_1 += rank
            total_rank_2 += rank
            word_count_2 += 1
        else:
            total_rank_1 += DEFAULT_RANK
        word_count_1 += 1

    if word_count_1 == 0:
        return 0, 0

    mean_word_rank_1: int = round(total_rank_1 / word_count_1)

    mean_word_rank_2: int = (
        round(total_rank_2 / word_count_2)
    ) if word_count_2 else 0

    return mean_word_rank_1, mean_word_rank_2


def mean_word_rank(text: str) -> tuple:
    """То же самое, но на вход подаётся текст, а не список лемм."""
    return calculate_mean_word_rank(get_lemmas(text))


if __name__ == "__main__":
    name, text = text_from_command_line_or_file(DEMO_TEXT)
    print_title(f"МЕТРИКА 1. СРЕДНИЙ РАНГ ЛЕКСИКИ ({name})")

    lemmas = get_lemmas(text)

    found = [(lemma, words_by_freq[lemma]) for lemma in lemmas
             if words_by_freq.get(lemma)]
    not_found = [lemma for lemma in lemmas if not words_by_freq.get(lemma)]

    print("\n  Леммы и их ранги (первые 25 слов текста):")
    for lemma in lemmas[:25]:
        rank = words_by_freq.get(lemma)
        print(f"   {lemma:<20} {rank if rank else 'нет в списке'}")

    print(f"\nВсего слов:             {len(lemmas)}")
    print(f"Найдено в списке:       {len(found)}")
    print(f"Нет в списке:           {len(not_found)}")
    if not_found:
        shown = ", ".join(sorted(set(not_found)))
        print(f"Не найдены:             {shown}")

    sum_found = sum(rank for _, rank in found)
    mwr1, mwr2 = calculate_mean_word_rank(lemmas)
    if lemmas:
        print(f"\nMWR1 = ({sum_found} + {len(not_found)} × {DEFAULT_RANK}) "
              f"/ {len(lemmas)} = {mwr1}")
    if found:
        print(f"MWR2 = {sum_found} / {len(found)} = {mwr2}")
