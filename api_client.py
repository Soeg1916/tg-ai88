import os
import logging
import aiohttp
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class AIApiClient:
    def __init__(self):
        try:
            self.api_url = "https://api.mistral.ai/v1/chat/completions"
            self.api_key = os.getenv("MISTRAL_API_KEY")
            if not self.api_key:
                logger.warning("No Mistral API key found")
                raise ValueError("Mistral API key not found")
            logger.info("Successfully initialized Mistral AI client")
        except Exception as e:
            logger.error(f"Error initializing Mistral AI client: {str(e)}")
            raise

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    async def get_response(self, conversation_context: List[Dict]) -> Optional[str]:
        """Get a response from Mistral AI API."""
        try:
            messages = self._prepare_messages(conversation_context)
            logger.info(f"Sending request to Mistral AI with {len(messages)} messages")

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            payload = {
                "model": "mistral-medium",  # Upgraded to a more capable model
                "messages": messages,
                "max_tokens": 800,  # Increased max tokens for more detailed responses
                "temperature": 0.75,  # Slightly higher temperature for more creative responses
                "top_p": 0.95,  # Slightly adjusted for better content diversity
                "stream": False
            }

            async with self.session.post(self.api_url, headers=headers, json=payload, timeout=30) as response:
                try:
                    if response.status == 200:
                        data = await response.json()
                        if 'choices' in data and data['choices']:
                            content = data['choices'][0]['message']['content'].strip()
                            if content:
                                logger.info("Successfully received AI response")
                                return content

                    error_msg = f"API request failed with status {response.status}"
                    if response.status != 200:
                        try:
                            error_data = await response.json()
                            error_msg += f": {error_data.get('error', {}).get('message', '')}"
                        except:
                            pass
                    logger.warning(error_msg)
                    return "I apologize, but I'm having trouble connecting to my AI service right now. Please try again in a moment."
                except Exception as e:
                    logger.error(f"Failed to parse API response: {str(e)}")
                    return "An error occurred while processing the response."

        except Exception as e:
            logger.error(f"Error getting response from Mistral: {str(e)}")
            return None

    def _prepare_messages(self, conversation_context: List[Dict]) -> List[Dict]:
        """Prepare the conversation messages in the format expected by Mistral AI."""
        messages = [{
            "role": "system",
            "content": (
                "You are an advanced AI assistant integrated into a Telegram bot with multiple capabilities. "
                "Current date: March 15, 2025. \n\n"
                
                "YOUR CAPABILITIES:\n"
                "1. Answer knowledge questions with detailed, accurate information\n"
                "2. Assist with creative tasks like writing, brainstorming, and problem-solving\n"
                "3. Explain complex topics in simple terms\n"
                "4. Engage in natural conversation with personality and humor when appropriate\n"
                "5. Provide thoughtful advice on personal and professional matters\n\n"
                
                "USAGE GUIDELINES:\n"
                "- Be direct and concise when possible while providing complete information\n"
                "- Match the user's communication style and level of formality\n"
                "- Include relevant context in your responses without unnecessary disclaimers\n"
                "- Admit when you don't know something rather than making up information\n"
                "- Avoid unnecessary repetition or verbosity\n"
                "- Don't mention your limitations unless directly asked\n\n"
                
                "The bot also has additional features that users can access with commands:\n"
                "- Image analysis for object detection and text extraction from photos\n"
                "- Social media video downloading (TikTok, Instagram, YouTube)\n"
                "- Web search and content extraction\n"
                "- Text-to-handwriting conversion\n\n"
                
                "Remember, your responses should be helpful, accurate, and tailored to the user's needs."
            )
        }]

        messages.extend([{
            "role": message["role"],
            "content": message["content"]
        } for message in conversation_context])

        return messages