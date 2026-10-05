# -*- coding: utf-8 -*-
"""
МЕТРИКА 6. Поточечная взаимная информация (PMI) и Modified PMI
биграмм слов по всему корпусу.

ЧТО ИЗМЕРЯЕТ
    Насколько сильно два слова «тянутся» друг к другу: насколько чаще они
    стоят рядом, чем стояли бы, если бы их появления в тексте
    были бы независимы друг от друга

    Высокое значение — устойчивое сочетание («социальное неравенство»),
    низкое — случайное («организация означает»).

    Метрика считается по КОРПУСУ (папке с текстами), а не по одному тексту.

КАК СЧИТАЕТСЯ
    1) Тексты делятся на предложения, слова приводятся к леммам; знаки
       препинания и числа убираются, служебные слова остаются.
    2) Считаются:
         N        — число всех токенов корпуса;
         f(x)     — сколько раз встретилась лемма x;
         f(x, y)  — сколько раз y стояло справа от x не дальше, чем на
                    w позиций (w — размер окна). Окно не выходит за конец
                    предложения;
         v        — среднее число соседей, реально учтённых для одного
                    токена (объяснение ниже).
    3) Для каждой пары (x, y):

         PMI = log2( P(x,y) / (P(x) × P(y)) )

           , где  P(x,y) = f(x,y) / (N × v)   — доля пар, которые составляют x и y,
                P(x)   = f(x) / N           — доля слов x в корпусе.

       После сокращения запись формулы:

         при окне 1:        PMI = log2( N × f(x,y) / (f(x) × f(y)) )
         при окне больше 1: PMI = log2( N × f(x,y) / (f(x) × f(y) × v) )

       Modified PMI = f(x,y) × PMI

    4) Итог по корпусу: среднее значение по всем разным парам и доля
       пар, у которых значение выше 0.

НАПРАВЛЕНИЕ ОКНА
    Окно идёт только ВПЕРЁД: для каждого слова x учитываются слова,
    стоящие справа от него (не дальше w позиций и не за концом предложения).
    Пара упорядочена: («социальный», «неравенство») и
    («неравенство», «социальный») — разные пары. Слева от слова соседи
    не ищутся. Так же описано в диссертации: «слова на дистанции пяти
    позиций справа от токена».

ЧТО ТАКОЕ v И ЗАЧЕМ ОНО НУЖНО
    Окно не может выйти за границу предложения. У последнего слова
    предложения справа нет соседей, у предпоследнего при окне 5 — только
    один, и так далее. Поэтому реальное число пар слов меньше, чем N × w.
    v — это и есть среднее число соседей на токен, посчитанное по факту:

         v = (число всех учтённых пар позиций) / N

    Произведение N × v — это общее число пар позиций в корпусе. Поэтому
    f(x,y) / (N × v) — настоящая вероятность того, что случайно взятая пара
    позиций занята словами x и y.

    При окне 1 поправка v в формуле не применяется.

ЧТО ТАКОЕ MODIFIED PMI И ПОЧЕМУ ЕГО ИСПОЛЬЗУЮТ
    У обычного PMI есть слабое место: пара, встретившаяся даже ОДИН раз,
    у которой оба слова тоже редкие, получает очень высокое значение,
    хотя это случайность. Пример для корпуса в 310 000 токенов:

         пара встретилась 1 раз, f(x) = f(y) = 1:
               PMI = log2(310000 × 1 / (1 × 1))       = 18.2

         устойчивое сочетание, f(x,y) = 50, f(x) = f(y) = 100:
               PMI = log2(310000 × 50 / (100 × 100))  = 10.6

    По обычному PMI случайная пара «сильнее» устойчивой. Modified PMI
    умножает PMI на f(x,y), то есть на число совместных употреблений:

         случайная пара:   1 × 18.2 =  18.2
         устойчивая пара: 50 × 10.6 = 530

    Теперь выигрывает та пара, которая и сильно связана, и действительно
    часто встречается. Modified PMI менее чувствителен к случайным единичным сочетаниям.

    Что надо помнить о Modified PMI:
      - его значения больше, чем у PMI, и растут вместе с размером корпуса
        (чаще встречаются пары, растёт f(x,y)). Поэтому сравнивать можно
        подкорпуса сопоставимого размера при одних и тех же условиях
        (окно, min_cooc). У PMI есть понятная шкала (0, 1, 2 ...),
        а у Modified PMI такой шкалы нет;
      - знак у него всегда тот же, что у PMI (f(x,y) всегда положительно),
        поэтому «доля пар выше 0» у Modified PMI и у PMI совпадает;
      - порог min_cooc решает ту же задачу другим способом: просто
        выбрасывает редкие пары.

КАК ЧИТАТЬ PMI
    Под логарифмом стоит отношение: сколько раз пара встретилась на самом
    деле / сколько раз она встретилась бы, если бы слова ставились
    независимо друг от друга (ожидаемое число совпадений).

         отношение      PMI = log2(отношение)    смысл
         ---------      ---------------------    -----
            1                   0                как случайная: слова не связаны
            2                   1                вдвое чаще случайного
            4                   2                вчетверо чаще
            8                   3                в восемь раз чаще
          1/2                  -1                вдвое реже случайного
          1/4                  -2                вчетверо реже

    Откуда ноль: логарифм единицы равен нулю, а отношение 1 означает
    «пара встречается ровно так часто, как при случайном соседстве».
    Поэтому 0 — граница между «связаны» (выше нуля) и «не связаны или
    избегают друг друга» (ниже нуля). Отсюда «доля пар с PMI > 0» —
    доля пар, которые встречаются чаще, чем при независимом выборе слов.

    Каждая единица PMI — это удвоение. Разница 5.7 и 3.5 — это не «чуть
    больше», а в 2^2.2 ≈ 4.6 раза.


Запуск (из корневой папки проекта translationese_metrics):
    python metrics/m6_pmi.py                          (папка texts, окно 5)
    python metrics/m6_pmi.py моя_папка                (своя папка с файлами .txt)
    python metrics/m6_pmi.py --window 1               (только соседние слова)
    python metrics/m6_pmi.py --window 1 --min-cooc 3  (пары, встретившиеся от 3 раз)
    python metrics/m6_pmi.py --demo                   (мини-корпус из трёх предложений)
    python metrics/m6_pmi.py --pair социальный неравенство   (разбор одной пары)
"""
import argparse
from collections import Counter
from math import log2

from razdel import sentenize, tokenize

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.common import (
    parse_cached, list_text_files, load_text,
    DEFAULT_FOLDER, print_title
)


class PMICalculator:
    """
    Считает PMI и Modified PMI для всех пар слов корпуса.

    window_size — размер окна (сколько слов справа учитывать);
    min_cooc    — пары, встретившиеся реже, в таблицу не попадают.

    Окно идёт только вперёд: учитываются слова справа от x, пара
    упорядочена — (x, y) и (y, x) считаются разными парами.
    """

    def __init__(
            self, window_size: int = 5,
            min_cooc: int = 1
    ):
        self.window_size = window_size
        self.min_cooc = min_cooc

        self.N_tokens = 0  # N
        self.total_window_positions = 0  # сколько соседей реально учтено
        self.token_freq = Counter()  # f(x)
        self.pair_freq = Counter()  # f(x, y)

    # ---------- подготовка текста ----------

    @staticmethod
    def _normalize_token(token: str):
        """Нижний регистр → только токены с буквами → лемма."""
        token = token.lower()
        if not any(char.isalpha() for char in token):
            return None
        return parse_cached(token).normal_form

    def _text_to_sentences(self, text: str) -> list:
        """Текст → список предложений, каждое — список лемм."""
        sentences = []
        # sentenize режет текст на предложения.
        # Каждое sent — объект, у которого есть текст предложения (sent.text).
        for sent in sentenize(text):
            lemmas = []
            # tokenize режет предложение на токены: слова, знаки препинания,
            # числа. tok.text — текст одного токена.
            for token in tokenize(sent.text):
                # Токен → лемма. Метод вернёт None, если в токене нет букв
                # (запятая, точка, число): такие токены нам не нужны.
                lemma = self._normalize_token(token.text)
                if lemma:
                    lemmas.append(lemma)
            if lemmas:
                sentences.append(lemmas)

        # Возвращаем список списков, например:
        # [["социальный", "неравенство", "расти"], ["доверие", "падать"]]
        return sentences

    # ---------- подсчёт частот ----------

    def fit(self, texts):
        """Проходит по корпусу и считает N, f(x), f(x, y)."""

        # Обнуляем всё: если fit вызвать повторно, старые числа не должны
        # складываться с новыми
        self.N_tokens = 0  # N: сколько всего слов в корпусе
        self.total_window_positions = 0  # сколько пар позиций учтено (нужно для v)
        self.token_freq.clear()  # f(x): частоты слов
        self.pair_freq.clear()  # f(x, y): частоты пар
        window_size = self.window_size

        for text in texts:
            # seq — одно предложение: список лемм
            for seq in self._text_to_sentences(text):
                seq_len = len(seq)

                # Частоты слов:
                # +1 к каждой лемме предложения
                for w in seq:
                    self.token_freq[w] += 1

                # Общее число слов корпуса растёт
                # на длину предложения
                self.N_tokens += seq_len

                # ПРИМЕР, который держим в голове (окно window_size = 2):
                #     seq = ["социальный", "неравенство", "снижать", "доверие"]
                #     номера:     0              1            2          3
                # seq_len = 4 (в предложении 4 слова)

                # Окно идёт только ВПЕРЁД: для каждого слова
                # ищем соседей только СПРАВА от него.

                for x_index, x_token in enumerate(seq):
                    # enumerate выдаёт слова вместе с их номерами.
                    # Цикл по словам предложения, по одному. Слово, для которого
                    # мы сейчас ищем соседей, называем x.
                    #   x_index — номер этого слова (0, 1, 2, 3),
                    #   x_token — само слово.
                    # Первый круг: x_index = 0, x_token = "социальный".
                    # Второй круг: x_index = 1, x_token = "неравенство", и так далее.

                    start = x_index + 1
                    # start — номер первого соседа справа.
                    # Для «социальный» (номер 0): start = 1, то есть «неравенство».

                    end = min(seq_len, x_index + 1 + window_size)
                    # end — номер, НА КОТОРОМ мы останавливаемся (сам он уже НЕ берётся).
                    # Окно длиной window_size начинается с start, поэтому «конец окна»
                    # равен start + window_size, то есть x_index + 1 + window_size.

                    # Но предложение может закончиться раньше. Поэтому берём меньшее
                    # из двух чисел: min(длина предложения, конец окна).
                    # Для «социальный» (номер 0): min(4, 0+1+2) = min(4, 3) = 3,
                    #   значит соседи — номера 1 и 2 (номер 3 уже не берём).
                    # Для «снижать» (номер 2): min(4, 2+1+2) = min(4, 5) = 4,
                    #   окно «хотело» дойти до 5, но предложение кончается на 3,
                    #   поэтому берём только номер 3.
                    # Для «доверие» (номер 3): min(4, 6) = 4, а start = 4. Соседей нет.

                    self.total_window_positions += (end - start)
                    # end - start — сколько соседей у слова x получилось на самом деле.
                    # «социальный»: 3 - 1 = 2 соседа
                    # «неравенство»: 4 - 2 = 2 соседа
                    # «снижать»:    4 - 3 = 1 сосед
                    # «доверие»:    4 - 4 = 0 соседей
                    # Здесь мы только копим СУММУ соседей по всему корпусу.
                    # Среднее число соседей на одно слово (v) считается позже, в методе
                    # avg_window: сумма соседей делится на число слов корпуса (N_tokens).

                    # Идём по номерам соседей справа: от start до end - 1.
                    for y_index in range(start, end):
                        # range(1, 3) даёт номера 1 и 2. Число 3 в него НЕ входит.
                        # Слово y — это сосед, с которым x образует пару.
                        self.pair_freq[(x_token, seq[y_index])] += 1
                        # seq[y_index] — слово с номером y_index (сосед y).
                        # (x_token, seq[y_index]) — пара слов: сначала x, потом y.
                        #   Порядок важен: пара («социальный», «неравенство»)
                        #   и пара («неравенство», «социальный») считаются разными.
                        # pair_freq — счётчик пар. «+= 1» значит: эта пара встретилась
                        #   ещё раз. Если пары в счётчике ещё не было, она появится
                        #   со значением 1.
                        #
                        # Что запишется для нашего примера:
                        #   x = «социальный»  → («социальный», «неравенство»)  +1
                        #                       («социальный», «снижать»)      +1
                        #   x = «неравенство» → («неравенство», «снижать»)     +1
                        #                       («неравенство», «доверие»)     +1
                        #   x = «снижать»     → («снижать», «доверие»)         +1
                        #   x = «доверие»     → ничего (справа никого нет)

        return self

    # ---------- формула ----------

    def avg_window(self) -> float:
        """
        v — среднее число соседей, реально учтённых для одного токена.
        Равно (число всех учтённых пар позиций) / N. Окно обрывается
        на границе предложения, поэтому v меньше размера окна.
        """
        if self.N_tokens == 0:
            return 0.0
        return self.total_window_positions / self.N_tokens

    def pmi(self, f_xy: int, f_x: int, f_y: int) -> float:
        """
        PMI одной пары по её частотам:
          окно 1:            log2( N × f(x,y) / (f(x) × f(y)) )
          окно больше 1:     log2( N × f(x,y) / (f(x) × f(y) × v) )
        Это записанная без вероятностей формула (9) диссертации.
        """
        N = self.N_tokens
        v = self.avg_window()
        if self.window_size > 1 and v > 0:
            return log2((N * f_xy) / (f_x * f_y * v))
        return log2((N * f_xy) / (f_x * f_y))

    def compute_scores(self) -> list:
        """
        Таблица пар: список словарей с ключами
        x, y, f(x,y), f(x), f(y), PMI, Mod. MI.
        Отсортирована по убыванию Modified PMI.
        """
        rows = []
        for (x_token, y_token), f_xy in self.pair_freq.items():
            if f_xy < self.min_cooc:
                continue
            f_x = self.token_freq[x_token]
            f_y = self.token_freq[y_token]
            pmi = self.pmi(f_xy, f_x, f_y)
            rows.append({
                "x": x_token, "y": y_token,
                "f(x,y)": f_xy, "f(x)": f_x, "f(y)": f_y,
                "PMI": pmi,
                "Mod. MI": f_xy * pmi,  # Modified PMI = f(x,y) × PMI
            })
        rows.sort(key=lambda r: (r["Mod. MI"], r["PMI"]), reverse=True)
        return rows

    # ---------- итоговые показатели ----------

    @staticmethod
    def average(rows: list, metric: str) -> float:
        """Среднее значение метрики по всем разным парам."""
        if not rows:
            return float("nan")
        return sum(r[metric] for r in rows) / len(rows)

    @staticmethod
    def threshold_share(rows: list, metric: str,
                        threshold: float = 0.0) -> float:
        """Доля пар, у которых значение метрики выше порога."""
        if not rows:
            return float("nan")
        return sum(1 for r in rows if r[metric] > threshold) / len(rows)

    # ---------- разбор одной пары ----------

    def explain_pair(self, x_word: str, y_word: str):
        """Печатает расчёт PMI для пары слов по шагам."""
        x = self._normalize_token(x_word)
        y = self._normalize_token(y_word)
        key = (x, y)
        f_x, f_y = self.token_freq.get(x, 0), self.token_freq.get(y, 0)
        f_xy = self.pair_freq.get(key, 0)
        N, v = self.N_tokens, self.avg_window()

        print(f"\nРАЗБОР ПАРЫ: {x_word} + {y_word}  (леммы: {x} + {y})")
        print(f"   N = {N}, f(x) = {f_x}, f(y) = {f_y}, f(x, y) = {f_xy}")
        if f_xy == 0:
            print("   Пара в корпусе не встретилась — PMI не определён.")
            return
        use_v = self.window_size > 1 and v > 0
        expected = f_x * f_y / N * (v if use_v else 1)
        print(f"   Ожидаемое число совпадений при независимости: "
              f"{f_x} × {f_y} / {N}"
              + (f" × {v:.3f}" if use_v else "") + f" = {expected:.3f}")
        print(f"   Реальное число больше ожидаемого в "
              f"{f_xy / expected:.2f} раза")
        pmi = self.pmi(f_xy, f_x, f_y)
        print(f"   PMI = log2({f_xy / expected:.2f}) = {pmi:.3f}")
        print(f"   Modified PMI = {f_xy} × {pmi:.3f} = {f_xy * pmi:.3f}")


def print_rows(rows: list, top_n: int = 15):
    print(f"   {'x':<18}{'y':<18}{'f(x,y)':>7}{'f(x)':>7}{'f(y)':>7}"
          f"{'PMI':>9}{'Mod. PMI':>10}")
    for r in rows[:top_n]:
        print(f"   {r['x']:<18}{r['y']:<18}{r['f(x,y)']:>7}{r['f(x)']:>7}"
              f"{r['f(y)']:>7}{r['PMI']:>9.3f}{r['Mod. MI']:>10.3f}")


# Мини-корпус для режима --demo: по нему удобно проверять расчёт вручную
DEMO_CORPUS = [
    "Социальное неравенство растёт. "
    "Социальное неравенство снижает доверие. Доверие растёт."
]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PMI для корпуса текстов")
    parser.add_argument("folder", nargs="?", default=DEFAULT_FOLDER,
                        help="папка с файлами .txt (по умолчанию texts)")
    parser.add_argument("--window", type=int, default=5,
                        help="размер окна (по умолчанию 5)")
    parser.add_argument("--min-cooc", type=int, default=1,
                        help="минимальная совместная встречаемость")
    parser.add_argument("--demo", action="store_true",
                        help="считать на мини-корпусе из трёх предложений")
    parser.add_argument("--pair", nargs=2, metavar=("X", "Y"),
                        help="разобрать по шагам одну пару слов")
    parser.add_argument("--top", type=int, default=15,
                        help="сколько пар показать")
    args = parser.parse_args()

    if args.demo:
        texts, source = DEMO_CORPUS, "Мини-корпус из трёх предложений"
    else:
        files = list_text_files(args.folder)
        if not files:
            raise SystemExit("В папке нет файлов .txt")
        texts = [load_text(path) for path in files]
        source = f"папка {args.folder}, текстов: {len(files)}"

    print_title(f"МЕТРИКА 6. PMI ({source})")
    if args.demo:
        print(f"\nТекст: {DEMO_CORPUS[0]}")

    calc = PMICalculator(window_size=args.window, min_cooc=args.min_cooc)
    calc.fit(texts)
    rows = calc.compute_scores()

    print(f"\nОкно: {args.window}, направление: вперёд (справа от слова), "
          f"минимальная совместная встречаемость: {args.min_cooc}")
    print(f"Токенов в корпусе (N):               {calc.N_tokens}")
    print(f"Среднее число соседей на токен (v):  {calc.avg_window():.3f}"
          + ("  (при окне 1 в формуле не используется)"
             if args.window == 1 else ""))
    print(f"Разных пар:                          {len(rows)}")

    print(f"\nПары с самым высоким Modified PMI (первые {args.top}):")
    print_rows(rows, args.top)

    if args.pair:
        calc.explain_pair(*args.pair)
    elif rows:
        calc.explain_pair(rows[0]["x"], rows[0]["y"])

    print("\nИТОГ ПО КОРПУСУ")
    for metric, label in (("PMI", "PMI"), ("Mod. MI", "Modified PMI")):
        print(f"   Среднее {label}: "
              f"{PMICalculator.average(rows, metric):.3f};  "
              f"доля пар выше 0: "
              f"{PMICalculator.threshold_share(rows, metric) * 100:.1f} %")
