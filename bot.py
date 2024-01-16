import requests
from bs4 import BeautifulSoup
import zipfile
import os
import telebot
from urllib.parse import quote_plus
import re
from telebot import types
import datetime
from config import config
from connectors import database
from helpers.fetch_series import fetch_series
from helpers.zip_helper import download_extract_zip
from config.logging import logger

bot = telebot.TeleBot(config.TOKEN)

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
    msg = bot.send_message(message.chat.id, "🔍 Searching....")
    # Check if the command is exactly '/movie'
    if message.text.strip() == '/movie':
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
        database.insert_details(movie_id, title, year, link, overview)

        movie_message += f"🎬 *{title}* ({year})\n"
        movie_message += f"_Download:_ /dl\_{movie_id}\n\n"

        # Send the message
    bot.edit_message_text(movie_message, msg.chat.id, msg.message_id, parse_mode='Markdown')


@bot.message_handler(regexp='^/dl')
def download_subtitle(message):
    movie_id = message.text.split('/dl_', 1)[1].strip()
    link = database.get_link(movie_id)
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
    msg = bot.send_message(message.chat.id, "🔍 Searching for the subtitles...")
    # Check if the command is exactly '/tv'
    if message.text.strip() == '/tv':
        bot.edit_message_text("Please provide a tv series name. For example, `/tv breaking bad`.", msg.chat.id,
                              msg.message_id)
        return

    # Get the series name from the message
    series_name = message.text.split('/tv ', 1)[1].strip()

    # Get series details
    tmdb_url = f'https://api.themoviedb.org/3/search/tv?api_key={config.TMDB_API_KEY}&query={quote_plus(series_name)}'
    tmdb_response = requests.get(tmdb_url).json()
    if tmdb_response['results']:
        series_data = tmdb_response['results'][0]
        series_id = series_data['id']
        overview = series_data['overview']
        year = re.search(r'\d{4}', series_data['first_air_date']).group()
    else:
        bot.edit_message_text("I'm sorry, but I couldn't find any series matching your search.", msg.chat.id,
                              msg.message_id)
        return

    results = database.check_series_available(series_id)

    if results:
        row = []
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
            row.append(button)
            if len(row) == 3:
                keyboard.row(*row)
                row = []
        if row:
            keyboard.row(*row)
        bot.send_photo(msg.chat.id, f"https://image.tmdb.org/t/p/original{series_data['poster_path']}",
                       caption=tv_message, reply_markup=keyboard, parse_mode='Markdown')
        bot.delete_message(msg.chat.id, msg.message_id, timeout=None)
    else:
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
        tv_message += f"🎬 *{series_data['name']}* ({year})\n\n"
        tv_message += f"{series_data['overview']}\n\n"
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
    update_all = types.InlineKeyboardButton(text="🔄 Update",
                                            callback_data=f"update_{series_id}_season_{season}")
    keyboard.row(download_all_button)
    keyboard.row(update_all)
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


@bot.callback_query_handler(func=lambda call: call.data.startswith('update_'))
def handle_update_button(call):
    # Extract the series ID and season number from the callback data
    _, series_id, _, season = call.data.split('_')
    series_id = int(series_id)
    season = int(season)
    msg = bot.send_message(call.message.chat.id, "🔄 Updating subtitles...")
    logger.info(f"Updating subtitles for series_id {series_id} and season {season}")

    old_data = database.fetch_old_data(series_id)

    # Get the current date and time
    current_datetime = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')

    # Get the last updated date and time from the database
    last_updated_datetime = old_data[0][6]
    if current_datetime[:10] == last_updated_datetime[:10]:
        bot.edit_message_text("The subtitles are already updated today.", msg.chat.id, msg.message_id)
        return
    else:
        fetch_series(config.HOST_URL, old_data[0][0], series_id, old_data[0][1], old_data[0][5])
        # Retrieve the episode numbers and links from the database
        episodes = database.get_series_links(series_id, season)

        # Download all subtitles and save them
        for season, episode, link, updated, series_name in episodes:
            chat_dir = f'subtitles/series/{series_id}/{season}/{episode}'
            if not os.path.exists(chat_dir):
                os.makedirs(chat_dir, exist_ok=True)

                # download & extract zip
                download_extract_zip(link, chat_dir, bot, msg)

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
        update_all = types.InlineKeyboardButton(text="🔄 Update",
                                                callback_data=f"update_{series_id}_season_{season}")
        keyboard.row(download_all_button)
        keyboard.row(update_all)

        message_season = f"*Download {episodes[0][4]} : Season {season}*\n _(Last updated: {datetime.datetime.strptime(episodes[0][3], '%Y-%m-%dT%H:%M:%S.%f').strftime('%d %B %Y, %H:%M:%S')})_"
        bot.edit_message_text(message_season, call.message.chat.id, call.message.message_id, reply_markup=keyboard,
                              parse_mode='Markdown')
        bot.delete_message(msg.chat.id, msg.message_id)
        logger.info(f"Sent message for series_id {series_id} and season {season}")


bot.polling()
