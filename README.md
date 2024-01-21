# Sinhala Subtitle Downloader Telegram Bot

## Overview

The Sinhala Subtitle Downloader Telegram Bot is a tool designed to simplify the process of obtaining Sinhala subtitles for movies and TV series. The bot offers a user-friendly interface with intuitive commands, leveraging an SQLite database for efficient data storage and retrieval.

## Features

1. **Subtitle Download:**
   - `/tv {tv series}` command for downloading Sinhala subtitles for a specific TV series.
   - `/movie {movie name}` command for fetching Sinhala subtitles for a particular movie.

## Environment Variables

The following environment variables are required to run the bot:

- `TOKEN`: Bot token.
- `TMDB_API_KEY`: TMDB API key. Get it from [The Movie Database (TMDb)](https://www.themoviedb.org/settings/api).
- `HOST_URL`: Only works with baiscope.lk for now.
- `TELEGRAM_LOGGING`: `True` or `False`.
- `LOG_CHANNEL_ID`: Channel ID where you want to send logs. Make sure to add the bot to that channel.

## How to Run

1. Rename the `sample.env` file to `.env` inside config folder.
2. Fill in the required values for the environment variables in the `.env` file.
3. Make sure to install the dependencies first by running `pip install -r requirements.txt`.
4. Run the bot using `python3 bot.py`.

## Future Enhancements

- Support for additional hosts such as PirateLK and Zoom.
- Integration with popular streaming platforms for instant access to subtitles (Chrome Extension).

## Disclaimer

The bot relies on external sources for subtitle retrieval, and availability is subject to content on the internet. The bot creator is not responsible for the content or accuracy of subtitles.

## Note

- Users are encouraged to provide feedback for improvement.
