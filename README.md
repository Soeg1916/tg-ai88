# Telegram Content Processing Bot

A Telegram bot that processes web content and YouTube videos using Google APIs and web scraping techniques.

## Features

- Web scraping for content retrieval
- YouTube video processing (download videos, extract audio)
- Google search integration
- Media handling (images, videos)
- Asynchronous request handling
- Error handling and logging

## Commands

- `/start` - Start the bot and get basic information
- `/help` - Get help with using the bot
- `/search <query>` - Search the web using Google
- `/scrape <url>` - Extract text content from a website
- `/youtube <url>` - Process a YouTube video

## Setup and Deployment

### Prerequisites

- Python 3.10+
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Google API Key with Custom Search API enabled
- Google Custom Search Engine ID

### Installation

1. Clone the repository
2. Create a `.env` file based on `.env.example` and add your API keys
3. Install dependencies (use requirements.txt)
4. Run the bot: `python main.py`

### Environment Variables

Create a `.env` file with the following variables:

