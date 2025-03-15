"""
Image processing service using Pillow.
"""
import io
import logging
import aiohttp
from PIL import Image, ImageFilter

logger = logging.getLogger(__name__)

class ImageProcessor:
    """Service for handling image processing tasks."""
    
    @staticmethod
    async def download_image(url: str) -> bytes:
        """
        Download an image from a URL.
        
        Args:
            url (str): The URL of the image
            
        Returns:
            bytes: The image data as bytes, or None if failed
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to download image: {url}, status: {response.status}")
                        return None
                    
                    return await response.read()
        
        except Exception as e:
            logger.error(f"Error downloading image: {e}")
            return None
    
    @staticmethod
    async def resize_image(image_data: bytes, width: int, height: int) -> bytes:
        """
        Resize an image.
        
        Args:
            image_data (bytes): The image data
            width (int): Target width
            height (int): Target height
            
        Returns:
            bytes: The processed image data
        """
        return await ImageProcessor._process_resize(image_data, width, height)
    
    @staticmethod
    async def crop_image(image_data: bytes, x: int, y: int, width: int, height: int) -> bytes:
        """
        Crop an image.
        
        Args:
            image_data (bytes): The image data
            x (int): Left coordinate
            y (int): Top coordinate
            width (int): Crop width
            height (int): Crop height
            
        Returns:
            bytes: The processed image data
        """
        return await ImageProcessor._process_crop(image_data, x, y, width, height)
    
    @staticmethod
    async def apply_filter(image_data: bytes, filter_type: str) -> bytes:
        """
        Apply a filter to an image.
        
        Args:
            image_data (bytes): The image data
            filter_type (str): The type of filter to apply (blur, contour, sharpen, etc.)
            
        Returns:
            bytes: The processed image data
        """
        return await ImageProcessor._process_filter(image_data, filter_type)
    
    @staticmethod
    async def _process_resize(image_data, width, height):
        """Perform the actual image resize using Pillow."""
        try:
            # Open the image from bytes
            img = Image.open(io.BytesIO(image_data))
            
            # Resize the image
            resized_img = img.resize((width, height), Image.LANCZOS)
            
            # Save the resized image to bytes
            output_buffer = io.BytesIO()
            resized_img.save(output_buffer, format=img.format or 'JPEG')
            
            return output_buffer.getvalue()
        
        except Exception as e:
            logger.error(f"Error resizing image: {e}")
            return image_data
    
    @staticmethod
    async def _process_crop(image_data, x, y, width, height):
        """Perform the actual image crop using Pillow."""
        try:
            # Open the image from bytes
            img = Image.open(io.BytesIO(image_data))
            
            # Crop the image
            cropped_img = img.crop((x, y, x + width, y + height))
            
            # Save the cropped image to bytes
            output_buffer = io.BytesIO()
            cropped_img.save(output_buffer, format=img.format or 'JPEG')
            
            return output_buffer.getvalue()
        
        except Exception as e:
            logger.error(f"Error cropping image: {e}")
            return image_data
    
    @staticmethod
    async def _process_filter(image_data, filter_type):
        """Apply the specified filter to the image using Pillow."""
        try:
            # Open the image from bytes
            img = Image.open(io.BytesIO(image_data))
            
            # Apply the filter based on the filter_type
            if filter_type.lower() == 'blur':
                filtered_img = img.filter(ImageFilter.BLUR)
            elif filter_type.lower() == 'contour':
                filtered_img = img.filter(ImageFilter.CONTOUR)
            elif filter_type.lower() == 'detail':
                filtered_img = img.filter(ImageFilter.DETAIL)
            elif filter_type.lower() == 'edge_enhance':
                filtered_img = img.filter(ImageFilter.EDGE_ENHANCE)
            elif filter_type.lower() == 'sharpen':
                filtered_img = img.filter(ImageFilter.SHARPEN)
            elif filter_type.lower() == 'smooth':
                filtered_img = img.filter(ImageFilter.SMOOTH)
            elif filter_type.lower() == 'emboss':
                filtered_img = img.filter(ImageFilter.EMBOSS)
            elif filter_type.lower() == 'find_edges':
                filtered_img = img.filter(ImageFilter.FIND_EDGES)
            else:
                # Default to no filter if the filter_type is not recognized
                filtered_img = img
            
            # Save the filtered image to bytes
            output_buffer = io.BytesIO()
            filtered_img.save(output_buffer, format=img.format or 'JPEG')
            
            return output_buffer.getvalue()
        
        except Exception as e:
            logger.error(f"Error applying filter to image: {e}")
            return image_data