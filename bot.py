import requests
from bs4 import BeautifulSoup
import zipfile
import os
import telebot
from urllib.parse import quote_plus
import re
from telebot import types
import datetime
from config import config, logging
from connectors import database
from helpers.fetch_series import fetch_series
from helpers.fetch_series_names import fetch_series_names
from helpers.zip_helper import download_extract_zip
from config.logging import logger

bot = telebot.TeleBot(config.TOKEN)
logging.set_bot(bot)
database.create_table_movie()
database.create_table_tv()


@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_message = "👋 *Welcome to the Sinhala Subtitle Download Bot!* 🎬\n\n"
    welcome_message += ("I'm here to help you find and download Sinhala subtitles for your favorite movies. Here's "
                        "what I can do:\n\n")
    welcome_message += ("1. 🎥 **Search for Movies**: You can search for a movie by its name, and I'll find the "
                        "Sinhala subtitles for it. To do this, use the `/movie` command followed by the movie name. "
                        "For example, `/movie Titanic`.\n\n")
    welcome_message += ("2. 📺 **Search for TV Series**: You can search for a tv series by its name, and I'll find the "
                        "Sinhala subtitles for it. To do this, use the `/tv` command followed by the series name. For "
                        "example, `/tv Breaking Bad`.\n\n")
    welcome_message += ("*Disclaimer*: _This bot merely provides a means to share subtitles found on the internet. All "
                        "subtitles shared by this bot are the property of their respective owners. Any credits and "
                        "intellectual property rights associated with the subtitles belong solely to the original "
                        "owners. This bot does not claim any ownership or responsibility for the subtitles shared._ 📝")
    photo = open('images/icon.jpg', 'rb')
    bot.send_photo(message.chat.id, photo, caption=welcome_message, parse_mode='Markdown')


@bot.message_handler(commands=['movie'])
def search_movie(message):
    logger.info("Received a request to search for a movie.")
    msg = bot.send_message(message.chat.id, "🔍 Searching....")
    # Check if the command is exactly '/movie'
    if message.text.strip() == '/movie':
        logger.info("No movie name provided. Requesting movie name.")
        bot.edit_message_text("Please provide a movie name. For example, `/movie Titanic`.", msg.chat.id,
                              msg.message_id)
        return

    # Get the movie name from the message
    movie_name = message.text.split('/movie ', 1)[1].strip()

    # Search for the movie on the website
    search_url = f'{config.HOST_URL}/?s={quote_plus(movie_name)}'
    r = requests.get(search_url)
    soup = BeautifulSoup(r.text, 'html.parser')

    # Find all movie titles and links
    movies = []
    for h2 in soup.find_all('h2', class_='entry-title'):
        if len(movies) >= 5:  # Stop after finding 5 movies
            logger.info("Found 5 movies. Breaking the loop.")
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
            tmdb_url = f'https://api.themoviedb.org/3/search/movie?api_key={config.TMDB_API_KEY}&query={search_title}'
            tmdb_response = requests.get(tmdb_url).json()

            if tmdb_response['results']:
                movie_data = tmdb_response['results'][0]
                movies.append((title, link, movie_data))
                logger.info(f"Added movie to the list: {title}")

    if not movies:
        logger.info("No movies found matching the search.")
        bot.edit_message_text("I'm sorry, but I couldn't find any movies matching your search.", msg.chat.id,
                              msg.message_id)
        return

    movie_message = ""

    for title, link, movie_data in movies:
        movie_id = movie_data['id']
        title = movie_data['title']
        overview = movie_data['overview']
        year = re.search(r'\d{4}', movie_data['release_date']).group()
        database.insert_details(movie_id, title, year, link, overview)
        logger.info(f"Inserted movie details into the database: {title}, Year: {year}")
        movie_message += f"🎬 *{title}* ({year})\n"
        movie_message += f"_Download:_ /dl\_{movie_id}\n\n"
        # Send the message
    logger.info("Sending the message with the found movies.")
    bot.edit_message_text(movie_message, msg.chat.id, msg.message_id, parse_mode='Markdown')


@bot.message_handler(regexp='^/dl')
def download_subtitle(message):
    logger.info("Received a request to download subtitles.")
    movie_id = message.text.split('/dl_', 1)[1].strip()
    link = database.get_link(movie_id)
    if link is None:
        logger.error("Invalid command. No link found for the provided movie ID.")
        bot.reply_to(message, "This command is incorrect. Please provide a valid command.")
        return
    chat_dir = f'subtitles/movies/{movie_id}'

    msg = bot.send_message(message.chat.id, "⏫ Uploading the subtitles...")

    # check if directory exists
    if os.path.isdir(chat_dir):
        logger.info("Directory exists. Sending all .srt files.")
        # Send all .srt files
        for file in os.listdir(chat_dir):
            if file.endswith('.srt'):
                with open(os.path.join(chat_dir, file), 'rb') as f:
                    bot.send_document(message.chat.id, f)
        bot.edit_message_text("✅ Subtitle Uploaded", msg.chat.id, msg.message_id, parse_mode='Markdown')
    else:
        logger.info("Directory does not exist. Creating directory and downloading subtitles.")
        bot.edit_message_text("⏳ Almost Done...", msg.chat.id, msg.message_id, parse_mode='Markdown')

        # Create a unique directory for this chat
        os.makedirs(chat_dir, exist_ok=True)

        download_extract_zip(link, chat_dir, bot, msg)

        # Send all .srt files
        for file in os.listdir(chat_dir):
            if file.endswith(('.srt', '.ass', '.ssa', '.vtt', '.stl', '.scc', '.ttml', '.sbv', '.idx', '.sub')):
                with open(os.path.join(chat_dir, file), 'rb') as f:
                    bot.send_document(message.chat.id, f)
        bot.edit_message_text("✅ Subtitle Uploaded", msg.chat.id, msg.message_id, parse_mode='Markdown')


@bot.message_handler(commands=['tv'])
def search_tv(message):
    logger.info("Received a request to search for a TV series.")
    msg = bot.send_message(message.chat.id, "🔍 Searching for the tv series...")
    # Check if the command is exactly '/tv'
    if message.text.strip() == '/tv':
        logger.info("No series name provided. Requesting series name.")
        bot.edit_message_text("Please provide a tv series name. For example, `/tv breaking bad`.", msg.chat.id,
                              msg.message_id)
        return

    # Get the series name from the message
    series_name = message.text.split('/tv ', 1)[1].strip()
    logger.info(f"Series name: {series_name}")
    # Fetch series names from your website
    series_names = fetch_series_names(config.HOST_URL, series_name)

    if not series_names:
        logger.info("No series found matching the search.")
        bot.edit_message_text("I'm sorry, but I couldn't find any series matching your search", msg.chat.id,
                              msg.message_id)
        return

    tv_message = ""

    for name in series_names:
        # Get series details from TMDB
        tmdb_url = f'https://api.themoviedb.org/3/search/tv?api_key={config.TMDB_API_KEY}&query={quote_plus(name)}'
        tmdb_response = requests.get(tmdb_url).json()

        if tmdb_response['results']:
            series_data = tmdb_response['results'][0]
            series_id = series_data['id']

            year = re.search(r'\d{4}', series_data['first_air_date']).group()
            logger.info(f"Found series: {series_data['name']} ({year})")
            tv_message += f"🎬 *{series_data['name']}* ({year})\n"
            tv_message += f"_Select:_ /s\_{series_id}\n\n"

    # Send the message
    logger.info("Sending the message with the found series.")
    bot.edit_message_text(tv_message, msg.chat.id, msg.message_id, parse_mode='Markdown')


@bot.message_handler(regexp='^/s')
def download_subtitle(message):
    logger.info("Received a request to download subtitles.")
    msg = bot.send_message(message.chat.id, "🔍 Searching for the subtitles...")
    series_id = message.text.split('/s_', 1)[1].strip()
    logger.info(f"Series ID: {series_id}")
    tmdb_url = f'https://api.themoviedb.org/3/tv/{series_id}?api_key={config.TMDB_API_KEY}'
    response = requests.get(tmdb_url)
    if response.status_code == 200:
        logger.info("Successfully retrieved series information from TMDB.")
        tmdb_response = response.json()
        series_name = tmdb_response['name']
        year = re.search(r'\d{4}', tmdb_response['first_air_date']).group()
        overview = tmdb_response['overview']
        poster_path = tmdb_response['poster_path']
        results = database.check_series_available(series_id)
        current_datetime = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')
        if results and current_datetime[:10] == results[0][6]:
            logger.info("Series is available in the database & its up to date")
            row = []
            tv_message = ""
            # Create a message with a keyboard of seasons
            seasons = sorted(set(season for series_name, year, season, episode, link, overview, updated in results))
            keyboard = types.InlineKeyboardMarkup()
            tv_message += f"🎬 *{results[0][0]}* ({results[0][1]})\n\n"
            tv_message += f"{results[0][5]}\n\n"
            tv_message += f"Please select a season:"
            for season in seasons:
                button = types.InlineKeyboardButton(text=f"Season {season}",
                                                    callback_data=f"series_{series_id}_season_{season}")
                row.append(button)
                if len(row) == 3:
                    keyboard.row(*row)
                    row = []
            if row:
                keyboard.row(*row)
            bot.send_photo(msg.chat.id, f"https://image.tmdb.org/t/p/original{tmdb_response['poster_path']}",
                           caption=tv_message, reply_markup=keyboard, parse_mode='Markdown')
            bot.delete_message(msg.chat.id, msg.message_id, timeout=None)

        else:
            logger.info("Series is not available in the database or not uptodate. Fetching series.")
            series = fetch_series(config.HOST_URL, series_name, series_id, year, overview)

            if not series:
                bot.edit_message_text("I'm sorry, but I couldn't find any series matching your search.", msg.chat.id,
                                      msg.message_id)
                return

            row = []
            tv_message = ""
            # Create a message with a keyboard of seasons
            seasons = sorted(set(season for title, season, episode, link in series))
            keyboard = types.InlineKeyboardMarkup()
            tv_message += f"🎬 *{series_name}* ({year})\n\n"
            tv_message += f"{overview}\n\n"
            tv_message += f"Please select a season:"
            for season in seasons:
                button = types.InlineKeyboardButton(text=f"Season {season}",
                                                    callback_data=f"series_{series_id}_season_{season}")
                row.append(button)
                if len(row) == 3:
                    keyboard.row(*row)
                    row = []
            if row:
                keyboard.row(*row)

            bot.send_photo(msg.chat.id, f"https://image.tmdb.org/t/p/original{poster_path}",
                           caption=tv_message, reply_markup=keyboard, parse_mode='Markdown')
            bot.delete_message(msg.chat.id, msg.message_id, timeout=None)

    elif response.status_code == 404:
        logger.error("Could not find a series with the provided ID.")
        bot.send_message(message.chat.id, "I'm sorry, but I couldn't find a series with that ID.")
    else:
        logger.error("An error occurred while trying to retrieve the series information.")
        bot.send_message(message.chat.id, "Something went wrong. Please try again later.")


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
    episodes = database.get_series_links(series_id, season)
    # Check if the season directory exists
    if not os.path.isdir(season_dir):
        # Download all subtitles and save them
        for season, episode, link, updated, series_name in episodes:
            chat_dir = f'subtitles/series/{series_id}/{season}/{episode}'
            os.makedirs(chat_dir, exist_ok=True)

            # download & extract zip
            download_extract_zip(link, chat_dir, bot, msg)
    else:
        logger.info(f"Subtitles for series_id {series_id} and season {season} already exist")
    # Create a message with a keyboard of episodes
    keyboard = types.InlineKeyboardMarkup()
    row = []
    for season, episode, link, updated, series_name in episodes:
        # Check if subtitles exist for the episode
        subtitle_exists = os.path.isdir(f'subtitles/series/{series_id}/{season}/{episode}')
        # Add a check or uncheck emoji based on whether subtitles exist
        episode_text = f"✅ E{episode}" if subtitle_exists else f"❌ E{episode}"
        callback_data = f"episode_{episode}_season_{season}_series_id_{series_id}"
        button = types.InlineKeyboardButton(text=episode_text, callback_data=callback_data)
        row.append(button)
        if len(row) == 4:
            keyboard.row(*row)
            row = []
    if row:
        keyboard.row(*row)
    download_all_button = types.InlineKeyboardButton(text="📥 Download All (.zip)",
                                                     callback_data=f"zip_{series_id}_season_{season}")
    keyboard.row(download_all_button)
    message_season = f"*Download {episodes[0][4]} : Season {season}*\n _(Last updated: {datetime.datetime.strptime(episodes[0][3], '%Y-%m-%dT%H:%M:%S.%f').strftime('%d %B %Y, %H:%M:%S')})_"
    bot.edit_message_text(message_season, msg.chat.id, msg.message_id, reply_markup=keyboard, parse_mode='Markdown')

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
    name = database.get_series_name(series_id)
    exists = f'subtitles/series/{series_id}/{season}/{episode}'
    # check if directory exists
    if os.path.isdir(exists):
        for file in os.listdir(exists):
            if file.endswith(('.srt', '.ass', '.ssa', '.vtt', '.stl', '.scc', '.ttml', '.sbv', '.idx', '.sub')):
                with open(os.path.join(exists, file), 'rb') as f:
                    bot.send_document(call.message.chat.id, f)
        bot.edit_message_text(f"✅ {name} S{season}:E{episode} Subtitle Uploaded", msg.chat.id, msg.message_id,
                              parse_mode='Markdown')
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
    series_name = database.get_series_name(series_id)

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
