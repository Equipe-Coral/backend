from src.core.gemini import gemini_client
import logging
import json
import re

logger = logging.getLogger(__name__)

class RouterAgent:
    """
    Agente Porteiro (The Router):
    Recebe a mensagem bruta e decide para qual fluxo ela deve ir.
    """
    
    def __init__(self):
        self.client = gemini_client

    async def classify_and_extract(self, text: str) -> dict:
        """
        Classifica mensagem do usuário
        Retorna classificação com fallback heurístico se API falhar
        """
        
        # FALLBACK HEURÍSTICO (antes de chamar API)
        # Garante que intenções claras não dependam apenas do LLM
        text_lower = text.lower().strip()
        
        # Gatilhos explícitos de demanda
        explicit_demand_triggers = [
            'criar demanda', 'criar uma demanda', 'nova demanda', 
            'fazer reclamação', 'fazer reclamacao', 'quero reclamar',
            'registrar problema', 'abrir chamado', 'denunciar', '1' # 1 é frequentemente usado em menus
        ]
        
        if any(trigger in text_lower for trigger in explicit_demand_triggers) or text_lower == '1':
            logger.info(f"🚀 Explicit demand trigger detected: {text}")
            return {
                "classification": "DEMANDA",
                "theme": "outros", # O Analyst vai descobrir o tema depois
                "location_mentioned": False,
                "location_text": None,
                "urgency": "media",
                "keywords": [],
                "confidence": 1.0
            }

        prompt = f"""Você é um classificador de intenções para um assistente cívico.
        
        Texto do usuário: "{text}"
        
        Classifique em:
        - ONBOARDING: Saudações ("oi", "ola") sem conteúdo.
        - DEMANDA: Relato de problema, solicitação de serviço ou intenção explícita ("quero criar demanda").
        - DUVIDA: Perguntas sobre leis, vereadores ou como funciona algo.
        - OUTRO: O que não se encaixa (elogios, spam).
        
        Retorne JSON estrito:
        {{
            "classification": "ONBOARDING" | "DEMANDA" | "DUVIDA" | "OUTRO",
            "theme": "saude" | "educacao" | "transporte" | "seguranca" | "zeladoria" | "outros",
            "location_mentioned": boolean,
            "location_text": string | null,
            "urgency": "baixa" | "media" | "alta",
            "keywords": [string]
        }}
        """
        
        try:
            response_text = await self.client.generate_content(prompt)
            result = self.client.parse_json(response_text)
            
            if not self._is_valid_result(result):
                logger.warning(f"Invalid classification from Gemini: {result}")
                return self._heuristic_classification(text)
                
            logger.info(f"Classification: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error in RouterAgent: {e}")
            return self._heuristic_classification(text)

    def _heuristic_classification(self, text: str) -> dict:
        """
        Classificação baseada em regras heurísticas simples (Fallback)
        """
        text_lower = text.lower().strip()
        
        # Palavras-chave básicas
        onboarding_words = ['oi', 'olá', 'ola', 'bom dia', 'boa tarde', 'boa noite', 'opa']
        
        if any(word == text_lower for word in onboarding_words):
            return {"classification": "ONBOARDING", "theme": "outros", "confidence": 0.9}
            
        return {
            "classification": "OUTRO",
            "theme": "outros",
            "location_mentioned": False,
            "location_text": None,
            "urgency": "media",
            "keywords": [],
            "confidence": 0.5
        }
    
    def _is_valid_result(self, result: dict) -> bool:
        return result.get('classification') in ['ONBOARDING', 'DEMANDA', 'DUVIDA', 'OUTRO']