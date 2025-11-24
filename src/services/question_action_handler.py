from src.core.state_manager import ConversationStateManager
from src.services.demand_handler import handle_create_demand_decision
from sqlalchemy.orm import Session
import logging
import google.generativeai as genai
from src.core.config import settings
from src.models.demand import Demand
from src.services.similarity_service import SimilarityService
from src.services.embedding_service import EmbeddingService
from src.agents.writer import WriterAgent

logger = logging.getLogger(__name__)

async def _reformulate_question_to_demand(question: str, theme: str, keywords: list) -> str:
    """
    Use Gemini to reformulate a user's question into a proper demand statement
    """
    logger.info(f"🔄 Starting reformulation: question='{question}', theme='{theme}', keywords={keywords}")
    
    try:
        genai.configure(api_key=settings.GOOGLE_GEMINI_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL_FLASH)
        
        prompt = f"""Você é um assistente que ajuda cidadãos a criar demandas por melhorias e legislação.

O usuário fez a seguinte pergunta sobre legislação:
"{question}"

Tema identificado: {theme}
Palavras-chave: {', '.join(keywords) if keywords else 'nenhuma'}

Sua tarefa é REFORMULAR esta pergunta como uma DEMANDA ou DESEJO de mudança legislativa.

IMPORTANTE:
- Transforme a pergunta em uma afirmação do que o usuário GOSTARIA que existisse
- Use linguagem clara e assertiva
- Mantenha o contexto e a intenção original
- Seja conciso (máximo 1-2 frases)
- NÃO use perguntas
- Use verbos como "gostaria", "necessito", "quero", "preciso"

Exemplos de transformação:
Pergunta: "quais os PL que permitem eu entrar com meu cachorro no restaurante?"
Demanda: "Gostaria de uma legislação que permitisse entrar com animais de estimação em estabelecimentos comerciais como restaurantes"

Pergunta: "existe alguma lei que obrigue estabelecimentos a terem água gratuita?"
Demanda: "Gostaria que estabelecimentos comerciais fossem obrigados a fornecer água potável gratuita"

Agora reformule a pergunta do usuário:"""

        logger.debug("📡 Calling Gemini API for reformulation...")
        response = await model.generate_content_async(prompt)
        
        if not response or not response.text:
            logger.error("❌ Gemini returned empty response")
            return question
            
        reformulated = response.text.strip()
        
        # Remove quotes if present
        reformulated = reformulated.strip('"\'')
        
        logger.info(f"✅ Successfully reformulated: '{question}' -> '{reformulated}'")
        return reformulated
        
    except Exception as e:
        logger.error(f"❌ Error reformulating question: {type(e).__name__}: {str(e)}", exc_info=True)
        logger.warning(f"⚠️ Falling back to original question due to error")
        return question

async def handle_question_action_choice(
    user_id: str,
    phone: str,
    text: str,
    state_context: dict,
    user_location: dict,
    db: Session
) -> str:
    """
    Handle user's choice after seeing PLs and similar demands from a question
    """

    state_manager = ConversationStateManager()
    writer = WriterAgent()
    choice = text.strip().lower()

    logger.info(f"📋 Processing question action choice for user {user_id}: choice='{choice}'")

    similar_demands_context = state_context.get('similar_demands', [])
    has_similar = len(similar_demands_context) > 0
    
    # --- CONSOLIDATED CHOICES ---
    
    # Choices that lead to ACTING (Create Demand or Create Legislative Idea)
    act_choices = ['1', 'criar', 'nova', 'nova demanda', 'criar demanda', 'ideia', 'legislativa', 'criar ideia']
    if has_similar:
        act_choices.append('3') # Option 3 when similar exist
        view_choices = ['2', 'apoiar', 'ver', 'ver demandas', 'demandas existentes']
        converse_choices = ['4', 'conversar', 'não', 'nao'] # Option 4 when similar exist
    else:
        act_choices.append('2') # Option 2 when similar do not exist (Idea)
        view_choices = [] # Not available
        converse_choices = ['3', 'conversar', 'não', 'nao'] # Option 3 when similar do not exist
        
    try:
        # Option 1, 2 (if no similar) or 3 (if similar exist) (Act: Create new demand OR Legislative Idea)
        if choice in act_choices:
            logger.info(f"✅ User chose to ACT via choice: {choice}")

            # Reformulate the question into a proper demand statement
            original_question = state_context.get('original_question')
            theme = state_context.get('theme')
            keywords = state_context.get('keywords', [])
            
            logger.info(f"🔄 Reformulating question: '{original_question}'")
            reformulated_demand = await _reformulate_question_to_demand(
                question=original_question,
                theme=theme,
                keywords=keywords
            )

            # Transition to demand creation flow
            state_manager.set_state(
                phone=phone,
                stage="confirming_problem",
                context={
                    "demand_content": reformulated_demand,
                    "original_question": original_question,
                    "classification": state_context.get('classification', {}),
                    "theme": theme,
                    "keywords": keywords,
                    "user_location": user_location,
                    "from_question": True,
                },
                db=db
            )

            # Use WriterAgent to ask for confirmation of the reformulated text
            response = await writer.ask_confirmation_for_action(
                theme=theme,
                reformulated_demand=reformulated_demand
            )

            return response

        # Option 2 (View and support similar demands - ONLY if has_similar is True)
        elif has_similar and choice in view_choices:
            logger.info("👥 User chose to view similar demands")

            demands_data = []
            available_demands_ids = []
            
            for demand_id in similar_demands_context:
                demand = db.query(Demand).filter(Demand.id == demand_id).first()
                if demand:
                    demands_data.append({
                        'id': str(demand.id),
                        'title': demand.title,
                        'description': demand.description,
                        'supporters_count': demand.supporters_count,
                        'location': demand.location
                    })
                    available_demands_ids.append(str(demand.id))

            if not demands_data:
                state_manager.clear_state(phone, db)
                return await writer.demand_not_found()

            # Build response with demand details using WriterAgent
            response = await writer.show_similar_demands_for_support(demands=demands_data)

            # Save state for handling support choice
            state_manager.set_state(
                phone=phone,
                stage="choosing_demand_to_support",
                context={
                    "available_demands": available_demands_ids,
                    "from_question": True
                },
                db=db
            )

            return response
        
        # Option 3 or 4 (Converse)
        elif choice in converse_choices:
            logger.info("💬 User chose to continue conversation")
            state_manager.clear_state(phone, db)

            return await writer.converse_only_message()

        # --- INVALID CHOICE ---
        else:
            logger.warning(f"⚠️ Invalid choice from user: '{choice}'")

            # Use WriterAgent for an appropriate error/guidance message
            return await writer.unclear_action_choice(has_similar=has_similar)

    except Exception as e:
        logger.error(f"❌ Error handling question action choice: {e}", exc_info=True)
        state_manager.clear_state(phone, db)
        return await writer.generic_error_response()