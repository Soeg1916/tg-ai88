"""
Message and callback handlers for the Telegram bot.
"""
import logging
import os
import re
from typing import Dict, Any

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import DOWNLOADS_FOLDER, MAX_FILE_SIZE
from services.youtube_service import YouTubeService
from services.social_media_service import SocialMediaService
from utils.helpers import is_valid_url, is_youtube_url, extract_youtube_id

logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle text messages sent to the bot.
    Detects URLs and processes them accordingly.
    """
    if not update.message or not update.message.text:
        return

    text = update.message.text
    
    # Check if the message contains a URL
    urls = re.findall(r'https?://\S+', text)
    
    if not urls:
        # If no URLs, this message will be handled by the main message handler
        return
    
    for url in urls:
        # Check if it's a YouTube URL
        if is_youtube_url(url):
            await process_youtube_url(update, context, url)
            return
        
        # Check if it's a TikTok or Instagram URL
        platform = SocialMediaService.identify_platform(url)
        if platform in ['tiktok', 'instagram']:
            await process_social_media_url(update, context, url, platform)
            return
        
        # Handle other types of URLs if needed
        # ...

async def process_social_media_url(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, platform: str) -> None:
    """Process a TikTok or Instagram URL detected in a message."""
    try:
        # Get content information
        content_info = await SocialMediaService.get_content_info(url)
        
        if not content_info or content_info.get('error'):
            error_msg = content_info.get('error', 'Unknown error')
            await update.message.reply_text(f"Could not retrieve information for this {platform.title()} content. Error: {error_msg}")
            return
        
        # Format the content information
        title = content_info.get("title", f"{platform.title()} content")
        uploader = content_info.get("uploader", "Unknown creator")
        duration = format_duration(content_info.get("duration", 0)) if content_info.get("duration") else "N/A"
        
        # Platform-specific info formatting
        platform_info = ""
        if platform == 'tiktok':
            like_count = format_number(content_info.get("like_count", 0)) if content_info.get("like_count") else "N/A"
            comment_count = format_number(content_info.get("comment_count", 0)) if content_info.get("comment_count") else "N/A"
            platform_info = f"❤️ Likes: {like_count}\n💬 Comments: {comment_count}\n"
        elif platform == 'instagram':
            like_count = format_number(content_info.get("like_count", 0)) if content_info.get("like_count") else "N/A"
            view_count = format_number(content_info.get("view_count", 0)) if content_info.get("view_count") else "N/A"
            platform_info = f"❤️ Likes: {like_count}\n👁️ Views: {view_count}\n"
        
        response = (
            f"📱 *{platform.title()} Content Detected*\n\n"
            f"*{title}*\n\n"
            f"👤 Creator: {uploader}\n"
            f"⏱️ Duration: {duration}\n"
            f"{platform_info}\n"
        )
        
        # Add buttons for downloading video or audio using proper InlineKeyboardMarkup
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [InlineKeyboardButton("📥 Download Video", callback_data=f"download_sm_video:{platform}:{url}")],
            [InlineKeyboardButton("🎵 Extract Audio", callback_data=f"extract_sm_audio:{platform}:{url}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_markdown(
            response,
            reply_markup=reply_markup
        )
    
    except Exception as e:
        logger.error(f"Error processing {platform} URL: {e}")
        await update.message.reply_text(
            f"Sorry, an error occurred while processing this {platform.title()} content. Please try again later."
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle callback queries from inline keyboards.
    """
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    
    # Handle YouTube download callbacks
    if query.data.startswith("download_yt_video:"):
        url = query.data.split(":", 1)[1]
        await download_youtube_video(query, context, url)
    
    elif query.data.startswith("extract_yt_audio:"):
        url = query.data.split(":", 1)[1]
        await extract_youtube_audio(query, context, url)
    
    # Handle social media download callbacks
    elif query.data.startswith("download_sm_video:"):
        _, platform, url = query.data.split(":", 2)
        await download_social_media_video(query, context, url, platform)
    
    elif query.data.startswith("extract_sm_audio:"):
        _, platform, url = query.data.split(":", 2)
        await extract_social_media_audio(query, context, url, platform)

async def process_youtube_url(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str) -> None:
    """Process a YouTube URL detected in a message."""
    try:
        # Get video information
        video_info = await YouTubeService.get_video_info(url)
        
        if not video_info:
            await update.message.reply_text("Could not retrieve information for this YouTube video.")
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
            f"📺 *YouTube Video Detected*\n\n"
            f"*{title}*\n\n"
            f"👤 Uploader: {uploader}\n"
            f"⏱️ Duration: {duration}\n"
            f"👁️ Views: {view_count}\n"
            f"📅 Upload Date: {upload_date}\n\n"
        )
        
        # Add buttons for downloading video or audio using proper InlineKeyboardMarkup
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [InlineKeyboardButton("📥 Download Video", callback_data=f"download_yt_video:{url}")],
            [InlineKeyboardButton("🎵 Extract Audio", callback_data=f"extract_yt_audio:{url}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_markdown(
            response,
            reply_markup=reply_markup
        )
    
    except Exception as e:
        logger.error(f"Error processing YouTube URL: {e}")
        await update.message.reply_text(
            "Sorry, an error occurred while processing this YouTube video. Please try again later."
        )

async def download_youtube_video(query, context, url):
    """Download a YouTube video and send it to the user."""
    await query.edit_message_text(
        f"⏳ Downloading video from YouTube...\n"
        f"This may take a moment depending on the video size."
    )
    
    try:
        # Download the video
        result = await YouTubeService.download_video(url)
        
        if not result or not os.path.exists(result):
            await query.edit_message_text(
                "❌ Failed to download the video. It might be too large or restricted."
            )
            return
        
        # Check file size
        file_size = os.path.getsize(result)
        if file_size > MAX_FILE_SIZE:
            await query.edit_message_text(
                f"❌ The video file is too large ({file_size / (1024 * 1024):.1f} MB) to send via Telegram.\n"
                f"Maximum allowed size is {MAX_FILE_SIZE / (1024 * 1024):.1f} MB."
            )
            # Clean up the file
            os.remove(result)
            return
        
        # Send the video file
        await query.edit_message_text("✅ Download complete! Sending video...")
        
        with open(result, "rb") as video_file:
            await context.bot.send_video(
                chat_id=query.message.chat_id,
                video=video_file,
                caption="Here's your requested YouTube video!",
                supports_streaming=True
            )
        
        # Clean up the file after sending
        os.remove(result)
        
    except Exception as e:
        logger.error(f"Error downloading YouTube video: {e}")
        await query.edit_message_text(
            "❌ An error occurred while downloading or sending the video."
        )

async def extract_youtube_audio(query, context, url):
    """Extract audio from a YouTube video and send it to the user."""
    await query.edit_message_text(
        f"⏳ Extracting audio from YouTube video...\n"
        f"This may take a moment."
    )
    
    try:
        # Extract the audio
        result = await YouTubeService.extract_audio(url)
        
        if not result or not os.path.exists(result):
            await query.edit_message_text(
                "❌ Failed to extract audio. The video might be restricted."
            )
            return
        
        # Check file size
        file_size = os.path.getsize(result)
        if file_size > MAX_FILE_SIZE:
            await query.edit_message_text(
                f"❌ The audio file is too large ({file_size / (1024 * 1024):.1f} MB) to send via Telegram.\n"
                f"Maximum allowed size is {MAX_FILE_SIZE / (1024 * 1024):.1f} MB."
            )
            # Clean up the file
            os.remove(result)
            return
        
        # Send the audio file
        await query.edit_message_text("✅ Audio extraction complete! Sending audio...")
        
        with open(result, "rb") as audio_file:
            await context.bot.send_audio(
                chat_id=query.message.chat_id,
                audio=audio_file,
                caption="Here's your requested audio from the YouTube video!"
            )
        
        # Clean up the file after sending
        os.remove(result)
        
    except Exception as e:
        logger.error(f"Error extracting audio from YouTube video: {e}")
        await query.edit_message_text(
            "❌ An error occurred while extracting or sending the audio."
        )

def format_duration(seconds):
    """Format duration from seconds to HH:MM:SS."""
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if hours:
        return f"{int(hours)}:{int(minutes):02d}:{int(seconds):02d}"
    else:
        return f"{int(minutes)}:{int(seconds):02d}"

async def download_social_media_video(query, context, url, platform):
    """Download a social media video and send it to the user."""
    await query.edit_message_text(
        f"⏳ Downloading video from {platform.title()}...\n"
        f"This may take a moment depending on the video size."
    )
    
    try:
        # Download the video
        result, error = await SocialMediaService.download_video(url)
        
        if not result or not os.path.exists(result) or error:
            await query.edit_message_text(
                f"❌ Failed to download the video: {error or 'Unknown error'}"
            )
            return
        
        # Check file size
        file_size = os.path.getsize(result)
        if file_size > MAX_FILE_SIZE:
            await query.edit_message_text(
                f"❌ The video file is too large ({file_size / (1024 * 1024):.1f} MB) to send via Telegram.\n"
                f"Maximum allowed size is {MAX_FILE_SIZE / (1024 * 1024):.1f} MB."
            )
            # Clean up the file
            os.remove(result)
            return
        
        # Send the video file
        await query.edit_message_text("✅ Download complete! Sending video...")
        
        with open(result, "rb") as video_file:
            await context.bot.send_video(
                chat_id=query.message.chat_id,
                video=video_file,
                caption=f"Here's your requested {platform.title()} video!",
                supports_streaming=True
            )
        
        # Clean up the file after sending
        os.remove(result)
        
    except Exception as e:
        logger.error(f"Error downloading {platform} video: {e}")
        await query.edit_message_text(
            f"❌ An error occurred while downloading or sending the {platform} video."
        )

async def extract_social_media_audio(query, context, url, platform):
    """Extract audio from a social media video and send it to the user."""
    await query.edit_message_text(
        f"⏳ Extracting audio from {platform.title()} video...\n"
        f"This may take a moment."
    )
    
    try:
        # Extract the audio
        result, error = await SocialMediaService.extract_audio(url)
        
        if not result or not os.path.exists(result) or error:
            await query.edit_message_text(
                f"❌ Failed to extract audio: {error or 'Unknown error'}"
            )
            return
        
        # Check file size
        file_size = os.path.getsize(result)
        if file_size > MAX_FILE_SIZE:
            await query.edit_message_text(
                f"❌ The audio file is too large ({file_size / (1024 * 1024):.1f} MB) to send via Telegram.\n"
                f"Maximum allowed size is {MAX_FILE_SIZE / (1024 * 1024):.1f} MB."
            )
            # Clean up the file
            os.remove(result)
            return
        
        # Send the audio file
        await query.edit_message_text("✅ Audio extraction complete! Sending audio...")
        
        with open(result, "rb") as audio_file:
            await context.bot.send_audio(
                chat_id=query.message.chat_id,
                audio=audio_file,
                caption=f"Here's the audio extracted from the {platform.title()} video!"
            )
        
        # Clean up the file after sending
        os.remove(result)
        
    except Exception as e:
        logger.error(f"Error extracting audio from {platform} video: {e}")
        await query.edit_message_text(
            f"❌ An error occurred while extracting or sending the audio from {platform}."
        )

def format_number(number):
    """Format large numbers with commas."""
    return f"{number:,}"