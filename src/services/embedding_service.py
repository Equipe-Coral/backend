from google.generativeai import embed_content
import google.generativeai as genai
import logging

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Gera embeddings para busca semântica"""
    
    def __init__(self):
        from src.core.config import settings
        genai.configure(api_key=settings.GOOGLE_GEMINI_API_KEY)
        self.model = "models/text-embedding-004"
    
    async def generate_embedding(self, text: str) -> list:
        """
        Gera embedding de um texto usando Gemini
        
        Args:
            text: Texto para gerar embedding (título + descrição da demanda)
        
        Returns:
            list: Vetor de 768 dimensões
        """
        try:
            # Limitar tamanho do texto (Gemini tem limite)
            text_truncated = text[:2000]
            
            result = embed_content(
                model=self.model,
                content=text_truncated,
                task_type="retrieval_document"
            )
            
            embedding = result['embedding']
            logger.info(f"Generated embedding with {len(embedding)} dimensions")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Retornar vetor zero como fallback
            return [0.0] * 768
    
    def prepare_text_for_embedding(self, title: str, description: str, theme: str) -> str:
        """
        Prepara texto combinado para gerar embedding mais rico
        
        Combina título, descrição e tema para melhor similaridade
        """
        combined = f"Tema: {theme}\nTítulo: {title}\nDescrição: {description}"
        return combined
