# -*- coding: utf-8 -*-
"""
ОБЩИЙ МОДУЛЬ: подготовка текста для всех метрик.

Здесь собрано всё, что нужно сделать с текстом ДО подсчёта метрик:
  1) выровнять пробелы (fix_spacing);
  2) посчитать словарные токены (count_word_tokens);
  3) привести слова к леммам (lemmatize_words);
  4) убрать стоп-слова и оставить знаменательную лексику
     (lemmatize_words_without_stopwords, count_content_words);
  5) разбить текст на предложения (split_into_sentences).

Логика перенесена из программы translationese_analyzer
(файлы tools/core/lemmatizators.py, tokens_counter.py,
custom_punkt_tokenizer.py, utils.py, start_analysis.py).

Запустите этот файл сам по себе, чтобы увидеть все шаги на примере
(из корневой папки проекта translationese_metrics):
    python utils/common.py
    python utils/common.py texts/text_1.txt  (свой текст)
"""
import os
import re
import sys
import warnings
from collections import defaultdict
from functools import lru_cache

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import conjunctions, prepositions, particles, pronouns
from data.nltk_stopwords_ru import nltk_stopwords_ru
from data.sentence_abbreviations import SENTENCE_ABBREVIATIONS

warnings.filterwarnings("ignore")

# Если консоль не умеет показывать какой-то символ (например, «→»),
# печатаем вместо него «?», а не останавливаем программу с ошибкой.
try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

_ALLOWED_CHARS = re.compile(r"[^А-Яа-яЁёA-Za-z\-]+")

# ──────────────────────────────────────────────────────────────
# 0. Морфологический анализатор
# ──────────────────────────────────────────────────────────────
# Основная программа работает с pymorphy2. На новых версиях Python
# (3.11 и выше) pymorphy2 не запускается, поэтому здесь есть запасной
# вариант — pymorphy3 (та же библиотека, обновлённая для новых версий).


def _load_morph():
    try:
        import pymorphy2
        return pymorphy2.MorphAnalyzer(), "pymorphy2"
    except Exception:
        import pymorphy3
        return pymorphy3.MorphAnalyzer(), "pymorphy3"


morph, MORPH_NAME = _load_morph()


@lru_cache(maxsize=200_000)
def parse_cached(token: str):
    """Возвращает первый (самый вероятный) разбор слова.
    Результат запоминается, чтобы не разбирать одно слово дважды."""
    token = token.strip()
    return morph.parse(token)[0]


# ──────────────────────────────────────────────────────────────
# 1. Чтение и выравнивание текста
# ──────────────────────────────────────────────────────────────

def read_text(path: str) -> str:
    """Читает текст из файла .txt. Ожидается кодировка UTF-8;
    если файл сохранён в старой кодировке Windows, читаем его как cp1251."""
    try:
        with open(path, "r", encoding="utf-8-sig") as file:
            return file.read()
    except UnicodeDecodeError:
        with open(path, "r", encoding="cp1251") as file:
            return file.read()


def fix_spacing(text: str) -> str:
    """Убирает переносы строк и лишние пробелы, расставляет пробелы
    после знаков препинания."""
    # Переносы строк заменяем одним пробелом
    text = re.sub(r'\n+', ' ', text)
    # "слово.Слово" превращаем в "слово. Слово"
    text = re.sub(r'([А-Яа-яЁёA-Za-z])\.([А-Яа-яЁёA-Za-z])', r'\1. \2', text)
    # Несколько пробелов подряд заменяем одним
    text = re.sub(r'\s+', ' ', text)
    # Знак препинания, слипшийся со следующим словом
    text = re.sub(r'([,.!?])([А-Яа-яЁёA-Za-z])', r'\1 \2', text)
    # Пробел перед знаком препинания убираем
    text = re.sub(r'\s+([,.!?])', r'\1', text)
    return text


def load_text(path: str) -> str:
    """Читает файл и сразу выравнивает пробелы."""
    return fix_spacing(read_text(path))


def list_text_files(folder: str) -> list:
    """Возвращает отсортированный список файлов .txt в папке."""
    files = [
        os.path.join(folder, name)
        for name in sorted(os.listdir(folder))
        if name.lower().endswith(".txt")
    ]
    # print(files)
    return files


# ──────────────────────────────────────────────────────────────
# 2. Словарные токены
# ──────────────────────────────────────────────────────────────

def count_word_tokens(text: str) -> int:
    """
    Число словарных токенов N — знаменатель большинства метрик.
    Токеном считается любая цепочка букв и цифр между границами слов.
    Знаки препинания не считаются, числа цифрами считаются.
    """
    return len(re.findall(r'\b\w+\b', text))


# ──────────────────────────────────────────────────────────────
# 3. Леммы всех слов
# ──────────────────────────────────────────────────────────────


def lemmatize_words(text: str) -> list:
    """
    Разбирает ВСЕ слова текста (включая служебные).
    Возвращает список разборов; у каждого есть:
      .word         — слово, как в тексте (в нижнем регистре),
      .normal_form  — лемма,
      .tag.POS      — часть речи.
    """
    text = re.sub(_ALLOWED_CHARS, ' ', text)
    return [parse_cached(token) for token in text.split()]


def get_lemmas(text: str) -> list:
    """Список лемм всех слов текста."""
    return [parsed.normal_form for parsed in lemmatize_words(text)]


# ──────────────────────────────────────────────────────────────
# 4. Стоп-слова и знаменательная лексика
# ──────────────────────────────────────────────────────────────

# Единый список стоп-слов: союзы + предлоги + частицы + местоимения.
# Союзы, предлоги и частицы хранятся в файлах папки data как множества
# (conjunctions_set, prepositions_set, particles_set), поэтому их
# объединяем знаком |; местоимения хранятся списком (pronouns_list).
all_stopwords = (
    conjunctions.conjunctions_set
    | prepositions.prepositions_set
    | prepositions.prepositions_set
    | particles.particles_set
    | set(nltk_stopwords_ru)
    | set(pronouns.pronouns_list)
)

# Длинные единицы («несмотря на то что») должны проверяться раньше
# коротких («несмотря на», «на»), поэтому сортируем по длине.
all_stopwords_sorted = sorted(list(all_stopwords), key=len, reverse=True)

_STOPWORDS_PATTERN = re.compile(
    r'(?<!-)\b(?:' +
    '|'.join(re.escape(w) for w in all_stopwords_sorted) +
    r')\b(?!-)',
    re.IGNORECASE
)


def remove_stopwords(text: str) -> tuple:
    """
    Удаляет стоп-слова из текста.
    Возвращает (текст без стоп-слов, сколько стоп-слов удалено).
    Составной союз или предлог («в связи с») удаляется целиком,
    как одна единица.
    """
    if not text:
        return "", 0

    removed_count = len(_STOPWORDS_PATTERN.findall(text))
    # Удаляем стоп-слова.
    text_without_stopwords = _STOPWORDS_PATTERN.sub('', text)
    # Заменяем недопустимые символы пробелами.
    text_with_allowed_chars = _ALLOWED_CHARS.sub(
        ' ', text_without_stopwords
    )
    # Убираем повторяющиеся пробелы и пробелы символы по краям строки.
    final_cleaned_text = re.sub(
        r'\s+', ' ', text_with_allowed_chars
    ).strip()

    return final_cleaned_text, removed_count


def lemmatize_words_without_stopwords(text: str) -> tuple:
    """
    Сначала удаляет стоп-слова, потом разбирает оставшиеся слова.
    Возвращает (список разборов, число удалённых стоп-слов).
    """
    cleaned_text, removed_count = remove_stopwords(text)
    parsed_words = [parse_cached(token) for token in cleaned_text.split()]
    return parsed_words, removed_count


# Знаменательные части речи (обозначения pymorphy2):
# существительное, глагол, инфинитив, причастия, деепричастие,
# предикатив, прилагательные, компаратив, наречие.
CONTENT_POS = {
    'NOUN', 'VERB', 'INFN', 'PRTF', 'PRTS',
    'GRND', 'PRED', 'ADJF', 'ADJS', 'COMP',
    'ADVB'}

# Глаголы, которые не считаются знаменательными: связочные и модальные
EXCLUDED_LEMMAS = {
    "быть", "являться", "стать", "сделаться", "оказаться", "явиться",
    "находиться", "становиться",
    "мочь", "смочь", "суметь", "уметь", "удаться", "собираться",
    "сделать", "делать", "иметь", "иметься",
}


def count_content_words(text: str) -> dict:
    """
    Частоты знаменательных лемм текста: {лемма: сколько раз встретилась}.
    Шаги: нижний регистр → удаление стоп-слов → леммы →
    только знаменательные части речи → без связочных и модальных глаголов.
    Словарь отсортирован по убыванию частоты.
    """
    parsed, _ = lemmatize_words_without_stopwords(text.lower())
    counts = defaultdict(int)
    for token in parsed:
        if getattr(token.tag, "POS", None) in CONTENT_POS:
            lemma = token.normal_form
            if lemma not in EXCLUDED_LEMMAS:
                counts[lemma] += 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


# ──────────────────────────────────────────────────────────────
# 5. Предложения
# ──────────────────────────────────────────────────────────────

# def split_into_sentences(text: str) -> list:
#     """
#     Делит текст на предложения. Точка после сокращений из списка
#     (г., рис., т. е. и др.) концом предложения не считается.
#     """
#     from nltk.tokenize.punkt import PunktSentenceTokenizer, PunktParameters
#     text = text.replace('\n', '')
#     params = PunktParameters()
#     params.abbrev_types = {abbr.lower() for abbr in sorted_abbrev}
#     return list(PunktSentenceTokenizer(params).tokenize(text))


from razdel.segmenters import sokr as _razdel_abbreviations

_razdel_abbreviations.SOKRS.update(SENTENCE_ABBREVIATIONS)


def split_into_sentences(text: str) -> list:
    """
    Делит текст на предложения с помощью Natasha и возвращает список строк.
    """
    from natasha import Doc, Segmenter

    # Создаём документ Natasha с исходным текстом
    doc = Doc(text)
    # Делим его на токены и предложения; предложения попадают в doc.sents
    doc.segment(Segmenter())

    sentences = []
    for sentence in doc.sents:
        # Natasha считает точку с запятой концом предложения, если дальше
        # идёт цифра или заглавная буква: «(ОШ 1,5;» и «95% ДИ 1,1–2,0)».
        # Такую часть присоединяем к предыдущей.
        if sentences and sentences[-1].endswith(";"):
            sentences[-1] = sentences[-1] + " " + sentence.text
        else:
            sentences.append(sentence.text)
    return sentences


# ──────────────────────────────────────────────────────────────
# Вспомогательное: выбор текста для запуска из командной строки
# ──────────────────────────────────────────────────────────────

# Корень проекта — папка, в которой лежат metrics, utils, data и texts.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_FOLDER = os.path.join(PROJECT_ROOT, "texts")


def text_from_command_line_or_file(demo_text: str) -> tuple:
    """
    Если после имени скрипта указан путь к файлу .txt — берём текст из него.
    Если ничего не указано — берём учебный текст demo_text.
    Возвращает (название, текст).
    """
    if len(sys.argv) > 1:
        path_to_text = sys.argv[1]
        return os.path.basename(path_to_text), load_text(path_to_text)
    return "Иллюстративный пример", fix_spacing(demo_text)


def folder_from_command_line() -> str:
    """Папка с текстами: указанная после имени скрипта или папка texts."""
    return sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FOLDER


def print_title(title: str):
    print()
    print("=" * 70)
    print("              ", title)
    print("=" * 70)


DEMO_TEXT = """
В.С. Садовников – автор многочисленных акварельных видов Петербурга времен Пушкина, Гоголя, Достоевского. Поэтическое восприятие города художник всегда сочетал с документальной точностью в изображениях архитектурных памятников. При этом он передавал впечатление живой жизни города, рисуя гуляющих людей разных сословий, мчащиеся по улице кареты. Акварели художника пользовались успехом, и, несмотря на свое положение крепостного, уже в 1820-е годы Садовников был хорошо известен. В 1838 году, после смерти своей владелицы княгини Н.П. Голицыной, послужившей прообразом старой графини в романе А.С. Пушкина, он получил вольную, и в том же году – звание свободного художника.
В течение всей жизни акварелист исполнял многочисленные заказы императорского двора. Он создавал разные виды Санкт-Петербурга по случаю коронации, бракосочетаний, рождения наследников, выездов и парадов. К ним относится и акварель с видом Мариинского дворца. Дворец был свадебным подарком по случаю бракосочетания дочери Николая I Марии Николаевны с герцогом Максимилианом Лейхтенбергским. Проект и строительство дворца император поручил любимому архитектору А.А. Штакеншнейдеру. Великолепное здание было построено в 1839–1844 годах и считается его лучшим творением.
"""

if __name__ == "__main__":
    name, text = text_from_command_line_or_file(DEMO_TEXT)
    print_title(f"ПОДГОТОВКА ТЕКСТА ({name})")
    print(f"Морфологический анализатор: {MORPH_NAME}")
    print(f"\nТекст:\n{text[:500]}{'...' if len(text) > 500 else ''}")

    print(f"\n1. Словарных токенов (N): {count_word_tokens(text)}")

    parsed = lemmatize_words(text)
    print("\n2. Слова и их леммы (первые 20):")
    for p in parsed[:20]:
        print(f"   {p.word:<18} → {p.normal_form:<18} {p.tag.POS}")

    cleaned, removed = remove_stopwords(text)
    print(f"\n3. Удалено стоп-слов: {removed}")
    print(f"   Текст без стоп-слов: {cleaned[:300]}")

    print("\n4. Частоты знаменательных лемм:")
    for lemma, freq in list(count_content_words(text).items())[:20]:
        print(f"   {lemma:<18} {freq}")

    sentences = split_into_sentences(text)
    print(f"\n5. Предложений: {len(sentences)}")
    for i, sentence in enumerate(sentences[:5], 1):
        print(f"   {i}. {sentence}")
