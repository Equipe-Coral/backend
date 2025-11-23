import logging
from typing import Optional
from sqlalchemy.orm import Session
from src.models.user import User
from src.models.conversation_state import ConversationState
from src.agents.profiler import ProfilerAgent
from src.core.state_manager import ConversationStateManager

logger = logging.getLogger(__name__)

async def handle_onboarding(
    phone: str,
    text: str,
    classification: dict,
    user: Optional[User],
    state: Optional[ConversationState],
    db: Session
) -> str:
    """
    Gerencia todo o fluxo de onboarding do usuário.
    
    Fluxo:
    1. Se usuário novo → Boas-vindas + pedir localização
    2. Se aguardando localização → Extrair e geocodificar
    3. Se localização inválida → Pedir novamente
    4. Se localização OK → Confirmar com usuário
    5. Se confirmado → Criar/atualizar user + finalizar onboarding
    
    Args:
        phone: Número de telefone do usuário
        text: Texto da mensagem
        classification: Resultado da classificação do RouterAgent
        user: Usuário existente ou None
        state: Estado da conversa ou None
        db: Sessão do banco de dados
        
    Returns:
        Mensagem de resposta para o usuário
    """
    
    profiler = ProfilerAgent()
    state_manager = ConversationStateManager()
    
    # Estado 1: Novo usuário ou sem estado
    if not state or state.current_stage == 'new_user':
        welcome_msg = """Olá! 👋 Bem-vindo(a) ao Coral!

Eu sou seu assistente cívico e estou aqui para te ajudar a:
✅ Entender leis e projetos que afetam sua vida
✅ Reportar problemas do seu bairro ou cidade
✅ Acompanhar o que acontece com suas demandas

Para começar, me conta: qual é o seu bairro ou cidade?"""
        
        state_manager.set_state(phone, 'awaiting_location', {}, db)
        logger.info(f"Onboarding started for {phone}")
        return welcome_msg
    
    # Estado 2: Aguardando localização
    if state.current_stage == 'awaiting_location':
        logger.info(f"Processing location for {phone}: {text}")
        location_data = await profiler.extract_location_from_text(text)
        
        # Check if location was extracted with sufficient confidence
        if not location_data.get('has_location') or location_data.get('confidence', 0) < 0.6:
            logger.warning(f"Location confidence too low for {phone}: {location_data.get('confidence')}")
            return """Desculpa, não consegui identificar sua localização. 😅

Pode me falar de novo? Exemplos:
- "Moro no Centro de São Paulo"
- "Sou de Copacabana, Rio de Janeiro"
- "Bairro Savassi, BH" """
        
        # Build location string for geocoding
        location_parts = []
        if location_data.get('neighborhood'):
            location_parts.append(location_data['neighborhood'])
        if location_data.get('city'):
            location_parts.append(location_data['city'])
        if location_data.get('state'):
            location_parts.append(location_data['state'])
        
        location_str = ", ".join(location_parts) if location_parts else location_data.get('full_address', '')
        
        if not location_str:
            logger.warning(f"Could not build location string for {phone}")
            return """Desculpa, não consegui identificar sua localização. 😅

Pode me falar de novo incluindo pelo menos a cidade? Por exemplo:
- "Moro em São Paulo"
- "Rio de Janeiro"
- "Sou de Belo Horizonte" """
        
        # Geocodificar
        logger.info(f"Geocoding location: {location_str}")
        geocoded = await profiler.geocode_location(location_str)
        
        # Build display text
        display_location = location_data.get('neighborhood') or location_data.get('city') or 'sua localização'
        if location_data.get('state'):
            display_location += f", {location_data['state']}"
        
        # Save to context for confirmation
        context = {
            'location_data': location_data,
            'geocoded': geocoded
        }
        state_manager.set_state(phone, 'confirming_location', context, db)
        
        confirm_msg = f"""Entendi! Você está em:
📍 {display_location}

Está correto? (responda sim ou não)"""
        
        logger.info(f"Asking location confirmation for {phone}: {display_location}")
        return confirm_msg
    
    # Estado 3: Confirmando localização
    if state.current_stage == 'confirming_location':
        text_lower = text.lower().strip()
        
        # Check for affirmative responses
        affirmative_words = ['sim', 'yes', 'correto', 'certo', 'isso', 'exato', 's', 'ss', 'isso mesmo', 'confirmo']
        negative_words = ['não', 'nao', 'no', 'n', 'nn', 'negativo', 'errado']
        
        is_affirmative = any(word in text_lower for word in affirmative_words)
        is_negative = any(word in text_lower for word in negative_words)
        
        if is_affirmative and not is_negative:
            # User confirmed location
            logger.info(f"Location confirmed by {phone}")
            
            location_data = state.context_data.get('location_data', {})
            geocoded = state.context_data.get('geocoded', {})
            
            # Build location JSON for database
            location_json = {
                'neighborhood': location_data.get('neighborhood'),
                'city': location_data.get('city'),
                'state': location_data.get('state'),
                'coordinates': geocoded.get('coordinates'),
                'formatted_address': geocoded.get('formatted_address')
            }
            
            try:
                if user:
                    # Update existing user
                    user.location_primary = location_json
                    user.status = 'active'
                    db.commit()
                    logger.info(f"Updated user {user.id} location")
                else:
                    # Create new user
                    user = await profiler.create_user(phone, location_json, db)
                    logger.info(f"Created new user {user.id}")
                
                # Clear conversation state
                state_manager.clear_state(phone, db)
                
                return """Perfeito! ✅ Seu perfil está criado.

Agora me conta: como posso te ajudar hoje?"""
                
            except Exception as e:
                logger.error(f"Error creating/updating user: {e}")
                return """Desculpa, ocorreu um erro ao salvar seus dados. 😓

Vamos tentar novamente? Me fala seu bairro ou cidade:"""
        
        elif is_negative:
            # User said no, ask for location again
            logger.info(f"Location rejected by {phone}, asking again")
            state_manager.set_state(phone, 'awaiting_location', {}, db)
            return "Sem problemas! Me fala então: qual é o seu bairro ou cidade?"
        
        else:
            # Unclear response, ask for clarification
            logger.info(f"Unclear confirmation response from {phone}: {text}")
            return """Desculpa, não entendi. 😅

A localização está correta? Por favor responda com "sim" ou "não"."""
    
    # Fallback - should not reach here in normal flow
    logger.warning(f"Unexpected state in onboarding: {state.current_stage if state else 'None'} for {phone}")
    state_manager.set_state(phone, 'awaiting_location', {}, db)
    return "Desculpa, algo deu errado. Vamos recomeçar: qual é o seu bairro ou cidade?"
