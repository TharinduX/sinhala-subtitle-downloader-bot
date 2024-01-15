import requests
from bs4 import BeautifulSoup
import zipfile
import os
from urllib.parse import urljoin, urlparse, unquote
import shutil
import rarfile
import logging
import py7zr


def download_extract_zip(link, chat_dir, bot, msg):
    logger = logging.getLogger(__name__)
    logger.info(f"Downloading subtitles from {link} to {chat_dir}")

    # Download the zip file
    r = requests.get(link)
    soup = BeautifulSoup(r.text, 'html.parser')
    for a in soup.find_all('a', href=True):
        if '/?tmstv=' in a['href']:
            zip_url = urljoin(link, a['href'])
            break
    r = requests.get(zip_url)
    parsed_url = urlparse(zip_url)
    file_name = os.path.basename(unquote(parsed_url.path))
    if not file_name:
        content_type = r.headers.get('Content-Type', '')
        if 'zip' in content_type:
            file_name = 'default.zip'
        elif 'x-rar-compressed' in content_type:
            file_name = 'default.rar'
        elif '7z' in content_type:
            file_name = 'default.7z'
        else:
            file_name = 'default.zip'  # Default to .zip if Content-Type header is not recognized
    else:
        _, ext = os.path.splitext(file_name)
        if ext not in ['.zip', '.rar', '.7z']:
            file_name = 'default' + ext
    zip_file_name = os.path.join(chat_dir, file_name)
    with open(zip_file_name, 'wb') as f:
        f.write(r.content)

    logger.info(f"Downloaded zip file {zip_file_name}")

    # Extract the subtitle files
    try:
        if zip_file_name.endswith('.zip'):
            with zipfile.ZipFile(zip_file_name, 'r') as zip_ref:
                zip_ref.extractall(chat_dir)
        elif zip_file_name.endswith('.rar'):
            with rarfile.RarFile(zip_file_name, 'r') as rar_ref:
                rar_ref.extractall(chat_dir)
        elif zip_file_name.endswith('.7z'):
            with py7zr.SevenZipFile(zip_file_name, mode='r') as z:
                z.extractall(path=chat_dir)
    except (zipfile.BadZipFile, rarfile.BadRarFile, py7zr.exceptions.Bad7zFile):
        shutil.rmtree(chat_dir)
        bot.edit_message_text("😰 The file is corrupted.", msg.chat.id, msg.message_id, parse_mode='Markdown')
        logger.error(f"Failed to extract subtitles from {zip_file_name}")
        return

    logger.info(f"Extracted subtitles to {chat_dir}")

    # Check if there are any subtitle files in the main directory
    srt_files = [file for file in os.listdir(chat_dir) if file.endswith('.srt')]
    if not srt_files:
        # No .srt files found in the main directory, find them in subdirectories
        for root, dirs, files in os.walk(chat_dir):
            for file in files:
                if file.endswith(('.srt', '.ass', '.ssa', '.vtt', '.stl', '.scc', '.ttml', '.sbv')):
                    # Move the .srt file to the main directory
                    shutil.move(os.path.join(root, file), chat_dir)

    logger.info(f"Moved .srt files to {chat_dir}")

    # Delete all files that are not subtitle files
    for root, dirs, files in os.walk(chat_dir, topdown=False):
        for file in files:
            if not file.endswith(('.srt', '.ass', '.ssa', '.vtt', '.stl', '.scc', '.ttml', '.sbv')):
                os.remove(os.path.join(root, file))
        for dir in dirs:
            shutil.rmtree(os.path.join(root, dir))

    logger.info(f"Cleaned up {chat_dir}")
