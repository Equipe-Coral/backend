from typing import List
from src.agents.detective import DetectiveAgent
from src.services.similarity_service import SimilarityService
from src.services.embedding_service import EmbeddingService
from src.core.state_manager import ConversationStateManager
from src.agents.writer import WriterAgent  # NOVO
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

async def handle_question(
    user_id: str,
    phone: str,
    text: str,
    classification: dict,
    user_location: dict,
    db: Session
) -> str:
    """
    Processa dúvidas do usuário buscando legislação via Gemini (DetectiveAgent)
    e formatando a resposta final com o WriterAgent.
    """

    # Instancia os serviços e agentes
    detective = DetectiveAgent()
    state_manager = ConversationStateManager()
    writer = WriterAgent()  # INSTANCIAÇÃO
    
    theme = classification.get('theme', 'outros')
    raw_keywords = classification.get('keywords', [])

    # Preparar keywords
    search_keywords = list(raw_keywords)
    if len(text.split()) < 10:
        search_keywords.extend([w for w in text.split() if len(w) > 3])
    search_keywords = list(dict.fromkeys(search_keywords))

    logger.info(f"❓ Processing question for user {user_id}: theme={theme}")

    try:
        # 1. Buscar legislação usando o Detective
        pls = await detective.find_related_pls(
            theme=theme,
            keywords=search_keywords,
            db=db,
            scope_level=3,  # Macro/Federal
            location=user_location,
            user_message=text
        )

        # 2. Gerar a resposta completa (PLs e Opções) usando WriterAgent
        response = await writer.explain_pls_and_actions(
            theme=theme,
            pls=pls
        )

        # 3. Salvar Estado (para a próxima escolha do usuário)
        state_manager.set_state(
            phone=phone,
            stage="choosing_demand_action_after_question",
            context={
                "theme": theme,
                "classification": classification,
                "found_pls": len(pls) > 0,
                "original_question": text,
                "keywords": search_keywords,
                # Salva PLs para referência futura no action_handler se necessário
                "pls": [{'title': p.get('title'), 'url': p.get('url')} for p in pls]
            },
            db=db
        )

        return response

    except Exception as e:
        logger.error(f"❌ Error handling question: {e}", exc_info=True)
        # Resposta de erro genérica via WriterAgent
        return await writer.generic_error_response()

    finally:
        # Fecha conexões se necessário (mantido do código original)
        await detective.close()