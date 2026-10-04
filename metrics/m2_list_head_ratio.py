# -*- coding: utf-8 -*-
"""
МЕТРИКА 2. List head ratio (LHR) — доля наиболее часто встречающихся
знаменательных слов корпуса в тексте.

Суть метрики: какую часть текста покрывает небольшое «ядро» самых частых
слов того корпуса, к которому текст относится.

Эта метрика считается по КОРПУСУ (папке с текстами), в два шага.

Шаг 1 — строим ядро (list head) по всему корпусу:
  1) из каждого текста удаляются стоп-слова, остальные слова
     приводятся к леммам;
  2) считается частота каждой леммы по всему корпусу;
  3) лемма попадает в ядро, если её частота не меньше 0,1 %
     от числа всех словарных токенов корпуса.

Шаг 2 — считаем LHR каждого текста:
  LHR = токены текста, чьи леммы входят в ядро /
        все словарные токены текста × 100

Запуск (из корневой папки проекта translationese_metrics):
    python metrics/m2_list_head_ratio.py              (папка texts)
    python metrics/m2_list_head_ratio.py ваша_папка   (своя папка с файлами .txt)

Обратите внимание: в маленьком корпусе порог 0,1 % проходит почти любая
лемма (в корпусе из 500 токенов достаточно встретиться один раз).
Метрика рассчитана на большие корпусы. Для учебного примера порог
можно поднять: измените COVERAGE_THRESHOLD ниже.
"""
import os
from collections import Counter
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.common import (
    count_word_tokens, lemmatize_words_without_stopwords,
    list_text_files, load_text, folder_from_command_line,
    print_title
)

# Порог в процентах: лемма входит в ядро, если её частота составляет
# не меньше этой доли от всех словарных токенов корпуса.
COVERAGE_THRESHOLD = 0.1


def lemmas_without_stopwords(text: str) -> list:
    """Леммы слов текста после удаления стоп-слов."""
    parsed, _ = lemmatize_words_without_stopwords(text)
    return [token.normal_form for token in parsed]


def calculate_lhr(
        corpus_lemmas: list,
        total_tokens_per_text: list,
        coverage_threshold: float = COVERAGE_THRESHOLD
) -> dict:
    """
    :param corpus_lemmas: список списков лемм после удаления стоп-слов
    :param total_tokens_per_text: число словарных токенов в каждом тексте
    :param coverage_threshold: порог попадания в ядро, в процентах

    :return: Возвращает словарь с частотами, ядром, LHR каждого текста
    и средними значениями LHR.
    """
    # Шаг 1. Частоты лемм по всему корпусу
    all_lemmas = []

    # Создаём общий список лемм всего корпуса.
    # extend() добавляет элементы каждого внутреннего списка.
    # Повторные употребления лемм сохраняются.
    for text_lemmas in corpus_lemmas:
        all_lemmas.extend(text_lemmas)

    # Считаем количество употреблений каждой леммы во всём корпусе.
    # Например: Counter({'язык': 10, 'текст': 7}).
    lemma_counts_in_corpus = Counter(all_lemmas)

    # Размер корпуса в словарных токенах
    total_corpus_tokens = max(1, sum(total_tokens_per_text))

    # Отбираем ядро
    # Создаем список лемм, которые войдут в частотное ядро.
    list_head_lemmas_by_freq = []

    # items() возвращает пары «лемма — частота».
    # Распаковываем каждую пару в переменные lemma и freq.
    for lemma, freq in lemma_counts_in_corpus.items():
        # Вычисляем долю употреблений этой леммы
        # среди всех токенов корпуса, в процентах.
        individual_coverage = (freq / total_corpus_tokens) * 100

        # Если доля не ниже порога, добавляем лемму в ядро.
        if individual_coverage >= coverage_threshold:
            list_head_lemmas_by_freq.append(lemma)

    # Сортируем ядро по убыванию частоты.
    # lambda получает лемму x и возвращает её частоту —
    # именно по этой частоте выполняется сортировка.
    # Список нужен для вывода результатов.
    list_head_lemmas_by_freq.sort(
        key=lambda x: lemma_counts_in_corpus[x], reverse=True
    )

    # Создаём множество лемм ядра для быстрых проверок через in.
    list_head_set = set(list_head_lemmas_by_freq)

    # Шаг 2. LHR каждого текста

    # Создаём список для значений LHR: одно число для каждого текста.
    lhr_values_per_text = []

    # Функция zip() сопоставляет леммы каждого текста
    # с его числом токенов.
    for text_lemmas, n_tokens in zip(
            corpus_lemmas,
            total_tokens_per_text
    ):
        if n_tokens <= 0:
            lhr_values_per_text.append(0.0)
            continue

        # За каждое употребление леммы из ядра прибавляем единицу.
        # Если одна лемма ядра встречается трижды, учитываем все три
        # употребления, а не одну уникальную лемму.
        total_list_head_tokens_in_text = sum(
            1 for lemma in text_lemmas if lemma in list_head_set
        )

        # LHR = употребления лемм ядра / все токены текста × 100.
        # Добавляем результат текущего текста в список.
        lhr_values_per_text.append(
            total_list_head_tokens_in_text / n_tokens * 100
        )

    # Среднее по корпусу: взвешенное (длинные тексты весят больше) и простое

    # Сумма этих весов служит знаменателем взвешенного среднего.
    total_weight_denominator = sum(total_tokens_per_text)

    # Сопоставляем LHR каждого текста с количеством его токенов.
    # Умножаем каждое значение LHR текста на соответствующий вес текста,
    # складываем произведения и делим на вычисленную выше сумму весов.
    mean_weighted = (
        sum(
            lhr_value * text_weight for lhr_value, text_weight
            in zip(lhr_values_per_text, total_tokens_per_text)
            )
        / total_weight_denominator if total_weight_denominator > 0 else 0.0
    )

    # Простое среднее: складываем значения LHR всех текстов
    # и делим на количество текстов. Каждый текст имеет одинаковый вес.
    mean_unweighted = (
            sum(lhr_values_per_text) / len(lhr_values_per_text)
    ) if lhr_values_per_text else 0.0

    return {
        'lemma_counts_in_corpus': lemma_counts_in_corpus,        # Частоты лемм в виде счетчика
        'list_head_lemmas_by_freq': list_head_lemmas_by_freq,    # Слова из ядра по частоте
        'lhr_values_per_text': lhr_values_per_text,              # Показатель LHR каждого текста
        'mean_lhr_weighted': mean_weighted,                      # Взвешенное среднее по корпусу
        'mean_lhr_unweighted': mean_unweighted,                  # Простое среднее по корпусу
        'total_corpus_tokens': total_corpus_tokens,              # Размер корпуса в токенах
        'coverage_threshold': coverage_threshold,                # Заданный порог в процентах
    }


def list_head_ratio(
        texts: list,
        coverage_threshold: float = COVERAGE_THRESHOLD
) -> dict:
    """LHR для списка текстов (каждый текст — строка)."""

    # Для каждого текста удаляем стоп-слова и получаем леммы.
    corpus_lemmas: list[list] = [lemmas_without_stopwords(text)
                                 for text in texts]

    # Считаем все словарные токены каждого исходного текста.
    total_tokens: list[int] = [count_word_tokens(text)
                               for text in texts]

    # Передаём подготовленные данные и порог в функцию расчёта.
    # Возвращаем полученный от неё словарь.
    return calculate_lhr(
        corpus_lemmas,
        total_tokens,
        coverage_threshold
    )


if __name__ == "__main__":
    folder = folder_from_command_line()
    files_paths = list_text_files(folder)
    print_title(f"МЕТРИКА 2. LIST HEAD RATIO (папка: {folder})")
    if not files_paths:
        raise SystemExit("В папке нет файлов .txt")

    texts: list[str] = [load_text(path) for path in files_paths]

    # Рассчитываем LHR и получаем словарь со всеми результатами:
    result: dict = list_head_ratio(texts)

    # Извлекаем общее количество токенов корпуса, включая стоп-слова.
    total = result['total_corpus_tokens']

    # Переводим процентный порог в минимальную частоту леммы.
    # Например: 100 000 токенов × 0,1 / 100 = 100 употреблений.
    min_freq_in_corpus = total * result['coverage_threshold'] / 100

    freq = result['lemma_counts_in_corpus']

    print(f"\nТекстов в корпусе:            {len(texts)}")
    print(f"Словарных токенов в корпусе:  {total}")
    print(f"Порог:                        "
          f"{result['coverage_threshold']} % — лемма должна "
          f"встретиться не менее {min_freq_in_corpus:.2f} раз")
    print(f"Лемм в ядре:                  "
          f"{len(result['list_head_lemmas_by_freq'])}")

    print("\nЯдро (первые 20 лемм):")
    for lemma in result['list_head_lemmas_by_freq'][:20]:
        print(f"   {lemma:<20} частота {freq[lemma]:<5} "
              f"покрытие {freq[lemma] / total * 100:.2f} %")

    print("\nLHR по текстам:")
    for path, value in zip(files_paths, result['lhr_values_per_text']):
        print(f"   {os.path.basename(path):<25} {value:.2f} %")

    print(f"\nСреднее LHR (взвешенное):   {result['mean_lhr_weighted']:.2f} %")
    print(f"Среднее LHR (невзвешенное): "
          f"{result['mean_lhr_unweighted']:.2f} %")
