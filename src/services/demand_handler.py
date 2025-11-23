# src/services/demand_handler.py

from sqlalchemy.orm import Session
from src.models.user import User
from src.models.demand import Demand
from src.models.interaction import Interaction
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def handle_demand_creation(
    user_id: str,
    phone: str,
    text: str,
    classification: dict,
    user_location: dict,
    interaction_id: str,
    db: Session
) -> str:
    """
    Processa a criação de demandas com logs detalhados e tratamento de erro.
    """
    logger.info(f"🔹 Starting demand creation for user {user_id}")
    logger.info(f"   Text: {text[:100]}")
    logger.info(f"   Theme: {classification.get('theme')}")

    try:
        intent = classification.get("classification")
        extracted_location = classification.get("location_text")
        urgency = classification.get("urgency", "baixa")
        theme = classification.get("theme", "outros")

        # Lógica simplificada para criar demanda direta
        if intent == "DEMANDA":
            
            # Define localização: usa a extraída da msg ou a do perfil do usuário como fallback
            demand_location = user_location
            if extracted_location:
                # Estrutura simples para quando vem do texto
                demand_location = {"raw_text": extracted_location, "origin": "message_text"}

            # Determinar escopo (simulado por enquanto)
            scope_level = 1
            logger.info(f"🔹 Scope level: {scope_level}")

            # Gerar título (simulado por enquanto)
            generated_title = f"Demanda via WhatsApp: {theme}"
            logger.info(f"🔹 Generated title: {generated_title}")

            new_demand = Demand(
                creator_id=user_id,
                title=generated_title,
                description=text,
                scope_level=scope_level,
                theme=theme,
                urgency=urgency,
                status='active',
                location=demand_location,
                affected_entity=None
            )

            db.add(new_demand)
            db.commit()
            db.refresh(new_demand)

            logger.info(f"✅ Demand created: ID={new_demand.id}, Title={new_demand.title}")

            # Atualizar a interação com o ID da demanda
            if interaction_id:
                interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
                if interaction:
                    interaction.demand_id = new_demand.id
                    db.commit()

            return (
                f"✅ **Demanda Registrada!**\n\n"
                f"🆔 ID: `{str(new_demand.id)[:8]}`\n"
                f"📂 Tema: {theme}\n"
                f"🚨 Urgência: {urgency}\n\n"
                f"Vou analisar se já existem leis sobre isso ou vizinhos com o mesmo problema."
            )

        elif intent == "DUVIDA":
            return "Recebi sua dúvida. (Funcionalidade de IA Jurídica em breve)"

        else:
            return f"Entendi. Você disse: {text}. Como posso ajudar com demandas do bairro?"

    except Exception as e:
        logger.error(f"❌ Error creating demand: {e}", exc_info=True)
        return """Ops! Tive um problema ao criar sua demanda. 😅
Pode tentar novamente? Se o erro persistir, isso será reportado para nossa equipe."""