"""
Translation handlers for the Telegram bot.
"""
import logging
import re
from typing import Optional, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from services.translate_service import TranslationService

logger = logging.getLogger(__name__)

# Regular expression to extract language code and text
# Matches: 
# - /tl en Hello world or /tl en (standard format)
# - /tl ja//en Hello world (source//dest format)
LANG_PATTERN = re.compile(r'^(?P<lang>\w{2,8})(?:\s+(?P<text>.+))?$')
SOURCE_DEST_PATTERN = re.compile(r'^(?P<source>\w{2,8})//(?P<dest>\w{2,8})(?:\s+(?P<text>.+))?$')

async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /tl command to translate text.
    
    Formats:
    - /tl <text> (auto-detects source language, translates to English)
    - /tl <lang_code> <text> (translates to specified language)
    - Reply to a message with /tl (translates the replied message to English)
    - Reply to a message with /tl <lang_code> (translates to specified language)
    
    Examples:
    - /tl Hello world (detect language, translate to English)
    - /tl es Hello world (translate to Spanish)
    - /tl fr (reply to message, translate to French)
    """
    # Check if it's a reply to another message
    is_reply = update.message.reply_to_message is not None
    
    if not context.args and not is_reply:
        # No arguments and not a reply - show help
        await show_translation_help(update)
        return
    
    # Determine the text to translate and target language
    text_to_translate, target_language = await extract_translation_params(update, context)
    
    if not text_to_translate:
        # No text to translate found
        await update.message.reply_text(
            "❌ Please provide text to translate or reply to a message to translate it."
        )
        return
    
    # Send a "translating" status message
    status_message = await update.message.reply_text(
        f"🔄 Translating to {target_language}..."
    )
    
    try:
        # Get the translation
        result = await TranslationService.translate_text(
            text=text_to_translate, 
            dest_language=target_language
        )
        
        # Create the response message
        translated_text = result['translated_text']
        src_lang_name = result['src_language_name']
        dest_lang_name = result['dest_language_name']
        
        response = (
            f"🌐 *Translation:* {src_lang_name} → {dest_lang_name}\n\n"
            f"{translated_text}"
        )
        
        # Create buttons for other common languages
        keyboard = []
        
        # Row 1: Common languages
        row1 = []
        if result['dest_language'] != 'en':
            row1.append(InlineKeyboardButton("🇬🇧 English", callback_data=f"translate:en:{result['src_language']}"))
        if result['dest_language'] != 'es':
            row1.append(InlineKeyboardButton("🇪🇸 Spanish", callback_data=f"translate:es:{result['src_language']}"))
        if result['dest_language'] != 'fr':
            row1.append(InlineKeyboardButton("🇫🇷 French", callback_data=f"translate:fr:{result['src_language']}"))
        if row1:
            keyboard.append(row1)
        
        # Row 2: More languages
        row2 = []
        if result['dest_language'] != 'de':
            row2.append(InlineKeyboardButton("🇩🇪 German", callback_data=f"translate:de:{result['src_language']}"))
        if result['dest_language'] != 'ru':
            row2.append(InlineKeyboardButton("🇷🇺 Russian", callback_data=f"translate:ru:{result['src_language']}"))
        if result['dest_language'] != 'ar':
            row2.append(InlineKeyboardButton("🇸🇦 Arabic", callback_data=f"translate:ar:{result['src_language']}"))
        if row2:
            keyboard.append(row2)
            
        # Row 3: Special languages based on common usage or user's query
        row3 = []
        if 'am' not in [result['dest_language'], result['src_language']]:
            row3.append(InlineKeyboardButton("🇪🇹 Amharic", callback_data=f"translate:am:{result['src_language']}"))
        if 'zh-cn' not in [result['dest_language'], result['src_language']]:
            row3.append(InlineKeyboardButton("🇨🇳 Chinese", callback_data=f"translate:zh-cn:{result['src_language']}"))
        if 'ja' not in [result['dest_language'], result['src_language']]:
            row3.append(InlineKeyboardButton("🇯🇵 Japanese", callback_data=f"translate:ja:{result['src_language']}"))
        if row3:
            keyboard.append(row3)
        
        # Add a "Show more languages" button
        keyboard.append([InlineKeyboardButton("🌐 More Languages", callback_data="translate:language_list")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Try to delete the status message
        try:
            await status_message.delete()
        except Exception:
            # If deletion fails, just continue
            pass
        
        # Send the translation with reply markup
        await update.message.reply_text(
            response,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Translation error: {e}")
        
        # Try to delete the status message
        try:
            await status_message.delete()
        except Exception:
            # If deletion fails, just continue
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
        "• `/tl Hello world` - Detect language and translate to English\n"
        "• `/tl es Hello world` - Translate to Spanish\n"
        "• Reply to any message with `/tl` - Translate to English\n"
        "• Reply with `/tl fr` - Translate to French\n\n"
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
        "• Hindi: `hi`\n"
        "• And many more..."
    )
    
    # Create a keyboard with common language options
    keyboard = [
        [
            InlineKeyboardButton("🇬🇧 English", callback_data="translate:en:auto"),
            InlineKeyboardButton("🇪🇸 Spanish", callback_data="translate:es:auto"),
            InlineKeyboardButton("🇫🇷 French", callback_data="translate:fr:auto")
        ],
        [
            InlineKeyboardButton("🇩🇪 German", callback_data="translate:de:auto"),
            InlineKeyboardButton("🇷🇺 Russian", callback_data="translate:ru:auto"),
            InlineKeyboardButton("🇸🇦 Arabic", callback_data="translate:ar:auto")
        ],
        [
            InlineKeyboardButton("🇨🇳 Chinese", callback_data="translate:zh-cn:auto"),
            InlineKeyboardButton("🇯🇵 Japanese", callback_data="translate:ja:auto"),
            InlineKeyboardButton("🇪🇹 Amharic", callback_data="translate:am:auto")
        ],
        [
            InlineKeyboardButton("🌐 All Languages", callback_data="translate:language_list")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def handle_translate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Handle translation-related callbacks.
    Returns True if callback was handled, False otherwise.
    """
    query = update.callback_query
    
    # Check if this is a translation callback
    if not query.data.startswith("translate:"):
        return False
    
    await query.answer()
    
    # Extract parameters from callback data
    # Format: translate:target_lang:source_lang
    parts = query.data.split(":")
    
    if len(parts) < 2:
        await query.edit_message_text("Invalid translation callback format.")
        return True
        
    action = parts[1]
    
    if action == "language_list":
        # Show language list
        await show_language_list(query)
        return True
    
    # Handle translation request
    # Format: translate:target_lang:source_lang
    if len(parts) >= 3:
        target_lang = parts[1]
        source_lang = parts[2]
        
        # Get original text (from original message text, removing the header)
        original_text = query.message.text
        
        # Extract only the translated text portion by removing the header
        if "🌐 *Translation:*" in original_text:
            text_parts = original_text.split("\n\n", 1)
            if len(text_parts) > 1:
                original_text = text_parts[1]
        
        # Perform new translation with updated target language
        status_text = f"🔄 Translating to {target_lang}..."
        await query.edit_message_text(status_text)
        
        try:
            # If source language is "auto", set it to None for auto-detection
            src_lang = None if source_lang == "auto" else source_lang
            
            result = await TranslationService.translate_text(
                text=original_text,
                dest_language=target_lang,
                src_language=src_lang
            )
            
            # Create the response message
            translated_text = result['translated_text']
            src_lang_name = result['src_language_name']
            dest_lang_name = result['dest_language_name']
            
            response = (
                f"🌐 *Translation:* {src_lang_name} → {dest_lang_name}\n\n"
                f"{translated_text}"
            )
            
            # Create buttons for other common languages (similar to original function)
            keyboard = []
            
            # Row 1: Common languages
            row1 = []
            if result['dest_language'] != 'en':
                row1.append(InlineKeyboardButton("🇬🇧 English", callback_data=f"translate:en:{result['src_language']}"))
            if result['dest_language'] != 'es':
                row1.append(InlineKeyboardButton("🇪🇸 Spanish", callback_data=f"translate:es:{result['src_language']}"))
            if result['dest_language'] != 'fr':
                row1.append(InlineKeyboardButton("🇫🇷 French", callback_data=f"translate:fr:{result['src_language']}"))
            if row1:
                keyboard.append(row1)
            
            # Row 2: More languages
            row2 = []
            if result['dest_language'] != 'de':
                row2.append(InlineKeyboardButton("🇩🇪 German", callback_data=f"translate:de:{result['src_language']}"))
            if result['dest_language'] != 'ru':
                row2.append(InlineKeyboardButton("🇷🇺 Russian", callback_data=f"translate:ru:{result['src_language']}"))
            if result['dest_language'] != 'ar':
                row2.append(InlineKeyboardButton("🇸🇦 Arabic", callback_data=f"translate:ar:{result['src_language']}"))
            if row2:
                keyboard.append(row2)
                
            # Row 3: Special languages
            row3 = []
            if 'am' not in [result['dest_language'], result['src_language']]:
                row3.append(InlineKeyboardButton("🇪🇹 Amharic", callback_data=f"translate:am:{result['src_language']}"))
            if 'zh-cn' not in [result['dest_language'], result['src_language']]:
                row3.append(InlineKeyboardButton("🇨🇳 Chinese", callback_data=f"translate:zh-cn:{result['src_language']}"))
            if 'ja' not in [result['dest_language'], result['src_language']]:
                row3.append(InlineKeyboardButton("🇯🇵 Japanese", callback_data=f"translate:ja:{result['src_language']}"))
            if row3:
                keyboard.append(row3)
            
            # Add a "Show more languages" button
            keyboard.append([InlineKeyboardButton("🌐 More Languages", callback_data="translate:language_list")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send the updated translation
            await query.edit_message_text(
                response,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Translation callback error: {e}")
            await query.edit_message_text(
                f"❌ Translation failed. Please try again later.\nError: {str(e)[:100]}"
            )
        
        return True
    
    return False

async def show_language_list(query) -> None:
    """Show a paginated list of available languages."""
    # Get all supported languages
    languages = TranslationService.get_supported_languages()
    
    # Create a formatted list of languages
    language_list = "🌐 *Available Languages*\n\n"
    
    # Sort languages by name
    sorted_languages = sorted(languages.items(), key=lambda x: x[1])
    
    # Get the original text (if it exists in the message)
    original_text = ""
    message_text = query.message.text
    
    # Check if we're showing the language list for an existing translation
    if "🌐 *Translation:*" in message_text:
        text_parts = message_text.split("\n\n", 1)
        if len(text_parts) > 1:
            original_text = text_parts[1]
    
    # Add languages to the message, grouped by first letter
    current_letter = None
    for code, name in sorted_languages:
        # Skip if code is auto (which isn't a real language)
        if code == 'auto':
            continue
            
        # Get the first letter of the language name
        first_letter = name[0].upper()
        
        # Add a header for a new letter
        if first_letter != current_letter:
            language_list += f"\n*{first_letter}*\n"
            current_letter = first_letter
        
        # Add the language with its code
        language_list += f"• {name.title()}: `{code}`\n"
    
    # Add usage instructions
    language_list += "\n*Usage:* `/tl [language_code] [text]`"
    
    # Create navigation buttons
    keyboard = [
        [InlineKeyboardButton("« Back to Translation", callback_data="translate:back")]
    ]
    
    # Add some common language buttons if we have original text
    if original_text:
        common_langs = [
            ("🇬🇧 English", "en"),
            ("🇪🇸 Spanish", "es"),
            ("🇫🇷 French", "fr"),
            ("🇩🇪 German", "de"),
            ("🇷🇺 Russian", "ru"),
            ("🇨🇳 Chinese", "zh-cn"),
            ("🇯🇵 Japanese", "ja"),
            ("🇪🇹 Amharic", "am")
        ]
        
        row1 = []
        row2 = []
        
        for i, (label, code) in enumerate(common_langs):
            button = InlineKeyboardButton(label, callback_data=f"translate:{code}:auto")
            if i < 4:
                row1.append(button)
            else:
                row2.append(button)
        
        if row1:
            keyboard.insert(0, row1)
        if row2:
            keyboard.insert(1, row2)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Update the message
    await query.edit_message_text(
        language_list,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def extract_translation_params(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Tuple[Optional[str], str]:
    """
    Extract the text to translate and the target language from the command.
    
    Returns:
        Tuple[Optional[str], str]: (text_to_translate, target_language)
    """
    is_reply = update.message.reply_to_message is not None
    
    # Default target language is English
    target_language = 'en'
    text_to_translate = None
    
    if context.args:
        # The command has arguments
        # Check if the first argument is a language code
        first_arg = context.args[0].lower()
        lang_match = TranslationService.get_language_code(first_arg)
        
        if lang_match:
            # First argument is a language code
            target_language = lang_match
            
            # Rest of the arguments form the text to translate
            if len(context.args) > 1:
                text_to_translate = ' '.join(context.args[1:])
            elif is_reply:
                # No text provided but it's a reply, use the replied message
                replied_msg = update.message.reply_to_message
                text_to_translate = replied_msg.text or replied_msg.caption or ''
        else:
            # First argument is not a language code, so the entire args is the text
            text_to_translate = ' '.join(context.args)
    elif is_reply:
        # No arguments but it's a reply, use the replied message and default to English
        replied_msg = update.message.reply_to_message
        text_to_translate = replied_msg.text or replied_msg.caption or ''
    
    return text_to_translate, target_language