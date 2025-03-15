"""
Configuration settings for the Telegram bot.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in the environment variables")

# API Keys
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

# Bot settings
MAX_CONTEXT_LENGTH = 10  # Maximum number of messages to keep in conversation context

# Paths
DOWNLOADS_FOLDER = "downloads"
os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)

# File size limits
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB (Telegram limit)

# Initialize a dictionary to track active games
game_states = {}