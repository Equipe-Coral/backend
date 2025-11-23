import google.generativeai as genai
from src.core.config import settings
import json
import logging
import re
from typing import Any

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

    def parse_json(self, text: str) -> Any:
        """
        Parser de JSON robusto que lida com:
        1. Blocos de markdown (```json ... ```)
        2. Listas [] ou Objetos {}
        3. Texto sujo ao redor do JSON
        """
        text = text.strip()
        
        # 1. Tentar remover blocos de código Markdown
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()

        # 2. Tentar encontrar o JSON (primeiro [ ou { até o último ] ou })
        try:
            idx_obj = text.find('{')
            idx_arr = text.find('[')
            
            start_idx = -1
            end_char = ''
            
            # Descobre se começa com { ou [
            if idx_obj != -1 and (idx_arr == -1 or idx_obj < idx_arr):
                start_idx = idx_obj
                end_char = '}'
            elif idx_arr != -1:
                start_idx = idx_arr
                end_char = ']'
            
            if start_idx != -1:
                end_idx = text.rfind(end_char)
                if end_idx != -1:
                    candidate = text[start_idx : end_idx + 1]
                    return json.loads(candidate)
            
            # Se não achou delimitadores, tenta parse direto (caso o texto seja só o JSON)
            return json.loads(text)
            
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from Gemini: {text[:100]}...")
            return [] if '[' in text else {}
        except Exception as e:
            logger.error(f"Error parsing JSON: {e}")
            return {}

gemini_client = GeminiClient()