from typing import List
from src.agents.detective import DetectiveAgent
from src.services.similarity_service import SimilarityService
from src.services.embedding_service import EmbeddingService
from src.core.state_manager import ConversationStateManager
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
    Processa dúvidas do usuário buscando legislação via Gemini (DetectiveAgent).
    """

    # Instancia os serviços
    detective = DetectiveAgent()
    embedding_service = EmbeddingService()
    state_manager = ConversationStateManager()

    theme = classification.get('theme', 'outros')
    raw_keywords = classification.get('keywords', [])

    # Preparar keywords
    search_keywords = list(raw_keywords)
    if len(text.split()) < 10:
        search_keywords.extend([w for w in text.split() if len(w) > 3])
    search_keywords = list(dict.fromkeys(search_keywords))

    logger.info(f"❓ Processing question for user {user_id}: theme={theme}")

    try:
        # 1. Buscar legislação usando o Detective (agora via Gemini)
        pls = await detective.find_related_pls(
            theme=theme,
            keywords=search_keywords,
            db=db,
            scope_level=3, # Macro/Federal
            location=user_location,
            user_message=text
        )

        # === CONSTRUIR RESPOSTA ===
        response = ""
        response += f"🔍 *Busquei informações sobre: {theme.replace('_', ' ').title()}*\n\n"

        # 1. Mostrar Legislação
        if pls:
            response += f"📜 *Encontrei {len(pls)} leis ou projetos relacionados:*\n\n"

            for pl in pls:
                # Ícone baseado na fonte
                icon = "🏛️"
                if "Senado" in pl.get('source', ''): icon = "🏢"
                elif "Municipal" in pl.get('source', ''): icon = "🏡"
                
                # Título e Link
                url = pl.get('url') or '#'
                response += f"{icon} *[{pl['title']}]({url})*\n"
                
                # Descrição concisa
                summary = pl.get('summary') or pl.get('ementa', '')
                response += f"_{summary}_\n"

                # Status
                status = pl.get('status', 'Ativo')
                response += f"📊 Status: {status}\n\n"

            # REMOVIDO: response += "---\n" (O traço foi retirado)
            response += "\n" # Apenas um espaço extra
        else:
            response += _build_no_legislation_message(theme, search_keywords)
            # REMOVIDO: response += "\n---\n" (O traço foi retirado)
            response += "\n\n"

        # 2. Botões de Ação com Explicação
        response += "*O que deseja fazer?*\n\n"
        
        response += "1️⃣ *Criar nova demanda sobre isso*\n"
        response += "_(Para registrar o problema e iniciar uma mobilização)_\n\n"
        
        response += "2️⃣ *Apoiar demandas existentes*\n"
        response += "_(Para fortalecer pedidos já feitos pela comunidade)_"

        # Salvar Estado
        state_manager.set_state(
            phone=phone,
            stage="choosing_demand_action_after_question",
            context={
                "theme": theme,
                "classification": classification,
                "found_pls": len(pls) > 0,
                "original_question": text,
                "keywords": search_keywords
            },
            db=db
        )

        return response

    except Exception as e:
        logger.error(f"❌ Error handling question: {e}", exc_info=True)
        return "❌ Desculpe, tive um problema técnico ao analisar sua dúvida. Tente novamente."

    finally:
        await detective.close()

def _build_no_legislation_message(theme: str, keywords: List[str]) -> str:
    return "📚 *Não encontrei leis específicas sobre isso no momento.*\n⚠️ O tema pode ser muito recente ou regulado por normas locais."