import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import re
import logging

logger = logging.getLogger(__name__)


def fetch_series_names(host_url, series_name):
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

    # Find all series titles
    series_names = set()
    for page in range(1, max_page + 1):
        if len(series_names) >= 5:
            logger.info("Found 5 series. Breaking the loop.")
            break  # Break the loop if we have found 5 series
        page_url = f'{host_url}/page/{page}/?s={quote_plus(series_name)}'
        r = requests.get(page_url)
        soup = BeautifulSoup(r.text, 'html.parser')

        for h2 in soup.find_all('h2', class_='entry-title'):
            cat_links = h2.find_next('span', class_='cat-links')
            if cat_links is not None:  # Add this line
                a_tags = cat_links.find_all('a')
                if any('TV' in a.text for a in a_tags):
                    a = h2.find('a', href=True)
                    text = a.text
                    match = re.search(r'\[S(\d{1,2})\s*:?\s*E(\d{1,2})', text)
                    if match:
                        # This is a series, add it to the list
                        title = text.split(' [')[0].split(' (')[0].strip()
                        series_names.add(title)
                        logger.info(f"Added series to the list: {title}")
    logger.info(f"Returning list of series names: {list(series_names)}")
    return list(series_names)
