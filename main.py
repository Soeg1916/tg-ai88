#!/usr/bin/env python
"""
Main entry point for the Telegram Bot.
"""
import logging
import os
from dotenv import load_dotenv

from bot import create_bot

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Start the bot."""
    # Load environment variables
    load_dotenv()
    
    # Create and run the bot
    bot = create_bot()
    
    logger.info("Bot started")
    
    # Run the bot until the user presses Ctrl-C
    bot.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == '__main__':
    main()
