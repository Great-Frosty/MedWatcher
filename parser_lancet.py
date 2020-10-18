import re
import os
import requests
import dbworker
import pandas as pd
from bs4 import BeautifulSoup


def check_updates(parse_limit=None):
    '''Goes through the list of articles at a given url, parses and adds new
    articles to storage. Returns a DataFrame.'''

    url = r'https://www.thelancet.com/online-first-research'
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'lxml')

    existing_urls = dbworker.select_urls('Lancet')

    # Next cycle checks if article is already in storage, parses it if not.
    for art in soup.find_all('div', class_='article-details')[:parse_limit]:
        text_url = art.find(href=re.compile(r'fulltext'))['href']
        full_text_url = f'https://www.thelancet.com{text_url}'

        if full_text_url not in existing_urls:
            data = parse_article(full_text_url)
            dbworker.add_article(data)
            print(f'Added {data[3]} to database!')
        else:
            print('we\'re fine with this article!')

    return None


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
    words_filtered = [word.lower() for word in words if word.isalnum()]
    # article_contents = list(set(words_filtered))
    article_contents = words_filtered

    formatted_data = (
        article_date,
        article_name,
        'Lancet',
        url,
        article_contents
    )
    return formatted_data


if __name__ == "__main__":
    check_updates()
