"""
Bot initialization and setup.
"""
import os
import sys
import logging
import asyncio
import time
import re
import json
import random
from typing import Dict, List, Tuple, Set, Optional, Any

# For dealing with Telegram's async deprecation warnings
import nest_asyncio
nest_asyncio.apply()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler
from telegram.ext import filters, ContextTypes, ChatMemberHandler

from api_client import AIApiClient
from conversation import ConversationManager
from message_counter import MessageCounter
import handlers.betting_handlers
import handlers.translate_handlers
import handlers.message_handlers
import handlers.photo_handlers
import handlers.game_handlers
import handlers.command_handlers
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
from handlers.game_handlers import checkers_command, end_checkers_command, move_checkers_command, handle_checkers_callback, handle_checkers_move_message

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
        "• Play games with virtual betting\n"
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
        # Games & Betting button
        [
            InlineKeyboardButton("💰 Check Wallet", callback_data="start_wallet"),
            InlineKeyboardButton("🎮 Betting Games", callback_data="help_betting")
        ],
        [
            InlineKeyboardButton("♟️ Play Checkers", callback_data="help_checkers"),
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
        "• /start - Start the bot and see welcome message\n"
        "• /clear - Clear your conversation history\n"
        "• /context - See your current conversation context\n\n"
        
        "*Media & Downloads*\n"
        "• /tiktok <url> - Download TikTok videos without watermark\n"
        "• /instagram <url> - Download Instagram videos/reels\n"
        "• /youtube <url> - Process YouTube videos\n\n"
        
        "*Information Tools*\n"
        "• /search <query> - Search the web for recent information\n"
        "• /scrape <url> - Extract content from a website\n"
        "• /img <search> - Search and send random images\n\n"
        
        "*Image Analysis*\n"
        "• Send any photo - Automatically analyze objects, text, and content\n"
        "• /analyze - Reply to a photo with this command to analyze it\n\n"
        
        "*Games & Fun*\n"
        "• /checkers [@username] - Play a game of checkers\n"
        "• /move A3-B4 - Make a move in your checkers game\n"
        "• /endcheckers - End the current checkers game\n"
        "• /fun - Play a number guessing game\n"
        "• /wallet - Check your virtual wallet balance\n"
        "• /resetwallet - Reset your wallet to default\n"
        "• /bet <game> <amount> [solo] - Start a betting game\n\n"
        
        "*Quick Betting Games*\n"
        "• /dice [amount] - Play a single-player dice roll game\n"
        "• /coin [amount] - Play a single-player coin flip game\n"
        "• /number [amount] - Play a single-player number guessing game\n"
        "• /rps [amount] - Play rock-paper-scissors against the bot\n"
        "  Default bet: 100 credits if amount not specified\n\n"
        
        "*Creative & Utilities*\n"
        "• /write <text> - Convert text to handwritten style\n"
        "• /insult @username - Generate a humorous roast for someone\n"
        "• /calculate 2+2*3 - Solve mathematical expressions\n"
        "• /total - Show total messages today\n"
        "• /ttotal - Show total messages this year\n"
        "• /admins - View group administrators (groups only)\n\n"
        
        "*Checkers Game Commands*\n"
        "• /checkers - Play against AI\n"
        "• /checkers @username - Challenge another user\n"
        "• /move A3-B4 - Move a piece (A3 to B4)\n"
        "• /endcheckers - End the current game\n\n"
        
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
            InlineKeyboardButton("🔍 Search Tools", callback_data="help_info")
        ],
        [
            InlineKeyboardButton("♟️ Games", callback_data="help_games"),
            InlineKeyboardButton("🎮 Fun Features", callback_data="help_fun")
        ],
        [
            InlineKeyboardButton("🖼️ Image Features", callback_data="help_image"),
            InlineKeyboardButton("🧮 Utilities", callback_data="help_utilities")
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
        
    # Store unique image search ID for this chat to track searches
    chat_id = update.effective_chat.id
    
    # Generate a unique timestamp for this search
    import time
    timestamp = int(time.time())
    
    # Get the original search term
    original_search_term = " ".join(context.args)
    search_term = original_search_term
    
    # Create a unique search key incorporating chat_id
    search_key = f"{chat_id}_{original_search_term.lower().replace(' ', '_')}"
    
    # Track search history for this chat/term to ensure variety
    # Format: {'term_key': {'last_search': timestamp, 'previous_links': [list of links]}}
    if 'image_search_history' not in context.chat_data:
        context.chat_data['image_search_history'] = {}
        
    # Adjust the search term if we've seen this search before
    import random
    search_history = context.chat_data['image_search_history']
    if search_key in search_history:
        # If the same search has been used recently, add variety
        time_since_last = timestamp - search_history[search_key].get('last_search', 0)
        
        # If searched within the last hour, add variety to the query
        if time_since_last < 3600:  # 3600 seconds = 1 hour
            # This is a repeated search, add variety
            modifiers = ["beautiful", "amazing", "colorful", "awesome", "cool", 
                         "recent", "best", "popular", "wonderful", "gorgeous",
                         "newest", "trending", "top rated", "excellent"]
            random_modifier = random.choice(modifiers)
            
            # Higher chance to add a modifier for frequent searches
            if time_since_last < 300:  # If within 5 minutes
                modifier_chance = 0.9
            else:
                modifier_chance = 0.7
                
            if random.random() < modifier_chance:
                search_term = f"{random_modifier} {search_term}"
                logger.info(f"Recent search detected, modified to: {search_term}")
    
    # Start with a search status message
    status_message = await update.message.reply_text(
        f"🔍 Searching for images of '*{original_search_term}*'...", 
        parse_mode="Markdown"
    )
    
    try:
        from services.google_search import GoogleSearchService
        
        # Generate a more varied random seed based on chat, user, and timestamp
        seed_value = (chat_id + update.effective_user.id + timestamp) % 1000
        
        # Get more results than needed so we can filter out duplicates and select random ones
        logger.info(f"Searching for images: {search_term} with seed {seed_value}")
        
        # Our enhanced Google search will already try multiple strategies if needed
        results = await GoogleSearchService.image_search(search_term, num_results=10)
        logger.info(f"Image search results count: {len(results)}")
        
        # Try to delete the status message regardless of result
        try:
            await status_message.delete()
        except Exception:
            # If we can't delete, we'll just ignore the error and continue
            pass
        
        if not results:
            await update.message.reply_markdown(
                "🔍 *Image Search Results*\n\n"
                f"❌ No images found for '*{original_search_term}*'.\n\n"
                "Please try a different search term."
            )
            return
            
        # Send up to 4 images in a group
        media_group = []
        valid_items = []
        selected_links = []
        
        # Get previously used links for this search term (if any)
        previous_links = []
        if search_key in search_history:
            previous_links = search_history[search_key].get('previous_links', [])
        
        # First collect all valid image links that haven't been sent recently
        logger.info(f"Processing {len(results)} image results")
        for i, item in enumerate(results):
            if 'link' in item:
                try:
                    link = item['link']
                    
                    # Skip if this link was recently sent to this chat for the same search
                    if link in previous_links:
                        logger.info(f"Skipping previously sent image: {link[:30]}...")
                        continue
                        
                    # Validate the link can be used as InputMediaPhoto
                    logger.info(f"Found valid image link {i+1}: {link[:30]}...")
                    InputMediaPhoto(link)
                    valid_items.append(item)
                except Exception as e:
                    # Skip any problematic URLs
                    logger.error(f"Invalid image link {i+1}: {str(e)}")
                    continue
        
        # If no new images found but we have results, allow reuse of previous links
        if not valid_items and results:
            logger.info("No new images found, using some previous links")
            for i, item in enumerate(results):
                if 'link' in item:
                    try:
                        # Validate the link can be used
                        InputMediaPhoto(item['link'])
                        valid_items.append(item)
                    except:
                        continue
        
        # If we have valid items, select up to 4
        if valid_items:
            logger.info(f"Collected {len(valid_items)} valid image items")
            # Shuffle to randomize selection
            random.shuffle(valid_items)
            logger.info(f"Shuffled valid items, now selecting up to 4")
            
            # Take up to 4 random images
            for i, item in enumerate(valid_items[:4]):
                link = item['link']
                logger.info(f"Adding image {i+1} to media group: {link[:30]}...")
                media_group.append(InputMediaPhoto(link))
                selected_links.append(link)
                    
        if media_group:
            try:
                # Send the media group
                await context.bot.send_media_group(
                    chat_id=update.effective_chat.id,
                    media=media_group
                )
                
                # Update search history with timestamp and links
                context.chat_data['image_search_history'][search_key] = {
                    'last_search': timestamp,
                    'previous_links': selected_links + previous_links[:20]  # Keep last ~24 links (6 searches x 4 images)
                }
                
            except Exception as e:
                logger.error(f"Error sending media group: {str(e)}")
                # Try to send images one by one if group fails
                sent_count = 0
                successful_links = []
                
                # Get a random selection if we have more than 3 for fallback
                fallback_group = media_group[:3]  # Limit to 3 on fallback
                
                for item in fallback_group:
                    try:
                        await context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=item.media
                        )
                        sent_count += 1
                        successful_links.append(item.media)
                    except Exception as e:
                        logger.error(f"Error sending individual photo: {str(e)}")
                        continue
                
                # Update history with the links that were actually sent
                if successful_links:
                    context.chat_data['image_search_history'][search_key] = {
                        'last_search': timestamp,
                        'previous_links': successful_links + previous_links[:20]
                    }
        else:
            await update.message.reply_markdown(
                "🔍 *Image Search Results*\n\n"
                f"⚠️ Found search results for '*{original_search_term}*' but couldn't retrieve valid images.\n\n"
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

async def insult_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate a humorous insult for a specified user"""
    if not context.args:
        await update.message.reply_markdown(
            "😈 *Insult Generator*\n\n"
            "Please provide a username after /insult\n\n"
            "Example: `/insult @username`\n\n"
            "I'll create a humorous roast for that person!"
        )
        return
        
    # Get the target username
    target = context.args[0]
    
    # Make sure it's a username mention format
    if not target.startswith('@'):
        target = '@' + target
        
    # List of funny, creative insults
    insults = [
        f"{target} is so boring, sleeping pills take them to fall asleep.",
        f"{target}'s selfies are the reason phones have a self-destruct option.",
        f"{target} is the human version of a participation award.",
        f"{target} is so bad at taking selfies, their phone automatically switches to the settings app.",
        f"I'd roast {target}, but my mom told me not to burn trash because it's bad for the environment.",
        f"{target} has such a way with words... too bad it's the wrong way.",
        f"{target} is proof that evolution can go in reverse.",
        f"If {target} was a spice, they'd be flour.",
        f"{target} is like a cloud - when they disappear, it's a beautiful day.",
        f"{target}'s cooking is the reason doorbells were invented.",
        f"{target} is so out of shape, they get tired walking to the refrigerator.",
        f"{target} is the reason why shampoo has instructions.",
        f"{target} is like a broken calculator - they can't even count on themselves.",
        f"{target} is the type to get lost in a grocery store and call for help.",
        f"{target} is so lazy, they have a remote control for their remote control.",
        f"{target} has a face only a mother could love... from a distance.",
        f"{target} thinks 'getting some fresh air' means opening the refrigerator.",
        f"{target} has a perfect face for radio and a perfect voice for silent films.",
        f"{target} has such a unique fashion sense - it's like they got dressed in the dark... during an earthquake.",
        f"If brains were dynamite, {target} wouldn't have enough to blow their nose.",
        f"{target} is as useful as a screen door on a submarine.",
        f"{target} is so old, their memory is in black and white.",
        f"{target} is so slow, they take 2 hours to watch 60 Minutes.",
        f"{target} is the reason why aliens won't talk to us.",
        f"{target} has delusions of adequacy.",
        f"{target} is living proof that nature sometimes makes mistakes.",
        f"{target} has all the charm and charisma of a dead fish.",
        f"{target}'s room is so dirty, they need a tetanus shot just to make their bed.",
        f"{target} is so predictable, fortune tellers charge them half price.",
        f"{target} is like a broken pencil - pointless.",
        f"{target} is so uninteresting, their imaginary friends ghosted them.",
        f"{target} dances like they're being electrocuted.",
        f"{target} sings like they're gargling mouthwash.",
        f"{target} has the fashion sense of a colorblind scarecrow.",
        f"{target} types with just their index fingers.",
        f"{target} eats pizza with a fork and knife.",
        f"{target} still uses Internet Explorer... by choice.",
        f"{target} couldn't pour water out of a boot if the instructions were on the heel.",
        f"{target} has fewer followers than a broken compass.",
        f"{target} is as deep as a parking lot puddle.",
        f"{target} dresses like they got their clothes from a dumpster behind a clown college.",
        f"{target} is so basic, they make plain yogurt look spicy.",
        f"{target} has the coordination of a newborn giraffe on an ice rink.",
        f"{target} has the charm of a mosquito at a blood bank.",
        f"{target} looks like they were drawn by a 5-year-old using their non-dominant hand.",
        f"{target} is about as useful as a chocolate teapot.",
        f"{target} has a face that would make an onion cry.",
        f"{target} has the personality of unseasoned boiled chicken.",
        f"{target} is like elevator music - annoying and forgettable.",
        f"{target} has all the appeal of a gas station bathroom."
    ]
    
    # Select a random insult
    import random
    insult = random.choice(insults)
    
    # Send just the insult with no extra text
    await update.message.reply_text(f"{insult}")

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

async def calculate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Calculate the result of a mathematical expression"""
    import re
    
    if not context.args:
        await update.message.reply_markdown(
            "🧮 *Calculator*\n\n"
            "Please provide a math expression after /calculate\n\n"
            "Example: `/calculate 2 + 2 * 3`\n\n"
            "I can handle basic operations like +, -, *, /, as well as parentheses and exponents (^)."
        )
        return
    
    expression = ' '.join(context.args)
    result = calculate_expression(expression)
    
    if result is not None:
        await update.message.reply_text(f"🧮 {expression} = {result}")
    else:
        await update.message.reply_text("❌ Invalid math expression. Please check your syntax.")

def calculate_expression(expression):
    """Calculate the result of a mathematical expression."""
    try:
        # Replace ^ with ** for exponentiation
        expression = expression.replace('^', '**')
        
        # Use safer eval by creating a local dict with only math functions
        import math
        import operator
        from decimal import Decimal
        
        # Define allowed functions and operators
        safe_dict = {
            'abs': abs, 'round': round,
            'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
            'asin': math.asin, 'acos': math.acos, 'atan': math.atan,
            'sqrt': math.sqrt, 'log': math.log, 'log10': math.log10,
            'pi': math.pi, 'e': math.e,
            'Decimal': Decimal
        }
        
        # Add basic operators
        safe_dict.update({k: getattr(operator, k) for k in [
            'add', 'sub', 'mul', 'truediv', 'pow', 'mod', 'floordiv'
        ]})
        
        # Check for unsafe constructs
        if any(keyword in expression for keyword in [
            'import', 'eval', 'exec', 'compile', 'globals', 'locals',
            'getattr', 'setattr', 'delattr', '__'
        ]):
            return None
        
        # Convert the expression to use safer functions
        sanitized_expr = expression
        sanitized_expr = sanitized_expr.replace('+', 'add(')
        sanitized_expr = sanitized_expr.replace('-', 'sub(')
        sanitized_expr = sanitized_expr.replace('*', 'mul(')
        sanitized_expr = sanitized_expr.replace('/', 'truediv(')
        sanitized_expr = sanitized_expr.replace('%', 'mod(')
        sanitized_expr = sanitized_expr.replace('//', 'floordiv(')
        
        # Unfortunately, this approach gets complex with nested expressions
        # So let's use direct eval with some safeguards
        
        # Simple security check: only allow specific characters
        if not re.match(r'^[0-9\.\+\-\*\/\(\)\^\s%]*$', expression):
            return None
            
        result = eval(expression)
        return result
        
    except Exception as e:
        logger.error(f"Error calculating expression: {str(e)}")
        return None

async def langs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show a list of supported languages for translation.
    Format: /langs
    """
    from services.translate_service import TranslationService
    
    # Get supported languages
    languages = TranslationService.get_supported_languages()
    
    # Format the message with languages in columns
    formatted_langs = []
    for code, name in sorted(languages.items(), key=lambda x: x[1]):
        formatted_langs.append(f"• {name.title()} (`{code}`)")
    
    # Split into chunks for better readability
    chunk_size = 20
    chunks = [formatted_langs[i:i + chunk_size] for i in range(0, len(formatted_langs), chunk_size)]
    
    # Create message text with all languages
    message_text = "🌐 *Supported Translation Languages*\n\n"
    
    for i, chunk in enumerate(chunks, 1):
        message_text += f"*Page {i}/{len(chunks)}*\n"
        message_text += "\n".join(chunk[:chunk_size]) + "\n\n"
    
    # Add usage examples
    message_text += "*Usage Examples:*\n"
    message_text += "• `/tl Hello world` - Auto-detect and translate to English\n"
    message_text += "• `/tl ja Hello world` - Translate to Japanese\n"
    message_text += "• `/tl fr//en Bonjour` - Translate from French to English\n"
    message_text += "• Reply to a message with `/tl` to translate it to English\n"
    
    # Send the message in chunks if it's too long
    max_length = 4000
    if len(message_text) > max_length:
        text_parts = [message_text[i:i + max_length] for i in range(0, len(message_text), max_length)]
        for part in text_parts:
            await update.message.reply_markdown(part)
    else:
        await update.message.reply_markdown(message_text)

async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /tl command to translate text.
    
    Formats:
    - /tl <text> (auto-detects source language, translates to English)
    - /tl <lang> <text> (translates to specified language)
    - /tl <source>//<dest> <text> (translates from source to destination language)
    - Reply to a message with /tl (translates the replied message to English)
    - Reply with /tl <lang> (translates to specified language)
    - Reply with /tl <source>//<dest> (translates from source to destination language)
    """
    # Check if it's a reply to another message
    is_reply = update.message.reply_to_message is not None
    
    if not context.args and not is_reply:
        # No arguments and not a reply - show help
        await show_translation_help(update)
        return
    
    # Extract the text to translate and the target language
    text_to_translate = None
    target_language = 'en'  # Default to English
    source_language = 'auto'  # Default to auto-detect
    
    if context.args:
        # Check if the first argument contains source//dest format
        first_arg = context.args[0].lower()
        if '//' in first_arg:
            parts = first_arg.split('//')
            if len(parts) == 2:
                source_language = parts[0]
                target_language = parts[1]
                # Rest of arguments form the text
                if len(context.args) > 1:
                    text_to_translate = ' '.join(context.args[1:])
        # Check if the first argument is a language code
        elif 2 <= len(first_arg) <= 8:  # Allow longer codes like 'zh-cn'
            target_language = first_arg
            # Rest of arguments form the text
            if len(context.args) > 1:
                text_to_translate = ' '.join(context.args[1:])
        else:
            # First argument is not a language code, so the entire args is the text
            text_to_translate = ' '.join(context.args)
    
    # If we're replying to a message, get text from that
    if is_reply and not text_to_translate:
        replied_msg = update.message.reply_to_message
        text_to_translate = replied_msg.text or replied_msg.caption or ''
    
    if not text_to_translate:
        await update.message.reply_text(
            "❌ Please provide text to translate or reply to a message to translate it."
        )
        return
    
    # Send a "translating" status message
    status_message = await update.message.reply_text(
        f"🔄 Translating to {target_language}..."
    )
    
    try:
        # Perform the translation using the specified source and target languages
        translated_text = await translate_text(text_to_translate, target_language, source_language)
        
        # Try to delete the status message
        try:
            await status_message.delete()
        except Exception:
            pass
        
        # Create a language info message to display which languages were used
        lang_info = f"({source_language} → {target_language})"
        if source_language == "auto":
            lang_info = f"(auto → {target_language})"
        
        # Send the translation without buttons
        await update.message.reply_text(
            f"🌐 *Translation* {lang_info}\n\n{translated_text}",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Translation error: {e}")
        
        # Try to delete the status message
        try:
            await status_message.delete()
        except Exception:
            pass
        
        # Send error message
        await update.message.reply_text(
            "❌ Translation failed. Please try again later or with different text."
        )

async def show_translation_help(update: Update) -> None:
    """Show help information for the translation command."""
    help_text = (
        "🌐 *Translation Help*\n\n"
        "*Usage:*\n"
        "• `/tl Hello world` - Auto-detect and translate to English\n"
        "• `/tl es Hello world` - Translate to Spanish\n"
        "• `/tl fr//en Bonjour` - Translate from French to English\n"
        "• Reply to any message with `/tl` - Translate to English\n"
        "• Reply with `/tl fr` - Translate to French\n"
        "• Reply with `/tl ja//en` - Translate from Japanese to English\n"
        "• `/langs` - Show all supported languages\n\n"
        "*Some Language Codes:*\n"
        "• English: `en`\n"
        "• Spanish: `es`\n"
        "• French: `fr`\n"
        "• German: `de`\n"
        "• Russian: `ru`\n"
        "• Arabic: `ar`\n"
        "• Chinese: `zh-cn`\n"
        "• Japanese: `ja`\n"
        "• Amharic: `am`\n"
        "• Portuguese: `pt`\n"
        "• Hindi: `hi`"
    )
    
    # Send the help text without any buttons
    await update.message.reply_text(
        help_text,
        parse_mode="Markdown"
    )

async def translate_text(text: str, target_lang: str = 'en', source_lang: str = 'auto') -> str:
    """
    Simple function to translate text using Google Translate API.
    
    Args:
        text: The text to translate
        target_lang: The language to translate to
        source_lang: The source language (auto for auto-detection)
        
    Returns:
        The translated text
    """
    import urllib.parse
    import aiohttp
    import json
    
    try:
        # Use Google Translate's API to translate text
        async with aiohttp.ClientSession() as session:
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "dt": "t",
                "sl": source_lang,
                "tl": target_lang,
                "q": text
            }
            
            full_url = f"{url}?{urllib.parse.urlencode(params)}"
            async with session.get(full_url) as response:
                if response.status != 200:
                    logger.error(f"Translation failed: {response.status}")
                    raise Exception(f"Translation service returned status code {response.status}")
                
                data = await response.json(content_type=None)
                translated_parts = []
                
                # Extract translated text from the data structure
                for part in data[0]:
                    if part[0]:
                        translated_parts.append(part[0])
                
                return ''.join(translated_parts)
                
    except Exception as e:
        logger.error(f"Translation error: {e}")
        raise Exception(f"Error translating text: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user messages and respond using AI."""
    try:
        if not update.message or not update.message.text:
            return

        user_id = update.effective_user.id
        user_message = update.message.text
        chat_type = update.message.chat.type
        bot_username = context.bot.username
        
        # Check if it's a math expression (when bot is mentioned)
        is_mentioned = False
        if chat_type != "private":
            if update.message.entities:
                for entity in update.message.entities:
                    if entity.type == "mention" and user_message[entity.offset:entity.offset+entity.length] == f"@{bot_username}":
                        is_mentioned = True
                        break
        else:
            is_mentioned = True
            
        if is_mentioned:
            # Look for math expression patterns
            # Simple pattern: numbers and math operators
            import re  # Explicitly import re within this function scope
            expression_pattern = r'[-+]?[0-9]*\.?[0-9]+[\+\-\*\/\^%][0-9\+\-\*\/\^\(\)\.\s%]*'
            math_pattern = re.search(expression_pattern, user_message)
            
            if math_pattern:
                expression = math_pattern.group(0).strip()
                result = calculate_expression(expression)
                if result is not None:
                    await update.message.reply_text(f"🧮 {expression} = {result}")
                    return
        
        # First, check if this is a URL we can process
        from handlers.message_handlers import process_youtube_url, process_social_media_url
        from services.social_media_service import SocialMediaService
        from utils.helpers import is_youtube_url
        
        # Check if the message contains a URL
        import re  # Make sure re is imported here as well
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
    application.add_handler(CommandHandler("insult", insult_command))
    application.add_handler(CommandHandler("calculate", calculate_command))
    application.add_handler(CommandHandler("tl", translate_command))
    application.add_handler(CommandHandler("langs", langs_command))
    
    # Add new command handlers
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("scrape", scrape_command))
    application.add_handler(CommandHandler("wallet", handlers.betting_handlers.wallet_command))
    application.add_handler(CommandHandler("resetwallet", handlers.betting_handlers.reset_wallet_command))
    application.add_handler(CommandHandler("bet", handlers.betting_handlers.bet_command))
    
    # Add direct game command handlers
    application.add_handler(CommandHandler("dice", handlers.betting_handlers.dice_command))
    application.add_handler(CommandHandler("coin", handlers.betting_handlers.coin_command))
    application.add_handler(CommandHandler("number", handlers.betting_handlers.number_command))
    application.add_handler(CommandHandler("rps", handlers.betting_handlers.rps_command))
    
    application.add_handler(CommandHandler("youtube", youtube_command))
    application.add_handler(CommandHandler("analyze", analyze_command))
    
    # Add checkers game handlers
    application.add_handler(CommandHandler("checkers", checkers_command))
    application.add_handler(CommandHandler("endcheckers", end_checkers_command))
    application.add_handler(CommandHandler("move", move_checkers_command))
    
    # Add photo handler
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Add callback query handlers
    application.add_handler(CallbackQueryHandler(handle_checkers_callback, pattern=r"^(join_checkers|move_checkers)"))
    
    # Add betting game callback handler
    application.add_handler(CallbackQueryHandler(
        handlers.betting_handlers.handle_betting_callback,
        pattern=r"^(join_betting_game|betting_game_move|cancel_betting_game)"
    ))
    
    application.add_handler(CallbackQueryHandler(handle_callback))  # Fallback for all other callbacks
    
    # Add chat member update handler
    application.add_handler(ChatMemberHandler(handle_chat_member_update, ChatMemberHandler.MY_CHAT_MEMBER))
    
    # Process all text messages - first try to handle checkers moves in private chats
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        lambda update, context: handle_private_message(update, context)
    ))
    
    # Process all remaining text messages with AI response handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    return application

async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Handler for private messages - tries to handle game moves first.
    Returns True if message was handled, False otherwise.
    """
    # First check if it's a checkers move
    if await handle_checkers_move_message(update, context):
        return True
    
    # Add any other game message handlers here
    # No need to add betting game logic here since it uses buttons exclusively
    
    # If not handled by any game, let it fallthrough to the next handler
    return False

def error_handler(update, context):
    """Log the error and send a message to the user."""
    logger.error(f"Update {update} caused error {context.error}")
    
    # Send error message to user
    if update and update.effective_chat:
        context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="Sorry, an error occurred while processing your request. Please try again."
        )
