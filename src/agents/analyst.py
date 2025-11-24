import logging
import google.generativeai as genai
import json

logger = logging.getLogger(__name__)

class AnalystAgent:
    """
    Agente responsável por analisar a qualidade da demanda e orquestrar a entrevista.
    """
    
    def __init__(self):
        # Assumindo que genai.configure foi chamado em src.core.gemini
        self.client = genai.GenerativeModel('gemini-2.0-flash-lite')

    async def analyze_completeness(self, current_text: str, current_data: dict) -> dict:
        """
        Analisa se temos informações suficientes para criar uma demanda de alta qualidade.
        Retorna o próximo campo a perguntar ou 'complete' se estiver tudo ok.
        """
        
        prompt = f"""
        Você é um analista de ouvidoria experiente. Analise os dados que já temos sobre uma demanda do cidadão.

        DADOS ATUAIS:
        - Histórico de relatos: "{current_text}"
        - Tema preliminar: {current_data.get('theme', 'Não Identificado')}
        - Localização inicial: {current_data.get('location', 'Não especificada')}
        
        CAMPOS CRÍTICOS (em ordem de prioridade para perguntar):
        1. LOCAL_ESPECIFICO: Se o tema for local (zeladoria, transporte, escola), o relato menciona o endereço exato, o nome da linha de ônibus ou o nome da instituição afetada? (Ex: Rua X, UBS Maria, Linha 300)
        2. URGENCIA: O relato sugere um problema urgente/grave? (Risco de vida/saúde ou persistência que exige prioridade).
        3. DETALHES: O relato está muito curto (menos de 5 palavras) ou vago, precisando de mais contexto (O que, como, quando)?

        TAREFA:
        Identifique QUAL é a informação mais crítica que está faltando para ter uma demanda de alta qualidade. Escolha APENAS UMA, seguindo a ordem de prioridade.
        
        Retorne APENAS o JSON válido:
        {{
            "status": "incomplete" ou "complete",
            "missing_field": "location_entity" | "urgency" | "details" | null,
            "reason": "Explicação curta do porquê precisamos disso"
        }}
        """
        # Note: A chamada ao LLM precisa ser feita de forma síncrona/assíncrona dependendo da sua configuração.
        try:
            # Assumindo o uso direto da SDK de forma assíncrona (se o ambiente permitir)
            response = await self.client.generate_content_async(prompt) 
            # Reutilizando o parser robusto de src/core/gemini
            from src.core.gemini import gemini_client
            return gemini_client.parse_json(response.text)
        except Exception as e:
            logger.error(f"Error in completeness analysis: {e}")
            return {"status": "complete", "missing_field": None} # Fallback para não travar

    async def determine_scope_level(self, classification: dict, user_location: dict) -> int:
        """Determina o nível de escopo da demanda (1, 2 ou 3) de forma heurística."""
        theme = classification.get('theme', 'outros')
        # Nível 1: Hiper-local
        if theme in ['zeladoria', 'iluminacao', 'buraco', 'vizinhanca']: 
            return 1
        # Nível 2: Serviço/Região
        if theme in ['transporte', 'saude', 'educacao', 'seguranca']: 
            return 2
        # Nível 3: Nacional/Macro
        return 3

    async def generate_demand_content(self, full_history_text: str, classification: dict, scope_level: int) -> dict:
        """Gera o título e descrição final baseados em toda a conversa"""
        prompt = f"""
        Gere um título oficial e uma descrição técnica detalhada para esta demanda cívica, baseada em todo o histórico de informações.
        
        Histórico da conversa: "{full_history_text}"
        Tema: {classification.get('theme')}
        
        JSON esperado:
        {{
            "title": "Título curto e impactante (max 10 palavras)",
            "description": "Descrição completa, formal e detalhada do problema, unindo todas as informações coletadas, mas sem frases de chat.",
            "affected_entity": "Nome da escola, linha de ônibus ou entidade afetada (se identificada, senão null)",
            "urgency_level": "Baixa", "Média", "Alta" ou "Crítica"
        }}
        """
        try:
            response = await self.client.generate_content_async(prompt) 
            from src.core.gemini import gemini_client
            return gemini_client.parse_json(response.text)
        except Exception:
            return {
                "title": f"Demanda sobre {classification.get('theme', 'Geral')}",
                "description": full_history_text,
                "affected_entity": None,
                "urgency_level": "Média"
            }