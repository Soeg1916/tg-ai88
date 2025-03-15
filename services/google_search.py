"""
Google Search API service.
"""
import logging
import os
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import GOOGLE_API_KEY, GOOGLE_CSE_ID

logger = logging.getLogger(__name__)

class GoogleSearchService:
    """Service for handling Google Custom Search API requests."""
    
    @staticmethod
    async def search(query: str, num_results: int = 5) -> list:
        """
        Search the web using Google Custom Search API.
        
        Args:
            query (str): The search query
            num_results (int): Number of results to return (max 10)
            
        Returns:
            list: A list of search results
        """
        if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
            logger.error("Google API key or CSE ID not found in environment variables")
            return []
        
        try:
            # Limit num_results to a maximum of 10 (Google API limit)
            if num_results > 10:
                num_results = 10
                
            # Perform the search
            results = GoogleSearchService._perform_search(query, GOOGLE_API_KEY, GOOGLE_CSE_ID, num_results)
            
            if 'items' not in results:
                return []
                
            return results['items']
            
        except HttpError as e:
            logger.error(f"Google search API error: {e}")
            return []
        
        except Exception as e:
            logger.error(f"Error performing Google search: {e}")
            return []
    
    @staticmethod
    async def image_search(query: str, num_results: int = 5) -> list:
        """
        Search for images using Google Custom Search API.
        
        Args:
            query (str): The search query
            num_results (int): Number of results to return (max 10)
            
        Returns:
            list: A list of image search results
        """
        if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
            logger.error("Google API key or CSE ID not found in environment variables")
            return []
        
        try:
            # Limit num_results to a maximum of 10 (Google API limit)
            if num_results > 10:
                num_results = 10
                
            # Perform the image search
            results = GoogleSearchService._perform_image_search(query, GOOGLE_API_KEY, GOOGLE_CSE_ID, num_results)
            
            if 'items' not in results:
                return []
                
            return results['items']
            
        except HttpError as e:
            logger.error(f"Google image search API error: {e}")
            return []
        
        except Exception as e:
            logger.error(f"Error performing Google image search: {e}")
            return []
    
    @staticmethod
    def _perform_search(query, api_key, cse_id, num_results):
        """Perform the actual Google search API call."""
        service = build("customsearch", "v1", developerKey=api_key)
        
        # Create the query
        result = service.cse().list(
            q=query,
            cx=cse_id,
            num=num_results
        ).execute()
        
        return result
    
    @staticmethod
    def _perform_image_search(query, api_key, cse_id, num_results):
        """Perform the actual Google image search API call."""
        service = build("customsearch", "v1", developerKey=api_key)
        
        # Create the query with image search type
        result = service.cse().list(
            q=query,
            cx=cse_id,
            num=num_results,
            searchType="image"
        ).execute()
        
        return result