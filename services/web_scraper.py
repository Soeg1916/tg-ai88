"""
Web scraper service for retrieving content from websites.
"""
import logging
import aiohttp
import trafilatura
from typing import Dict, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

async def get_website_text_content(url: str) -> str:
    """
    Asynchronously retrieve and extract the main text content from a website.
    
    Args:
        url (str): The URL of the website to scrape.
        
    Returns:
        str: The extracted text content.
    """
    try:
        # First try using trafilatura for best content extraction
        downloaded = trafilatura.fetch_url(url)
        
        if downloaded:
            content = trafilatura.extract(downloaded)
            
            if content and len(content.strip()) > 0:
                return content
        
        # Fallback to custom extraction with BeautifulSoup if trafilatura fails
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Failed to retrieve content from URL: {url}, status code: {response.status}")
                    return ""
                
                html = await response.text()
                
                # Parse the HTML with BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')
                
                # Remove unwanted elements
                for element in soup(['script', 'style', 'header', 'footer', 'nav']):
                    element.decompose()
                
                # Extract text
                text = soup.get_text(separator='\n')
                
                # Clean up the text
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                content = '\n'.join(lines)
                
                return content
    
    except Exception as e:
        logger.error(f"Error extracting content from URL: {url}, error: {e}")
        return ""

async def get_website_metadata(url: str) -> dict:
    """
    Retrieve metadata from a website (title, description, etc.).
    
    Args:
        url (str): The URL of the website to scrape.
        
    Returns:
        dict: The metadata extracted from the website.
    """
    metadata = {
        'title': '',
        'description': '',
        'keywords': '',
        'image': '',
        'site_name': ''
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Failed to retrieve metadata from URL: {url}, status code: {response.status}")
                    return metadata
                
                html = await response.text()
                
                # Parse the HTML with BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract title
                title_tag = soup.find('title')
                if title_tag:
                    metadata['title'] = title_tag.string
                
                # Extract meta tags
                meta_tags = soup.find_all('meta')
                for tag in meta_tags:
                    # Description
                    if tag.get('name') == 'description':
                        metadata['description'] = tag.get('content', '')
                    
                    # Keywords
                    elif tag.get('name') == 'keywords':
                        metadata['keywords'] = tag.get('content', '')
                    
                    # Open Graph metadata
                    elif tag.get('property') == 'og:title':
                        metadata['title'] = tag.get('content', '')
                    
                    elif tag.get('property') == 'og:description':
                        metadata['description'] = tag.get('content', '')
                    
                    elif tag.get('property') == 'og:image':
                        metadata['image'] = tag.get('content', '')
                    
                    elif tag.get('property') == 'og:site_name':
                        metadata['site_name'] = tag.get('content', '')
                
                return metadata
    
    except Exception as e:
        logger.error(f"Error extracting metadata from URL: {url}, error: {e}")
        return metadata