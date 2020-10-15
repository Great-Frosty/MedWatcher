import sqlite3 as sql
import json
import config


def adapt_list_to_string(lst):
    return ', '.join(lst).encode('utf8')


def convert_string_to_list(string):
    reverse = string.decode('utf8').split(', ')
    return reverse


def add_article(data):
    """Inserts parsed article data and some meta information into the db.
    Data must come in a following format:
    (date, name, journal, url, contents)."""

    date, name, journal, url, contents = data

    conn = sql.connect(config.db_file, detect_types=sql.PARSE_DECLTYPES)
    c = conn.cursor()

    no_errs = True
    try:
        c.execute('''INSERT INTO articles VALUES (?, ?, ?, ?, ?)
                    ''', (date, name, journal, url, contents))
    except sql.IntegrityError:
        print('This url already exists, row insertion skipped.')
        no_errs = False

    conn.commit()
    conn.close()
    return no_errs


def select_by_keywords(keywords, journals=['Lancet']):
    '''Returns a list of rows, that match search criteria. Keywords and
    journals to search must be supplied as lists.'''

    keywords = ' OR '.join(keywords)
    journals = ' OR '.join(journals)

    conn = sql.connect(config.db_file, detect_types=sql.PARSE_DECLTYPES)
    c = conn.cursor()

    c.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS searchable_contents
                USING fts4(name, journal, url, contents)''')

    c.execute('''INSERT
                 INTO searchable_contents
                 SELECT name, journal, url, contents
                 FROM articles''')

    results = c.execute('''SELECT name, url
                       FROM searchable_contents
                       WHERE contents MATCH ?
                       INTERSECT
                       SELECT name, url
                       FROM searchable_contents
                       WHERE journal MATCH ?
                    ''', (keywords, journals))

    output = results.fetchall()

    c.execute('''DELETE FROM searchable_contents''')

    conn.commit()
    conn.close()
    return output


def select_urls(journal):
    '''Minor function used to fetch urls already stored in the database.'''

    conn = sql.connect(config.db_file, detect_types=sql.PARSE_DECLTYPES)
    c = conn.cursor()

    c.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS searchable_urls
                 USING fts4(journal, url)''')

    c.execute('''INSERT OR REPLACE
                 INTO searchable_urls
                 SELECT journal, url
                 FROM articles''')

    results = c.execute('''SELECT url
                           FROM searchable_urls
                           WHERE journal MATCH ?
                           ''', (journal,))

    output = results.fetchall()
    output = [row[0] for row in output]

    c.execute('''DELETE
                 FROM searchable_urls''')

    conn.commit()
    conn.close()
    return output


sql.register_adapter(list, adapt_list_to_string)
sql.register_converter('list', convert_string_to_list)

if __name__ == "__main__":

    conn = sql.connect(config.db_file, detect_types=sql.PARSE_DECLTYPES)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS articles
    (date text, name text, journal text, url text UNIQUE, contents list)''')

    conn.commit()
    conn.close()
