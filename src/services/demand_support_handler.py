from src.core.state_manager import ConversationStateManager
from src.models.demand import Demand
from src.models.demand_supporter import DemandSupporter
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.agents.writer import WriterAgent # NOVO
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
    """

    state_manager = ConversationStateManager()
    writer = WriterAgent() # INSTANCIAÇÃO
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

            # Substitui string hardcoded por chamada ao WriterAgent
            return await writer.ask_for_new_demand_description()

        # Try to parse as number
        try:
            choice_number = int(choice)

            # Validate choice is within range
            if choice_number < 1 or choice_number > len(available_demands):
                # Substitui string hardcoded por chamada ao WriterAgent
                return await writer.unclear_support_choice(num_options=len(available_demands))

            # Get the demand ID (convert to 0-indexed)
            demand_id = available_demands[choice_number - 1]

            # Check if demand exists
            demand = db.query(Demand).filter(Demand.id == demand_id).first()
            if not demand:
                state_manager.clear_state(phone, db)
                # Substitui string hardcoded por chamada ao WriterAgent
                return await writer.demand_not_found()

            # Check if user already supports this demand (for immediate response)
            existing_support = db.query(DemandSupporter).filter(
                DemandSupporter.demand_id == demand_id,
                DemandSupporter.user_id == user_id
            ).first()

            if existing_support:
                state_manager.clear_state(phone, db)
                # Substitui string hardcoded por chamada ao WriterAgent
                return await writer.demand_already_supported(
                    title=demand.title, 
                    current_count=demand.supporters_count
                )

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

                # Substitui string hardcoded por chamada ao WriterAgent (Sucesso)
                return await writer.demand_supported_success(
                    title=demand.title, 
                    new_count=demand.supporters_count
                )

            except IntegrityError:
                db.rollback()
                state_manager.clear_state(phone, db)
                # Substitui string hardcoded por chamada ao WriterAgent (Fallback de erro de integridade)
                return await writer.demand_already_supported(
                    title=demand.title, 
                    current_count=demand.supporters_count
                )

        except ValueError:
            # Not a number and not 'nova'
            # Substitui string hardcoded por chamada ao WriterAgent
            return await writer.unclear_support_choice(num_options=len(available_demands))

    except Exception as e:
        logger.error(f"❌ Error handling demand support choice: {e}", exc_info=True)
        state_manager.clear_state(phone, db)
        # Substitui string hardcoded por chamada ao WriterAgent (Erro genérico)
        return await writer.generic_error_response()