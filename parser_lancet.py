import re
import os
import requests
import pandas as pd
from bs4 import BeautifulSoup


def check_updates(existing, parse_limit=None):
    '''Goes through the list of articles at a given url, parses and adds new
    articles to storage. Returns a DataFrame.'''

    url = r'https://www.thelancet.com/online-first-research'
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'lxml')

    # Next cycle checks if article is already in storage, parses it if not.
    for art in soup.find_all('div', class_='article-details')[:parse_limit]:
        text_url = art.find(href=re.compile(r'fulltext'))['href']
        full_text_url = f'https://www.thelancet.com{text_url}'

        if full_text_url not in existing['url'].values:
            data = parse_article(full_text_url)
            existing = existing.append(data, ignore_index=True)
        else:
            print('We already have this article in storage.')

    return existing


def parse_article(url):
    '''Goes to a given article url, retrieves all the required info, returns it
    as pandas DataFrame.'''

    print(f'Parsing {url}')
    article_page = requests.get(url)
    article_soup = BeautifulSoup(article_page.text, 'lxml')

    # Got article name.
    article_name = article_soup.h1.text

    # Got publishing date.
    article_date = article_soup.find(
        'span',
        class_="article-header__publish-date__value"
        ).text

    # Following lines convert article paragraphs to a set of unique words.
    paragraphs = article_soup.find_all('div', class_='section-paragraph')
    sections = [section.text for section in paragraphs]

    # We only keep a part of the article located before References,
    # we don't want words from References checked for keywords.
    entire_text = '\n'.join(sections).split('References')[0]
    words = re.split(re.compile(r'\s'), entire_text)

    # All words are converted to lowercase,
    # words containing numbers are discarded.
    # Again, reasoning is rather self-explanatory.
    words_filtered = [word.lower() for word in words if word.isalpha()]
    article_contents = list(set(words_filtered))

    formatted_data = {
        'name': article_name,
        'date': article_date,
        'url': url,
        'contents': article_contents
    }

    return formatted_data


# def is_non_zero_file(fpath):
#     '''Checks if the specified file exists and is not empty.'''

#     return os.path.isfile(fpath) and os.path.getsize(fpath) > 0

# Probably we don't need this one. check_for_updates can look at all existing
# ulrs, and parse ones that are not in the database. 
def parse():
    pass

    # if is_non_zero_file('article_storage.json'):
    #     with open('article_storage.json', 'r') as file:
    #         existing_articles = pd.read_json(file, convert_dates=False)
    #     print('Storage successfully read!')
    # else:
    #     print('Article storage is empty.')
    #     columns = ['name', 'date', 'url', 'contents']
    #     existing_articles = pd.DataFrame(columns=columns)

    # existing_articles = check_updates(existing_articles)

    # with open('article_storage.json', 'w') as file:
    #     existing_articles.to_json(file, orient='columns', date_format=None)


if __name__ == "__main__":
    parse()
