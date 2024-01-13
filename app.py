import requests
from bs4 import BeautifulSoup
import zipfile
import os
import telebot
from urllib.parse import urljoin, urlparse, unquote, quote_plus
import re
import db
import shutil

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TOKEN')
TMDB_API_KEY = os.getenv('TMDB_API_KEY')
HOST_URL = os.getenv('HOST_URL')

bot = telebot.TeleBot(TOKEN)

db.create_table()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_message = "👋 *Welcome to the Sinhala Subtitle Download Bot!* 🎬\n\n"
    welcome_message += "I'm here to help you find and download Sinhala subtitles for your favorite movies. Here's what I can do:\n\n"
    welcome_message += "1. **Search for Movies**: You can search for a movie by its name, and I'll find the Sinhala subtitles for it. To do this, use the `/search` command followed by the movie name. For example, `/search Titanic`.\n\n"
    welcome_message += "_Please note that the availability of subtitles depends on the movie and the source of the subtitles. If you have any issues or need further assistance, feel free to ask me! @theRECK3r_"
    bot.reply_to(message, welcome_message, parse_mode='Markdown')


@bot.message_handler(commands=['search'])
def search_movie(message):

    # Check if the command is exactly '/search'
    if message.text.strip() == '/search':
        bot.send_message(message.chat.id, "Please provide a movie name. For example, `/search Titanic`.")
        return

    # Get the movie name from the message
    movie_name = message.text.split('/search ', 1)[1].strip()

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
        bot.send_message(message.chat.id, "I'm sorry, but I couldn't find any movies matching your search.")
        return

    movie_message = ""

    for title, link, movie_data in movies:
        movie_id = movie_data['id']
        title = movie_data['title']
        overview = movie_data['overview']
        year = re.search(r'\d{4}', movie_data['release_date']).group()
        db.insert_details(movie_id, title, year, link, overview)

        movie_message += f"🎬 *{title}* ({year})\n"
        movie_message += f"{overview}\n"
        movie_message += f"_Download:_ /dl\_{movie_id}\n\n"

        # Send the message
    bot.send_message(message.chat.id, movie_message, parse_mode='Markdown')


@bot.message_handler(regexp='^/dl')
def download_subtitle(message):
    movie_id = message.text.split('/dl_', 1)[1].strip()
    link = db.get_link(movie_id)
    chat_dir = f'subtitles/{movie_id}'

    #check if directory exists
    if os.path.isdir(chat_dir):
        # Send all .srt files
        for file in os.listdir(chat_dir):
            if file.endswith('.srt'):
                with open(os.path.join(chat_dir, file), 'rb') as f:
                    bot.send_document(message.chat.id, f)
    else:
        r = requests.get(link)
        soup = BeautifulSoup(r.text, 'html.parser')

        # Find the zip file link
        for a in soup.find_all('a', href=True):
            if '/?tmstv=' in a['href']:
                zip_url = urljoin(link, a['href'])
                break

        # Create a unique directory for this chat
        os.makedirs(chat_dir, exist_ok=True)

        # Download the zip file
        r = requests.get(zip_url)
        parsed_url = urlparse(zip_url)
        zip_file_name = os.path.join(chat_dir, os.path.basename(unquote(parsed_url.path)))
        if not os.path.basename(unquote(parsed_url.path)):
            zip_file_name = os.path.join(chat_dir, 'default.zip')
        with open(zip_file_name, 'wb') as f:
            f.write(r.content)

        # Extract the .srt file
        with zipfile.ZipFile(zip_file_name, 'r') as zip_ref:
            zip_ref.extractall(chat_dir)

        # Check if there are any .srt files in the main directory
        srt_files = [file for file in os.listdir(chat_dir) if file.endswith('.srt')]

        if not srt_files:
            # No .srt files found in the main directory, find them in subdirectories
            for root, dirs, files in os.walk(chat_dir):
                for file in files:
                    if file.endswith('.srt'):
                        # Move the .srt file to the main directory
                        shutil.move(os.path.join(root, file), chat_dir)

        # Delete all files that are not .srt files
        for root, dirs, files in os.walk(chat_dir, topdown=False):
            for file in files:
                if not file.endswith('.srt'):
                    os.remove(os.path.join(root, file))
            for dir in dirs:
                os.rmdir(os.path.join(root, dir))

        # Send all .srt files
        for file in os.listdir(chat_dir):
            if file.endswith('.srt'):
                with open(os.path.join(chat_dir, file), 'rb') as f:
                    bot.send_document(message.chat.id, f)

bot.polling()
