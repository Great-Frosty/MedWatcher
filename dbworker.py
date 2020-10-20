import sqlite3 as sql
import json
import config


def add_article(data):
    """Inserts parsed article data and some meta information into the db.
    Data must come in a following format:
    (date, name, journal, url, contents)."""

    date, name, journal, url, contents = data

    conn = sql.connect(config.db_file)
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
                USING fts5(name, journal, url, contents)''')

    c.execute('''INSERT
                 INTO searchable_contents
                 SELECT name, journal, url, contents
                 FROM articles''')
    
    # try/except here is a hack. if user uses sqlite commands in his request - 
    # the whole thing crashes. Instead of crashing it - we will simply return 
    # "bad request" message. Huzzah!
    try:
        results = c.execute('''SELECT name, url
                            FROM
                            (SELECT name, url, journal
                                FROM searchable_contents
                                WHERE contents MATCH ?
                                ORDER BY bm25(searchable_contents) DESC
                            )
                            WHERE journal MATCH ?
                        ''', (keywords,journals,))

        output = results.fetchall()
        c.execute('''DELETE FROM searchable_contents''')
        
        conn.commit()
        conn.close()
    except:
        output = []
    return output


def select_urls(journal):
    '''Minor function used to fetch urls already stored in the database.'''

    conn = sql.connect(config.db_file, detect_types=sql.PARSE_DECLTYPES)
    c = conn.cursor()

    c.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS searchable_urls
                 USING fts5(journal, url)''')

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


def set_user_state(user_id, state):
    '''Changes the state of the user in the database.'''

    conn = sql.connect(config.db_file)
    conn.execute('''UPDATE user_data
                    SET state = ?
                    WHERE id = ?''', (state, user_id))
    conn.commit()
    conn.close()


def get_user_state(user_id):
    '''Returns user state by id.'''

    conn = sql.connect(config.db_file)
    selected = conn.execute('''SELECT state
                    FROM user_data
                    WHERE id = ?''', (user_id,))
    state = selected.fetchone()
    conn.commit()
    conn.close()

    # This is a bad thing to do. Needs to be fixed later.
    try:
        return state[0]
    except TypeError:
        add_user(user_id)
        return config.States.S_START.value


def set_user_terms(user_id, keywords, op_type, term):
    '''Inserts user's keywords in the table. Parameter [op_type] should be
    either 'SEARCH' or 'SUB'. Parameter [term] is either 'JOURNALS' or
    'KEYWORDS'.'''

    # This clause is needed to use a single function for several different
    # data insertion operations.
    insertion_column = ''
    if op_type == 'SEARCH':
        insertion_column = f'{term.lower()}_searched'
    elif op_type == 'SUB':
        insertion_column = f'{term.lower()}_subbed'


    conn = sql.connect(config.db_file)
    conn.execute('''UPDATE user_data
                    SET ''' + insertion_column + ''' = ?
                    WHERE id = ?''', (keywords, user_id))

    conn.commit()
    conn.close()


def get_user_keywords(user_id, op_type):
    '''Returns user's keywords.'''

    if op_type == 'SEARCH':
        selected_column = 'keywords_searched'
    elif op_type == 'SUB':
        selected_column = 'keywords_subbed'
    
    conn = sql.connect(config.db_file)
    res = conn.execute('''SELECT ''' + selected_column +
                    ''' FROM user_data
                    WHERE id = ?''', (user_id, ))
    keywords = res.fetchone()
    return keywords[0]


def get_user_journals(user_id, op_type):
    '''Returns user's journals.'''

    if op_type == 'SEARCH':
        selected_column = 'journals_searched'
    elif op_type == 'SUB':
        selected_column = 'journals_subbed'
    
    conn = sql.connect(config.db_file)
    res = conn.execute('''SELECT ''' + selected_column +
                    ''' FROM user_data
                    WHERE id = ?''', (user_id, ))
    keywords = res.fetchone()
    return keywords[0]


def set_mailing_days(user_id, days):

    conn = sql.connect(config.db_file)
    conn.execute('''UPDATE user_data
                    SET days = ?
                    WHERE id = ?''', (days, user_id))
    conn.commit()
    conn.close()


def get_mailing_days(user_id):

    conn = sql.connect(config.db_file)
    res = conn.execute('''SELECT days
                          FROM user_data
                          WHERE id = ?''', (user_id,))
    output = res.fetchone()
    return output


def set_user_delivery_time(user_id, time):

    conn = sql.connect(config.db_file)
    conn.execute('''UPDATE user_data
                    SET time = ?
                    WHERE id = ?''', (time, user_id))
    conn.commit()
    conn.close()


def get_user_delivery_time(user_id):

    conn = sql.connect(config.db_file)
    res = conn.execute('''SELECT time
                    FROM user_data
                    WHERE id = ?''', (user_id,))
    return res


def add_user(user_id):
    '''Adds a new user in the database.'''

    conn = sql.connect(config.db_file)
    conn.execute('''INSERT INTO user_data (id)
                    VALUES(?)''', (user_id,))
    conn.commit()
    conn.close()


def check_if_user_exists(user_id):

    conn = sql.connect(config.db_file)
    result = conn.execute('''SELECT id
                             FROM user_data
                             WHERE id = ?''', (user_id,))
    return bool(result.fetchone())


conn = sql.connect(config.db_file, detect_types=sql.PARSE_DECLTYPES)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS articles
(date text, name text, journal text, url text UNIQUE, contents text)''')

c.execute('''CREATE TABLE IF NOT EXISTS user_data
                        (id text UNIQUE,
                        journals_searched text,
                        keywords_searched text,
                        journals_subbed text,
                        keywords_subbed text,
                        days text,
                        time text,
                        state text)''')

conn.commit()
conn.close()
#TODO: add scheduling functionality