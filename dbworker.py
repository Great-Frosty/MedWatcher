import sqlite3
import json


def adapt_list_to_json(lst):
    return json.dumps(lst).encode('utf8')


def convert_json_to_list(data):
    return json.loads(data.decode('utf8'))


sqlite3.register_adapter(list, adapt_list_to_json)
sqlite3.register_converter('json', convert_json_to_list)

conn = sqlite3.connect('example.db')


def add_article(data, journal):
    pass


def select_by_keywords(keywords, journals):
    pass

def select_urls(journal):
    pass

# TODO: Оч. просто. Парсим сайт, кладем статьи по одной в базу. до начала
# парсинга вытаскиваем все урлы, парсим только те, которых нет в бд.
# При запросе либо по расписанию, либо от команды /search, дергаем
# select_by_keywords. ??? PROFIT