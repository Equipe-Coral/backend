from src.core.gemini import gemini_client
import logging
import json

logger = logging.getLogger(__name__)

class RouterAgent:
    def __init__(self):
        self.client = gemini_client

    async def classify_and_extract(self, text: str) -> dict:
        prompt = f"""
Você é um assistente de classificação cívica no Brasil.

Analise a mensagem do cidadão e responda em JSON com:

{{
  "classification": "ONBOARDING" | "DEMANDA" | "DUVIDA" | "OUTRO",
  "theme": "saude" | "transporte" | "educacao" | "seguranca" | "meio_ambiente" | "zeladoria" | "outros",
  "location_mentioned": true | false,
  "location_text": "texto extraído sobre localização" ou null,
  "urgency": "critica" | "alta" | "media" | "baixa",
  "keywords": ["palavra1", "palavra2", ...],
  "confidence": 0.0 a 1.0
}}

Regras:
- ONBOARDING: primeira interação, saudação, mensagem vaga
- DEMANDA: reclamação, problema concreto, sugestão de melhoria
- DUVIDA: pergunta sobre lei, PL, direitos, processo
- OUTRO: elogio, feedback sobre a plataforma, fora de escopo

Mensagem: {text}
"""
        try:
            response_text = await self.client.generate_content(prompt)
            result = self.client.parse_json(response_text)
            
            # Validate basic structure
            if "classification" not in result:
                logger.warning("Invalid classification result from Gemini, using default")
                return self._default_result()
                
            return result
            
        except Exception as e:
            logger.error(f"Error in RouterAgent: {e}")
            return self._default_result()

    def _default_result(self):
        return {
            "classification": "OUTRO",
            "theme": "outros",
            "location_mentioned": False,
            "location_text": None,
            "urgency": "baixa",
            "keywords": [],
            "confidence": 0.0
        }
