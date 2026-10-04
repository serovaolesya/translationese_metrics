# -*- coding: utf-8 -*-
"""
МЕТРИКИ 3 и 4. Средняя длина клауз и число клауз на предложение.

Идея: насколько сложно устроены предложения. Обе метрики считаются
вместе, потому что обе требуют учета клауз текста.

Как считается:
  1) текст делится на предложения;
  2) каждое предложение разбирает синтаксический парсер Natasha:
     у каждого слова есть:
       pos — часть речи токена;
       feats — морфологические признаки;
       rel — отношение токена к его синтаксической вершине
       в формате Universal Dependencies;
  3) по сочетанию pos, feats и rel алгоритм находит вершины клауз;
  4) если вершины не найдены, условно учитывается одна клауза;
  5) число клауз на предложение = все клаузы / все предложения;
     средняя длина клаузы = все токены без пунктуации / все клаузы.


Синтаксические отношения, используемые в алгоритме:

  root — корень дерева предложения, его главная вершина.
    Пример: «Авторы анализируют данные».
    Главная вершина: «анализируют».
    Корень не обязательно является глаголом:
    в «Результаты значимы» вершиной может быть «значимы».

  ccomp — clausal complement, клауза-дополнение при предикате.
    Пример: «Авторы утверждают, что метод работает».
    Связь: утверждают → работает.
    Зависимая клауза: «что метод работает».

  advcl — adverbial clause modifier, обстоятельственная клауза.
    Может выражать время, причину, условие, цель и другие значения.
    Пример: «Когда исследование завершилось, авторы написали статью».
    Связь: написали → завершилось.
    Также используется для деепричастных конструкций:
    «Изучив данные, авторы сделали вывод».
    Связь: сделали → изучив.

  acl:relcl — relative clause modifier, относительная клауза при имени; подтип отношения acl.
    Пример: «Метод, который предложили авторы, оказался полезным».
    Связь: метод → предложили.
    Относительная клауза: «который предложили авторы».

  parataxis — паратаксис, свободное присоединение конструкции
    без обычного подчинения или явного сочинения.
    Пример: «Автор сказал: “Метод работает”».
    Связь: сказал → работает.

  acl — clausal modifier of nominal, клаузальный модификатор имени.
    Пример: «Авторы проверили метод, предложенный коллегами».
    Связь: метод → предложенный.
    Отношение acl шире причастного оборота и может обозначать
    другие предикативные конструкции при имени.

Как текущий алгоритм классифицирует найденные вершины:

  - VERB с root, ccomp, advcl или acl:relcl → категория finite;
    исключение: advcl с VerbForm=Conv → категория advcl_conv;

  - VERB с parataxis, если VerbForm не Part, Conv или Inf,
    → категория finite;

  - VERB с acl и VerbForm=Part → категория acl_part;

  - ADJ с Variant=Short и root, ccomp, advcl или acl:relcl
    → категория finite;

Важно:
  Названия finite, advcl_conv и acl_part — категории программы.
  Отношение UD само по себе не определяет финитность.
  Например, advcl бывает у инфинитивных конструкций.

Запуск (из корневой папки проекта translationese_metrics):
    python metrics/m3_m4_clauses.py                   (учебный пример)
    python metrics/m3_m4_clauses.py texts/text_1.txt  (свой текст)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.common import split_into_sentences, text_from_command_line_or_file, print_title

# Модели Natasha загружаются один раз, при первом обращении
_models = {}


def _get_models():
    if not _models:
        from natasha import (
            Segmenter,
            NewsEmbedding,
            NewsMorphTagger,
            NewsSyntaxParser,
        )

        # Создаём объект с числовыми представлениями слов.
        # Его передаём морфологическому и синтаксическому анализаторам.
        word_embeddings = NewsEmbedding()

        # Инструмент разделения текста на токены и предложения.
        _models["segmenter"] = Segmenter()
        # Инструмент определения частей речи
        # и морфологических признаков токенов.
        _models["morph_tagger"] = NewsMorphTagger(word_embeddings)
        # Инструмент определения синтаксических связей между токенами.
        _models["syntax_parser"] = NewsSyntaxParser(word_embeddings)
    return _models


def parse_sentence(sentence: str):
    """
    Возвращает предложение, разобранное Natasha (список токенов в .tokens).
    """
    from natasha import Doc
    models = _get_models()

    # Создаём документ, содержащий переданное предложение.
    doc = Doc(sentence)

    # Делим документ на токены и предложения.
    # Результаты сохраняются в doc.tokens и doc.sents.
    doc.segment(models["segmenter"])

    # Определяем часть речи и морфологические признаки каждого токена.
    # Результаты сохраняются в token.pos и token.feats.
    doc.tag_morph(models["morph_tagger"])

    # Определяем синтаксические связи между токенами:
    # token.head_id — идентификатор вершины, от которой зависит токен;
    # token.rel — тип отношения к этой вершине.
    doc.parse_syntax(models["syntax_parser"])

    return doc


# Отношения, при которых глагол считается вершиной финитной клаузы
FINITE_CLAUSE_RELS = {"root", "advcl", "ccomp", "acl:relcl"}

CLAUSE_TYPE_NAMES = {
    "finite": "финитная клауза",
    "advcl_conv": "деепричастный оборот",
    "acl_part": "причастный оборот",
}


def _feature(tok, name: str) -> str:
    """Значение морфологического признака токена (или пустая строка)."""
    feats = getattr(tok, 'feats', None) or {}
    return feats.get(name, '')


def classify_token(token):
    """
    Решает, является ли слово вершиной клаузы.
    Возвращает 'finite', 'advcl_conv', 'acl_part' или None.
    """

    # tok.pos: часть речи (VERB, ADJ, NOUN, AUX, PUNCT…);
    # tok.rel: тип связи с главным словом;
    # tok.feats: словарь морфологических признаков, например
    # {'VerbForm': 'Fin', 'Tense': 'Pres'} или {'Variant': 'Short'}.

    # Берём у слова тип синтаксической связи (rel) и часть речи (pos).
    # getattr вернёт None, если у слова нет такого свойства.
    rel = getattr(token, 'rel', None)
    pos = getattr(token, 'pos', None)

    # Отсеиваем слова, которые не могут быть вершиной клаузы:
    # - без типа связи (rel is None) ни одно из правил ниже не применить;
    # - вершина клаузы - только глагол или прилагательное,
    #   остальные части речи пропускаем.
    if rel is None or pos not in ('VERB', 'ADJ'):
        return None

    # ---------- Прилагательные ----------
    if pos == 'ADJ':

        # Признак Variant: 'Short' у краткой формы («значимы»),
        variant = _feature(token, 'Variant')

        # Краткое прилагательное в роли сказуемого работает как глагол:
        # «Результаты значимы». Связь должна быть одной из списка
        # FINITE_CLAUSE_RELS (корень предложения или придаточное).
        if variant == 'Short' and rel in FINITE_CLAUSE_RELS:
            return 'finite'  # «результаты значимы»

        return None

    # ---------- Глаголы и неличные формы глаголов ----------
    # Форма глагола (признак VerbForm): Fin — личная, Inf — инфинитив,
    # Part — причастие, Conv — деепричастие.
    verb_form = _feature(token, 'VerbForm')

    # Связи root (главная клауза), ccomp (дополнительная: «утверждают,
    # что…»), advcl (обстоятельственная), acl:relcl (относительная:
    # «различия, которые…») дают клаузу.
    if rel in FINITE_CLAUSE_RELS:

        # Деепричастие в обстоятельственной связи — деепричастный оборот.
        if rel == 'advcl' and verb_form == 'Conv':
            return 'advcl_conv'  # деепричастный оборот
        return 'finite'

    # Клауза, стоящая рядом без союза (parataxis) - БСП: считаем только
    # личные формы, причастия, деепричастия и инфинитивы исключаем.
    if rel == 'parataxis' and verb_form not in ('Part', 'Conv', 'Inf'):
        return 'finite'

    # Причастие, которое определяет существительное (acl),
    # — причастный оборот.
    if rel == 'acl' and verb_form == 'Part':
        return 'acl_part'

    # Ни одно правило не подошло: слово не является вершиной клаузы.
    return None


def analyze_clause_structure(sentences: list) -> dict:
    """
    :param sentences: список предложений текста
    :return: словарь с числом клауз, клауз на предложение и длиной клаузы
    """
    # Число найденных вершин каждого типа во всём тексте
    # (финитные клаузы, деепричастные обороты, причастные обороты).
    clause_counts_by_type = {
        'finite': 0,
        'advcl_conv': 0,
        'acl_part': 0,
    }
    total_clauses = 0
    total_non_punct_tokens = 0
    # Число предложений, где алгоритм нашёл
    # не больше одной финитной клаузы.
    simple_sentences = 0

    for sentence in sentences:
        doc = parse_sentence(sentence)

        # Токены без знаков препинания
        total_non_punct_tokens += len(
            [token for token in doc.tokens
             if getattr(token, 'pos', None) != 'PUNCT']
        )

        # Это словарь-включение: берём те же ключи, что в общем словаре,
        # и каждому даём ноль. Получается
        # {'finite': 0, 'advcl_conv': 0, 'acl_part': 0}.
        sent_counts = {key: 0 for key in clause_counts_by_type}

        for tok in doc.tokens:

            # Определяем, является ли токен вершиной клаузы.
            # Получаем название категории или None.
            clause_type = classify_token(tok)
            if clause_type:
                sent_counts[clause_type] += 1

        for key in clause_counts_by_type:
            clause_counts_by_type[key] += sent_counts[key]

        clauses_num = sum(sent_counts.values())
        total_clauses += (
            clauses_num) if clauses_num > 0 else 1  # минимум одна клауза

        # Простое предложение — не больше одной финитной клаузы
        if sent_counts['finite'] <= 1:
            simple_sentences += 1

    total_sentences = len(sentences)
    return {
        'total_sentences': total_sentences,
        'total_clauses': total_clauses,
        'finite_clauses': clause_counts_by_type['finite'],
        'advcl_conv_clauses': clause_counts_by_type['advcl_conv'],
        'acl_part_clauses': clause_counts_by_type['acl_part'],
        'total_non_punct_tokens': total_non_punct_tokens,
        'avg_clauses_per_sent': (
            total_clauses / total_sentences if total_sentences else 0.0),
        'avg_tokens_per_clause': (
            total_non_punct_tokens / total_clauses if total_clauses else 0.0),
        'simple_ratio': (
            simple_sentences / total_sentences * 100
            if total_sentences else 0.0),
    }


def clause_metrics(text: str) -> dict:
    """Метрики клауз для текста."""
    return analyze_clause_structure(split_into_sentences(text))


DEMO_TEXT = """
В.С. Садовников является автором многочисленных акварельных видов Петербурга времен Пушкина, Гоголя, Достоевского. Поэтическое восприятие города художник всегда сочетал с документальной точностью в изображениях архитектурных памятников. При этом он передавал впечатление живой жизни города, рисуя гуляющих людей разных сословий. Акварели художника пользовались успехом. Несмотря на свое положение крепостного, уже в 1820-е годы Садовников был хорошо известен. В 1838 году, после смерти своей владелицы княгини Н.П. Голицыной, послужившей прообразом старой графини в романе А.С. Пушкина, он получил вольную, и в том же году – звание свободного художника.
В течение всей жизни акварелист исполнял многочисленные заказы императорского двора. Он создавал разные виды Санкт-Петербурга по случаю коронации, бракосочетаний, рождения наследников, выездов и парадов. К ним относится и акварель с видом Мариинского дворца. Дворец стал свадебным подарком по случаю бракосочетания дочери Николая I Марии Николаевны с герцогом Максимилианом Лейхтенбергским. Проект и строительство дворца император поручил любимому архитектору А.А. Штакеншнейдеру. Великолепное здание было построено в 1839–1844 годах и считается его лучшим творением.
"""

if __name__ == "__main__":
    name, text = text_from_command_line_or_file(DEMO_TEXT)
    print_title(f"МЕТРИКИ 3–4. КЛАУЗЫ ({name})")

    sentences = split_into_sentences(text)

    print("\nВершины клауз по предложениям (первые 100 предложений):")
    for i, sentence in enumerate(sentences[:100], start=1):

        # Получаем документ с результатами разбора предложения:
        # токенами, частями речи, морфологическими признаками
        # и синтаксическими связями.
        doc = parse_sentence(sentence)

        # Печатаем номер и исходный текст предложения.
        print(f"\n{i}. {sentence}")

        # Собираем сведения о токенах, признанных вершинами клауз.
        # Каждый элемент списка — кортеж из трёх значений:
        # (текст токена, синтаксическое отношение, тип клаузы).
        heads = [
            (token.text, token.rel, classify_token(token))
            for token in doc.tokens
            if classify_token(token)]

        # Распаковываем каждый кортеж и печатаем его значения.
        for word, rel, clause_type in heads:
            print(f"     {word:<18} rel = {rel:<10} "
                  f"→ {CLAUSE_TYPE_NAMES[clause_type]}")
        if not heads:
            print("     вершин не найдено → считается 1 клауза")

    # Рассчитываем показатели для всех предложений текста.
    clause_analysis_results = analyze_clause_structure(sentences)

    print(f"\nПредложений:              {clause_analysis_results['total_sentences']}")
    print(f"Клауз всего:              {clause_analysis_results['total_clauses']}")
    print(f"   финитных:              {clause_analysis_results['finite_clauses']}")
    print(f"   деепричастных оборотов: {clause_analysis_results['advcl_conv_clauses']}")
    print(f"   причастных оборотов:   {clause_analysis_results['acl_part_clauses']}")
    print(f"Токенов без пунктуации:   {clause_analysis_results['total_non_punct_tokens']}")

    if clause_analysis_results['total_sentences']:
        print(f"\nКлауз на предложение = {clause_analysis_results['total_clauses']} / "
              f"{clause_analysis_results['total_sentences']} ="
              f" {clause_analysis_results['avg_clauses_per_sent']:.2f}")

        print(f"Средняя длина клаузы = {clause_analysis_results['total_non_punct_tokens']} / "
              f"{clause_analysis_results['total_clauses']} = "
              f"{clause_analysis_results['avg_tokens_per_clause']:.2f}")
