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

from services.image_analyzer import ImageAnalyzer

logger = logging.getLogger(__name__)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle photo messages sent to the bot.
    Analyze the photo content and return detailed information.
    """
    if not update.message or not update.message.photo:
        return

    # Get the largest photo (best quality)
    photo = update.message.photo[-1]
    caption = update.message.caption or "No caption provided"
    
    # Send a status message
    status_message = await update.message.reply_text(
        "🔍 *Analyzing your image...*\n\n"
        "I'm examining this image with my AI vision tools.\n"
        "Just a moment while I process what I see!",
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        # Get the file
        photo_file = await context.bot.get_file(photo.file_id)
        photo_bytes = await download_telegram_file(photo_file.file_path)
        
        if not photo_bytes:
            await status_message.edit_text(
                "❌ *Error*\n\n"
                "Sorry, I couldn't download your image for analysis.\n"
                "Please try again with a different image.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
            
        # Analyze the image
        analysis_result = await ImageAnalyzer.analyze_image(photo_bytes)
        
        if "error" in analysis_result:
            await status_message.edit_text(
                "❌ *Error*\n\n"
                f"Sorry, I couldn't analyze your image: {analysis_result['error']}\n"
                "Please try again with a different image.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
            
        # Generate an annotated image and summary
        annotated_image, summary_text = await ImageAnalyzer.generate_analysis_image(photo_bytes, analysis_result)
        
        # Delete the status message
        try:
            await status_message.delete()
        except Exception:
            # If we can't delete, just continue
            pass
            
        # Format a nice response message
        response_text = (
            "🔍 *Image Analysis Results*\n\n"
            f"{summary_text}\n\n"
        )
        
        # Check if there's extracted text to display
        if analysis_result.get('text') and len(analysis_result['text']) > 0:
            extracted_text = analysis_result['text']
            # Truncate long text for the message
            if len(extracted_text) > 700:
                truncated_text = extracted_text[:700] + "...(text truncated)"
            else:
                truncated_text = extracted_text
                
            response_text += (
                "📄 *Full Extracted Text:*\n"
                f"`{truncated_text}`\n\n"
            )
        
        # Create the file-like object for the annotated image
        annotated_image_io = io.BytesIO(annotated_image)
        annotated_image_io.name = "analyzed_image.jpg"
        
        # Send the analyzed image with the results
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=annotated_image_io,
            caption=response_text[:1024],  # Telegram caption limit
            parse_mode=ParseMode.MARKDOWN
        )
        
        # If we have a lot of text that was truncated in the message, send it as a separate message
        if analysis_result.get('text') and len(analysis_result['text']) > 700:
            full_text_message = (
                "📝 *Complete Extracted Text:*\n\n"
                f"{analysis_result['text']}"
            )
            
            # Split into chunks if needed (Telegram has a 4096 character limit)
            await send_long_message(
                update.effective_chat.id,
                full_text_message,
                context.bot,
                parse_mode=ParseMode.MARKDOWN
            )
            
    except Exception as e:
        logger.error(f"Error analyzing photo: {str(e)}")
        
        # Try to delete the status message
        try:
            await status_message.delete()
        except Exception:
            pass
            
        await update.message.reply_text(
            "❌ *Error*\n\n"
            "Sorry, I encountered an error while analyzing your image.\n"
            "This might be due to API limitations or the image format.\n\n"
            "Please try again with a different image.",
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
        # If replying to a photo, analyze that photo
        photo = update.message.reply_to_message.photo[-1]  # Get largest size
        
        # Create a fake update to reuse handle_photo
        fake_update = Update(
            update_id=update.update_id,
            message=update.message.reply_to_message
        )
        
        await handle_photo(fake_update, context)
    else:
        await update.message.reply_markdown(
            "📷 *Image Analyzer*\n\n"
            "Send me any photo and I'll analyze it to:\n"
            "• Detect objects and scenes\n"
            "• Extract text (OCR)\n"
            "• Detect faces and expressions\n"
            "• Identify landmarks and logos\n\n"
            "You can also reply to an existing photo with /analyze to analyze it.\n\n"
            "Example: Send a photo of text to extract its content, or a photo of a landmark to identify it."
        )