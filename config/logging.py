import logging
import os

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

# Create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)  # use the same formatter for the stream handler

# Add the handlers to the logger
logger.addHandler(handler)
logger.addHandler(stream_handler)  # add the stream handler to the logger
