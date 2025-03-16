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
        import random
        
        if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
            logger.error("Google API key or CSE ID not found in environment variables")
            return []
        
        try:
            # Limit num_results to a maximum of 10 (Google API limit)
            if num_results > 10:
                num_results = 10
            
            # Generate a more varied random seed
            random_seed = random.randint(1, 1000)
            
            # Try multiple search strategies if needed
            max_attempts = 3
            for attempt in range(max_attempts):
                # Adjust the query slightly for each attempt to get different results
                search_query = query
                if attempt > 0:
                    # For retry attempts, add some variation to the query
                    modifiers = ["latest", "best", "high quality", "top", "popular", "trending"]
                    search_query = f"{random.choice(modifiers)} {query}"
                    logger.info(f"Retry attempt {attempt}: Using modified query: {search_query}")
                
                # Use a different random seed for each attempt
                current_seed = random_seed + (attempt * 100)
                
                # Perform the image search
                results = GoogleSearchService._perform_image_search(
                    search_query, GOOGLE_API_KEY, GOOGLE_CSE_ID, num_results, current_seed)
                
                # Check if we got any results
                if 'items' in results and len(results['items']) > 0:
                    logger.info(f"Found {len(results['items'])} image search results for query: {search_query}")
                    return results['items']
                else:
                    logger.warning(f"No image search results found for query: {search_query} on attempt {attempt+1}")
            
            # If we reach here, all attempts failed
            logger.error(f"All {max_attempts} search attempts failed for query: {query}")
            return []
            
        except HttpError as e:
            logger.error(f"Google image search API error: {e}")
            # Try to parse quota errors
            if "quota" in str(e).lower():
                logger.error("Google API quota exceeded. Consider updating the API key.")
            return []
        
        except Exception as e:
            logger.error(f"Error performing Google image search: {e}")
            return []
    
    @staticmethod
    def _perform_search(query, api_key, cse_id, num_results):
        """Perform the actual Google search API call."""
        service = build("customsearch", "v1", developerKey=api_key)
        
        # Create the query with date sort parameter to get the most recent results
        # Include dateRestrict to get results from the past 7 days
        result = service.cse().list(
            q=query,
            cx=cse_id,
            num=num_results,
            sort="date",
            dateRestrict="d7"  # Results from the last 7 days
        ).execute()
        
        return result
    
    @staticmethod
    def _perform_image_search(query, api_key, cse_id, num_results, random_seed=None):
        """Perform the actual Google image search API call."""
        try:
            import time
            from random import choice, sample
            
            # Create a unique search ID using combination of query and timestamp to avoid caching issues
            unique_query_id = str(int(time.time()))[-4:]
            
            # Make a more diverse set of search queries by adding variations
            variations = ["", "images", "photos", "pictures", "gallery"]
            
            # Try to avoid API restrictions by varying request patterns
            service = build("customsearch", "v1", developerKey=api_key, cache_discovery=False)
            
            # Add additional search parameters for randomization
            search_params = {
                'q': query,
                'cx': cse_id,
                'num': num_results,
                'searchType': "image",
                'safe': "active",     # Keep safe search on
                'imgSize': choice(["LARGE", "XLARGE", "XXLARGE", "HUGE"]),  # Vary image sizes
                'gl': choice(["us", "uk", "ca", "au"]),  # Vary regions
            }
            
            # Add randomization to the search
            if random_seed is not None:
                # Use different search techniques for variety
                if random_seed % 5 == 0:
                    # Add random query modifier
                    search_params['q'] = f"{query} {choice(variations)} {unique_query_id}"
                    search_params['sort'] = "date"
                    search_params['dateRestrict'] = "m1"
                elif random_seed % 5 == 1:
                    # Use relevance sorting
                    search_params['q'] = f"{query} {choice(variations)}"
                    search_params['sort'] = "relevance"
                elif random_seed % 5 == 2:
                    # Use larger date range
                    search_params['q'] = f"{query} {choice(variations)}"
                    search_params['dateRestrict'] = "m3"  # Last 3 months
                elif random_seed % 5 == 3:
                    # Image color dominance variation
                    search_params['q'] = f"{query}"
                    search_params['imgDominantColor'] = choice(["black", "blue", "brown", "gray", "green", "pink", "purple", "teal", "white", "yellow"])
                else:
                    # Image type variation
                    search_params['q'] = f"{query}"
                    search_params['imgType'] = choice(["clipart", "face", "lineart", "stock", "photo", "animated"])
                    
                # Add randomness to the result start index (when showing a subset of results)
                start_index = (random_seed % 10) + 1  # Values: 1-10
                search_params['start'] = start_index
            
            # Log the search parameters
            logger.info(f"Performing image search with params: {search_params}")
            
            # Execute the search
            result = service.cse().list(**search_params).execute()
            
            if 'items' not in result:
                # If no results, try a broader search as fallback
                logger.info("No results found with initial parameters, trying fallback search")
                # Simplified fallback search params
                fallback_params = {
                    'q': query,
                    'cx': cse_id,
                    'num': num_results,
                    'searchType': "image",
                    'safe': "active"
                }
                # Try the fallback search
                result = service.cse().list(**fallback_params).execute()
                
            return result
            
        except Exception as e:
            logger.error(f"Error in image search API call: {str(e)}")
            # Return empty result structure
            return {"items": []}