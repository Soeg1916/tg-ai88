"""
Bot initialization and setup.
"""
import os
import logging
import random
import re
from datetime import datetime
import nest_asyncio
nest_asyncio.apply()

from telegram import Update, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler,
    ChatMemberHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

from conversation import ConversationManager
from message_counter import MessageCounter
from api_client import AIApiClient
from config import BOT_TOKEN, game_states, DOWNLOADS_FOLDER
import utils.helpers as helpers
from handlers.command_handlers import search_command, scrape_command, youtube_command
from handlers.message_handlers import handle_callback
from handlers.photo_handlers import handle_photo, analyze_command

logger = logging.getLogger(__name__)

# Initialize conversation manager and message counter
conversation_manager = ConversationManager()
message_counter = MessageCounter()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    welcome_text = (
        "👋 *Welcome to your AI Assistant*\n\n"
        "I'm a sophisticated bot that can help you with conversations, media downloads, and information search.\n\n"
        "💡 *What I can do:*\n"
        "• Chat with you using AI\n"
        "• Download videos from TikTok, Instagram, and YouTube\n"
        "• Search the web and find images\n"
        "• Analyze images to detect objects and extract text\n"
        "• Extract content from websites\n"
        "• Convert text to handwritten style\n"
        "• And much more!\n\n"
        "Try the buttons below to explore my features, or just start chatting with me right away!"
    )
    
    # Create an inline keyboard with common commands
    
    keyboard = [
        [
            InlineKeyboardButton("🔍 Web Search", callback_data="help_search"),
            InlineKeyboardButton("🖼️ Image Search", callback_data="help_img")
        ],
        [
            InlineKeyboardButton("📱 TikTok Download", callback_data="help_tiktok"),
            InlineKeyboardButton("📸 Instagram Download", callback_data="help_instagram")
        ],
        [
            InlineKeyboardButton("🎬 YouTube Download", callback_data="help_youtube"),
            InlineKeyboardButton("📝 Handwritten Text", callback_data="help_write")
        ],
        [
            InlineKeyboardButton("📚 All Commands", callback_data="help_all")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_markdown(welcome_text, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = (
        "🤖 *AI Telegram Bot Commands* 🤖\n\n"
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
        "• Send any photo - Automatically analyze objects, text, and content\n"
        "• /analyze - Reply to a photo with this command to analyze it\n\n"
        
        "*Fun & Utilities*\n"
        "• /write <text> - Convert text to handwritten style\n"
        "• /fun - Play a number guessing game\n"
        "• /total - Show total messages today\n"
        "• /ttotal - Show total messages this year\n"
        "• /admins - View group administrators (groups only)\n\n"
        
        "*Pro Tips*:\n"
        "• Send any URL to automatically process YouTube/TikTok/Instagram links\n"
        "• Send any photo to automatically analyze it (objects, text, faces)\n"
        "• Mention the bot in group chats to interact with it\n"
        "• Reply to the bot's messages to continue conversation threads"
    )
    
    # Create an inline keyboard with common command categories
    
    keyboard = [
        [
            InlineKeyboardButton("📱 Media Downloads", callback_data="help_media"),
            InlineKeyboardButton("🔍 Information Tools", callback_data="help_info")
        ],
        [
            InlineKeyboardButton("🖼️ Image Features", callback_data="help_image"),
            InlineKeyboardButton("🎮 Fun & Utilities", callback_data="help_fun")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_markdown(help_text, reply_markup=reply_markup)

async def total_messages_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show total messages for today."""
    count = message_counter.get_today_count()
    await update.message.reply_text(f"📊 *Message Statistics*\n\n📅 Today's total: *{count}* messages", parse_mode="Markdown")

async def total_messages_year(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show total messages for the year."""
    count = message_counter.get_year_count()
    await update.message.reply_text(f"📊 *Yearly Message Statistics*\n\n📈 Total for {datetime.now().year}: *{count}* messages", parse_mode="Markdown")

async def fun_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start a number guessing game."""
    user_id = update.effective_user.id
    if user_id not in game_states:
        # Start a new game
        game_number = random.randint(1, 100)
        game_states[user_id] = {"number": game_number, "attempts": 0}
        
        # Create a progress bar of 10 segments to represent 1-100
        segment = game_number // 10  # Which segment the number falls into
        progress_segments = ["⬜️"] * 10
        for i in range(0, segment):
            progress_segments[i] = "🟩"
        progress_bar = "".join(progress_segments)
        
        # Hide the actual position with a fake progress bar
        fake_progress_bar = "⬜️" * 10
        
        game_message = (
            "🎮 *Number Guessing Game* 🎮\n\n"
            "I'm thinking of a number between *1 and 100*.\n"
            "Can you guess what it is?\n\n"
            f"Progress: {fake_progress_bar}\n\n"
            "Reply with your guess (1-100)!"
        )
        
        await update.message.reply_markdown(game_message)
    else:
        # Game already in progress
        attempts = game_states[user_id]["attempts"]
        await update.message.reply_markdown(
            "🎮 *Game in Progress* 🎮\n\n"
            f"You've already made *{attempts}* attempt(s).\n"
            "Keep guessing a number between 1 and 100 or use /clear to end the game."
        )

async def clear_context(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear conversation context."""
    user_id = update.effective_user.id
    conversation_manager.clear_context(user_id)
    await update.message.reply_text("🗑️ *Conversation context cleared!*\n\nI've forgotten our previous conversation. What would you like to talk about now?", parse_mode="Markdown")

async def show_context(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current conversation context."""
    user_id = update.effective_user.id
    context_summary = conversation_manager.get_context_summary(user_id)
    
    if not context_summary.strip():
        await update.message.reply_text("📭 *No conversation history found*\n\nWe haven't had any conversation yet. Feel free to start chatting!", parse_mode="Markdown")
        return
        
    await update.message.reply_text(f"🧠 *Current Conversation Context*\n\n{context_summary}", parse_mode="Markdown")

async def show_admins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show group admins."""
    if update.effective_chat.type in ['group', 'supergroup']:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        admin_list = "\n".join([f"👤 *{admin.user.first_name}*" + (f" (@{admin.user.username})" if admin.user.username else "") for admin in admins])
        await update.message.reply_text(f"👑 *Group Administrators*\n\n{admin_list}", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ *This command only works in groups!*\n\nAdd me to a group to use this feature.", parse_mode="Markdown")

async def image_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Search and send images."""
    if not context.args:
        await update.message.reply_markdown(
            "🔍 *Image Search*\n\n"
            "Please provide a search term after /img\n\n"
            "Example: `/img cute puppies`"
        )
        return
        
    search_term = " ".join(context.args)
    status_message = await update.message.reply_text(f"🔍 Searching for images of '*{search_term}*'...", parse_mode="Markdown")
    
    try:
        from services.google_search import GoogleSearchService
        
        # Get search results - limit to 4 images as requested
        results = await GoogleSearchService.image_search(search_term, num_results=4)
        
        # Delete the status message regardless of result
        try:
            await status_message.delete()
        except Exception:
            # If we can't delete, we'll just ignore the error and continue
            pass
        
        if not results:
            await update.message.reply_markdown(
                "🔍 *Image Search Results*\n\n"
                f"❌ No images found for '*{search_term}*'.\n\n"
                "Please try a different search term."
            )
            return
            
        # Send up to 4 images max
        media_group = []
        count = 0
        
        for item in results[:4]:  # Limit to 4 results
            if 'link' in item:
                try:
                    media_group.append(InputMediaPhoto(item['link']))
                    count += 1
                except Exception:
                    # Skip any problematic URLs
                    continue
                
                # Limit to exactly 4 images
                if count >= 4:
                    break
                    
        if media_group:
            try:
                await context.bot.send_media_group(
                    chat_id=update.effective_chat.id,
                    media=media_group
                )
                await update.message.reply_markdown(
                    f"🖼️ Here are *{len(media_group)}* images for '*{search_term}*'\n\n"
                    "Want more? Try another search with `/img`"
                )
            except Exception as e:
                logger.error(f"Error sending media group: {str(e)}")
                # Try to send images one by one if group fails
                sent_count = 0
                for item in media_group[:3]:  # Limit to 3 on fallback
                    try:
                        await context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=item.media
                        )
                        sent_count += 1
                    except:
                        continue
                
                if sent_count > 0:
                    await update.message.reply_markdown(
                        f"🖼️ Found *{sent_count}* images for '*{search_term}*'"
                    )
        else:
            await update.message.reply_markdown(
                "🔍 *Image Search Results*\n\n"
                f"⚠️ Found search results for '*{search_term}*' but couldn't retrieve images.\n\n"
                "Please try a different search term."
            )
            
    except Exception as e:
        # Try to delete the status message even in case of error
        try:
            await status_message.delete()
        except:
            pass
            
        logger.error(f"Error in image search: {str(e)}")
        await update.message.reply_markdown(
            "❌ *Error*\n\n"
            "Sorry, an error occurred while searching for images.\n"
            "This might be due to API limits or connectivity issues.\n\n"
            "Please try again later."
        )

async def convert_to_handwritten(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Convert text to handwritten style."""
    if not context.args:
        await update.message.reply_markdown(
            "✍️ *Text to Handwriting Converter*\n\n"
            "Please provide text after /write\n\n"
            "Example: `/write This will look like handwriting`"
        )
        return
        
    text = " ".join(context.args)
    
    # Check for text length limits to avoid creating huge images
    if len(text) > 300:
        await update.message.reply_markdown(
            "⚠️ *Text Too Long*\n\n"
            "Your text is too long! Please limit it to 300 characters.\n"
            f"Current length: *{len(text)}* characters"
        )
        return
        
    status_message = await update.message.reply_text("✍️ Converting your text to handwritten style... Please wait.")
    
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io
        import random
        import os
        import time
        
        # Create a temporary directory for handwritten images if it doesn't exist
        if not os.path.exists('temp_images'):
            os.makedirs('temp_images')
            
        # Create a unique filename based on timestamp and user ID
        timestamp = int(time.time())
        user_id = update.effective_user.id
        filename = f"temp_images/handwritten_{user_id}_{timestamp}.png"
            
        # Set up the image parameters
        width = 800
        height = max(30 * (len(text) // 40 + 1) + 100, 300)  # Adjust height based on text length, min 300px
        
        # Create a slightly off-white background for a paper-like effect
        background_color = (252, 252, 250)  # Slightly off-white
        image = Image.new('RGB', (width, height), background_color)
        draw = ImageDraw.Draw(image)
        
        # Try to load a handwriting-like font, or use default if not available
        try:
            font = ImageFont.truetype('arial.ttf', 30)
        except IOError:
            font = ImageFont.load_default()
        
        # Draw a subtle paper texture/lines
        line_color = (230, 230, 230)  # Light gray for paper lines
        for y in range(0, height, 40):
            draw.line([(0, y), (width, y)], fill=line_color, width=1)
            
        # Add a subtle paper border
        border_color = (220, 220, 220)
        # Draw border lines manually
        draw.line([(0, 0), (width-1, 0)], fill=border_color, width=2)  # Top
        draw.line([(0, 0), (0, height-1)], fill=border_color, width=2)  # Left
        draw.line([(width-1, 0), (width-1, height-1)], fill=border_color, width=2)  # Right
        draw.line([(0, height-1), (width-1, height-1)], fill=border_color, width=2)  # Bottom
        
        # Add some randomness to make it look more handwritten
        y_pos = 45  # Start a bit down from the top
        line_width = 40  # characters per line
        words = text.split()
        
        current_line = ""
        # Use a dark blue/black color for the text
        text_color = (10, 10, 40)  
        
        for word in words:
            # Check if adding this word would exceed the line width
            if len(current_line) + len(word) + 1 > line_width:
                # Draw the current line
                x_offset = random.randint(-2, 2)  # Slight horizontal variation
                y_offset = random.randint(-1, 1)  # Slight vertical variation
                
                # Add slight rotation to some characters for more realism
                for i, char in enumerate(current_line):
                    char_x = 30 + x_offset + i * 15  # Adjust character spacing
                    char_y = y_pos + y_offset + random.randint(-1, 1)
                    # Randomly adjust character sizing slightly
                    size_adjust = random.uniform(0.95, 1.05)
                    # Draw the character
                    draw.text((char_x, char_y), char, fill=text_color, font=font)
                
                # Move to next line
                y_pos += 40 + random.randint(-3, 3)
                current_line = word + " "
            else:
                current_line += word + " "
        
        # Draw the last line if there's any text left
        if current_line:
            x_offset = random.randint(-2, 2)
            y_offset = random.randint(-1, 1)
            
            for i, char in enumerate(current_line):
                char_x = 30 + x_offset + i * 15
                char_y = y_pos + y_offset + random.randint(-1, 1)
                draw.text((char_x, char_y), char, fill=text_color, font=font)
            
        # Save the image to disk first (for cleanup later)
        image.save(filename, format='PNG')
            
        # Save the image to a byte buffer for sending
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        # Try to delete the status message
        try:
            await status_message.delete()
        except:
            pass
        
        # Send the image to the user
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=img_byte_arr,
            caption="✍️ Here's your text in handwritten style!"
        )
        
        # Clean up the file after sending
        try:
            if os.path.exists(filename):
                os.remove(filename)
        except:
            pass
        
    except Exception as e:
        logger.error(f"Error converting text to handwritten style: {str(e)}")
        await update.message.reply_markdown(
            "❌ *Error*\n\n"
            "Sorry, an error occurred while converting your text to handwritten style.\n"
            "Please try again with a shorter text."
        )

async def tiktok_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Download TikTok video without watermark"""
    if not context.args:
        await update.message.reply_markdown(
            "📱 *TikTok Downloader*\n\n"
            "Please provide a TikTok video URL after /tiktok\n\n"
            "Example: `/tiktok https://www.tiktok.com/@username/video/1234567890`\n\n"
            "I can download TikTok videos without the watermark!"
        )
        return

    url = context.args[0]
    status_message = await update.message.reply_text("⏳ *Processing TikTok Video*\n\nDownloading and removing watermark...", parse_mode="Markdown")

    try:
        from services.social_media_service import SocialMediaService
        
        # Process TikTok URL
        platform = SocialMediaService.identify_platform(url)
        
        if platform != 'tiktok':
            # Delete the status message
            try:
                await status_message.delete()
            except Exception:
                pass
                
            await update.message.reply_markdown(
                "❌ *Invalid Link*\n\n"
                "The URL provided does not appear to be a valid TikTok link.\n\n"
                "Please make sure you're using a link from the TikTok app or website."
            )
            return
            
        # Directly download the video instead of showing options
        result, error = await SocialMediaService.download_video(url)
        
        if not result or error:
            # Delete the status message
            try:
                await status_message.delete()
            except Exception:
                pass
                
            await update.message.reply_markdown(
                f"❌ *Download Failed*\n\n"
                f"Sorry, I couldn't download this TikTok content: {error or 'Unknown error'}\n\n"
                f"This might be due to TikTok's restrictions or a problem with the URL."
            )
            return
            
        # Check if result is a directory (for TikTok slide posts)
        if os.path.isdir(result):
            # This is a slide post with multiple media files
            await status_message.edit_text("✅ Downloaded TikTok slides. Sending them now...")
            
            # Get all files in the directory
            media_files = []
            for filename in sorted(os.listdir(result)):
                file_path = os.path.join(result, filename)
                
                # Skip non-media files and files that are too large
                if os.path.isdir(file_path) or filename.endswith('.json'):
                    continue
                
                file_size = os.path.getsize(file_path)
                if file_size > 50 * 1024 * 1024:  # 50MB limit for Telegram
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
            
            # Delete the status message
            try:
                await status_message.delete()
            except Exception:
                pass
            
            # Clean up the directory
            import shutil
            shutil.rmtree(result)
            
        else:
            # Regular single video file
            # Check file size
            file_size = os.path.getsize(result)
            if file_size > 50 * 1024 * 1024:  # 50MB limit for Telegram
                # Delete the status message
                try:
                    await status_message.delete()
                except Exception:
                    pass
                    
                await update.message.reply_markdown(
                    f"❌ *File Too Large*\n\n"
                    f"The video file is too large ({file_size / (1024 * 1024):.1f} MB) to send via Telegram.\n"
                    f"Maximum allowed size is 50 MB."
                )
                # Clean up the file
                os.remove(result)
                return
            
            # Add extract audio button
            keyboard = [
                [InlineKeyboardButton("🎵 Extract Audio", callback_data=f"extract_sm_audio:tiktok:{url}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Delete the status message
            try:
                await status_message.delete()
            except Exception:
                pass
            
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

    except Exception as e:
        logger.error(f"Error processing TikTok URL: {str(e)}")
        
        # Delete the status message
        try:
            await status_message.delete()
        except Exception:
            pass
            
        await update.message.reply_markdown(
            "❌ *Error*\n\n"
            "Sorry, I couldn't process this TikTok video.\n"
            "This might be due to TikTok's restrictions or a problem with the URL.\n\n"
            "Please try again with a different link."
        )

async def instagram_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Download Instagram video or reel"""
    if not context.args:
        await update.message.reply_markdown(
            "📱 *Instagram Downloader*\n\n"
            "Please provide an Instagram video/reel URL after /instagram\n\n"
            "Example: `/instagram https://www.instagram.com/p/abcdef123456/`\n\n"
            "I can download Instagram videos and reels or extract their audio!"
        )
        return

    url = context.args[0]
    status_message = await update.message.reply_text("⏳ *Processing Instagram Content*\n\nExtracting media information...", parse_mode="Markdown")

    try:
        from services.social_media_service import SocialMediaService
        
        # Process Instagram URL
        platform = SocialMediaService.identify_platform(url)
        
        if platform != 'instagram':
            # Delete the status message
            try:
                await status_message.delete()
            except Exception:
                pass
                
            await update.message.reply_markdown(
                "❌ *Invalid Link*\n\n"
                "The URL provided does not appear to be a valid Instagram link.\n\n"
                "Please make sure you're using a link from the Instagram app or website."
            )
            return
            
        # Create a message with options to download video or audio
        # Inline keyboard imports moved to top of file
        
        keyboard = [
            [InlineKeyboardButton("📥 Download Video", callback_data=f"download_sm_video:instagram:{url}")],
            [InlineKeyboardButton("🎵 Extract Audio", callback_data=f"extract_sm_audio:instagram:{url}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Delete the status message
        try:
            await status_message.delete()
        except Exception:
            pass
            
        await update.message.reply_markdown(
            "📱 *Instagram Content Detected*\n\n"
            "What would you like to do with this content?",
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"Error processing Instagram URL: {str(e)}")
        
        # Delete the status message
        try:
            await status_message.delete()
        except Exception:
            pass
            
        await update.message.reply_markdown(
            "❌ *Error*\n\n"
            "Sorry, I couldn't process this Instagram content.\n"
            "This might be due to Instagram's restrictions or a problem with the URL.\n\n"
            "Please try again with a different link."
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user messages and respond using AI."""
    try:
        if not update.message or not update.message.text:
            return

        user_id = update.effective_user.id
        user_message = update.message.text
        chat_type = update.message.chat.type
        bot_username = context.bot.username
        
        # First, check if this is a URL we can process
        from handlers.message_handlers import process_youtube_url, process_social_media_url
        from services.social_media_service import SocialMediaService
        from utils.helpers import is_youtube_url
        
        # Check if the message contains a URL
        urls = re.findall(r'https?://\S+', user_message)
        if urls:
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

        # Handle game guesses
        if user_id in game_states:
            try:
                guess = int(user_message)
                if guess < 1 or guess > 100:
                    await update.message.reply_text("🔢 Please enter a number between 1 and 100.")
                    return
                    
                target = game_states[user_id]["number"]
                game_states[user_id]["attempts"] += 1
                attempts = game_states[user_id]["attempts"]

                if guess == target:
                    # Player won!
                    # Create a progress bar showing where the number was
                    segment = target // 10  # Which segment the number falls into
                    progress_segments = ["⬜️"] * 10
                    for i in range(0, segment):
                        progress_segments[i] = "🟩"
                    progress_bar = "".join(progress_segments)
                    
                    # Format attempt rating based on number of attempts
                    rating = ""
                    if attempts <= 3:
                        rating = "🌟 Amazing!"
                    elif attempts <= 6:
                        rating = "✨ Great job!"
                    elif attempts <= 10:
                        rating = "👍 Good work!"
                    else:
                        rating = "🎯 You got it!"
                    
                    del game_states[user_id]
                    await update.message.reply_markdown(
                        f"🎊 *CORRECT!* 🎊\n\n"
                        f"You guessed the number *{target}* in *{attempts}* attempts!\n"
                        f"{rating}\n\n"
                        f"Progress: {progress_bar}\n\n"
                        f"Type /fun to play again!"
                    )
                    return
                elif guess < target:
                    # Calculate how close they are as a percentage
                    closeness = (guess / target) * 100
                    hint = ""
                    
                    if closeness >= 90:
                        hint = "You're very close! 🔥"
                    elif closeness >= 75:
                        hint = "Getting warmer! 🌡️"
                    
                    await update.message.reply_markdown(
                        f"*{guess}* is too low! Try *higher* ⬆️\n{hint}"
                    )
                    return
                else:
                    # Calculate how close they are as a percentage
                    closeness = (target / guess) * 100
                    hint = ""
                    
                    if closeness >= 90:
                        hint = "You're very close! 🔥"
                    elif closeness >= 75:
                        hint = "Getting warmer! 🌡️"
                    
                    await update.message.reply_markdown(
                        f"*{guess}* is too high! Try *lower* ⬇️\n{hint}"
                    )
                    return
            except ValueError:
                # Not a valid number
                pass

        # Process URLs (TikTok, Instagram, YouTube)
        if helpers.is_valid_url(user_message):
            from services.social_media_service import SocialMediaService
            
            # Check for TikTok and Instagram URLs
            platform = SocialMediaService.identify_platform(user_message)
            if platform == 'tiktok':
                # Send a processing message first
                status_message = await update.message.reply_text("⏳ *Processing TikTok Video*\n\nDownloading and removing watermark...", parse_mode="Markdown")
                
                # Download the video
                result, error = await SocialMediaService.download_video(user_message)
                
                if not result or error:
                    # Delete the status message
                    try:
                        await status_message.delete()
                    except Exception:
                        pass
                        
                    await update.message.reply_markdown(
                        f"❌ *Download Failed*\n\n"
                        f"Sorry, I couldn't download this TikTok content: {error or 'Unknown error'}\n\n"
                        f"This might be due to TikTok's restrictions or a problem with the URL."
                    )
                    return
                    
                # Check if result is a directory (for TikTok slide posts)
                if os.path.isdir(result):
                    # This is a slide post with multiple media files
                    await status_message.edit_text("✅ Downloaded TikTok slides. Sending them now...")
                    
                    # Get all files in the directory
                    media_files = []
                    for filename in sorted(os.listdir(result)):
                        file_path = os.path.join(result, filename)
                        
                        # Skip non-media files and files that are too large
                        if os.path.isdir(file_path) or filename.endswith('.json'):
                            continue
                        
                        file_size = os.path.getsize(file_path)
                        if file_size > 50 * 1024 * 1024:  # 50MB limit for Telegram
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
                                    [InlineKeyboardButton("🎵 Extract Audio", callback_data=f"extract_sm_audio:tiktok:{user_message}")]
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
                    
                    # Delete the status message
                    try:
                        await status_message.delete()
                    except Exception:
                        pass
                    
                    # Clean up the directory
                    import shutil
                    shutil.rmtree(result)
                    
                else:
                    # Regular single video file
                    # Check file size
                    file_size = os.path.getsize(result)
                    if file_size > 50 * 1024 * 1024:  # 50MB limit for Telegram
                        # Delete the status message
                        try:
                            await status_message.delete()
                        except Exception:
                            pass
                            
                        await update.message.reply_markdown(
                            f"❌ *File Too Large*\n\n"
                            f"The video file is too large ({file_size / (1024 * 1024):.1f} MB) to send via Telegram.\n"
                            f"Maximum allowed size is 50 MB."
                        )
                        # Clean up the file
                        os.remove(result)
                        return
                    
                    # Add extract audio button
                    keyboard = [
                        [InlineKeyboardButton("🎵 Extract Audio", callback_data=f"extract_sm_audio:tiktok:{user_message}")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    # Delete the status message
                    try:
                        await status_message.delete()
                    except Exception:
                        pass
                    
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
                
                return
            elif platform == 'instagram':
                # Create a message with options to download video or audio
                # Inline keyboard imports moved to top of file
                
                keyboard = [
                    [InlineKeyboardButton("📥 Download Video", callback_data=f"download_sm_video:instagram:{user_message}")],
                    [InlineKeyboardButton("🎵 Extract Audio", callback_data=f"extract_sm_audio:instagram:{user_message}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"📱 *Instagram Content Detected*\nUse the buttons below to download video or extract audio",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                return
            
            # Check for YouTube URL
            if helpers.is_youtube_url(user_message):
                context.args = [user_message]
                await youtube_command(update, context)
                return

        # Skip processing for group messages unless bot is mentioned or replied to
        if chat_type in ['group', 'supergroup']:
            is_mentioned = False
            if bot_username:
                is_mentioned = f"@{bot_username}" in user_message

            is_reply_to_bot = (
                update.message.reply_to_message and 
                update.message.reply_to_message.from_user.id == context.bot.id
            )

            if not (is_mentioned or is_reply_to_bot):
                return

        # Add message to counter
        message_counter.add_message()

        # Add message to conversation context
        conversation_manager.add_message(user_id, "user", user_message)
        conversation_context = conversation_manager.get_context(user_id)

        await context.bot.send_chat_action(chat_id=update.message.chat_id, action='typing')

        async with AIApiClient() as ai_client:
            ai_response = await ai_client.get_response(conversation_context)

            if ai_response:
                conversation_manager.add_message(user_id, "assistant", ai_response)
                await update.message.reply_text(ai_response)
            else:
                error_message = (
                    "I apologize, but I couldn't generate a response at the moment. "
                    "Please try again in a few moments."
                )
                await update.message.reply_text(error_message)

    except Exception as e:
        logger.error(f"Error in handle_message: {str(e)}")
        await update.message.reply_text(
            "Sorry, I encountered an error while processing your message. "
            "Please try again in a moment."
        )

async def handle_chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle updates to chat members (including bot joins)."""
    try:
        if update.my_chat_member and update.my_chat_member.new_chat_member:
            new_status = update.my_chat_member.new_chat_member.status
            chat_id = update.effective_chat.id
            logger.info(f"Chat member update in chat {chat_id}, new status: {new_status}")

            # Check if bot was added to a group
            if new_status == "member" and update.effective_chat.type in ['group', 'supergroup']:
                logger.info(f"Bot was added to group {chat_id}")
                
                # Inform the group
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"Thanks for adding me! You can mention me or reply to my messages for assistance!"
                )

    except Exception as e:
        logger.error(f"Error in chat member update handler: {str(e)}")

def create_bot():
    """Create and configure the bot with all necessary handlers."""
    # Get the bot token from environment variable
    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set")
    
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_context))
    application.add_handler(CommandHandler("context", show_context))
    application.add_handler(CommandHandler("admins", show_admins))
    application.add_handler(CommandHandler("total", total_messages_today))
    application.add_handler(CommandHandler("ttotal", total_messages_year))
    application.add_handler(CommandHandler("fun", fun_command))
    application.add_handler(CommandHandler("img", image_search))
    application.add_handler(CommandHandler("write", convert_to_handwritten))
    application.add_handler(CommandHandler("tiktok", tiktok_command))
    application.add_handler(CommandHandler("instagram", instagram_command))
    
    # Add new command handlers
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("scrape", scrape_command))
    application.add_handler(CommandHandler("youtube", youtube_command))
    application.add_handler(CommandHandler("analyze", analyze_command))
    
    # Add photo handler
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Add chat member update handler
    application.add_handler(ChatMemberHandler(handle_chat_member_update, ChatMemberHandler.MY_CHAT_MEMBER))
    
    # Process all text messages with AI response handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    return application

def error_handler(update, context):
    """Log the error and send a message to the user."""
    logger.error(f"Update {update} caused error {context.error}")
    
    # Send error message to user
    if update and update.effective_chat:
        context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="Sorry, an error occurred while processing your request. Please try again."
        )
