from sqlalchemy.orm import Session
from src.models.demand import Demand
from src.models.demand_supporter import DemandSupporter
from src.services.embedding_service import EmbeddingService
import logging

logger = logging.getLogger(__name__)

class DemandService:
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
    
    async def create_demand(
        self,
        creator_id: str,
        title: str,
        description: str,
        scope_level: int,
        theme: str,
        location: dict,
        affected_entity: str,
        urgency: str,
        db: Session
    ) -> Demand:
        """Cria nova demanda com embedding"""
        
        # Gerar embedding
        text_for_embedding = self.embedding_service.prepare_text_for_embedding(
            title, description, theme
        )
        embedding = await self.embedding_service.generate_embedding(text_for_embedding)
        
        demand = Demand(
            creator_id=creator_id,
            title=title,
            description=description,
            scope_level=scope_level,
            theme=theme,
            location=location,
            affected_entity=affected_entity,
            urgency=urgency,
            supporters_count=1,
            embedding=embedding  # NOVO
        )
        
        db.add(demand)
        db.flush()
        
        # Adicionar criador como apoiador
        supporter = DemandSupporter(
            demand_id=demand.id,
            user_id=creator_id
        )
        db.add(supporter)
        
        db.commit()
        db.refresh(demand)
        
        logger.info(f"✅ Demand created with embedding: {demand.id}")
        return demand
    
    async def add_supporter(
        self,
        demand_id: str,
        user_id: str,
        db: Session
    ) -> bool:
        """
        Adiciona usuário como apoiador de uma demanda
        
        Returns:
            bool: True se adicionou, False se já era apoiador
        """
        # Verificar se já apoia
        existing = db.query(DemandSupporter).filter(
            DemandSupporter.demand_id == demand_id,
            DemandSupporter.user_id == user_id
        ).first()
        
        if existing:
            logger.info(f"User {user_id} already supports demand {demand_id}")
            return False
        
        # Adicionar apoio
        supporter = DemandSupporter(
            demand_id=demand_id,
            user_id=user_id
        )
        db.add(supporter)
        
        # Incrementar contador
        demand = db.query(Demand).filter(Demand.id == demand_id).first()
        if demand:
            demand.supporters_count += 1
        
        db.commit()
        
        logger.info(f"✅ User {user_id} now supports demand {demand_id}")
        return True
    
    def get_demand_link(self, demand_id) -> str:
        # Placeholder for link generation
        return f"https://coral.app/demands/{demand_id}"
