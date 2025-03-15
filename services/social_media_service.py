"""
Service for handling social media video processing (TikTok, Instagram, etc.)
"""
import logging
import os
import re
import requests
from typing import Dict, Optional, Any, Tuple
import yt_dlp

from config import DOWNLOADS_FOLDER

logger = logging.getLogger(__name__)

class SocialMediaService:
    """Service for handling social media content processing tasks."""
    
    # Regular expressions to identify different social media platforms
    TIKTOK_REGEX = re.compile(r'(vm\.tiktok\.com|vt\.tiktok\.com|tiktok\.com|www\.tiktok\.com)')
    INSTAGRAM_REGEX = re.compile(r'(instagram\.com|instagr\.am|www\.instagram\.com)\/(?:p|reel|reels|stories)\/([^\/\?]+)')
    
    @staticmethod
    def identify_platform(url: str) -> str:
        """
        Identify the social media platform from a URL.
        
        Args:
            url (str): The social media URL
            
        Returns:
            str: The platform name ('tiktok', 'instagram', or 'unknown')
        """
        if SocialMediaService.TIKTOK_REGEX.search(url):
            return 'tiktok'
        elif SocialMediaService.INSTAGRAM_REGEX.search(url):
            return 'instagram'
        else:
            return 'unknown'
    
    @staticmethod
    async def get_content_info(url: str) -> dict:
        """
        Get information about social media content.
        
        Args:
            url (str): The social media URL
            
        Returns:
            dict: Information about the content
        """
        platform = SocialMediaService.identify_platform(url)
        
        # Resolve URL redirects for shortened links
        url = SocialMediaService._resolve_url_redirects(url)
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'noplaylist': True,
            'cookiefile': None,  # Don't use cookies
            'socket_timeout': 10,  # Reduced timeout
            'retries': 3,  # Retry on connection failures
            'extractor_args': {
                'TikTok': {'download_without_watermark': True},
            }
        }
        
        try:
            # Get content information
            info = SocialMediaService._extract_info(url, ydl_opts)
            
            if not info:
                return {'error': 'Failed to extract content information'}
                
            # Extract common fields
            result = {
                'id': info.get('id'),
                'title': info.get('title'),
                'description': info.get('description'),
                'duration': info.get('duration'),
                'uploader': info.get('uploader'),
                'platform': platform,
                'url': url,
                'thumbnail': info.get('thumbnail'),
            }
            
            # Add platform-specific fields
            if platform == 'tiktok':
                result.update({
                    'like_count': info.get('like_count'),
                    'comment_count': info.get('comment_count'),
                    'share_count': info.get('share_count'),
                })
            elif platform == 'instagram':
                result.update({
                    'like_count': info.get('like_count'),
                    'comment_count': info.get('comment_count'),
                    'view_count': info.get('view_count'),
                })
                
            return result
            
        except Exception as e:
            logger.error(f"Error getting content info: {e}")
            return {'error': str(e)}
    
    @staticmethod
    async def download_video(url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Download a video from TikTok or Instagram.
        
        Args:
            url (str): The social media URL
            
        Returns:
            Tuple[Optional[str], Optional[str]]: (file_path, error_message)
        """
        # Ensure the downloads directory exists
        os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)
        
        platform = SocialMediaService.identify_platform(url)
        
        # Resolve URL redirects for shortened links
        url = SocialMediaService._resolve_url_redirects(url)
        
        # Create a unique filename based on the URL and platform
        filename = f"{platform}_{hash(url) % 1000000}.mp4"
        output_path = os.path.join(DOWNLOADS_FOLDER, filename)
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'best[ext=mp4]/best',
            'outtmpl': output_path,
            'noplaylist': False,  # Changed to handle slide shows/playlists
            'cookiefile': None,
            'socket_timeout': 10,
            'retries': 3,
            'ignoreerrors': True,  # Continue on errors with individual entries
            'playlistend': 10      # Limit to 10 entries to prevent excessive downloads
        }
        
        # Add platform-specific options
        if platform == 'tiktok':
            ydl_opts.update({
                'extractor_args': {
                    'TikTok': {
                        'download_without_watermark': True,
                        'extract_flat': False,  # Ensure all slides are processed
                        'allow_unplayable_formats': True  # Allow image formats
                    }
                },
                'writethumbnail': True,  # Save thumbnails (for slides with images)
                'writeinfojson': True,   # Save metadata
                'concurrent_fragment_downloads': 5  # Speed up downloads
            })
        
        try:
            # First, get info to check if this is a playlist/slide post
            info = SocialMediaService._extract_info(url, {**ydl_opts, 'skip_download': True})
            
            if not info:
                return None, "Failed to extract content information"
            
            # Check if this is a TikTok slide post (has entries or is_gallery property)
            is_slide_post = False
            if platform == 'tiktok' and (
                    info.get('entries') or 
                    info.get('is_gallery') or 
                    '_type' in info and info['_type'] == 'playlist'):
                is_slide_post = True
                logger.info(f"Detected TikTok slide post: {url}")
                
                # For slide posts, we need to handle each slide separately
                if is_slide_post and info.get('entries'):
                    # Create a directory for this post
                    post_dir = os.path.join(DOWNLOADS_FOLDER, f"tiktok_slide_{hash(url) % 1000000}")
                    os.makedirs(post_dir, exist_ok=True)
                    
                    # Modify output template for slide entries
                    ydl_opts['outtmpl'] = os.path.join(post_dir, '%(playlist_index)s-%(title).100s.%(ext)s')
                    
                    # Download all slides
                    success = SocialMediaService._download_content(url, ydl_opts)
                    
                    if not success:
                        return None, "Failed to download slide content"
                    
                    # Return the directory containing all slides
                    return post_dir, None
            
            # If not a slide post, download as usual
            success = SocialMediaService._download_content(url, ydl_opts)
            
            if not success:
                return None, "Failed to download the video"
                
            # Return the path to the downloaded file
            return output_path, None
            
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            
            # Clean up if file was partially downloaded
            if os.path.exists(output_path):
                os.remove(output_path)
                
            return None, str(e)
    
    @staticmethod
    async def extract_audio(url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract audio from a social media video.
        
        Args:
            url (str): The social media URL
            
        Returns:
            Tuple[Optional[str], Optional[str]]: (file_path, error_message)
        """
        # Ensure the downloads directory exists
        os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)
        
        platform = SocialMediaService.identify_platform(url)
        
        # Resolve URL redirects for shortened links
        url = SocialMediaService._resolve_url_redirects(url)
        
        # Create a unique filename based on the URL and platform
        filename = f"{platform}_audio_{hash(url) % 1000000}.mp3"
        output_path = os.path.join(DOWNLOADS_FOLDER, filename)
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': output_path.replace('.mp3', ''),  # yt-dlp will add the extension
            'noplaylist': False,  # Changed to handle slide shows with music
            'cookiefile': None,
            'socket_timeout': 10,
            'retries': 3,
            'ignoreerrors': True,  # Continue on errors with individual entries
            'playlistend': 10      # Limit to 10 entries to prevent excessive downloads
        }
        
        # Add platform-specific options
        if platform == 'tiktok':
            ydl_opts.update({
                'extractor_args': {
                    'TikTok': {
                        'download_without_watermark': True,
                        'extract_flat': False  # Ensure all slides are processed
                    }
                },
                'concurrent_fragment_downloads': 5  # Speed up downloads
            })
        
        try:
            # First, get info to check if this is a playlist/slide post
            info = SocialMediaService._extract_info(url, {**ydl_opts, 'skip_download': True})
            
            if not info:
                return None, "Failed to extract content information"
            
            # Check if this is a TikTok slide post with entries
            is_slide_post = False
            if platform == 'tiktok' and (
                    info.get('entries') or 
                    info.get('is_gallery') or 
                    '_type' in info and info['_type'] == 'playlist'):
                is_slide_post = True
                logger.info(f"Detected TikTok slide post for audio extraction: {url}")
                
                # For TikTok slides, we need to extract the original sound/music which is usually the same for all slides
                if is_slide_post and info.get('entries'):
                    # Find the main audio track from the slide post
                    main_audio_url = None
                    for entry in info.get('entries', []):
                        if entry and entry.get('music_url') or entry.get('audio_url'):
                            main_audio_url = entry.get('music_url') or entry.get('audio_url')
                            break
                    
                    # If we found a direct music URL, download it
                    if main_audio_url:
                        # Create audio-specific options
                        audio_opts = {
                            'quiet': True,
                            'no_warnings': True,
                            'format': 'bestaudio/best',
                            'postprocessors': [{
                                'key': 'FFmpegExtractAudio',
                                'preferredcodec': 'mp3',
                                'preferredquality': '192',
                            }],
                            'outtmpl': output_path.replace('.mp3', ''),
                            'noplaylist': True,
                            'cookiefile': None,
                            'socket_timeout': 10,
                            'retries': 3
                        }
                        
                        # Download the music directly
                        with yt_dlp.YoutubeDL(audio_opts) as ydl:
                            ydl.download([main_audio_url])
                            return output_path, None
                    
                    # Create a directory for all audio tracks from the slides
                    post_dir = os.path.join(DOWNLOADS_FOLDER, f"tiktok_audio_{hash(url) % 1000000}")
                    os.makedirs(post_dir, exist_ok=True)
                    
                    # Modify output template for slide entries
                    ydl_opts['outtmpl'] = os.path.join(post_dir, '%(playlist_index)s-%(title).100s.%(ext)s')
                    
                    # Download all audio tracks from slides
                    success = SocialMediaService._download_content(url, ydl_opts)
                    
                    if not success:
                        return None, "Failed to extract audio from slides"
                    
                    # Return the directory containing all audio files
                    return post_dir, None
            
            # If not a slide post, extract audio as usual
            success = SocialMediaService._download_content(url, ydl_opts)
            
            if not success:
                return None, "Failed to extract audio"
                
            # Return the path to the extracted audio file
            return output_path, None
            
        except Exception as e:
            logger.error(f"Error extracting audio: {e}")
            
            # Clean up if file was partially downloaded
            if os.path.exists(output_path):
                os.remove(output_path)
                
            return None, str(e)
    
    @staticmethod
    def _extract_info(url, ydl_opts):
        """Extract content information using yt-dlp."""
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception as e:
            logger.error(f"Error extracting content info: {e}")
            return None
    
    @staticmethod
    def _download_content(url, ydl_opts):
        """Download content using yt-dlp."""
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                return True
        except Exception as e:
            logger.error(f"Error downloading with yt-dlp: {e}")
            return False
    
    @staticmethod
    def _resolve_url_redirects(url: str) -> str:
        """Resolve URL redirects for shortened links."""
        try:
            # Handle shortened TikTok links or any other redirects
            if ('vm.tiktok.com' in url or 'vt.tiktok.com' in url or 
                'tiktok.com/t/' in url or 'bit.ly' in url or 
                'goo.gl' in url or 'tinyurl.com' in url or
                't.co' in url or 'ow.ly' in url):
                
                # Use a proper user agent to avoid blocks
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Referer': 'https://www.google.com/'
                }
                
                # Use timeout to avoid hanging
                response = requests.head(url, allow_redirects=True, headers=headers, timeout=5)
                if response.status_code == 200:
                    resolved_url = response.url
                    logger.info(f"Resolved URL: {url} → {resolved_url}")
                    return resolved_url
            
            return url
        except Exception as e:
            logger.error(f"Error resolving URL redirects: {e}")
            return url