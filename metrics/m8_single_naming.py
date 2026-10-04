# -*- coding: utf-8 -*-
"""
МЕТРИКА 8. Единичное именование (single naming).

Идея: какая доля именованных сущностей текста состоит из одного слова
(«Фуко», а не «Мишель Фуко»).

Как считается:
  1) в тексте находятся именованные сущности (модуль entities.py);
  2) у каждой сущности считаются слова, разделённые пробелом;
  3) число однословных сущностей делится на число всех сущностей
     и умножается на 100.

«Одно слово» здесь значит «без пробелов»: «Санкт-Петербург» — одно слово,
«А. В. Иванов» — три.

Запуск (из корневой папки проекта translationese_metrics):
    python metrics/m8_single_naming.py                   (учебный пример)
    python metrics/m8_single_naming.py texts/text_1.txt  (свой текст)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.common import text_from_command_line_or_file, print_title
from utils.entities import extract_entities, DEMO_TEXT

def single_naming_frequency(entities: list) -> float:
    """
    :param entities: список сущностей [(текст, тип), ...]
    :return: доля однословных сущностей, в процентах
    """
    entities_count = len(entities)
    single_entities_count = 0

    for entity, entity_type in entities:
        if len(entity.split()) == 1:
            single_entities_count += 1

    if entities_count > 0:
        return round(single_entities_count / entities_count * 100, 3)
    return 0.0


def single_naming(text: str) -> float:
    """Единичное именование для текста (в процентах)."""
    return single_naming_frequency(extract_entities(text))


if __name__ == "__main__":
    name, text = text_from_command_line_or_file(DEMO_TEXT)
    print_title(f"МЕТРИКА 8. ЕДИНИЧНОЕ ИМЕНОВАНИЕ ({name})")

    found = extract_entities(text)
    single = [entity for entity, _ in found if len(entity.split()) == 1]

    print(f"\nСущности ({len(found)}), первые 30:")
    for entity, entity_type in found[:30]:
        words = len(entity.split())
        print(f"   {entity:<40} {entity_type:<6} слов: {words}")

    value = single_naming_frequency(found)
    if found:
        print(f"\nЕдиничное именование = {len(single)} / {len(found)} "
              f"× 100 = {value} %")
    else:
        print("\nСущностей в тексте нет.")
