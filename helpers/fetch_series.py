import datetime
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import re
from connectors import database
import logging

logger = logging.getLogger(__name__)


def fetch_series(host_url, series_name, series_id, year, overview):
    # Search for the series on the website
    logger.info(f"Fetching series names for: {series_name}")
    search_url = f'{host_url}/?s={quote_plus(series_name)}'
    r = requests.get(search_url)
    soup = BeautifulSoup(r.text, 'html.parser')

    # Find the total number of pages
    page_numbers = soup.find_all('a', class_='page-numbers')
    if page_numbers:
        max_page = max(int(a.text) for a in page_numbers if a.text.isdigit())
    else:
        max_page = 1
    logger.info(f"Total number of pages found: {max_page}")

    # Find all series titles, seasons, episodes, and links
    series = []
    for page in range(1, max_page + 1):
        page_url = f'{host_url}/page/{page}/?s={quote_plus(series_name)}'
        r = requests.get(page_url)
        soup = BeautifulSoup(r.text, 'html.parser')

        for h2 in soup.find_all('h2', class_='entry-title'):
            a = h2.find('a', href=True)
            text = a.text
            match = re.search(r'\[S(\d{1,2})\s*:?\s*E(\d{1,2})', text)
            if match and series_name.lower() in text.lower():
                # This is a series, add it to the list
                title = text[:match.end()].strip()
                search_title = title.split(' [')[0].split(' (')[0].strip()
                season = match.group(1).zfill(2)
                episode = match.group(2)
                link = a['href']
                series.append((title, season, episode, link))
                logger.info(f"Added series to the list: {title}, Season: {season}, Episode: {episode}")
                database.insert_tv_details(series_id, search_title, year, season, episode, link, overview,
                                           datetime.datetime.now().isoformat())
                logger.info(
                    f"Inserted series details into the database: {search_title}, Year: {year}, Season: {season}, "
                    f"Episode: {episode}")
    logger.info(f"Returning list of series: {series}")
    return series
