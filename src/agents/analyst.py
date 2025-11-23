import logging

logger = logging.getLogger(__name__)

class AnalystAgent:
    """
    Agente responsável por analisar demandas, determinar escopo e gerar conteúdo estruturado.
    """
    
    async def determine_scope_level(self, classification: dict, user_location: dict) -> int:
        """
        Determina o nível de escopo da demanda (1, 2 ou 3).
        Por enquanto, retorna 1 (Hiper-local) como padrão.
        """
        # TODO: Implementar lógica real com LLM ou heurísticas
        return 1
    
    async def generate_demand_content(self, text: str, classification: dict, scope_level: int) -> dict:
        """
        Gera título e descrição estruturados para a demanda.
        """
        theme = classification.get('theme', 'Geral')
        
        return {
            "title": f"Demanda sobre {theme}",
            "description": text,
            "affected_entity": None
        }
