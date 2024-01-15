import requests
from bs4 import BeautifulSoup
import zipfile
import os
import telebot
from urllib.parse import urljoin, urlparse, unquote, quote_plus
import re
import db
import shutil
from telebot import types
from dotenv import load_dotenv
import rarfile
import logging

from helpers.zip_helper import download_extract_zip

load_dotenv()

TOKEN = os.getenv('TOKEN')
TMDB_API_KEY = os.getenv('TMDB_API_KEY')
HOST_URL = os.getenv('HOST_URL')

bot = telebot.TeleBot(TOKEN)

db.create_table_movie()
db.create_table_tv()

# Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create a file handler
handler = logging.FileHandler('bot.log')
handler.setLevel(logging.INFO)

# Create a stream handler (this will print logs to the terminal)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)

# Create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)  # use the same formatter for the stream handler

# Add the handlers to the logger
logger.addHandler(handler)
logger.addHandler(stream_handler)  # add the stream handler to the logger


@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_message = "👋 *Welcome to the Sinhala Subtitle Download Bot!* 🎬\n\n"
    welcome_message += ("I'm here to help you find and download Sinhala subtitles for your favorite movies. Here's "
                        "what I can do:\n\n")
    welcome_message += ("1. **Search for Movies**: You can search for a movie by its name, and I'll find the Sinhala "
                        "subtitles for it. To do this, use the `/search` command followed by the movie name. For "
                        "example, `/search Titanic`.\n\n")
    welcome_message += ("*Disclaimer*: _This bot merely provides a means to share subtitles found on the internet. "
                        "All subtitles shared by this bot are the property of their respective owners. Any credits and "
                        "intellectual property rights associated with the subtitles belong solely to the original "
                        "owners. This bot does not claim any ownership or responsibility for the subtitles shared._")
    bot.reply_to(message, welcome_message, parse_mode='Markdown')


@bot.message_handler(commands=['movie'])
def search_movie(message):
    msg = bot.send_message(message.chat.id, "🔍 Searching....")
    # Check if the command is exactly '/search'
    if message.text.strip() == '/movie':
        bot.edit_message_text("Please provide a movie name. For example, `/search Titanic`.", msg.chat.id,
                              msg.message_id)
        return

    # Get the movie name from the message
    movie_name = message.text.split('/movie ', 1)[1].strip()

    # Search for the movie on the website
    search_url = f'{HOST_URL}/?s={quote_plus(movie_name)}'
    r = requests.get(search_url)
    soup = BeautifulSoup(r.text, 'html.parser')

    # Find all movie titles and links
    movies = []
    for h2 in soup.find_all('h2', class_='entry-title'):
        if len(movies) >= 5:  # Stop after finding 5 movies
            break
        a = h2.find('a', href=True)
        text = a.text
        match = re.search(r'\(\d{4}\)', text)
        if match:
            # This is a movie, add it to the list
            title = text[:match.end()].strip()
            search_title = title.split(' (')[0].strip()
            link = a['href']

            # get the movie details
            tmdb_url = f'https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={search_title}'
            tmdb_response = requests.get(tmdb_url).json()

            if tmdb_response['results']:
                movie_data = tmdb_response['results'][0]
                movies.append((title, link, movie_data))

    if not movies:
        bot.edit_message_text("I'm sorry, but I couldn't find any movies matching your search.", msg.chat.id,
                              msg.message_id)
        return

    movie_message = ""

    for title, link, movie_data in movies:
        movie_id = movie_data['id']
        title = movie_data['title']
        overview = movie_data['overview']
        year = re.search(r'\d{4}', movie_data['release_date']).group()
        db.insert_details(movie_id, title, year, link, overview)

        movie_message += f"🎬 *{title}* ({year})\n"
        movie_message += f"_Download:_ /dl\_{movie_id}\n\n"

        # Send the message
    bot.edit_message_text(movie_message, msg.chat.id, msg.message_id, parse_mode='Markdown')


@bot.message_handler(regexp='^/dl')
def download_subtitle(message):
    movie_id = message.text.split('/dl_', 1)[1].strip()
    link = db.get_link(movie_id)
    if link is None:
        bot.reply_to(message, "This command is incorrect. Please provide a valid command.")
        return
    chat_dir = f'subtitles/movies/{movie_id}'

    msg = bot.send_message(message.chat.id, "⏫ Uploading the subtitles...")

    # check if directory exists
    if os.path.isdir(chat_dir):
        # Send all .srt files
        for file in os.listdir(chat_dir):
            if file.endswith('.srt'):
                with open(os.path.join(chat_dir, file), 'rb') as f:
                    bot.send_document(message.chat.id, f)
        bot.edit_message_text("✅ Subtitle Uploaded", msg.chat.id, msg.message_id, parse_mode='Markdown')
    else:
        bot.edit_message_text("⏳ Almost Done...", msg.chat.id, msg.message_id, parse_mode='Markdown')
        r = requests.get(link)
        soup = BeautifulSoup(r.text, 'html.parser')

        # Find the zip file link
        for a in soup.find_all('a', href=True):
            if '/?tmstv=' in a['href']:
                zip_url = urljoin(link, a['href'])
                break

        # Create a unique directory for this chat
        os.makedirs(chat_dir, exist_ok=True)

        download_extract_zip(link, chat_dir, bot, msg)

        # Send all .srt files
        for file in os.listdir(chat_dir):
            if file.endswith('.srt'):
                with open(os.path.join(chat_dir, file), 'rb') as f:
                    bot.send_document(message.chat.id, f)
        bot.edit_message_text("✅ Subtitle Uploaded", msg.chat.id, msg.message_id, parse_mode='Markdown')


@bot.message_handler(commands=['tv'])
def search_tv(message):
    msg = bot.send_message(message.chat.id, "🔍 Searching for the subtitles...")
    # Check if the command is exactly '/tv'
    if message.text.strip() == '/tv':
        bot.edit_message_text("Please provide a tv series name. For example, `/search breaking bad`.", msg.chat.id,
                              msg.message_id)
        return

    # Get the series name from the message
    series_name = message.text.split('/tv ', 1)[1].strip()

    # Get series details
    tmdb_url = f'https://api.themoviedb.org/3/search/tv?api_key={TMDB_API_KEY}&query={quote_plus(series_name)}'
    tmdb_response = requests.get(tmdb_url).json()
    if tmdb_response['results']:
        series_data = tmdb_response['results'][0]
        series_id = series_data['id']
        year = re.search(r'\d{4}', series_data['first_air_date']).group()
    else:
        bot.edit_message_text("I'm sorry, but I couldn't find any series matching your search.", msg.chat.id,
                              msg.message_id)
        return

    results = db.check_series_available(series_id)

    if results:
        tv_message = ""
        # Create a message with a keyboard of seasons
        seasons = sorted(set(season for series_name, year, season, episode, link in results))
        keyboard = types.InlineKeyboardMarkup()
        tv_message += f"🎬 *{series_data['name']}* ({year})\n\n"
        tv_message += f"{series_data['overview']}\n\n"
        tv_message += f"Please select a season:"
        for season in seasons:
            button = types.InlineKeyboardButton(text=f"Season {season}",
                                                callback_data=f"series_{series_id}_season_{season}")
            keyboard.add(button)
        bot.send_photo(msg.chat.id, f"https://image.tmdb.org/t/p/original{series_data['poster_path']}",
                       caption=tv_message, reply_markup=keyboard, parse_mode='Markdown')
        bot.delete_message(msg.chat.id, msg.message_id, timeout=None)
    else:
        # Search for the series on the website
        search_url = f'{HOST_URL}/?s={quote_plus(series_name)}'
        r = requests.get(search_url)
        soup = BeautifulSoup(r.text, 'html.parser')

        # Find the total number of pages
        page_numbers = soup.find_all('a', class_='page-numbers')
        max_page = max(int(a.text) for a in page_numbers if a.text.isdigit())

        # Find all series titles, seasons, episodes, and links
        series = []
        for page in range(1, max_page + 1):
            page_url = f'{HOST_URL}/page/{page}/?s={quote_plus(series_name)}'
            r = requests.get(page_url)
            soup = BeautifulSoup(r.text, 'html.parser')

            for h2 in soup.find_all('h2', class_='entry-title'):
                a = h2.find('a', href=True)
                text = a.text
                match = re.search(r'\[S(\d{2}) : E(\d{2})\]', text)
                if match and series_name.lower() in text.lower():
                    # This is a series, add it to the list
                    title = text[:match.end()].strip()
                    search_title = title.split(' [')[0].strip()
                    season = match.group(1)
                    episode = match.group(2)
                    link = a['href']
                    series.append((title, season, episode, link))
                    db.insert_tv_details(series_id, search_title, year, season, episode, link, series_data['overview'])

        if not series:
            bot.edit_message_text("I'm sorry, but I couldn't find any series matching your search.", msg.chat.id,
                                  msg.message_id)
            return

        tv_message = ""
        # Create a message with a keyboard of seasons
        seasons = sorted(set(season for title, season, episode, link in series))
        keyboard = types.InlineKeyboardMarkup()
        tv_message += f"🎬 *{series_data['name']}* ({year})\n\n"
        tv_message += f"{series_data['overview']}\n\n"
        tv_message += f"Please select a season:"
        for season in seasons:
            button = types.InlineKeyboardButton(text=f"Season {season}",
                                                callback_data=f"series_{series_id}_season_{season}")
            keyboard.add(button)
        bot.send_photo(msg.chat.id, f"https://image.tmdb.org/t/p/original{series_data['poster_path']}",
                       caption=tv_message, reply_markup=keyboard, parse_mode='Markdown')
        bot.delete_message(msg.chat.id, msg.message_id, timeout=None)


@bot.callback_query_handler(func=lambda call: call.data.startswith('series_'))
def handle_season_button(call):
    # Extract the series ID and season number from the callback data
    _, series_id, _, season = call.data.split('_')
    series_id = int(series_id)
    season = int(season)

    logger.info(f"Handling season button for series_id {series_id} and season {season}")
    msg = bot.send_message(call.message.chat.id, "🔍 Searching for the subtitles...")

    # Define the directory of the season
    season_dir = f'subtitles/series/{series_id}/{season}'

    # Retrieve the episode numbers and links from the database
    episodes = db.get_series_links(series_id, season)

    # Check if the season directory exists
    if not os.path.isdir(season_dir):
        # Download all subtitles and save them
        for season, episode, link in episodes:
            chat_dir = f'subtitles/series/{series_id}/{season}/{episode}'
            os.makedirs(chat_dir, exist_ok=True)

            # download & extract zip
            download_extract_zip(link, chat_dir, bot, msg)
    else:
        logger.info(f"Subtitles for series_id {series_id} and season {season} already exist")
    # Create a message with a keyboard of episodes
    keyboard = types.InlineKeyboardMarkup()
    row = []
    for season, episode, link in episodes:
        # Check if subtitles exist for the episode
        subtitle_exists = os.path.isdir(f'subtitles/series/{series_id}/{season}/{episode}')
        # Add a check or uncheck emoji based on whether subtitles exist
        episode_text = f"✅ {episode}" if subtitle_exists else f"❌ {episode}"
        callback_data = f"episode_{episode}_season_{season}_series_id_{series_id}"
        button = types.InlineKeyboardButton(text=episode_text, callback_data=callback_data)
        row.append(button)
        if len(row) == 4:
            keyboard.row(*row)
            row = []
    if row:
        keyboard.row(*row)
    download_all_button = types.InlineKeyboardButton(text="Download All",
                                                     callback_data=f"zip_{series_id}_season_{season}")
    keyboard.row(download_all_button)
    message_season = f"Download Subtitles: Season {season}"
    bot.edit_message_text(message_season, msg.chat.id, msg.message_id, reply_markup=keyboard)

    logger.info(f"Sent message for series_id {series_id} and season {season}")


@bot.callback_query_handler(func=lambda call: call.data.startswith('episode_'))
def download_subtitle(call):
    # Extract the series ID, season number, and episode number from the callback data
    _, episode, _, season, _, series_id = call.data.split('_', 5)
    series_id = int(series_id.split('_')[1])
    season = int(season)
    episode = int(episode)

    logger.info(f"Uploading subtitles for series_id {series_id}, season {season}, episode {episode}")

    msg = bot.send_message(call.message.chat.id, "⏫ Uploading the subtitles...")

    exists = f'subtitles/series/{series_id}/{season}/{episode}'
    # check if directory exists
    if os.path.isdir(exists):
        for file in os.listdir(exists):
            if file.endswith(('.srt', '.ass', '.ssa', '.vtt', '.stl', '.scc', '.ttml', '.sbv')):
                with open(os.path.join(exists, file), 'rb') as f:
                    bot.send_document(call.message.chat.id, f)
        bot.edit_message_text("✅ Subtitle Uploaded", msg.chat.id, msg.message_id, parse_mode='Markdown')
    else:
        bot.reply_to(call.message, "The subtitles for this episode are not available. Please try another episode.")
        logger.error(f"Subtitles not found for series_id {series_id}, season {season}, episode {episode}")


@bot.callback_query_handler(func=lambda call: call.data.startswith('zip_'))
def zip_download(call):
    # Extract the series ID and season number from the callback data
    _, series_id, _, season = call.data.split('_')
    series_id = int(series_id)
    season = int(season)

    logger.info(f"Downloading & Compressing subtitles for series_id {series_id} and season {season}")

    msg = bot.send_message(call.message.chat.id, "🗜️ Compressing the subtitles...")

    # Get the series name from the database
    series_name = db.get_series_name(series_id)

    # Define the directory of the season
    season_dir = f'subtitles/series/{series_id}/{season}'

    # Define the zip file name
    zip_file_name = os.path.join(season_dir, f'{series_name} - Season {season}.zip')

    # Check if the zip file already exists
    if not os.path.exists(zip_file_name):
        # Create a ZipFile object in write mode
        with zipfile.ZipFile(zip_file_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Walk the directory tree and add files to the ZipFile object
            for root, dirs, files in os.walk(season_dir):
                for file in files:
                    # Skip .zip files
                    if not file.endswith('.zip'):
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, arcname=os.path.relpath(file_path, start=season_dir))

    # Send the zip file to the user
    with open(zip_file_name, 'rb') as zipf:
        bot.send_document(call.message.chat.id, zipf)
    bot.edit_message_text(f'✅ {series_name} - Season {season} zip file uploaded', msg.chat.id, msg.message_id,
                          parse_mode='Markdown')

    logger.info(f'Sent zip file for series_id {series_id} and season {season}')


bot.polling()
