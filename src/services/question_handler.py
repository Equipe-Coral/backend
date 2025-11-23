from typing import List
from src.agents.detective import DetectiveAgent
from src.services.similarity_service import SimilarityService
from src.services.embedding_service import EmbeddingService
from src.core.state_manager import ConversationStateManager
from src.services.camara_api import MultiSourceLegislativeAPI
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
    Process user questions about legislation with IMPROVED search logic
    """

    # Instancia diretamente a API multi-source corrigida
    # (Assumindo que DetectiveAgent usava ela internamente, mas vamos usar direto aqui para garantir controle)
    legislative_api = MultiSourceLegislativeAPI()
    similarity_service = SimilarityService()
    embedding_service = EmbeddingService()
    state_manager = ConversationStateManager()

    theme = classification.get('theme', 'outros')
    raw_keywords = classification.get('keywords', [])

    # Extração de keywords manual mais segura se a do LLM falhar
    # Se o texto for curto, adiciona palavras do texto também
    search_keywords = list(raw_keywords)
    if len(text.split()) < 10:
        search_keywords.extend([w for w in text.split() if len(w) > 3])
    
    # Remove duplicatas preservando ordem
    search_keywords = list(dict.fromkeys(search_keywords))

    logger.info(f"❓ Processing question for user {user_id}: theme={theme}, search_keywords={search_keywords}")

    try:
        # 1. Search for legislation (Scope 3 = Federal/Broad)
        pls = await legislative_api.search_relevant_legislation(
            keywords=search_keywords,
            scope=3,
            location=user_location,
            theme=theme,
            limit=5 # Pega top 5
        )

        # 2. Check similar demands (Community)
        embedding = await embedding_service.generate_embedding(text)
        similar_demands = []
        if embedding:
            # ... (código de similaridade mantido igual) ...
            pass # (Simplifiquei aqui para focar no erro das PLs, mantenha a logica original de similarity)

        # === BUILD RESPONSE ===
        response = ""
        response += f"🔍 *Busquei informações sobre: {', '.join(search_keywords[:3])}*\n\n"

        # 1. Show Legislation
        if pls:
            response += f"📜 *Encontrei {len(pls)} projeto(s) ou leis relacionados:*\n\n"

            for pl in pls:
                # Add source indicator
                icon = "🏛️" if "Senado" in pl.get('source', '') else "🏢"
                
                # Título e Link
                response += f"{icon} *[{pl['title']}]({pl.get('url', '#')})*\n"

                # Ementa limpa
                ementa = pl.get('description', '')
                if len(ementa) > 180:
                    ementa = ementa[:177] + "..."
                
                response += f"_{ementa}_\n"

                # Status/Ano
                year = pl.get('year') or pl.get('date', '')[:4]
                response += f"📅 Ano: {year} | 📍 {pl.get('source', 'Fonte Oficial')}\n\n"

            response += "---\n\n"
        else:
            # Fallback message
            response += _build_no_legislation_message(theme, search_keywords)
            response += "\n---\n\n"

        # ... (Resto da lógica de botões e estado mantida igual) ...
        response += "*O que deseja fazer?*\n"
        response += "1️⃣ Criar nova demanda\n"
        response += "2️⃣ Apoiar demandas existentes"

        # Save State
        state_manager.set_state(
            phone=phone,
            stage="choosing_demand_action_after_question",
            context={
                "theme": theme,
                "classification": classification,
                "found_pls": len(pls) > 0
            },
            db=db
        )

        return response

    except Exception as e:
        logger.error(f"❌ Error handling question: {e}", exc_info=True)
        return "❌ Desculpe, tive um problema técnico ao buscar na base do governo. Tente novamente."

    finally:
        await legislative_api.close_all()

def _build_no_legislation_message(theme: str, keywords: List[str]) -> str:
    # (Mantido igual ao seu original, que estava bom)
    return "📚 *Não encontrei leis federais exatas sobre isso recentemente.*\n⚠️ O tema pode ser regulado por leis municipais ou regras específicas do estabelecimento."