from sqlalchemy.orm import Session
from sqlalchemy import text
from src.models.demand import Demand
import logging

logger = logging.getLogger(__name__)

class SimilarityService:
    """Busca demandas similares usando pgvector"""
    
    async def find_similar_demands(
        self,
        embedding: list,
        theme: str,
        scope_level: int,
        user_location: dict,
        db: Session,
        similarity_threshold: float = 0.80,
        max_results: int = 5
    ) -> list:
        """
        Busca demandas similares usando busca vetorial
        
        Args:
            embedding: Vetor de embedding da nova demanda
            theme: Tema da demanda (filtro)
            scope_level: Escopo da demanda (filtro)
            user_location: Localização do usuário (para filtro geográfico em Nível 1)
            db: Sessão do banco
            similarity_threshold: Threshold de similaridade cosseno (0.0-1.0)
            max_results: Máximo de resultados
        
        Returns:
            list: Lista de demandas similares com score de similaridade
        """
        
        # Converter embedding para string PostgreSQL
        embedding_str = '[' + ','.join(map(str, embedding)) + ']'
        
        # Query com sintaxe correta para SQLAlchemy + psycopg2
        query = text("""
            SELECT 
                id,
                title,
                description,
                scope_level,
                theme,
                location,
                supporters_count,
                created_at,
                1 - (embedding <=> CAST(:embedding AS vector)) as similarity
            FROM demands
            WHERE 
                status = 'active'
                AND theme = :theme
                AND scope_level = :scope_level
                AND embedding IS NOT NULL
                AND 1 - (embedding <=> CAST(:embedding AS vector)) >= :threshold
            ORDER BY similarity DESC
            LIMIT :max_results
        """)
        
        try:
            # Executar query
            result = db.execute(
                query,
                {
                    "embedding": embedding_str,
                    "theme": theme,
                    "scope_level": scope_level,
                    "threshold": similarity_threshold,
                    "max_results": max_results
                }
            )
            
            similar_demands = []
            for row in result:
                demand_dict = {
                    "id": str(row.id),
                    "title": row.title,
                    "description": row.description,
                    "scope_level": row.scope_level,
                    "theme": row.theme,
                    "location": row.location,
                    "supporters_count": row.supporters_count,
                    "created_at": row.created_at,
                    "similarity": float(row.similarity)
                }
                
                # Filtro geográfico adicional para Nível 1 (hiper-local)
                if scope_level == 1:
                    if self._is_geographically_close(demand_dict['location'], user_location):
                        similar_demands.append(demand_dict)
                else:
                    similar_demands.append(demand_dict)
            
            logger.info(f"✅ Found {len(similar_demands)} similar demands (threshold: {similarity_threshold})")
            return similar_demands
            
        except Exception as e:
            logger.error(f"❌ Error finding similar demands: {e}")
            # Retornar lista vazia em caso de erro
            return []
    
    def _is_geographically_close(self, demand_location: dict, user_location: dict, max_distance_km: float = 2.0) -> bool:
        """
        Verifica se localização da demanda está próxima do usuário
        Usa fórmula de Haversine para distância
        
        Args:
            demand_location: Localização da demanda
            user_location: Localização do usuário
            max_distance_km: Distância máxima em km
        
        Returns:
            bool: True se está próximo
        """
        if not demand_location or not user_location:
            return True  # Se não tem coordenadas, aceita
        
        demand_coords = demand_location.get('coordinates')
        user_coords = user_location.get('coordinates')
        
        if not demand_coords or not user_coords:
            return True
        
        try:
            from math import radians, cos, sin, asin, sqrt
            
            lat1, lon1 = radians(demand_coords[0]), radians(demand_coords[1])
            lat2, lon2 = radians(user_coords[0]), radians(user_coords[1])
            
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * asin(sqrt(a))
            
            distance_km = 6371 * c  # Raio da Terra em km
            
            is_close = distance_km <= max_distance_km
            logger.debug(f"Distance: {distance_km:.2f}km | Close: {is_close}")
            
            return is_close
            
        except Exception as e:
            logger.error(f"Error calculating distance: {e}")
            return True  # Em caso de erro, aceita
