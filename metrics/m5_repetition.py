# -*- coding: utf-8 -*-
"""
МЕТРИКА 5. Повторяемость знаменательной лексики (lexical repetition).

Что измеряет:
    Число разных знаменательных лемм, встретившихся минимум
    дважды, в расчёте на 100 словарных токенов текста.


Как считается:
    1) count_content_words() получает частоты знаменательных лемм;
    2) выбираются леммы с частотой не меньше двух;
    3) считается число таких разных лемм;
    4) это число делится на число всех словарных токенов текста;
    5) результат умножается на 100 и округляется до трёх знаков.

Каждая повторяющаяся лемма учитывается в числителе один раз,
независимо от того, встретилась она два раза или двадцать.

Запуск (из корневой папки проекта translationese_metrics):
    python metrics/m5_repetition.py                   (учебный пример)
    python metrics/m5_repetition.py texts/text_1.txt  (свой текст)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.common import (
    count_word_tokens,
    count_content_words,
    text_from_command_line_or_file,
    print_title,
)


def calculate_repetition(
        total_tokens_count: int,
        content_word_counts: dict
) -> tuple:
    """
    Рассчитывает показатель по готовым счётчикам.

    :param total_tokens_count: число словарных токенов в тексте
    :param content_word_counts: счетчик - {знаменательная лемма: частота}

    :return: (повторяемость в %, число лемм с частотой ≥ 2)
    """
    # За каждую лемму с частотой 2 и больше прибавляем единицу
    repeated_types_count = sum(
        1 for count in content_word_counts.values() if count >= 2
    )
    if total_tokens_count > 0:
        repetition = round(
            repeated_types_count / total_tokens_count * 100, 3
        )
        return repetition, repeated_types_count
    return 0, 0


def repetition(text: str) -> float:
    """Повторяемость для текста (в процентах)."""
    # Считаем все словарные токены текста.
    total_tokens_count = count_word_tokens(text)

    # Получаем частоты знаменательных лемм.
    content_lemma_frequencies = count_content_words(text)

    # Функция возвращает два значения.
    # Второе здесь не требуется, поэтому записываем его в _.
    lexical_repetition_percent, _ = calculate_repetition(
        total_tokens_count,
        content_lemma_frequencies,
    )

    return lexical_repetition_percent


DEMO_TEXT = """
В.С. Садовников – автор многочисленных акварельных видов Петербурга времен Пушкина, Гоголя, Достоевского. Поэтическое восприятие города художник всегда сочетал с документальной точностью в изображениях архитектурных памятников. При этом он передавал впечатление живой жизни города, рисуя гуляющих людей разных сословий, мчащиеся по улице кареты. Акварели художника пользовались успехом, и, несмотря на свое положение крепостного, уже в 1820-е годы Садовников был хорошо известен. В 1838 году, после смерти своей владелицы княгини Н.П. Голицыной, послужившей прообразом старой графини в романе А.С. Пушкина, он получил вольную, и в том же году – звание свободного художника.
В течение всей жизни акварелист исполнял многочисленные заказы императорского двора. Он создавал разные виды Санкт-Петербурга по случаю коронации, бракосочетаний, рождения наследников, выездов и парадов. К ним относится и акварель с видом Мариинского дворца. Дворец был свадебным подарком по случаю бракосочетания дочери Николая I Марии Николаевны с герцогом Максимилианом Лейхтенбергским. Проект и строительство дворца император поручил любимому архитектору А.А. Штакеншнейдеру. Великолепное здание было построено в 1839–1844 годах и считается его лучшим творением.
"""

if __name__ == "__main__":
    name, text = text_from_command_line_or_file(DEMO_TEXT)

    print_title(f"МЕТРИКА 5. ПОВТОРЯЕМОСТЬ ЗНАМЕНАТЕЛЬНОЙ ЛЕКСИКИ ({name})")

    # Подготавливаем данные для расчёта.
    total_tokens_count = count_word_tokens(text)
    content_lemma_frequencies = count_content_words(text)

    # Получаем показатель и число разных повторяющихся лемм.
    lexical_repetition_percent, repeated_lemma_count = (
        calculate_repetition(
            total_tokens_count,
            content_lemma_frequencies,
        )
    )

    # Собираем пары (лемма, частота) только для лемм,
    # встретившихся не меньше двух раз.
    repeated_lemmas_with_frequencies = [
        (lemma, lemma_frequency)
        for lemma, lemma_frequency in content_lemma_frequencies.items()
        if lemma_frequency >= 2
    ]

    print("\nЗнаменательные леммы с частотой 2 и больше:")

    # Показываем максимум первые 40 пар.
    # :<20 выравнивает леммы слева в поле шириной 20 символов.
    for lemma, lemma_frequency in repeated_lemmas_with_frequencies[:40]:
        print(f"   {lemma:<20} {lemma_frequency}")

    # Если пар больше 40, сообщаем, сколько осталось за пределами вывода.
    if len(repeated_lemmas_with_frequencies) > 40:
        remaining_lemma_count = (
                len(repeated_lemmas_with_frequencies) - 40
        )
        print(f"   ... и ещё {remaining_lemma_count}")

    # len(словарь) — число его ключей, то есть разных лемм.
    print(
        f"\nРазных знаменательных лемм:   "
        f"{len(content_lemma_frequencies)}"
    )
    print(
        f"Из них с частотой ≥ 2:        "
        f"{repeated_lemma_count}"
    )
    print(
        f"Словарных токенов в тексте:   "
        f"{total_tokens_count}"
    )

    # Показываем формулу только для непустого текста.
    # Здесь деление не выполняется: печатаются готовые значения.
    if total_tokens_count > 0:
        print(
            f"\nПовторяемость = {repeated_lemma_count} / "
            f"{total_tokens_count} × 100 = "
            f"{lexical_repetition_percent} %"
        )
