"""
Message and callback handlers for the Telegram bot.
"""
import logging
import os
import re
from typing import Dict, Any, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
        # For TikTok links, download and send the video directly
        if platform == 'tiktok':
            # Send a processing message first
            processing_msg = await update.message.reply_text("⏳ Processing TikTok video... This may take a moment.")
            
            # Download the video
            result, error = await SocialMediaService.download_video(url)
            
            if not result or error:
                await processing_msg.edit_text(f"❌ Failed to download the TikTok content: {error or 'Unknown error'}")
                return
                
            # Check if result is a directory (for TikTok slide posts)
            if os.path.isdir(result):
                # This is a slide post with multiple media files
                await processing_msg.edit_text("✅ Downloaded TikTok slides. Sending them now...")
                
                # Get all files in the directory
                media_files = []
                for filename in sorted(os.listdir(result)):
                    file_path = os.path.join(result, filename)
                    
                    # Skip non-media files and files that are too large
                    if os.path.isdir(file_path) or filename.endswith('.json'):
                        continue
                    
                    file_size = os.path.getsize(file_path)
                    if file_size > MAX_FILE_SIZE:
                        continue  # Skip files that are too large
                    
                    media_files.append(file_path)
                
                # Send all media files (up to 10)
                for i, file_path in enumerate(media_files[:10]):
                    file_ext = os.path.splitext(file_path)[1].lower()
                    
                    try:
                        # Add extract audio button for the first slide
                        caption = f"TikTok Slide {i+1}/{len(media_files)}"
                        reply_markup = None
                        
                        if i == 0:  # Only add button to the first slide
                            keyboard = [
                                [InlineKeyboardButton("🎵 Extract Audio", callback_data=f"extract_sm_audio:tiktok:{url}")]
                            ]
                            reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        if file_ext in ['.jpg', '.jpeg', '.png', '.webp']:
                            # Send as photo
                            with open(file_path, "rb") as photo_file:
                                await context.bot.send_photo(
                                    chat_id=update.message.chat_id,
                                    photo=photo_file,
                                    caption=caption,
                                    reply_markup=reply_markup
                                )
                        elif file_ext in ['.mp4', '.avi', '.mkv', '.mov']:
                            # Send as video
                            with open(file_path, "rb") as video_file:
                                await context.bot.send_video(
                                    chat_id=update.message.chat_id,
                                    video=video_file,
                                    caption=caption,
                                    supports_streaming=True,
                                    reply_markup=reply_markup
                                )
                        else:
                            # Send as document
                            with open(file_path, "rb") as doc_file:
                                await context.bot.send_document(
                                    chat_id=update.message.chat_id,
                                    document=doc_file,
                                    caption=caption,
                                    reply_markup=reply_markup
                                )
                    except Exception as e:
                        logger.error(f"Error sending slide {i+1}: {e}")
                        continue  # Continue with next file even if one fails
                
                # Delete the processing message
                await processing_msg.delete()
                
                # Clean up the directory
                import shutil
                shutil.rmtree(result)
                
            else:
                # Regular single video file
                # Check file size
                file_size = os.path.getsize(result)
                if file_size > MAX_FILE_SIZE:
                    await processing_msg.edit_text(
                        f"❌ The video file is too large ({file_size / (1024 * 1024):.1f} MB) to send via Telegram.\n"
                        f"Maximum allowed size is {MAX_FILE_SIZE / (1024 * 1024):.1f} MB."
                    )
                    # Clean up the file
                    os.remove(result)
                    return
                
                # Add extract audio button
                keyboard = [
                    [InlineKeyboardButton("🎵 Extract Audio", callback_data=f"extract_sm_audio:tiktok:{url}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Delete the processing message
                await processing_msg.delete()
                
                # Send the video file directly
                with open(result, "rb") as video_file:
                    await context.bot.send_video(
                        chat_id=update.message.chat_id,
                        video=video_file,
                        caption="Here's your TikTok video!",
                        supports_streaming=True,
                        reply_markup=reply_markup
                    )
                
                # Clean up the file after sending
                os.remove(result)
        
        # For Instagram, keep using the buttons approach
        else:
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
            
            # Format Instagram-specific info
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
            
            # Add buttons for downloading video or audio
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
        
    # Handle checkers game help
    elif query.data == "help_checkers":
        help_text = (
            "♟️ *Checkers Game* ♟️\n\n"
            "Play the classic game of Checkers right in Telegram!\n\n"
            "*How to play:*\n"
            "• Use `/checkers` to start a game against the AI\n"
            "• Use `/checkers @username` to challenge another user\n"
            "• Make moves with `/move A3-B4` format\n"
            "• End a game with `/endcheckers`\n\n"
            "*Game Rules:*\n"
            "• Regular pieces move diagonally forward one space\n"
            "• Captures are made by jumping over opponent pieces\n"
            "• Reach the opponent's end to make a King\n"
            "• Kings can move diagonally forward or backward\n"
            "• Win by capturing all opponent pieces or blocking all moves\n\n"
            "Try it now with `/checkers`!"
        )
        await query.edit_message_text(text=help_text, parse_mode=ParseMode.MARKDOWN)
        return
    
    # Handle calculator help
    elif query.data == "help_calculate":
        help_text = (
            "🧮 *Calculator* 🧮\n\n"
            "Solve mathematical expressions right in Telegram!\n\n"
            "*How to use:*\n"
            "• Use `/calculate 2+2*3` to calculate the result\n"
            "• Or just mention the bot with a math problem: `@YourBot 5+7/2`\n\n"
            "*Supported operations:*\n"
            "• Addition: `5+3`\n"
            "• Subtraction: `10-4`\n"
            "• Multiplication: `6*8`\n"
            "• Division: `20/5`\n"
            "• Exponentiation: `2^3` (2 cubed)\n"
            "• Modulo: `10%3` (remainder after division)\n"
            "• Parentheses: `(4+2)*3`\n\n"
            "Try it now with `/calculate 15/3+2^2`!"
        )
        await query.edit_message_text(text=help_text, parse_mode=ParseMode.MARKDOWN)
        return
    
    # Handle translation callbacks
    elif query.data.startswith("translate:"):
        try:
            # Format: translate:lang_code:original_text
            parts = query.data.split(":", 2)
            if len(parts) < 3:
                await query.message.reply_text("❌ Invalid translation request")
                return
                
            target_lang = parts[1]
            original_text = parts[2]
            
            # If the original text was cut (limited to 50 chars), use the message text
            if len(original_text) < 50 and "..." not in original_text:
                # Use the full text from the original message
                # We need to find the original text in the data
                from bot import translate_text
                
                # Call the translation function
                translated_text = await translate_text(original_text, target_lang)
                
                # Edit the existing message with the new translation
                # Extract the original response text (first line)
                original_title = "🌐 *Translation*\n\n"
                
                # Update message with the new translation
                await query.message.edit_text(
                    f"{original_title}{translated_text}",
                    parse_mode="Markdown",
                    reply_markup=query.message.reply_markup
                )
            
        except Exception as e:
            logger.error(f"Translation callback error: {e}")
            await query.message.reply_text("❌ Translation failed. Please try again.")
    
    # Handle translation help menu callbacks
    elif query.data.startswith("translate_help:"):
        try:
            # Format: translate_help:lang_code
            parts = query.data.split(":", 1)
            if len(parts) < 2:
                await query.message.reply_text("❌ Invalid language selection")
                return
                
            target_lang = parts[1]
            from bot import translate_text
            
            help_text = (
                "How to use translation:\n\n"
                "• `/tl Hello world` - Translate to English\n"
                "• `/tl es Hello world` - Translate to Spanish\n"
                "• Reply to any message with `/tl` - Translate to English\n"
                "• Reply with `/tl fr` - Translate to French"
            )
            
            # Translate the help text
            translated_help = await translate_text(help_text, target_lang)
            
            # Send the translated help
            await query.message.edit_text(
                f"🌐 *Translation Help* ({target_lang})\n\n{translated_help}",
                parse_mode="Markdown",
                reply_markup=query.message.reply_markup
            )
            
        except Exception as e:
            logger.error(f"Translation help callback error: {e}")
            await query.message.reply_text("❌ Translation help failed. Please try again.")
    
    # Handle help menu callbacks
    elif query.data == "help_all":
        # Show all commands
        help_text = (
            "🤖 *All Commands* 🤖\n\n"
            "*Conversation*\n"
            "• /start - Start the bot and see available commands\n"
            "• /clear - Clear your conversation history\n"
            "• /context - See your current conversation context\n\n"
            
            "*Media & Downloads*\n"
            "• /tiktok <url> - Download TikTok videos without watermark\n"
            "• /instagram <url> - Download Instagram videos/reels\n"
            "• /youtube <url> - Process YouTube videos\n\n"
            
            "*Information Tools*\n"
            "• /search <query> - Search the web for information\n"
            "• /scrape <url> - Extract content from a website\n"
            "• /img <search> - Search and send images\n\n"
            
            "*Image Analysis*\n"
            "• Send any photo - Analyze objects, text, and content\n"
            "• /analyze - Reply to a photo with this command to analyze it\n\n"
            
            "*Fun & Utilities*\n"
            "• /write <text> - Convert text to handwritten style\n"
            "• /fun - Play a number guessing game\n"
            "• /insult @username - Generate a humorous roast for someone\n"
            "• /calculate <expression> - Solve math calculations\n"
            "• /tl <text> - Translate text between languages\n"
            "• /total - Show total messages today\n"
            "• /ttotal - Show total messages this year\n"
            "• /admins - View group administrators (groups only)"
        )
        await query.message.edit_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    elif query.data == "help_media":
        # Show media download commands
        help_text = (
            "📱 *Media Download Commands* 📱\n\n"
            "• /tiktok <url> - Download TikTok videos without watermark\n"
            "• /instagram <url> - Download Instagram videos/reels\n"
            "• /youtube <url> - Process YouTube videos\n\n"
            "Simply paste any TikTok, Instagram, or YouTube URL in the chat to get download options automatically!"
        )
        
        # Create back button
        keyboard = [[InlineKeyboardButton("« Back to Menu", callback_data="help_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(help_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    elif query.data == "help_info":
        # Show information tools
        help_text = (
            "🔍 *Information Tools* 🔍\n\n"
            "• /search <query> - Search the web for information\n"
            "• /scrape <url> - Extract content from a website\n"
            "• /img <search> - Search and send images\n\n"
            "Try these commands to get information from the web quickly!"
        )
        
        # Create back button
        keyboard = [[InlineKeyboardButton("« Back to Menu", callback_data="help_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(help_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    elif query.data == "help_image":
        # Show image features
        help_text = (
            "🖼️ *Image Features* 🖼️\n\n"
            "• Send any photo - If you tag me, I'll analyze objects, text, and content\n"
            "• /analyze - Reply to a photo with this command to analyze it\n\n"
            "Note: Image analysis is currently limited due to API restrictions."
        )
        
        # Create back button
        keyboard = [[InlineKeyboardButton("« Back to Menu", callback_data="help_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(help_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    elif query.data == "help_fun":
        # Show fun & utilities
        help_text = (
            "🎮 *Fun & Utilities* 🎮\n\n"
            "• /write <text> - Convert text to handwritten style\n"
            "• /fun - Play a number guessing game\n"
            "• /insult @username - Generate a humorous roast for someone\n"
            "• /calculate <expression> - Solve math calculations\n"
            "• /tl <text> - Translate text between languages\n"
            "• /total - Show total messages today\n"
            "• /ttotal - Show total messages this year\n"
            "• /admins - View group administrators (groups only)\n\n"
            "Try these commands for some entertainment and useful features!"
        )
        
        # Create back button
        keyboard = [[InlineKeyboardButton("« Back to Menu", callback_data="help_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(help_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    # Specific feature help options from the start menu
    elif query.data == "help_search":
        help_text = (
            "🔍 *Web Search* 🔍\n\n"
            "Use the `/search` command followed by your query to search the web.\n\n"
            "Example: `/search latest AI developments`\n\n"
            "I'll return the most relevant information I can find!"
        )
        
        # Create back button
        keyboard = [[InlineKeyboardButton("« Back to Menu", callback_data="help_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(help_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    elif query.data == "help_img":
        help_text = (
            "🖼️ *Image Search* 🖼️\n\n"
            "Use the `/img` command followed by your search term to find images.\n\n"
            "Example: `/img cute puppies`\n\n"
            "I'll return up to 4 images matching your search!"
        )
        
        # Create back button
        keyboard = [[InlineKeyboardButton("« Back to Menu", callback_data="help_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(help_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    elif query.data == "help_tiktok":
        help_text = (
            "📱 *TikTok Download* 📱\n\n"
            "Use the `/tiktok` command followed by a TikTok URL to download videos without watermark.\n\n"
            "Example: `/tiktok https://vm.tiktok.com/XXXXX/`\n\n"
            "Alternatively, just paste any TikTok URL in the chat, and I'll offer download options automatically!"
        )
        
        # Create back button
        keyboard = [[InlineKeyboardButton("« Back to Menu", callback_data="help_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(help_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    elif query.data == "help_instagram":
        help_text = (
            "📸 *Instagram Download* 📸\n\n"
            "Use the `/instagram` command followed by an Instagram post or reel URL to download videos.\n\n"
            "Example: `/instagram https://www.instagram.com/p/XXXXX/`\n\n"
            "Alternatively, just paste any Instagram URL in the chat, and I'll offer download options automatically!"
        )
        
        # Create back button
        keyboard = [[InlineKeyboardButton("« Back to Menu", callback_data="help_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(help_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    elif query.data == "help_youtube":
        help_text = (
            "🎬 *YouTube Download* 🎬\n\n"
            "Use the `/youtube` command followed by a YouTube URL to download videos or extract audio.\n\n"
            "Example: `/youtube https://www.youtube.com/watch?v=XXXXX`\n\n"
            "Alternatively, just paste any YouTube URL in the chat, and I'll offer download options automatically!"
        )
        
        # Create back button
        keyboard = [[InlineKeyboardButton("« Back to Menu", callback_data="help_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(help_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    elif query.data == "help_write":
        help_text = (
            "✍️ *Handwritten Text* ✍️\n\n"
            "Use the `/write` command followed by your text to convert it to a handwritten style.\n\n"
            "Example: `/write This looks like it's handwritten!`\n\n"
            "I'll create an image that looks like your text was written by hand. Maximum 300 characters."
        )
        
        # Create back button
        keyboard = [[InlineKeyboardButton("« Back to Menu", callback_data="help_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(help_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    elif query.data == "help_insult":
        help_text = (
            "😈 *Insult Generator* 😈\n\n"
            "Use the `/insult` command followed by a username to generate a humorous roast for that person.\n\n"
            "Example: `/insult @username`\n\n"
            "I'll create a funny, creative roast perfect for friendly banter in group chats!"
        )
        
        # Create back button
        keyboard = [[InlineKeyboardButton("« Back to Menu", callback_data="help_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(help_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    elif query.data == "help_translate":
        help_text = (
            "🌐 *Translation Tool* 🌐\n\n"
            "Translate text between languages with the `/tl` command.\n\n"
            "*Usage Options:*\n"
            "• Reply to a message with `/tl` - Translates it to English\n"
            "• `/tl <lang>` - Translates to specified language\n"
            "  Example: `/tl ja` - Translates to Japanese\n"
            "• `/tl <source>//<dest>` - Translates from source to destination language\n"
            "  Example: `/tl ja//en` - Translates from Japanese to English\n"
            "• `/langs` - Get a list of supported languages\n\n"
            "*Common Language Codes:*\n"
            "• English: `en`\n"
            "• Spanish: `es`\n"
            "• French: `fr`\n"
            "• German: `de`\n"
            "• Chinese: `zh-cn`\n"
            "• Japanese: `ja`\n"
            "• Arabic: `ar`"
        )
        
        # Create back button
        keyboard = [[InlineKeyboardButton("« Back to Menu", callback_data="help_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(help_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    elif query.data == "help_back":
        # Back to main menu
        help_text = (
            "🤖 *AI Telegram Bot Commands* 🤖\n\n"
            "Choose a category to see specific commands:"
        )
        
        # Create keyboard with categories
        keyboard = [
            [
                InlineKeyboardButton("📱 Media Downloads", callback_data="help_media"),
                InlineKeyboardButton("🔍 Information Tools", callback_data="help_info")
            ],
            [
                InlineKeyboardButton("🖼️ Image Features", callback_data="help_image"),
                InlineKeyboardButton("🎮 Fun & Utilities", callback_data="help_fun")
            ],
            [
                InlineKeyboardButton("🌐 Translation", callback_data="help_translate"),
                InlineKeyboardButton("📚 All Commands", callback_data="help_all")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(help_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

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
        
        # Add buttons for downloading video or audio
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
        f"⏳ Downloading content from {platform.title()}...\n"
        f"This may take a moment depending on the content size."
    )
    
    try:
        # Download the video
        result, error = await SocialMediaService.download_video(url)
        
        if not result or not os.path.exists(result) or error:
            await query.edit_message_text(
                f"❌ Failed to download the content: {error or 'Unknown error'}"
            )
            return
        
        # Check if result is a directory (for TikTok slide posts)
        if os.path.isdir(result):
            # This is a slide post with multiple media files
            await query.edit_message_text("✅ Download complete! Found multiple slides. Sending them...")
            
            # Get all files in the directory
            media_files = []
            for filename in sorted(os.listdir(result)):
                file_path = os.path.join(result, filename)
                
                # Skip non-media files and files that are too large
                if os.path.isdir(file_path) or filename.endswith('.json'):
                    continue
                
                file_size = os.path.getsize(file_path)
                if file_size > MAX_FILE_SIZE:
                    continue  # Skip files that are too large
                
                media_files.append(file_path)
            
            # Send all media files (up to 10)
            for i, file_path in enumerate(media_files[:10]):
                file_ext = os.path.splitext(file_path)[1].lower()
                
                try:
                    if file_ext in ['.jpg', '.jpeg', '.png', '.webp']:
                        # Send as photo
                        with open(file_path, "rb") as photo_file:
                            await context.bot.send_photo(
                                chat_id=query.message.chat_id,
                                photo=photo_file,
                                caption=f"TikTok Slide {i+1}/{len(media_files)}"
                            )
                    elif file_ext in ['.mp4', '.avi', '.mkv', '.mov']:
                        # Send as video
                        with open(file_path, "rb") as video_file:
                            await context.bot.send_video(
                                chat_id=query.message.chat_id,
                                video=video_file,
                                caption=f"TikTok Slide {i+1}/{len(media_files)}",
                                supports_streaming=True
                            )
                    else:
                        # Send as document
                        with open(file_path, "rb") as doc_file:
                            await context.bot.send_document(
                                chat_id=query.message.chat_id,
                                document=doc_file,
                                caption=f"TikTok Slide {i+1}/{len(media_files)}"
                            )
                except Exception as e:
                    logger.error(f"Error sending slide {i+1}: {e}")
                    continue  # Continue with next file even if one fails
            
            # Send a final message
            if media_files:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"✅ Successfully sent {len(media_files)} slides from {platform.title()} post!"
                )
            else:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"⚠️ No suitable media files found in the {platform.title()} post."
                )
            
            # Clean up the directory
            import shutil
            shutil.rmtree(result)
            
        else:
            # Regular single video file
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
        f"⏳ Extracting audio from {platform.title()} content...\n"
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
        
        # Check if result is a directory (for TikTok slide posts)
        if os.path.isdir(result):
            # This is a slide post with multiple audio files
            await query.edit_message_text("✅ Audio extraction complete! Found multiple audio tracks. Sending them...")
            
            # Get all audio files in the directory
            audio_files = []
            for filename in sorted(os.listdir(result)):
                file_path = os.path.join(result, filename)
                
                # Skip non-audio files and files that are too large
                if os.path.isdir(file_path) or not filename.endswith('.mp3'):
                    continue
                
                file_size = os.path.getsize(file_path)
                if file_size > MAX_FILE_SIZE:
                    continue  # Skip files that are too large
                
                audio_files.append(file_path)
            
            # Send all audio files (up to 5)
            for i, file_path in enumerate(audio_files[:5]):
                try:
                    with open(file_path, "rb") as audio_file:
                        await context.bot.send_audio(
                            chat_id=query.message.chat_id,
                            audio=audio_file,
                            caption=f"TikTok Audio {i+1}/{len(audio_files)} from slide post"
                        )
                except Exception as e:
                    logger.error(f"Error sending audio track {i+1}: {e}")
                    continue  # Continue with next file even if one fails
            
            # Send a final message
            if audio_files:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"✅ Successfully sent {len(audio_files)} audio tracks from {platform.title()} slide post!"
                )
            else:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"⚠️ No suitable audio files found in the {platform.title()} post."
                )
            
            # Clean up the directory
            import shutil
            shutil.rmtree(result)
            
        else:
            # Regular single audio file
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
                    caption=f"Here's the audio extracted from the {platform.title()} content!"
                )
            
            # Clean up the file after sending
            os.remove(result)
        
    except Exception as e:
        logger.error(f"Error extracting audio from {platform} content: {e}")
        await query.edit_message_text(
            f"❌ An error occurred while extracting or sending the audio from {platform}."
        )

def format_number(number):
    """Format large numbers with commas."""
    return f"{number:,}"