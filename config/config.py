import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TOKEN')
TMDB_API_KEY = os.getenv('TMDB_API_KEY')
HOST_URL = os.getenv('HOST_URL')

