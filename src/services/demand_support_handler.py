from src.core.state_manager import ConversationStateManager
from src.models.demand import Demand
from src.models.demand_supporter import DemandSupporter
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import logging

logger = logging.getLogger(__name__)

async def handle_demand_support_choice(
    user_id: str,
    phone: str,
    text: str,
    state_context: dict,
    db: Session
) -> str:
    """
    Handle user's choice to support a specific demand from a list

    Flow:
    1. Parse user choice (number or 'nova')
    2. If number: add user as supporter to that demand
    3. If 'nova': redirect to demand creation flow

    Args:
        user_id: UUID of the user
        phone: User's phone number
        text: User's choice message
        state_context: Context from conversation state with available_demands list
        db: Database session

    Returns:
        Response message confirming support or redirecting to creation
    """

    state_manager = ConversationStateManager()
    choice = text.strip().lower()

    available_demands = state_context.get('available_demands', [])

    logger.info(f"💪 Processing demand support choice for user {user_id}: choice='{choice}'")

    try:
        # Check if user wants to create new demand instead
        if choice in ['nova', 'criar', 'criar nova', 'nova demanda']:
            logger.info("✅ User chose to create new demand instead of supporting")

            # Redirect to demand creation flow
            state_manager.set_state(
                phone=phone,
                stage="confirming_problem",
                context={
                    "demand_content": state_context.get('original_question', ''),
                    "classification": state_context.get('classification', {}),
                    "from_question": True
                },
                db=db
            )

            response = """📝 *Vamos criar uma nova demanda!*

Por favor, descreva o problema ou reivindicação que você quer registrar."""

            return response

        # Try to parse as number
        try:
            choice_number = int(choice)

            # Validate choice is within range
            if choice_number < 1 or choice_number > len(available_demands):
                response = f"""❓ *Escolha inválida.*

Por favor, digite um número entre 1 e {len(available_demands)}, ou digite *'nova'* para criar sua própria demanda."""
                return response

            # Get the demand ID (convert to 0-indexed)
            demand_id = available_demands[choice_number - 1]

            # Check if demand exists
            demand = db.query(Demand).filter(Demand.id == demand_id).first()
            if not demand:
                state_manager.clear_state(phone, db)
                return "❌ Desculpe, essa demanda não existe mais. Tente novamente."

            # Check if user already supports this demand
            existing_support = db.query(DemandSupporter).filter(
                DemandSupporter.demand_id == demand_id,
                DemandSupporter.user_id == user_id
            ).first()

            if existing_support:
                state_manager.clear_state(phone, db)
                response = f"""✅ *Você já apoia esta demanda!*

*{demand.title}*

💪 Total de apoiadores: {demand.supporters_count}

Continue mobilizando mais pessoas! 🚀"""
                return response

            # Add user as supporter
            try:
                supporter = DemandSupporter(
                    demand_id=demand_id,
                    user_id=user_id
                )
                db.add(supporter)

                # Update supporters count
                demand.supporters_count += 1

                db.commit()

                logger.info(f"✅ User {user_id} now supports demand {demand_id}")

                state_manager.clear_state(phone, db)

                response = f"""🎉 *Parabéns! Você agora apoia esta demanda!*

*{demand.title}*

💪 Total de apoiadores: {demand.supporters_count}

Quanto mais pessoas apoiarem, maior a pressão para resolver o problema! Compartilhe com amigos e vizinhos! 🚀"""

                return response

            except IntegrityError:
                db.rollback()
                state_manager.clear_state(phone, db)
                return "❌ Você já apoia essa demanda!"

        except ValueError:
            # Not a number
            response = f"""❓ *Não entendi sua escolha.*

Por favor, digite o *número* da demanda que você quer apoiar (1, 2, 3...)
Ou digite *'nova'* para criar sua própria demanda."""
            return response

    except Exception as e:
        logger.error(f"❌ Error handling demand support choice: {e}", exc_info=True)
        state_manager.clear_state(phone, db)
        return """❌ Desculpe, tive um problema ao processar seu apoio.

Por favor, tente novamente."""
