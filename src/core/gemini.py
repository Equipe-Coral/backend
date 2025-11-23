import google.generativeai as genai
from src.core.config import settings
import json
import logging

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self):
        if not settings.GOOGLE_GEMINI_API_KEY:
            logger.warning("GOOGLE_GEMINI_API_KEY not set")
            self.model = None
            return

        genai.configure(api_key=settings.GOOGLE_GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL_FLASH)

    async def generate_content(self, prompt: str) -> str:
        if not self.model:
            raise ValueError("Gemini API key not configured")
        
        try:
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error calling Gemini: {e}")
            raise

    def parse_json(self, text: str) -> dict:
        """Robust JSON parser for LLM responses"""
        try:
            # Try direct parse
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON block
            try:
                start = text.find('{')
                end = text.rfind('}') + 1
                if start != -1 and end != -1:
                    json_str = text[start:end]
                    return json.loads(json_str)
            except Exception:
                pass
            
            logger.error(f"Failed to parse JSON from Gemini: {text}")
            return {}

gemini_client = GeminiClient()
