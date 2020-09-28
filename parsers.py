import requests
from bs4 import BeautifulSoup
import re
from collections import deque


url = r'https://www.thelancet.com/online-first-research'

r = requests.get(url)

soup = BeautifulSoup(r.text, 'lxml')

keywords = ['human', 'oocyte']
relevant = []
all_articles = deque(maxlen=800)

for article in soup.find_all('div', class_='article-details'):
    text_url = article.find(href=re.compile(r'fulltext'))['href']
    full_text_url = f'https://www.thelancet.com{text_url}'

    # article_body = requests.get(full_text_url)
    # article_soup = BeautifulSoup(article_body.text, 'lxml')


    if full_text_url not in all_articles:
        all_articles.append(full_text_url)

print(*all_articles, sep='\n')

    # Заходим в каждой статье по кнопке Full-Text HTML, ищем ключевые слова
    # article_body = requests.get(full_text_url)
    # article_soup = BeautifulSoup(article_body.text, 'lxml')

    # for section in article_soup.find_all('div', class_='section-paragraph'):
    #     for keyword in keywords:
    #         if keyword in section.text:
    #             if full_text_url not in relevant:
    #                 print(f'added an article\n{full_text_url}\nto relevant! Keyword = {keyword}')
    #                 relevant.append(full_text_url)
    #                 break

