from sqlalchemy.orm import Session
from src.models.interaction import Interaction
from src.services.demand_service import DemandService
from src.services.similarity_service import SimilarityService
from src.services.embedding_service import EmbeddingService
from src.core.state_manager import ConversationStateManager
from src.agents.analyst import AnalystAgent
from src.agents.writer import WriterAgent
from src.agents.detective import DetectiveAgent
from src.agents.scribe import ScribeAgent
import logging

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
    Inicia o fluxo de entrevista para criar uma demanda rica.
    """
    state_manager = ConversationStateManager()
    analyst = AnalystAgent()
    writer = WriterAgent()

    # Inicializa o contexto da entrevista
    context = {
        'full_text': text, # Acumula o texto de todas as respostas
        'classification': classification,
        'user_location': user_location,
        'interaction_id': interaction_id,
        'collected_data': {
            'theme': classification.get('theme'),
            'location': user_location.get('formatted_address')
        }
    }

    # 1. Analisar se já temos tudo na primeira mensagem
    analysis = await analyst.analyze_completeness(text, context['collected_data'])
    
    if analysis['status'] == 'incomplete':
        # Falta algo -> Inicia entrevista
        missing = analysis['missing_field']
        context['missing_field'] = missing
        
        state_manager.set_state(phone, 'drafting_demand', context, db)
        
        if missing == 'details':
            return await writer.ask_for_more_details()
        elif missing == 'location_entity':
            return await writer.ask_for_specific_location(classification.get('theme'))
        elif missing == 'urgency':
            return await writer.ask_for_urgency()
    
    # Se estiver completo de primeira (raro, mas possível)
    return await _finalize_demand_draft(phone, context, db)


async def handle_demand_drafting(
    user_id: str,
    phone: str,
    text: str,
    state_context: dict,
    db: Session
) -> str:
    """
    Processa as respostas da entrevista (loop de perguntas).
    """
    analyst = AnalystAgent()
    writer = WriterAgent()
    state_manager = ConversationStateManager()

    # 1. Atualizar contexto com a nova resposta
    current_full_text = state_context.get('full_text', '') + "\n" + text
    state_context['full_text'] = current_full_text
    
    # Atualiza dados específicos baseados no que foi perguntado
    last_missing = state_context.get('missing_field')
    if last_missing == 'location_entity':
        state_context['collected_data']['location'] = text # Simplificação
    
    # 2. Re-analisar completude
    analysis = await analyst.analyze_completeness(
        current_full_text, 
        state_context.get('collected_data', {})
    )

    if analysis['status'] == 'incomplete':
        # Ainda falta algo -> Próxima pergunta
        missing = analysis['missing_field']
        state_context['missing_field'] = missing
        
        # Salva estado atualizado
        state_manager.update_context(phone, state_context, db)
        
        if missing == 'details':
            return await writer.ask_for_more_details()
        elif missing == 'location_entity':
            theme = state_context['classification'].get('theme')
            return await writer.ask_for_specific_location(theme)
        elif missing == 'urgency':
            return await writer.ask_for_urgency()

    # 3. Se completou -> Finalizar rascunho e pedir confirmação
    return await _finalize_demand_draft(phone, state_context, db)


async def _finalize_demand_draft(phone: str, context: dict, db: Session) -> str:
    """Gera o conteúdo final estruturado e pede confirmação"""
    analyst = AnalystAgent()
    writer = WriterAgent()
    state_manager = ConversationStateManager()

    # Determinar escopo final
    scope_level = await analyst.determine_scope_level(
        context['classification'], 
        context['user_location']
    )

    # Gerar conteúdo estruturado com IA
    final_content = await analyst.generate_demand_content(
        context['full_text'],
        context['classification'],
        scope_level
    )

    # Atualizar contexto para o estágio de confirmação
    context['demand_content'] = final_content
    context['scope_level'] = scope_level
    
    state_manager.set_state(phone, 'confirming_problem', context, db)

    return await writer.confirm_final_demand(
        title=final_content['title'],
        desc=final_content['description'],
        urgency=final_content.get('urgency_level', 'Média')
    )


async def handle_problem_confirmation(
    user_id: str,
    phone: str,
    confirmation_text: str,
    state_context: dict,
    db: Session
) -> str:
    """
    Processa a confirmação do entendimento do problema.
    Se confirmado → oferece opções (Demanda, Ideia Legislativa, Conversar)
    Se não confirmado → pede para reformular
    """

    state_manager = ConversationStateManager()
    writer = WriterAgent() # INSTANCIAÇÃO
    confirmation_lower = confirmation_text.lower().strip()

    # Confirmação POSITIVA
    positive_keywords = [
        'sim', 's', 'yes', 'y', 'correto', 'exato', 'isso', 'ok', 'okay',
        'certo', 'perfeito', 'pode', 'confirmo', 'entendeu', 'entendi',
        'isso mesmo', 'é isso', 'sim!', 's!', '1', 'uhum', 'ahan', 'aham'
    ]

    if any(keyword in confirmation_lower for keyword in positive_keywords):
        # A lógica para desvio de fluxo (from_question) foi mantida por compatibilidade
        from_question = state_context.get('from_question', False)
        
        if from_question:
            analyst = AnalystAgent()
            classification = state_context.get('classification', {})
            user_location = state_context.get('user_location', {})
            
            scope_level = await analyst.determine_scope_level(classification, user_location)
            demand_text = state_context.get('demand_content')
            
            demand_content = await analyst.generate_demand_content(
                demand_text, classification, scope_level
            )
            
            state_context['scope_level'] = scope_level
            state_context['demand_content'] = demand_content
            
            return await handle_create_demand_decision(
                user_id=user_id,
                phone=phone,
                decision_text='1',
                state_context=state_context,
                db=db
            )
        else:
            # Normal flow - offer options including Legislative Idea
            state_manager.set_state(phone, 'asking_create_demand', state_context, db)

            return await writer.present_action_options(has_similar_demands=False)

    # Confirmação NEGATIVA
    negative_keywords = [
        'não', 'nao', 'n', 'no', 'errado', 'incorreto', 'negativo',
        'não!', 'nao!', 'n!', 'não está', 'nao esta', '2'
    ]

    if any(keyword in confirmation_lower for keyword in negative_keywords):
        state_manager.clear_state(phone, db)

        return await writer.ask_problem_rephrase()

    # Resposta não reconhecida
    else:
        return await writer.unclear_confirmation_request()


async def handle_create_demand_decision(
    user_id: str,
    phone: str,
    decision_text: str,
    state_context: dict,
    db: Session
) -> str:
    """
    Processa a decisão de criar demanda, ideia legislativa ou apenas conversar.
    """

    state_manager = ConversationStateManager()
    writer = WriterAgent() # INSTANCIAÇÃO
    # ScribeAgent é necessário para a Opção 2
    from src.agents.scribe import ScribeAgent
    
    decision_lower = decision_text.lower().strip()

    # Opção 1: CRIAR DEMANDA (Com busca de similares)
    if decision_lower in ['1', 'criar', 'demanda', 'criar demanda', 'uma demanda']:
        # ... (lógica de embedding e busca de similares) ...
        demand_content = state_context['demand_content']
        classification = state_context['classification']
        scope_level = state_context['scope_level']
        user_location = state_context['user_location']

        embedding_service = EmbeddingService()
        similarity_service = SimilarityService()
        
        text_for_embedding = embedding_service.prepare_text_for_embedding(
            demand_content['title'], demand_content['description'], classification.get('theme', 'Outros')
        )
        embedding = await embedding_service.generate_embedding(text_for_embedding)

        similar_demands = await similarity_service.find_similar_demands(
            embedding=embedding, theme=classification.get('theme', 'Outros'),
            scope_level=scope_level, user_location=user_location, db=db,
            similarity_threshold=0.80, max_results=3
        )

        # Se encontrou similares → oferecer escolha
        if similar_demands:
            logger.info(f"Found {len(similar_demands)} similar demands for user {user_id}")

            state_context['embedding'] = embedding
            state_context['similar_demands'] = [
                {'id': d['id'], 'title': d['title'], 'similarity': d['similarity'], 'supporters_count': d['supporters_count']}
                for d in similar_demands
            ]
            state_manager.set_state(phone, 'choosing_similar_or_new', state_context, db)

            return await writer.show_similar_demands(
                demands=state_context['similar_demands']
            )

        # Não encontrou similares → criar nova diretamente
        else:
            logger.info(f"No similar demands found, creating new demand for user {user_id}")
            return await _create_new_demand(
                user_id=user_id, phone=phone, state_context=state_context,
                embedding=embedding, db=db
            )

    # Opção 2: CRIAR IDEIA LEGISLATIVA
    elif decision_lower in ['2', 'ideia', 'legislativa', 'ideia legislativa', 'criar ideia']:
        scribe = ScribeAgent()
        demand_content = state_context.get('demand_content', {})
        text_to_process = demand_content.get('description', '') or state_context.get('original_text', '')
        
        draft = await scribe.draft_legislative_idea(text_to_process)
        
        response = await writer.legislative_idea_ready(draft)
        
        state_manager.clear_state(phone, db)
        return response

    # Opção 3: APENAS CONVERSAR
    elif decision_lower in ['3', 'conversar', 'apenas conversar']:
        state_manager.clear_state(phone, db)

        return await writer.converse_only_message()

    # Resposta não reconhecida
    else:
        return await writer.unclear_decision_request()


async def _create_new_demand(
    user_id: str,
    phone: str,
    state_context: dict,
    embedding: list,
    db: Session
) -> str:
    """
    Função auxiliar para criar uma nova demanda.
    """
    from src.services.demand_service import DemandService
    from src.agents.detective import DetectiveAgent

    demand_service = DemandService()
    state_manager = ConversationStateManager()
    writer = WriterAgent() # INSTANCIAÇÃO

    demand_content = state_context['demand_content']
    classification = state_context['classification']
    scope_level = state_context['scope_level']
    user_location = state_context['user_location']
    interaction_id = state_context.get('interaction_id')

    demand_location = user_location
    if classification.get('location_mentioned') and classification.get('location_text'):
        demand_location = {'text': classification['location_text'], 'coordinates': None}

    # Buscar PLs relacionados à demanda
    detective = DetectiveAgent()
    related_pls = await detective.find_related_pls(
        theme=classification.get('theme', 'outros'), keywords=classification.get('keywords', []),
        db=db, scope_level=scope_level, location=user_location
    )

    # Criar demanda
    demand = await demand_service.create_demand(
        creator_id=user_id, title=demand_content['title'], description=demand_content['description'],
        scope_level=scope_level, theme=classification.get('theme', 'Outros'), location=demand_location,
        affected_entity=demand_content.get('affected_entity'), urgency=classification.get('urgency', 'Média'),
        db=db
    )

    # Atualizar interaction se disponível
    if interaction_id:
        interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if interaction:
            interaction.demand_id = demand.id
            db.commit()

    # Limpar estado
    state_manager.clear_state(phone, db)
    
    # Preparar dados do PL para o WriterAgent
    pl_details = [
        {'title': pl['title'], 'url': pl['url']} for pl in related_pls[:2]
    ]

    response = await writer.demand_created(
        title=demand_content['title'],
        theme=classification.get('theme', 'Outros'),
        scope_level=scope_level,
        urgency=classification.get('urgency', 'Média'),
        share_link=demand_service.get_demand_link(demand.id),
        related_pls=pl_details
    )

    return response


async def handle_demand_choice(
    user_id: str,
    phone: str,
    choice_text: str,
    state_context: dict,
    db: Session
) -> str:
    """
    Processa escolha do usuário: apoiar existente ou criar nova
    """

    demand_service = DemandService()
    state_manager = ConversationStateManager()
    writer = WriterAgent() # INSTANCIAÇÃO

    choice_lower = choice_text.lower().strip()
    similar_demands = state_context.get('similar_demands', [])

    # Opção 1: Apoiar demanda existente
    if choice_lower.isdigit():
        choice_num = int(choice_lower)

        if 1 <= choice_num <= len(similar_demands):
            selected_demand = similar_demands[choice_num - 1]

            # Adicionar como apoiador
            was_added = await demand_service.add_supporter(
                demand_id=selected_demand['id'], user_id=user_id, db=db
            )

            if was_added:
                new_count = selected_demand['supporters_count'] + 1
                response = await writer.demand_supported_success(
                    title=selected_demand['title'], new_count=new_count
                )
            else:
                response = await writer.demand_already_supported(
                    title=selected_demand['title'], 
                    current_count=selected_demand['supporters_count']
                )


            # Limpar estado
            state_manager.clear_state(phone, db)
            return response
        else:
            # Opção inválida (número fora do range)
            return await writer.unclear_support_choice(num_options=len(similar_demands))

    # Opção 2: Criar nova demanda
    elif 'nova' in choice_lower or 'criar' in choice_lower:
        # Recuperar embedding do contexto
        embedding = state_context.get('embedding')

        # Criar nova demanda
        return await _create_new_demand(
            user_id=user_id, phone=phone, state_context=state_context,
            embedding=embedding, db=db
        )

    else:
        # Resposta não reconhecida
        return await writer.unclear_support_choice(num_options=len(similar_demands))