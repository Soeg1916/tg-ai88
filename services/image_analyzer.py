"""
Image analysis service using Google Cloud Vision API.
This service leverages our existing Google APIs to detect objects, analyze content,
and perform OCR (Optical Character Recognition) on images.
"""
import os
import logging
import base64
import io
import aiohttp
from typing import Dict, List, Optional, Any, Tuple
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

class ImageAnalyzer:
    """Service for analyzing images and extracting information."""
    
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    VISION_API_URL = "https://vision.googleapis.com/v1/images:annotate"
    
    @staticmethod
    async def download_image(url: str) -> Optional[bytes]:
        """Download image data from a URL."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        logger.error(f"Failed to download image: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error downloading image: {str(e)}")
            return None
    
    @classmethod
    async def analyze_image(cls, image_data: bytes) -> Dict:
        """
        Perform full image analysis including:
        - Label detection (objects, scenes)
        - Text detection (OCR)
        - Face detection
        - Landmark detection
        - Logo detection
        - Safe search detection
        
        Args:
            image_data (bytes): The raw image data
            
        Returns:
            Dict: Analysis results
        """
        if not cls.GOOGLE_API_KEY:
            return {"error": "Google API key is not configured"}
        
        # Encode image to base64
        encoded_image = base64.b64encode(image_data).decode('utf-8')
        
        # Prepare the Vision API request
        payload = {
            "requests": [
                {
                    "image": {
                        "content": encoded_image
                    },
                    "features": [
                        {"type": "LABEL_DETECTION", "maxResults": 15},
                        {"type": "TEXT_DETECTION", "model": "builtin/latest"},
                        {"type": "FACE_DETECTION", "maxResults": 10},
                        {"type": "LANDMARK_DETECTION", "maxResults": 5},
                        {"type": "LOGO_DETECTION", "maxResults": 5},
                        {"type": "IMAGE_PROPERTIES"},
                        {"type": "SAFE_SEARCH_DETECTION"},
                        {"type": "OBJECT_LOCALIZATION", "maxResults": 10}
                    ]
                }
            ]
        }
        
        # Make the API request
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    cls.VISION_API_URL,
                    params={"key": cls.GOOGLE_API_KEY},
                    json=payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return cls._process_vision_results(result)
                    else:
                        error_text = await response.text()
                        logger.error(f"Vision API error: {response.status}, {error_text}")
                        return {"error": f"API returned error {response.status}"}
        except Exception as e:
            logger.error(f"Error analyzing image: {str(e)}")
            return {"error": str(e)}
    
    @classmethod
    def _process_vision_results(cls, api_result: Dict) -> Dict:
        """Process and organize the Google Vision API results."""
        if not api_result.get('responses') or not api_result['responses'][0]:
            return {"error": "No results returned from API"}
        
        response = api_result['responses'][0]
        
        # Process the results
        results = {
            "labels": [],
            "text": "",
            "faces": 0,
            "face_details": [],
            "landmarks": [],
            "logos": [],
            "safe_search": {},
            "objects": [],
            "colors": [],
            "dominant_colors": []
        }
        
        # Process label annotations (objects, scenes)
        if 'labelAnnotations' in response:
            results['labels'] = [
                {
                    "description": label.get('description', ''),
                    "score": label.get('score', 0)
                }
                for label in response['labelAnnotations']
            ]
        
        # Process text annotations (OCR)
        if 'textAnnotations' in response and response['textAnnotations']:
            # The first result contains the entire extracted text
            results['text'] = response['textAnnotations'][0].get('description', '')
        
        # Process face annotations
        if 'faceAnnotations' in response:
            results['faces'] = len(response['faceAnnotations'])
            results['face_details'] = [
                {
                    "joy": cls._get_likelihood(face.get('joyLikelihood')),
                    "sorrow": cls._get_likelihood(face.get('sorrowLikelihood')),
                    "anger": cls._get_likelihood(face.get('angerLikelihood')),
                    "surprise": cls._get_likelihood(face.get('surpriseLikelihood')),
                    "headwear": cls._get_likelihood(face.get('headwearLikelihood'))
                }
                for face in response['faceAnnotations']
            ]
        
        # Process landmark annotations
        if 'landmarkAnnotations' in response:
            results['landmarks'] = [
                {
                    "name": landmark.get('description', ''),
                    "score": landmark.get('score', 0)
                }
                for landmark in response['landmarkAnnotations']
            ]
        
        # Process logo annotations
        if 'logoAnnotations' in response:
            results['logos'] = [
                {
                    "name": logo.get('description', ''),
                    "score": logo.get('score', 0)
                }
                for logo in response['logoAnnotations']
            ]
        
        # Process safe search annotations
        if 'safeSearchAnnotation' in response:
            safe_search = response['safeSearchAnnotation']
            results['safe_search'] = {
                "adult": cls._get_likelihood(safe_search.get('adult')),
                "spoof": cls._get_likelihood(safe_search.get('spoof')),
                "medical": cls._get_likelihood(safe_search.get('medical')),
                "violence": cls._get_likelihood(safe_search.get('violence')),
                "racy": cls._get_likelihood(safe_search.get('racy'))
            }
        
        # Process localized objects
        if 'localizedObjectAnnotations' in response:
            results['objects'] = [
                {
                    "name": obj.get('name', ''),
                    "score": obj.get('score', 0),
                    "box": obj.get('boundingPoly', {}).get('normalizedVertices', [])
                }
                for obj in response['localizedObjectAnnotations']
            ]
            
        # Process image properties (colors)
        if 'imagePropertiesAnnotation' in response:
            if 'dominantColors' in response['imagePropertiesAnnotation']:
                colors_info = response['imagePropertiesAnnotation']['dominantColors'].get('colors', [])
                
                # Extract color information
                for color_info in colors_info:
                    if 'color' in color_info:
                        color_data = color_info['color']
                        rgb = {
                            'red': color_data.get('red', 0),
                            'green': color_data.get('green', 0),
                            'blue': color_data.get('blue', 0),
                            'score': color_info.get('score', 0),
                            'pixelFraction': color_info.get('pixelFraction', 0)
                        }
                        results['colors'].append(rgb)
                
                # Get top 3 dominant colors
                results['dominant_colors'] = sorted(
                    results['colors'], 
                    key=lambda x: x.get('score', 0), 
                    reverse=True
                )[:3]
        
        return results
    
    @staticmethod
    def _get_likelihood(likelihood_text: str) -> float:
        """Convert likelihood text to a probability score."""
        likelihood_map = {
            'UNKNOWN': 0.0,
            'VERY_UNLIKELY': 0.0,
            'UNLIKELY': 0.25,
            'POSSIBLE': 0.5,
            'LIKELY': 0.75,
            'VERY_LIKELY': 1.0
        }
        return likelihood_map.get(likelihood_text, 0.0)
    
    @classmethod
    async def generate_analysis_image(cls, image_data: bytes, analysis_results: Dict) -> Tuple[bytes, str]:
        """
        Generate an annotated image highlighting detected objects, text, and faces.
        
        Returns:
            Tuple[bytes, str]: (Processed image data, text summary)
        """
        try:
            # Open the image
            image = Image.open(io.BytesIO(image_data))
            
            # Create a draw object
            draw = ImageDraw.Draw(image)
            
            # Try to use a nice font, default to system font if not available
            try:
                font = ImageFont.truetype('arial.ttf', 15)
            except IOError:
                font = ImageFont.load_default()
            
            # Summary text to return
            summary = []
            
            # Add labels at the top
            if analysis_results.get('labels'):
                top_labels = [label['description'] for label in analysis_results['labels'][:5]]
                label_text = "Objects: " + ", ".join(top_labels)
                summary.append(f"📋 *Objects Detected*: {', '.join(top_labels)}")
                draw.text((10, 10), label_text, fill=(255, 255, 0), font=font)
            
            # If there's text, add a section in the summary
            if analysis_results.get('text'):
                extracted_text = analysis_results['text']
                if len(extracted_text) > 100:
                    extracted_text = extracted_text[:100] + "..."
                summary.append(f"📝 *Extracted Text*: \n{extracted_text}")
            
            # Add face info if detected
            if analysis_results.get('faces', 0) > 0:
                face_count = analysis_results['faces']
                face_text = f"Detected {face_count} {'face' if face_count == 1 else 'faces'}"
                
                # Add emotions if available
                if analysis_results.get('face_details'):
                    emotions = []
                    for face in analysis_results['face_details']:
                        # Find the strongest emotion
                        emotion_dict = {
                            'joy': face.get('joy', 0),
                            'sorrow': face.get('sorrow', 0),
                            'anger': face.get('anger', 0),
                            'surprise': face.get('surprise', 0)
                        }
                        strongest_emotion = max(emotion_dict, key=emotion_dict.get)
                        if emotion_dict[strongest_emotion] > 0.5:  # Only include if confidence is high enough
                            emotions.append(strongest_emotion)
                    
                    if emotions:
                        face_text += f" with emotions: {', '.join(emotions)}"
                
                draw.text((10, 30), face_text, fill=(255, 0, 255), font=font)
                summary.append(f"👤 *Faces*: {face_count} {'face' if face_count == 1 else 'faces'} detected")
            
            # Add landmarks if detected
            if analysis_results.get('landmarks'):
                landmarks = [landmark['name'] for landmark in analysis_results['landmarks']]
                if landmarks:
                    summary.append(f"🏙️ *Landmarks*: {', '.join(landmarks)}")
            
            # Add logos if detected
            if analysis_results.get('logos'):
                logos = [logo['name'] for logo in analysis_results['logos']]
                if logos:
                    summary.append(f"🏢 *Logos*: {', '.join(logos)}")
            
            # Add detailed object info if detected
            if analysis_results.get('objects'):
                objects = [obj['name'] for obj in analysis_results['objects'][:5]]
                if objects:
                    # Draw bounding boxes on the image
                    width, height = image.size
                    for obj in analysis_results['objects']:
                        if 'box' in obj and obj['box']:
                            # Different color for each object type
                            color_hash = hash(obj['name']) % 255
                            box_color = (color_hash, 255 - color_hash, 255)
                            
                            try:
                                # Extract box vertices
                                vertices = obj['box']
                                if vertices and len(vertices) >= 4:
                                    # Convert normalized coordinates to image coordinates
                                    points = []
                                    for vertex in vertices:
                                        x = int(vertex.get('x', 0) * width)
                                        y = int(vertex.get('y', 0) * height)
                                        points.append((x, y))
                                    
                                    # Draw bounding box
                                    if len(points) >= 4:
                                        for i in range(4):
                                            draw.line([points[i], points[(i+1) % 4]], fill=box_color, width=3)
                                        
                                        # Draw label
                                        label_x = points[0][0]
                                        label_y = points[0][1] - 15
                                        draw.text((label_x, max(0, label_y)), obj['name'], fill=box_color, font=font)
                            except Exception as e:
                                logger.error(f"Error drawing object box: {str(e)}")
                    
                    summary.append(f"🔍 *Detailed Objects*: {', '.join(objects)}")
            
            # Add dominant color information
            if analysis_results.get('dominant_colors'):
                colors_info = []
                y_pos = 50  # Position for color swatches
                
                for i, color in enumerate(analysis_results['dominant_colors']):
                    r = color.get('red', 0)
                    g = color.get('green', 0)
                    b = color.get('blue', 0)
                    percentage = int(color.get('score', 0) * 100)
                    
                    # Draw color swatch
                    img_width, _ = image.size
                    x1 = img_width - 60
                    y1 = y_pos
                    x2 = img_width - 10
                    y2 = y_pos + 20
                    draw.rectangle([(x1, y1), (x2, y2)], fill=(r, g, b))
                    draw.text((img_width - 100, y_pos), f"{percentage}%", fill=(255, 255, 255), font=font)
                    
                    y_pos += 25
                    colors_info.append(f"RGB({r},{g},{b}): {percentage}%")
                
                if colors_info:
                    summary.append(f"🎨 *Dominant Colors*: {', '.join(colors_info)}")
            
            # Add safety info if concerning
            if analysis_results.get('safe_search'):
                safety = analysis_results['safe_search']
                concerns = []
                for category, score in safety.items():
                    if score > 0.75:  # Only include high confidence safety concerns
                        concerns.append(category)
                
                if concerns:
                    summary.append(f"⚠️ *Content Advisory*: This image may contain {', '.join(concerns)} content")
            
            # Save the image to a byte buffer
            output = io.BytesIO()
            image.save(output, format='JPEG')
            output.seek(0)
            
            # Create a text summary
            summary_text = "\n".join(summary)
            if not summary_text:
                summary_text = "No significant elements detected in this image."
                
            return output.getvalue(), summary_text
            
        except Exception as e:
            logger.error(f"Error generating analysis image: {str(e)}")
            return image_data, "Error generating analysis visualization."