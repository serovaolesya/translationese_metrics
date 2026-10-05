# -*- coding: utf-8 -*-
"""
ВСЕ ВОСЕМЬ МЕТРИК СРАЗУ для папки с текстами.

Для каждого файла .txt считаются метрики 1–5, 7, 8,
для всей папки (корпуса) — PMI,
печатается таблица и сохраняется в файл results_texts.csv (открывается в Excel).

Запуск (из корневой папки проекта translationese_metrics):
    python run_all.py                    (папка texts)
    python run_all.py моя_папка          (своя папка)
    python run_all.py папка_1 папка_2 (две папки — два корпуса подряд)

Чтобы сравнить переводные и непереводные тексты, положите их
в две разные папки и укажите обе.
"""

import csv
import os
import sys

from utils.common import (
    count_word_tokens, count_content_words, get_lemmas,
    list_text_files, load_text, split_into_sentences,
    DEFAULT_FOLDER, print_title
)
from metrics.m1_mean_word_rank import calculate_mean_word_rank
from metrics.m2_list_head_ratio import calculate_lhr, lemmas_without_stopwords
from metrics.m3_m4_clauses import analyze_clause_structure
from metrics.m5_repetition import calculate_repetition
from metrics.m6_pmi import PMICalculator
from metrics.m7_explicit_naming import find_pronouns, calculate_explicit_naming_ratio
from metrics.m8_single_naming import single_naming_frequency
from utils.entities import extract_entities

COLUMNS = [
    ("file", "Файл"),
    ("tokens", "Токены"),
    ("mwr1", "MWR1"),
    ("mwr2", "MWR2"),
    ("lhr", "LHR, %"),
    ("clause_length", "Длина клаузы"),
    ("clauses_per_sent", "Клауз на предл."),
    ("repetition", "Повтор., %"),
    ("explicit_naming", "Экспл. наз., %"),
    ("single_naming", "Един. имен., %"),
]


def analyze_folder(folder: str) -> tuple:
    """Считает все метрики для папки. Возвращает (строки таблицы, PMI)."""
    files: list = list_text_files(folder)

    if not files:
        raise SystemExit(f'В папке {folder} нет файлов .txt')

    preprocessed_texts: list[str] = [load_text(path) for path in files]
    rows = []

    for path, text in zip(files, preprocessed_texts):
        print(f"   обрабатывается {os.path.basename(path)} ...")

        word_tokens_num = count_word_tokens(text)
        mwr1, mwr2 = calculate_mean_word_rank(get_lemmas(text))
        clauses = analyze_clause_structure(split_into_sentences(text))
        repetition, _ = calculate_repetition(
            word_tokens_num, count_content_words(text))
        entities = extract_entities(text)
        explicit = calculate_explicit_naming_ratio(
            len(find_pronouns(text)), len(entities))
        single = single_naming_frequency(entities)

        rows.append({
            "file": os.path.basename(path),
            "tokens": word_tokens_num,
            "mwr1": mwr1,
            "mwr2": mwr2,
            "lhr": None,  # заполняется ниже: нужна вся папка
            "clause_length": round(clauses["avg_tokens_per_clause"], 2),
            "clauses_per_sent": round(clauses["avg_clauses_per_sent"], 2),
            "repetition": repetition,
            "explicit_naming": explicit,
            "single_naming": single,
        })

    # LHR: ядро строится по всей папке
    lhr: dict = calculate_lhr(
        [lemmas_without_stopwords(text) for text in preprocessed_texts],
        [row["tokens"] for row in rows],
    )
    for row, value in zip(rows, lhr["lhr_values_per_text"]):
        row["lhr"] = round(value, 2)

    # PMI: считается по всей папке, при окне 1 и окне 5
    pmi_summary = []
    for window in (1, 5):
        calc = PMICalculator(window_size=window).fit(preprocessed_texts)
        pairs = calc.compute_scores()
        pmi_summary.append({
            "window": window,
            "avg_pmi": PMICalculator.average(pairs, "PMI"),
            "share_pmi": PMICalculator.threshold_share(pairs, "PMI"),
            "avg_mod": PMICalculator.average(pairs, "Mod. MI"),
            "share_mod": PMICalculator.threshold_share(pairs, "Mod. MI"),
        })
    return rows, pmi_summary


def print_table(rows: list):
    widths = [max(len(title), 16) if key == "file" else len(title) + 2
              for key, title in COLUMNS]
    widths[0] = max(widths[0], max(len(r["file"]) for r in rows) + 2)
    print("".join(f"{title:<{w}}" if key == "file" else f"{title:>{w}}"
                  for (key, title), w in zip(COLUMNS, widths)))
    for row in rows:
        print("".join(
            f"{row[key]:<{w}}" if key == "file" else f"{row[key]:>{w}}"
            for (key, _), w in zip(COLUMNS, widths)))


def print_pmi_summary(pmi_summary: list):
    """
    Печатает итог по PMI таблицей: показатели в строках, окна в столбцах.
    """
    # (подпись строки, ключ в словаре, это доля?)
    lines = [
        ("Среднее PMI", "avg_pmi", False),
        ("Доля пар с PMI > 0", "share_pmi", True),
        ("Среднее Modified PMI", "avg_mod", False),
        ("Доля пар с Modified PMI > 0", "share_mod", True),
    ]
    label_width = max(len(label) for label, _, _ in lines) + 2
    col_width = 11

    header = "".join(f"{'окно ' + str(item['window']):>{col_width}}"
                     for item in pmi_summary)
    print(f"   {'':<{label_width}}{header}")
    print("   " + "-" * (label_width + col_width * len(pmi_summary)))
    for label, key, is_share in lines:
        cells = "".join(
            f"{item[key] * 100:.2f} %".rjust(col_width) if is_share
            else f"{item[key]:.2f}".rjust(col_width)
            for item in pmi_summary)
        print(f"   {label:<{label_width}}{cells}")


def save_csv(rows: list, folder: str) -> str:
    name = os.path.basename(os.path.normpath(folder))
    path = f"results_{name}.csv"
    # utf-8-sig и точка с запятой — чтобы файл сразу открывался в Excel
    with open(path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow([title for _, title in COLUMNS])
        for row in rows:
            writer.writerow([str(row[key]).replace(".", ",")
                             if key != "file" else row[key]
                             for key, _ in COLUMNS])
    return path


if __name__ == "__main__":
    folders = sys.argv[1:] or [DEFAULT_FOLDER]

    for folder in folders:
        print_title(f"ВСЕ МЕТРИКИ (папка: {folder})")
        rows, pmi_summary = analyze_folder(folder)

        print("\nМЕТРИКИ ПО ТЕКСТАМ")
        print_table(rows)

        print("\nPMI ПО ВСЕЙ ПАПКЕ (минимальная совместная встречаемость 1)")
        print_pmi_summary(pmi_summary)

        print(f"\nТаблица сохранена в файл {save_csv(rows, folder)}")
