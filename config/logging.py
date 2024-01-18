import logging
import os
from config import config

chat_id = config.LOG_CHANNEL_ID

# Initialize the bot variable
bot = None

# Create the logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create a file handler
handler = logging.FileHandler('logs/bot.log')
handler.setLevel(logging.INFO)

# Create a stream handler (this will print logs to the terminal)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)


# Function to set the bot
def set_bot(bot_object):
    global bot
    bot = bot_object


# Function to send logs to your Telegram channel
def telegram_log(message):
    if os.getenv('TELEGRAM_LOGGING') == 'TRUE':
        # Send the message to your Telegram channel
        bot.send_message(chat_id=chat_id, text=message)


# Create a custom handler
class TelegramHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        telegram_log(log_entry)


# Set the custom handler
telegram_handler = TelegramHandler()
logger.addHandler(telegram_handler)

# Create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)  # use the same formatter for the stream handler
telegram_handler.setFormatter(formatter)  # use the same formatter for the telegram handler

# Add the handlers to the logger
logger.addHandler(handler)
logger.addHandler(stream_handler)  # add the stream handler to the logger
