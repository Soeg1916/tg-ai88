"""
Photo message handlers for the Telegram bot.
"""
import logging
import io
import os
from typing import Optional, Dict, Any, List, Tuple

from telegram import Update, InputMediaPhoto
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

# We'll import handle_message from the handlers module to avoid circular imports
from handlers.message_handlers import handle_message as process_message

logger = logging.getLogger(__name__)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle photo messages sent to the bot.
    In group chats: Only respond if the bot is mentioned or directly replied to.
    In private chats: Process normally.
    """
    if not update.message or not update.message.photo:
        return

    # Get the largest photo (best quality)
    photo = update.message.photo[-1]
    caption = update.message.caption
    
    # Get the bot's username to check for mentions
    bot_username = context.bot.username
    
    # Check if this is in a group chat
    is_group = update.effective_chat.type in ["group", "supergroup"]
    
    # In group chats, only respond if:
    # 1. Bot is mentioned in caption
    # 2. Message is a reply to the bot's message
    # 3. User used a command
    bot_mentioned = False
    replied_to_bot = False
    is_command = False
    
    if caption and bot_username and f"@{bot_username}" in caption:
        bot_mentioned = True
    
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        if update.message.reply_to_message.from_user.id == context.bot.id:
            replied_to_bot = True
    
    if caption and caption.startswith("/"):
        is_command = True
        
    # In group chats, only process if bot is mentioned/replied to
    if is_group and not (bot_mentioned or replied_to_bot or is_command):
        # Silently ignore the message - don't respond at all
        return
        
    # Process the message if it has a caption
    if caption:
        # Use the handle_message function that we imported as process_message
        await process_message(update, context)
        return
    
    # In private chats or when explicitly addressed in groups, respond with the help message
    await update.message.reply_text(
        "ℹ️ *Image received*\n\n"
        "I noticed you sent an image without any text. If you'd like me to analyze this image, "
        "please use the /analyze command as a reply to this image.\n\n"
        "Alternatively, you can resend the image with a caption describing what you'd like me to do.",
        parse_mode=ParseMode.MARKDOWN
    )
        
async def download_telegram_file(file_path: str) -> Optional[bytes]:
    """Download a file from Telegram servers."""
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(file_path) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    logger.error(f"Failed to download Telegram file: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error downloading Telegram file: {str(e)}")
        return None

async def send_long_message(chat_id: int, text: str, bot, parse_mode: str = None, chunk_size: int = 4000) -> List[int]:
    """Send a long message by splitting it into chunks."""
    message_ids = []
    
    # Split the message into chunks
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size]
        message = await bot.send_message(
            chat_id=chat_id,
            text=chunk,
            parse_mode=parse_mode
        )
        message_ids.append(message.message_id)
        
    return message_ids

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /analyze command which provides info about the image analysis capability.
    Format: /analyze (should be used as a reply to an image)
    """
    if update.message.reply_to_message and update.message.reply_to_message.photo:
        # If replying to a photo, tell the user that the image analysis service is currently unavailable
        await update.message.reply_markdown(
            "ℹ️ *Image Analysis Service Notice*\n\n"
            "I'm sorry, but the image analysis service is currently unavailable due to API limitations.\n\n"
            "The image analysis capability will be restored once the necessary API access is configured."
        )
    else:
        await update.message.reply_markdown(
            "📷 *Image Analyzer*\n\n"
            "I'm sorry, but the image analysis service is currently unavailable due to API limitations.\n\n"
            "The image analysis capability will be restored once the necessary API access is configured."
        )