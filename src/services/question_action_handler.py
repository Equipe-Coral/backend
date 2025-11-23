from src.core.state_manager import ConversationStateManager
from src.services.demand_handler import handle_create_demand_decision
from sqlalchemy.orm import Session
import logging
import google.generativeai as genai
from src.core.config import settings

logger = logging.getLogger(__name__)

async def _reformulate_question_to_demand(question: str, theme: str, keywords: list) -> str:
    """
    Use Gemini to reformulate a user's question into a proper demand statement
    
    Example transformation:
    Input: "quais os PL que permitem eu entrar com meu cachorro no restaurante?"
    Output: "Gostaria de uma legislação que permitisse entrar com animais de estimação em estabelecimentos comerciais"
    
    Args:
        question: The user's original question
        theme: The classified theme
        keywords: Extracted keywords
        
    Returns:
        Reformulated demand statement
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
        # Fallback: return original question
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

    Flow:
    1. Parse user choice (1, 2, or 3)
    2. Route to appropriate action:
       - 1: Start demand creation flow
       - 2: Show similar demands for support
       - 3: Continue conversational mode

    Args:
        user_id: UUID of the user
        phone: User's phone number
        text: User's choice message
        state_context: Context from conversation state
        user_location: User's location data
        db: Database session

    Returns:
        Response message based on user's choice
    """

    state_manager = ConversationStateManager()
    choice = text.strip()

    logger.info(f"📋 Processing question action choice for user {user_id}: choice='{choice}'")

    similar_demands = state_context.get('similar_demands', [])
    has_similar = len(similar_demands) > 0

    try:
        # Option 1: Create new demand
        if choice in ['1', 'criar', 'nova', 'nova demanda', 'criar demanda']:
            logger.info("✅ User chose to create new demand")

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
            # Save state with reformulated demand
            state_manager.set_state(
                phone=phone,
                stage="confirming_problem",
                context={
                    "demand_content": reformulated_demand,  # Use reformulated version
                    "original_question": original_question,  # Keep original for reference
                    "classification": state_context.get('classification', {}),
                    "theme": theme,
                    "keywords": keywords,
                    "user_location": user_location,  # Add user location
                    "from_question": True  # Flag to indicate this came from question flow
                },
                db=db
            )

            response = f"""📝 *Vamos criar uma demanda sobre "{theme}"*

Deixa eu confirmar se entendi corretamente:

*Demanda:* {reformulated_demand}

Está correto? (Responda *sim* ou *não*)"""

            return response

        # Option 2: View and support similar demands
        elif choice in ['2', 'apoiar', 'ver', 'ver demandas', 'demandas existentes']:
            if not has_similar:
                # User chose to just chat more (when no similar demands exist)
                logger.info("💬 User chose to continue conversation")
                state_manager.clear_state(phone, db)

                response = """💬 *Entendi! Como posso ajudar mais?*

Pode me contar mais sobre o que você precisa, ou fazer outra pergunta sobre legislação."""
                return response

            logger.info("👥 User chose to view similar demands")

            # Get demand details to show
            from src.models.demand import Demand

            demands_data = []
            for demand_id in similar_demands[:3]:
                demand = db.query(Demand).filter(Demand.id == demand_id).first()
                if demand:
                    demands_data.append({
                        'id': str(demand.id),
                        'title': demand.title,
                        'description': demand.description,
                        'supporters_count': demand.supporters_count,
                        'location': demand.location
                    })

            if not demands_data:
                state_manager.clear_state(phone, db)
                return "❌ Desculpe, não consegui carregar as demandas. Tente novamente."

            # Build response with demand details
            response = "🔍 *Aqui estão as demandas da comunidade relacionadas:*\n\n"

            for i, demand in enumerate(demands_data, 1):
                response += f"*{i}. {demand['title']}*\n"

                # Truncate long descriptions
                description = demand['description']
                if len(description) > 150:
                    description = description[:150] + '...'
                response += f"{description}\n\n"

                response += f"💪 {demand['supporters_count']} pessoas apoiam\n"
                response += f"📍 {demand['location'].get('city', 'Local não especificado')}\n\n"
                response += "---\n\n"

            response += "*Quer apoiar alguma dessas demandas?*\n\n"
            response += "Digite o *número* da demanda que você quer apoiar (1, 2, 3...)\n"
            response += "Ou digite *'nova'* para criar sua própria demanda"

            # Save state for handling support choice
            state_manager.set_state(
                phone=phone,
                stage="choosing_demand_to_support",
                context={
                    "available_demands": [d['id'] for d in demands_data],
                    "from_question": True
                },
                db=db
            )

            return response

        # Option 3: Just continue conversation (only available when similar demands exist)
        elif choice in ['3', 'conversar', 'não', 'nao']:
            if has_similar:
                logger.info("💬 User chose to continue conversation")
                state_manager.clear_state(phone, db)

                response = """💬 *Entendi! Como posso ajudar mais?*

Pode me contar mais sobre o que você precisa, ou fazer outra pergunta sobre legislação."""
                return response
            else:
                # Invalid choice when only 2 options available
                response = """❓ *Não entendi sua escolha.*

Digite:
1️⃣ para criar uma nova demanda
2️⃣ para apenas conversar mais"""
                return response

        # Invalid choice
        else:
            logger.warning(f"⚠️ Invalid choice from user: '{choice}'")

            if has_similar:
                response = """❓ *Não entendi sua escolha.*

Digite:
1️⃣ para criar uma nova demanda
2️⃣ para ver e apoiar demandas existentes
3️⃣ para apenas conversar mais"""
            else:
                response = """❓ *Não entendi sua escolha.*

Digite:
1️⃣ para criar uma nova demanda
2️⃣ para apenas conversar mais"""

            return response

    except Exception as e:
        logger.error(f"❌ Error handling question action choice: {e}", exc_info=True)
        state_manager.clear_state(phone, db)
        return """❌ Desculpe, tive um problema ao processar sua escolha.

Por favor, tente novamente."""
