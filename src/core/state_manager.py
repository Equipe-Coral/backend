import logging
from typing import Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from src.models.conversation_state import ConversationState

logger = logging.getLogger(__name__)

class ConversationStateManager:
    """Gerencia estados da conversa para multi-turn interactions"""

    def get_state(self, phone: str, db: Session) -> Optional[ConversationState]:
        """
        Busca o estado atual da conversa para um telefone.
        
        Args:
            phone: Número de telefone
            db: Sessão do banco de dados
            
        Returns:
            ConversationState ou None se não existir
        """
        try:
            # Forçar busca no banco (não usar cache)
            db.expire_all()
            
            state = db.query(ConversationState).filter(
                ConversationState.phone == phone
            ).first()
            
            if state:
                # Forçar reload dos dados do banco
                db.refresh(state)
                logger.info(f"State found for {phone}: {state.current_stage}")
                logger.debug(f"State context_data: {state.context_data}")
            else:
                logger.info(f"No state found for {phone}")
                
            return state
            
        except Exception as e:
            logger.error(f"Error getting conversation state: {e}")
            return None

    def set_state(
        self, 
        phone: str, 
        stage: str, 
        context: Dict, 
        db: Session
    ) -> ConversationState:
        """
        Define ou atualiza o estado da conversa (upsert).
        
        Args:
            phone: Número de telefone
            stage: Novo estágio da conversa
            context: Dados de contexto (JSONB)
            db: Sessão do banco de dados
            
        Returns:
            ConversationState criado ou atualizado
        """
        try:
            state = db.query(ConversationState).filter(
                ConversationState.phone == phone
            ).first()
            
            if state:
                # Update existing state
                state.current_stage = stage
                state.context_data = context
                state.last_message_at = func.now()
                logger.info(f"Updated state for {phone}: {stage}")
            else:
                # Create new state
                state = ConversationState(
                    phone=phone,
                    current_stage=stage,
                    context_data=context
                )
                db.add(state)
                logger.info(f"Created new state for {phone}: {stage}")
            
            db.commit()
            db.refresh(state)
            return state
            
        except Exception as e:
            logger.error(f"Error setting conversation state: {e}")
            db.rollback()
            raise

    def clear_state(self, phone: str, db: Session) -> bool:
        """
        Remove o estado da conversa (conversa finalizada).
        
        Args:
            phone: Número de telefone
            db: Sessão do banco de dados
            
        Returns:
            True se removido com sucesso, False caso contrário
        """
        try:
            deleted_count = db.query(ConversationState).filter(
                ConversationState.phone == phone
            ).delete()
            
            db.commit()
            
            if deleted_count > 0:
                logger.info(f"Cleared state for {phone}")
                return True
            else:
                logger.info(f"No state to clear for {phone}")
                return False
                
        except Exception as e:
            logger.error(f"Error clearing conversation state: {e}")
            db.rollback()
            return False

    def update_context(self, phone: str, new_data: Dict, db: Session) -> bool:
        """
        Atualiza o contexto sem mudar o estágio.
        
        Args:
            phone: Número de telefone
            new_data: Novos dados para adicionar ao contexto
            db: Sessão do banco de dados
            
        Returns:
            True se atualizado com sucesso, False caso contrário
        """
        try:
            state = db.query(ConversationState).filter(
                ConversationState.phone == phone
            ).first()
            
            if not state:
                logger.warning(f"No state found to update context for {phone}")
                return False
            
            # Merge new data with existing context
            if state.context_data:
                state.context_data.update(new_data)
            else:
                state.context_data = new_data
            
            state.last_message_at = func.now()
            
            db.commit()
            logger.info(f"Updated context for {phone}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating context: {e}")
            db.rollback()
            return False
