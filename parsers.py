import requests
from bs4 import BeautifulSoup
import re
import pandas as pd


def check_updates(existing, parse_limit=None):
    '''Goes through the list of articles at a given url, parses and adds new
    articles to storage.'''

    url = r'https://www.thelancet.com/online-first-research'
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'lxml')

    for article in soup.find_all('div', class_='article-details')[:parse_limit]:
        text_url = article.find(href=re.compile(r'fulltext'))['href']
        full_text_url = f'https://www.thelancet.com{text_url}'

        if full_text_url not in existing['url'].values:
            data = parse_article(full_text_url)
            existing = existing.append(data, ignore_index=True)
        else:
            print('We already have this article in storage')

    return existing


def parse_article(url):
    '''Goes to a given article url, retrieves all the required info, returns it
    as a pandas DataFrame.'''

    print(f'Parsing {url}')
    article_body = requests.get(url)
    article_soup = BeautifulSoup(article_body.text, 'lxml')

    article_name = article_soup.h1.text
    article_date = article_soup.find('span', class_="article-header__publish-date__value").text
    sections_text = [section.text for section in article_soup.find_all('div', class_='section-paragraph')]
    article_text = '\n'.join(sections_text).split('References')[0]
    article_contents = list(set([word.lower() for word in re.split(re.compile(r'\s'), article_text) if word.isalpha()]))

    formatted_data = {
        'name': article_name,
        'date': article_date,
        'url': url,
        'contents': article_contents
    }

    return formatted_data


with open('article_storage.json', 'r') as file:

    try:
        existing_articles = pd.read_json(file, orient='columns', convert_dates=False)
        print('Storage successfully read!')
    except ValueError:
        print(f'Articles are empty')
        columns = ['name', 'date', 'url', 'contents']
        existing_articles = pd.DataFrame(columns=columns)
        
    existing_articles = check_updates(existing_articles)

with open('article_storage.json', 'w') as file:
    existing_articles.to_json(file, orient='columns', date_format=None)
