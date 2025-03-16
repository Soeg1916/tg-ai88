"""
Command handlers for the Telegram bot.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from services.google_search import GoogleSearchService
from services.web_scraper import get_website_text_content
from services.youtube_service import YouTubeService
from utils.helpers import is_valid_url, is_youtube_url, truncate_text

logger = logging.getLogger(__name__)

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /search command to search the web using Google.
    
    Format: /search <query>
    """
    query = " ".join(context.args) if context.args else ""
    
    if not query:
        await update.message.reply_text(
            "Please provide a search query.\n"
            "Example: /search Python programming tutorial"
        )
        return
    
    await update.message.reply_text(f"🔍 Searching for the latest results on: {query}...")
    
    try:
        # Perform Google search with emphasis on latest results
        results = await GoogleSearchService.search(query)
        
        if not results:
            await update.message.reply_text("No recent results found for your search query.")
            return
        
        # Format the results
        response = f"📰 Latest search results for: *{query}*\n(from the past 7 days)\n\n"
        
        for i, result in enumerate(results, 1):
            title = result.get("title", "No title")
            link = result.get("link", "#")
            snippet = result.get("snippet", "No description")
            
            response += f"*{i}. {title}*\n{snippet}\n{link}\n\n"
        
        await update.message.reply_markdown(truncate_text(response))
    
    except Exception as e:
        logger.error(f"Error performing search: {e}")
        await update.message.reply_text(
            "Sorry, an error occurred while searching. Please try again later."
        )

async def scrape_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /scrape command to extract content from a website.
    
    Format: /scrape <url>
    """
    if not context.args:
        await update.message.reply_text(
            "Please provide a URL to scrape.\n"
            "Example: /scrape https://example.com"
        )
        return
    
    url = context.args[0]
    
    if not is_valid_url(url):
        await update.message.reply_text(
            "Please provide a valid URL.\n"
            "Example: /scrape https://example.com"
        )
        return
    
    await update.message.reply_text(f"🔍 Extracting content from: {url}...")
    
    try:
        # Extract text content from the URL
        content = await get_website_text_content(url)
        
        if not content:
            await update.message.reply_text("No content could be extracted from the provided URL.")
            return
        
        # Truncate the content to fit in a Telegram message
        truncated_content = truncate_text(content)
        
        await update.message.reply_text(
            f"📄 Content from {url}:\n\n{truncated_content}",
            disable_web_page_preview=True
        )
    
    except Exception as e:
        logger.error(f"Error scraping content: {e}")
        await update.message.reply_text(
            "Sorry, an error occurred while extracting content. Please try again later."
        )

async def youtube_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /youtube command to process YouTube videos.
    
    Format: /youtube <url>
    """
    if not context.args:
        await update.message.reply_text(
            "Please provide a YouTube video URL.\n"
            "Example: /youtube https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        return
    
    url = context.args[0]
    
    if not is_youtube_url(url):
        await update.message.reply_text(
            "Please provide a valid YouTube video URL.\n"
            "Example: /youtube https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        return
    
    status_message = await update.message.reply_text(f"⏳ Processing YouTube video... Please wait")
    
    try:
        # Get video information
        video_info = await YouTubeService.get_video_info(url)
        
        if not video_info:
            await update.message.reply_text("Could not retrieve information for the provided video URL.")
            return
        
        # Format the video information
        title = video_info.get("title", "Unknown title")
        duration = format_duration(video_info.get("duration", 0))
        view_count = format_number(video_info.get("view_count", 0))
        uploader = video_info.get("uploader", "Unknown uploader")
        upload_date = video_info.get("upload_date", "Unknown date")
        
        # Convert YYYYMMDD to a more readable format
        if upload_date and len(upload_date) == 8:
            year = upload_date[0:4]
            month = upload_date[4:6]
            day = upload_date[6:8]
            upload_date = f"{year}-{month}-{day}"
        
        response = (
            f"*{title}*\n\n"
            f"👤 Uploader: {uploader}\n"
            f"⏱️ Duration: {duration}\n"
            f"👁️ Views: {view_count}\n"
            f"📅 Upload Date: {upload_date}\n\n"
        )
        
        # Add buttons for downloading video or audio
        keyboard = [
            [
                {"text": "Download Video", "callback_data": f"download_video:{url}"},
                {"text": "Extract Audio", "callback_data": f"extract_audio:{url}"}
            ]
        ]
        
        # Delete the status message
        try:
            await status_message.delete()
        except Exception:
            pass
            
        # Send response with improved formatting
        await update.message.reply_markdown(
            response,
            reply_markup={"inline_keyboard": keyboard}
        )
    
    except Exception as e:
        logger.error(f"Error processing YouTube video: {e}")
        await update.message.reply_text(
            "Sorry, an error occurred while processing the YouTube video. Please try again later."
        )

def format_duration(seconds):
    """Format duration from seconds to HH:MM:SS."""
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if hours:
        return f"{int(hours)}:{int(minutes):02d}:{int(seconds):02d}"
    else:
        return f"{int(minutes)}:{int(seconds):02d}"

def format_number(number):
    """Format large numbers with commas."""
    return f"{number:,}"