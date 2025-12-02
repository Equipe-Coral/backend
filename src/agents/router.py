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
        
        REGRAS DE CLASSIFICAÇÃO:
        
        1. ONBOARDING: Apenas saudações vazias ("oi", "olá", "bom dia") SEM contexto adicional.
        
        2. DEMANDA: Use esta classificação quando o usuário:
           - Menciona um problema específico (buraco, lixo, iluminação, calçada quebrada, etc)
           - Quer relatar/reclamar/denunciar algo
           - Diz explicitamente "quero criar demanda", "relatar problema", etc
           - Responde "sim", "quero", "vamos lá" após ser perguntado se quer relatar algo
           - Descreve uma situação negativa que precisa ser resolvida
        
        3. DUVIDA: Perguntas sobre leis, vereadores, como funciona algo, informações sobre serviços públicos.
        
        4. OUTRO: Apenas use para mensagens vagas, sem contexto claro, ou que não se encaixam nas categorias acima.
        
        IMPORTANTE: Se houver QUALQUER indício de problema ou intenção de relatar algo, classifique como DEMANDA.
        
        Retorne JSON estrito:
        {{
            "classification": "ONBOARDING" | "DEMANDA" | "DUVIDA" | "OUTRO",
            "theme": "saude" | "educacao" | "transporte" | "seguranca" | "zeladoria" | "mobilidade" | "infraestrutura" | "outros",
            "location_mentioned": boolean,
            "location_text": string | null,
            "urgency": "baixa" | "media" | "alta" | "critica",
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
        onboarding_words = ['oi', 'olá', 'ola', 'bom dia', 'boa tarde', 'boa noite', 'opa', 'hey', 'ei']
        demand_keywords = [
            'problema', 'quebrado', 'buraco', 'iluminação', 'iluminacao', 'lixo', 
            'esgoto', 'calçada', 'calcada', 'rua', 'avenida', 'escola', 'posto', 
            'hospital', 'ônibus', 'onibus', 'trem', 'metrô', 'metro',
            'relatar', 'reclamar', 'reclamação', 'reclamacao', 'denunciar', 'denúncia', 'denuncia',
            'criar demanda', 'nova demanda', 'abrir chamado', 'registrar'
        ]
        question_keywords = ['como', 'o que', 'qual', 'quando', 'onde', 'por que', 'porque', 'quem', 'lei', 'vereador']
        
        if any(word == text_lower for word in onboarding_words):
            return {
                "classification": "ONBOARDING", 
                "theme": "outros", 
                "location_mentioned": False,
                "location_text": None,
                "urgency": "baixa",
                "keywords": [],
                "confidence": 0.9
            }
        
        # Detectar intenção de criar demanda
        if any(keyword in text_lower for keyword in demand_keywords):
            return {
                "classification": "DEMANDA",
                "theme": "outros",
                "location_mentioned": False,
                "location_text": None,
                "urgency": "media",
                "keywords": [k for k in demand_keywords if k in text_lower],
                "confidence": 0.7
            }
        
        # Detectar pergunta
        if any(keyword in text_lower for keyword in question_keywords):
            return {
                "classification": "DUVIDA",
                "theme": "outros",
                "location_mentioned": False,
                "location_text": None,
                "urgency": "baixa",
                "keywords": [],
                "confidence": 0.6
            }
            
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