# -*- coding: utf-8 -*-
"""
ИМЕНОВАННЫЕ СУЩНОСТИ — общий модуль для метрик 7 и 8.

ЧТО ДЕЛАЕТ
    Находит в тексте имена людей (PER), места (LOC) и организации (ORG)
    с помощью модели распознавания именованных сущностей из Natasha.
    Результат — список пар (текст сущности, тип).

ПОЧЕМУ НУЖНЫ ДВА СПИСКА ПРАВОК
    Модель ошибается, поэтому её результат правится вручную:
      - false_named_entities (файл data/false_named_entities.py) —
        слова, которые модель ошибочно принимает за имена
        («Интернет», «СМИ»). Такие находки выбрасываются;
      - CUSTOM_NAMED_ENTITIES (ниже) — имена, которые модель пропускает
        или режет на части. Они добавляются вручную.
    Оба списка можно дополнять под свои тексты.

КАК ЭТО РАБОТАЕТ (ШАГИ extract_entities)
    1. В тексте ищутся записи из CUSTOM_NAMED_ENTITIES и берутся
       в квадратные скобки: «в [Минздрава России] сообщили...».
    2. Текст со скобками отдаётся модели Natasha, она находит сущности.
    3. Из найденного моделью выбрасываются слова из false_named_entities.
    4. К результату добавляются сущности, которые были взяты в скобки
       на шаге 1, вместе с их типом из CUSTOM_NAMED_ENTITIES.

ЧТО ВАЖНО ЗНАТЬ
    Шаги 2 и 4 работают независимо друг от друга, поэтому:
      - если модель сама нашла сущность из CUSTOM_NAMED_ENTITIES,
        она будет посчитана дважды (моделью и по списку);
      - если модель разрезала сущность на части («Минздрава» + «России»),
        эти части остаются, а целая сущность добавляется ещё раз;
      - если одна запись списка вложена в другую («ИПО Красноярского ГМУ…»
        и «Красноярского ГМУ…»), скобки получаются вложенными, и вручную
        такая сущность не добавится.
    Запуск файла покажет, откуда взялась каждая находка.

Запуск (из корневой папки проекта translationese_metrics):
    python utils/entities.py                   (учебный пример)
    python utils/entities.py texts/text_1.txt  (свой текст)
"""
import re

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.common import text_from_command_line_or_file, print_title
from data.false_named_entities import false_named_entities

# Сущности, которые модель не распознаёт: {текст сущности: тип}.
# Типы PER, LOC, ORG
CUSTOM_NAMED_ENTITIES = {
    # 'Сущность': 'ТИП',
}

# Модели Natasha загружаются долго, поэтому грузим их один раз,
# при первом обращении, и дальше берём из этого словаря.
_models = {}


def _get_models():
    """Возвращает модели Natasha; при первом вызове загружает их."""
    if not _models:
        #  Segmenter — делит текст на токены и предложения;
        #  NewsEmbedding — числовые представления слов, нужны модели;
        #  NewsNERTagger — сама модель распознавания сущностей.
        from natasha import Segmenter, NewsEmbedding, NewsNERTagger
        _models["segmenter"] = Segmenter()
        _models["ner_tagger"] = NewsNERTagger(NewsEmbedding())
    return _models


def _mark_custom_entities(text: str) -> str:
    """
    Шаг 1. Берёт в квадратные скобки сущности из CUSTOM_NAMED_ENTITIES.
    Пример: «в Минздрава России» -> «в [Минздрава России]».
    """
    for entity in CUSTOM_NAMED_ENTITIES:
        if entity in text:
            text = text.replace(entity, f"[{entity}]")
    return text


def _find_with_model(processed_text: str) -> list:
    """
    Находит сущности моделью Natasha и исключает
    ложные срабатывания из false_named_entities.

    :return: список [(текст сущности, тип), ...]
    """
    from natasha import Doc
    models = _get_models()

    # Создаём документ и размечаем сущности.
    # Результат лежит в doc.ner.spans: у каждого найденного фрагмента
    # есть start и stop (позиции в тексте) и type (PER, LOC, ORG).
    doc = Doc(processed_text)
    doc.segment(models["segmenter"])
    doc.tag_ner(models["ner_tagger"])

    # Список сущностей, прошедших проверку.
    filtered_model_entities = []

    for entity_span in doc.ner.spans:

        # Извлекаем исходное написание найденной сущности.
        entity_text = doc.text[
            entity_span.start:entity_span.stop
        ]

        # Пропускаем записи из списка ложных срабатываний.
        if entity_text in false_named_entities:
            continue

        # Добавляем пару: написание сущности и её тип.
        filtered_model_entities.append(
            (entity_text, entity_span.type)
        )

    return filtered_model_entities


def _find_custom(processed_text: str) -> list:
    """
    Шаг 4. Достаёт сущности, взятые в квадратные скобки на шаге 1,
    и подставляет их тип из CUSTOM_NAMED_ENTITIES.
    :return: список [(текст сущности, тип), ...]
    """
    custom_found = []

    # Регулярное выражение \[([^\]]+)\] означает: найти текст между
    # «[» и первой «]»; скобки в результат не входят.
    for entity in re.findall(r"\[([^\]]+)\]", processed_text):
        entity_type = CUSTOM_NAMED_ENTITIES.get(entity)
        if entity_type and entity not in false_named_entities:
            custom_found.append((entity, entity_type))

    return custom_found


def extract_entities(text: str) -> list:
    """
    Возвращает список именованных сущностей текста:
    [(текст сущности, тип), ...].
    Каждое упоминание считается отдельно.
    """
    processed_text = _mark_custom_entities(text)

    # Сначала то, что нашла модель, потом то, что добавлено вручную.
    return _find_with_model(processed_text) + _find_custom(processed_text)


DEMO_TEXT = """
В.С. Садовников – автор многочисленных акварельных видов Петербурга времен Пушкина, Гоголя, Достоевского. Поэтическое восприятие города художник всегда сочетал с документальной точностью в изображениях архитектурных памятников. При этом он передавал впечатление живой жизни города, рисуя гуляющих людей разных сословий, мчащиеся по улице кареты. Акварели художника пользовались успехом, и, несмотря на свое положение крепостного, уже в 1820-е годы Садовников был хорошо известен. В 1838 году, после смерти своей владелицы княгини Н.П. Голицыной, послужившей прообразом старой графини в романе А.С. Пушкина, он получил вольную, и в том же году – звание свободного художника.
В течение всей жизни акварелист исполнял многочисленные заказы императорского двора. Он создавал разные виды Санкт-Петербурга по случаю коронации, бракосочетаний, рождения наследников, выездов и парадов. К ним относится и акварель с видом Мариинского дворца. Дворец был свадебным подарком по случаю бракосочетания дочери Николая I Марии Николаевны с герцогом Максимилианом Лейхтенбергским. Проект и строительство дворца император поручил любимому архитектору А.А. Штакеншнейдеру. Великолепное здание было построено в 1839–1844 годах и считается его лучшим творением.
"""


# ──────────────────────────────────────────────────────────────
# Запуск из командной строки: показываем каждый шаг поиска.
# ──────────────────────────────────────────────────────────────

def _print_entities(entities: list, limit: int = 50):
    """Печатает таблицу «сущность — тип»; не больше limit строк."""
    if not entities:
        print("   (ничего не найдено)")
        return
    print(f"   {'Сущность':<45}{'Тип'}")
    for entity, entity_type in entities[:limit]:
        print(f"   {entity:<45}{entity_type}")
    if len(entities) > limit:
        print(f"   ... и ещё {len(entities) - limit}")


if __name__ == "__main__":
    name, text = text_from_command_line_or_file(DEMO_TEXT)

    print_title(f"ИМЕНОВАННЫЕ СУЩНОСТИ ({name})")

    # Что из ручного списка есть в тексте
    processed_text = _mark_custom_entities(text)

    # Ищем сущности
    model_entities = _find_with_model(processed_text)


    print(f"\n   Найдено моделью: {len(model_entities)}\n")
    _print_entities(model_entities)
    #
    # # Шаг 4. Что добавлено вручную
    # custom_entities = _find_custom(processed_text)
    #
    # print("\n" + "-" * 70)
    # print("СУЩНОСТИ ИЗ РУЧНОГО СПИСКА (CUSTOM_NAMED_ENTITIES)")
    # print("-" * 70)
    # marked = re.findall(r"\[([^\]]+)\]", processed_text)
    # print(f"Найдено в тексте и взято в скобки: {len(marked)}")
    # for entity in marked:
    #     print(f"   [{entity}]")
    #
    # print("\n" + "-" * 70)
    # print("СУЩНОСТИ, ДОБАВЛЕННЫЕ ВРУЧНУЮ")
    # print("-" * 70)
    #
    # print(f"Добавлено по списку: {len(custom_entities)}")
    # _print_entities(custom_entities)
    #
    # # Итог: то же самое возвращает extract_entities(text)
    # all_entities = model_entities + custom_entities
    #
    # print("\n" + "-" * 70)
    # print("ИТОГ")
    # print("-" * 70)
    # print(f"Всего сущностей: {len(model_entities)} (модель) + "
    #       f"{len(custom_entities)} (вручную) = {len(all_entities)}")
