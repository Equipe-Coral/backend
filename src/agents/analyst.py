import logging
import google.generativeai as genai
import json
from src.core.gemini import gemini_client

logger = logging.getLogger(__name__)

class AnalystAgent:
    """
    Agente responsável por analisar a qualidade da demanda e orquestrar a entrevista.
    """
    
    def __init__(self):
        self.client = gemini_client # Usa o cliente centralizado

    async def analyze_completeness(self, current_text: str, current_data: dict) -> dict:
        """
        Analisa se temos informações suficientes para criar uma demanda de alta qualidade.
        """
        prompt = f"""
        Você é um analista de ouvidoria. Analise os dados que já temos sobre uma demanda.

        RELATO ATUAL: "{current_text}"
        TEMA: {current_data.get('theme', 'Não Identificado')}
        LOCAL: {current_data.get('location', 'Não especificada')}
        
        VERIFIQUE SE FALTA ALGO CRÍTICO (apenas 1 por vez):
        1. LOCAL_ESPECIFICO: Se o tema exige local (buraco, escola, ônibus), sabemos onde é?
        2. URGENCIA: Sabemos se é urgente/grave?
        3. DETALHES: O relato é muito curto (menos de 5 palavras) ou vago?

        Retorne JSON:
        {{
            "status": "incomplete" ou "complete",
            "missing_field": "location_entity" | "urgency" | "details" | null,
            "reason": "Explicação curta"
        }}
        """
        
        try:
            response_text = await self.client.generate_content(prompt) 
            return self.client.parse_json(response_text)
        except Exception as e:
            logger.error(f"Error in completeness analysis: {e}")
            return {"status": "complete", "missing_field": None} 

    async def determine_scope_level(self, classification: dict, user_location: dict) -> int:
        """Determina o nível de escopo da demanda (1, 2 ou 3)."""
        theme = classification.get('theme', 'outros')
        if theme in ['zeladoria', 'iluminacao', 'buraco', 'vizinhanca']: return 1
        if theme in ['transporte', 'saude', 'educacao', 'seguranca']: return 2
        return 3

    async def generate_demand_content(self, full_history_text: str, classification: dict, scope_level: int) -> dict:
        """Gera o título e descrição final."""
        prompt = f"""
        Gere um título oficial e uma descrição técnica para esta demanda cívica.
        
        Histórico: "{full_history_text}"
        Tema: {classification.get('theme')}
        
        JSON esperado:
        {{
            "title": "Título curto (max 10 palavras)",
            "description": "Descrição completa e formal.",
            "affected_entity": "Entidade afetada (se houver)",
            "urgency_level": "Baixa", "Média", "Alta" ou "Crítica"
        }}
        """
        try:
            response_text = await self.client.generate_content(prompt) 
            return self.client.parse_json(response_text)
        except Exception:
            return {
                "title": f"Demanda sobre {classification.get('theme')}",
                "description": full_history_text,
                "urgency_level": "Média"
            }