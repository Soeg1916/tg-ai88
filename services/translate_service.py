"""
Translation service using direct HTTP requests to Google Translate API.
"""
import logging
import asyncio
import os
import json
from typing import Dict, Tuple, Optional, List
import urllib.parse
import random

# We're using aiohttp which should already be installed for the bot
try:
    import aiohttp
except ImportError:
    import subprocess
    subprocess.check_call(["pip", "install", "aiohttp"])
    import aiohttp

logger = logging.getLogger(__name__)

# Language dictionary with codes and names
LANGUAGES = {
    'af': 'afrikaans',
    'sq': 'albanian',
    'am': 'amharic',
    'ar': 'arabic',
    'hy': 'armenian',
    'az': 'azerbaijani',
    'eu': 'basque',
    'be': 'belarusian',
    'bn': 'bengali',
    'bs': 'bosnian',
    'bg': 'bulgarian',
    'ca': 'catalan',
    'ceb': 'cebuano',
    'ny': 'chichewa',
    'zh-cn': 'chinese (simplified)',
    'zh-tw': 'chinese (traditional)',
    'co': 'corsican',
    'hr': 'croatian',
    'cs': 'czech',
    'da': 'danish',
    'nl': 'dutch',
    'en': 'english',
    'eo': 'esperanto',
    'et': 'estonian',
    'tl': 'filipino',
    'fi': 'finnish',
    'fr': 'french',
    'fy': 'frisian',
    'gl': 'galician',
    'ka': 'georgian',
    'de': 'german',
    'el': 'greek',
    'gu': 'gujarati',
    'ht': 'haitian creole',
    'ha': 'hausa',
    'haw': 'hawaiian',
    'iw': 'hebrew',
    'he': 'hebrew',
    'hi': 'hindi',
    'hmn': 'hmong',
    'hu': 'hungarian',
    'is': 'icelandic',
    'ig': 'igbo',
    'id': 'indonesian',
    'ga': 'irish',
    'it': 'italian',
    'ja': 'japanese',
    'jw': 'javanese',
    'kn': 'kannada',
    'kk': 'kazakh',
    'km': 'khmer',
    'ko': 'korean',
    'ku': 'kurdish (kurmanji)',
    'ky': 'kyrgyz',
    'lo': 'lao',
    'la': 'latin',
    'lv': 'latvian',
    'lt': 'lithuanian',
    'lb': 'luxembourgish',
    'mk': 'macedonian',
    'mg': 'malagasy',
    'ms': 'malay',
    'ml': 'malayalam',
    'mt': 'maltese',
    'mi': 'maori',
    'mr': 'marathi',
    'mn': 'mongolian',
    'my': 'myanmar (burmese)',
    'ne': 'nepali',
    'no': 'norwegian',
    'or': 'odia',
    'ps': 'pashto',
    'fa': 'persian',
    'pl': 'polish',
    'pt': 'portuguese',
    'pa': 'punjabi',
    'ro': 'romanian',
    'ru': 'russian',
    'sm': 'samoan',
    'gd': 'scots gaelic',
    'sr': 'serbian',
    'st': 'sesotho',
    'sn': 'shona',
    'sd': 'sindhi',
    'si': 'sinhala',
    'sk': 'slovak',
    'sl': 'slovenian',
    'so': 'somali',
    'es': 'spanish',
    'su': 'sundanese',
    'sw': 'swahili',
    'sv': 'swedish',
    'tg': 'tajik',
    'ta': 'tamil',
    'te': 'telugu',
    'th': 'thai',
    'tr': 'turkish',
    'uk': 'ukrainian',
    'ur': 'urdu',
    'ug': 'uyghur',
    'uz': 'uzbek',
    'vi': 'vietnamese',
    'cy': 'welsh',
    'xh': 'xhosa',
    'yi': 'yiddish',
    'yo': 'yoruba',
    'zu': 'zulu'
}

# Add some additional language aliases for easier user input
LANGUAGE_ALIASES = {
    # Common abbreviations and variations
    "amh": "am",
    "eng": "en",
    "esp": "es",
    "chinese": "zh-cn",
    "mandarin": "zh-cn",
    "cantonese": "zh-tw",
    "simplified chinese": "zh-cn",
    "traditional chinese": "zh-tw",
    "english": "en",
    "french": "fr",
    "spanish": "es",
    "deutsch": "de",
    "german": "de",
    "italian": "it",
    "japanese": "ja",
    "korean": "ko",
    "russian": "ru",
    "arabic": "ar",
    "portuguese": "pt",
    "hindi": "hi",
    "bengali": "bn",
    "turkish": "tr",
    "dutch": "nl",
    "swedish": "sv",
    "polish": "pl",
    "finnish": "fi",
    "danish": "da",
    "norwegian": "no",
    "czech": "cs",
    "greek": "el",
    "hebrew": "he",
    "thai": "th",
    "vietnamese": "vi",
    "persian": "fa",
    "indonesian": "id",
    "malay": "ms",
    "romanian": "ro",
    "ukrainian": "uk",
    "hungarian": "hu",
    "bulgarian": "bg",
    "slovak": "sk",
    "amharic": "am",
    "croatian": "hr",
    "estonian": "et",
    "latvian": "lv",
    "lithuanian": "lt",
    "slovenian": "sl",
    "serbian": "sr",
}

class TranslationService:
    """Service for handling translation requests."""
    
    @staticmethod
    def get_language_code(language: str) -> Optional[str]:
        """
        Convert a language name or alias to its code.
        
        Args:
            language (str): Language name, code, or alias
            
        Returns:
            Optional[str]: The language code if found, None otherwise
        """
        # Convert to lowercase for comparison
        language = language.lower().strip()
        
        # Direct code match
        if language in LANGUAGES:
            return language
            
        # Check aliases
        if language in LANGUAGE_ALIASES:
            return LANGUAGE_ALIASES[language]
            
        # No match found
        return None
    
    @staticmethod
    def get_supported_languages() -> Dict[str, str]:
        """
        Get a list of all supported languages.
        
        Returns:
            Dict[str, str]: Dictionary of language codes and names
        """
        return LANGUAGES
    
    @staticmethod
    async def detect_language(text: str) -> Tuple[str, float]:
        """
        Detect the language of the given text using an HTTP request.
        
        Args:
            text (str): The text to detect
            
        Returns:
            Tuple[str, float]: (language_code, confidence)
        """
        try:
            # Keep text short for language detection
            detect_text = text[:100]
            
            # Use Google Translate's API to detect language
            async with aiohttp.ClientSession() as session:
                url = "https://translate.googleapis.com/translate_a/single"
                params = {
                    "client": "gtx",
                    "dt": "t",
                    "sl": "auto",
                    "tl": "en",
                    "q": detect_text
                }
                
                full_url = f"{url}?{urllib.parse.urlencode(params)}"
                async with session.get(full_url) as response:
                    if response.status != 200:
                        logger.error(f"Language detection failed: {response.status}")
                        return "en", 0.0
                    
                    data = await response.json(content_type=None)
                    detected_lang = data[2] if len(data) > 2 else "en"
                    return detected_lang, 1.0  # Hard-coded confidence since API doesn't return it
            
        except Exception as e:
            logger.error(f"Error detecting language: {e}")
            return "en", 0.0  # Default to English with 0 confidence on error
    
    @staticmethod
    async def translate_text(text: str, dest_language: str = 'en', src_language: Optional[str] = None) -> Dict:
        """
        Translate text to the target language using an HTTP request.
        
        Args:
            text (str): The text to translate
            dest_language (str): The destination language code
            src_language (str, optional): The source language code
            
        Returns:
            Dict: Translation results containing:
                - translated_text: The translated text
                - src_language: Detected or provided source language
                - dest_language: Destination language
                - confidence: Confidence score of language detection
        """
        try:
            # If source language is not provided, use auto-detection
            detected_lang = None
            confidence = 0.0
            
            if not src_language:
                src_language = "auto"
            
            # Use Google Translate's API to translate text
            async with aiohttp.ClientSession() as session:
                url = "https://translate.googleapis.com/translate_a/single"
                params = {
                    "client": "gtx",
                    "dt": "t",
                    "sl": src_language,
                    "tl": dest_language,
                    "q": text
                }
                
                full_url = f"{url}?{urllib.parse.urlencode(params)}"
                async with session.get(full_url) as response:
                    if response.status != 200:
                        logger.error(f"Translation failed: {response.status}")
                        raise Exception(f"Translation service returned status code {response.status}")
                    
                    try:
                        data = await response.json(content_type=None)
                        translated_parts = []
                        
                        # Extract translated text from the data structure
                        for part in data[0]:
                            if part[0]:
                                translated_parts.append(part[0])
                        
                        translated_text = ''.join(translated_parts)
                        
                        # Format the result
                        actual_src_lang = data[2] if len(data) > 2 and src_language == "auto" else src_language
                        
                        result = {
                            "translated_text": translated_text,
                            "src_language": actual_src_lang,
                            "src_language_name": LANGUAGES.get(actual_src_lang, "Unknown"),
                            "dest_language": dest_language,
                            "dest_language_name": LANGUAGES.get(dest_language, "Unknown"),
                            "confidence": 1.0  # Hard-coded confidence since API doesn't return it
                        }
                        
                        return result
                    except Exception as e:
                        logger.error(f"Error parsing translation response: {e}")
                        raise
            
        except Exception as e:
            logger.error(f"Translation error: {e}")
            raise