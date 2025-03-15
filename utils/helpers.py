"""
Helper utilities for the Telegram bot.
"""
import re
import html
from urllib.parse import urlparse, parse_qs

def is_valid_url(url: str) -> bool:
    """
    Check if a given string is a valid URL.
    
    Args:
        url (str): The URL to validate
        
    Returns:
        bool: True if valid URL, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def is_youtube_url(url: str) -> bool:
    """
    Check if a given URL is a YouTube video URL.
    
    Args:
        url (str): The URL to check
        
    Returns:
        bool: True if YouTube URL, False otherwise
    """
    if not is_valid_url(url):
        return False
    
    # Check for YouTube domain patterns
    youtube_patterns = [
        r'(youtube\.com\/watch\?v=)',
        r'(youtu\.be\/)',
        r'(youtube\.com\/shorts\/)'
    ]
    
    return any(re.search(pattern, url) for pattern in youtube_patterns)

def extract_youtube_id(url: str) -> str:
    """
    Extract the YouTube video ID from a URL.
    
    Args:
        url (str): The YouTube URL
        
    Returns:
        str: The YouTube video ID, or empty string if not found
    """
    if not is_youtube_url(url):
        return ""
    
    # Handle youtu.be URLs
    if 'youtu.be' in url:
        path = urlparse(url).path
        return path.strip('/')
    
    # Handle youtube.com/shorts URLs
    if '/shorts/' in url:
        parts = url.split('/shorts/')
        if len(parts) > 1:
            # Remove any query parameters
            return parts[1].split('?')[0].split('&')[0]
    
    # Handle standard YouTube URLs
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    
    return query_params.get('v', [''])[0]

def truncate_text(text: str, max_length: int = 4000) -> str:
    """
    Truncate text to a maximum length while keeping whole words.
    
    Args:
        text (str): The text to truncate
        max_length (int): Maximum length of the text
        
    Returns:
        str: The truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    # Truncate at the last space before max_length
    truncated = text[:max_length].rsplit(' ', 1)[0]
    
    # Add ellipsis if text was truncated
    if len(truncated) < len(text):
        truncated += "..."
    
    return truncated

def clean_html(html_text: str) -> str:
    """
    Clean HTML tags from text.
    
    Args:
        html_text (str): The HTML text to clean
        
    Returns:
        str: The cleaned text
    """
    # First, unescape HTML entities
    unescaped = html.unescape(html_text)
    
    # Then remove HTML tags
    tag_pattern = re.compile(r'<[^>]+>')
    text = tag_pattern.sub('', unescaped)
    
    # Replace multiple whitespaces with a single space
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text