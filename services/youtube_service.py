"""
Service for handling YouTube video processing.
"""
import logging
import os
import tempfile
from typing import Dict, Optional, Any
import json
from pathlib import Path
import yt_dlp

from config import DOWNLOADS_FOLDER

logger = logging.getLogger(__name__)

class YouTubeService:
    """Service for handling YouTube video processing tasks."""
    
    @staticmethod
    async def get_video_info(url: str) -> dict:
        """
        Get information about a YouTube video.
        
        Args:
            url (str): The YouTube video URL
            
        Returns:
            dict: Information about the video
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'format': 'best',
            'noplaylist': True,
        }
        
        try:
            # Get video information
            info = YouTubeService._extract_info(url, ydl_opts)
            
            if not info:
                return {}
                
            # Extract relevant fields
            return {
                'id': info.get('id'),
                'title': info.get('title'),
                'description': info.get('description'),
                'duration': info.get('duration'),
                'view_count': info.get('view_count'),
                'uploader': info.get('uploader'),
                'upload_date': info.get('upload_date'),
                'thumbnail': info.get('thumbnail'),
                'formats': info.get('formats', []),
                'categories': info.get('categories', []),
                'tags': info.get('tags', []),
            }
            
        except Exception as e:
            logger.error(f"Error getting YouTube video info: {e}")
            return {}
    
    @staticmethod
    async def download_video(url: str, format_id: str = None) -> str:
        """
        Download a YouTube video.
        
        Args:
            url (str): The YouTube video URL
            format_id (str, optional): The format ID to download
            
        Returns:
            str: Path to the downloaded file, or error message
        """
        # Ensure the downloads directory exists
        os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)
        
        # Create a unique filename based on the URL
        filename = f"youtube_{hash(url) % 1000000}.mp4"
        output_path = os.path.join(DOWNLOADS_FOLDER, filename)
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'best[ext=mp4]' if not format_id else format_id,
            'outtmpl': output_path,
            'noplaylist': True,
        }
        
        try:
            # Download the video
            success = YouTubeService._download_video(url, ydl_opts)
            
            if not success:
                return None
                
            # Return the path to the downloaded file
            return output_path
            
        except Exception as e:
            logger.error(f"Error downloading YouTube video: {e}")
            
            # Clean up if file was partially downloaded
            if os.path.exists(output_path):
                os.remove(output_path)
                
            return None
    
    @staticmethod
    async def extract_audio(url: str) -> str:
        """
        Extract audio from a YouTube video.
        
        Args:
            url (str): The YouTube video URL
            
        Returns:
            str: Path to the downloaded audio file, or error message
        """
        # Ensure the downloads directory exists
        os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)
        
        # Create a unique filename based on the URL
        filename = f"youtube_audio_{hash(url) % 1000000}.mp3"
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
            'noplaylist': True,
        }
        
        try:
            # Download and extract audio
            success = YouTubeService._download_video(url, ydl_opts)
            
            if not success:
                return None
                
            # Return the path to the extracted audio file
            return output_path
            
        except Exception as e:
            logger.error(f"Error extracting audio from YouTube video: {e}")
            
            # Clean up if file was partially downloaded
            if os.path.exists(output_path):
                os.remove(output_path)
                
            return None
    
    @staticmethod
    def _extract_info(url, ydl_opts):
        """Extract video information using yt-dlp."""
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception as e:
            logger.error(f"Error extracting YouTube video info: {e}")
            return None
    
    @staticmethod
    def _download_video(url, ydl_opts):
        """Download video using yt-dlp."""
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                return True
        except Exception as e:
            logger.error(f"Error downloading with yt-dlp: {e}")
            return False