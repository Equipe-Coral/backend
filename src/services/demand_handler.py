from sqlalchemy.orm import Session
from src.models.interaction import Interaction
from src.services.demand_service import DemandService
from src.services.similarity_service import SimilarityService
from src.services.embedding_service import EmbeddingService
from src.core.state_manager import ConversationStateManager
from src.agents.analyst import AnalystAgent
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
    Orquestra criação de demanda com novo fluxo conversacional:
    1. Determinar scope_level
    2. Gerar título/descrição
    3. CONFIRMAR ENTENDIMENTO com o usuário
    4. Aguardar confirmação antes de processar
    """

    analyst = AnalystAgent()
    demand_service = DemandService()
    embedding_service = EmbeddingService()
    state_manager = ConversationStateManager()

    # 1. Determinar escopo
    scope_level = await analyst.determine_scope_level(classification, user_location)

    # 2. Gerar conteúdo estruturado
    demand_content = await analyst.generate_demand_content(text, classification, scope_level)

    # 3. CONFIRMAR ENTENDIMENTO - NOVO FLUXO
    # Salvar contexto para próxima mensagem
    context = {
        'stage': 'confirming_problem_understanding',
        'demand_content': demand_content,
        'classification': classification,
        'scope_level': scope_level,
        'user_location': user_location,
        'interaction_id': interaction_id,
        'original_text': text
    }
    state_manager.set_state(phone, 'confirming_problem', context, db)

    # Montar mensagem de confirmação
    scope_emoji = {1: "📍", 2: "🏘️", 3: "🏙️"}
    theme_display = classification.get('theme', 'outros').replace('_', ' ').title()

    response = f"""📝 Deixa eu confirmar se entendi corretamente:

**{demand_content['title']}**

{demand_content['description']}

{scope_emoji.get(scope_level, "📍")} Escopo: Nível {scope_level}
📋 Tema: {theme_display}
🔹 Urgência: {classification.get('urgency', 'Média')}

Entendi corretamente?

✅ Digite *"sim"* para confirmar
❌ Digite *"não"* para corrigir"""

    return response


async def handle_problem_confirmation(
    user_id: str,
    phone: str,
    confirmation_text: str,
    state_context: dict,
    db: Session
) -> str:
    """
    Processa a confirmação do entendimento do problema.
    Se confirmado → pergunta se quer criar demanda
    Se não confirmado → pede para reformular
    """

    state_manager = ConversationStateManager()
    confirmation_lower = confirmation_text.lower().strip()

    # Confirmação POSITIVA - expandida com mais variações
    positive_keywords = [
        'sim', 's', 'yes', 'y', 'correto', 'exato', 'isso', 'ok', 'okay',
        'certo', 'perfeito', 'pode', 'confirmo', 'entendeu', 'entendi',
        'isso mesmo', 'é isso', 'sim!', 's!', '1', 'uhum', 'ahan', 'aham'
    ]

    if any(keyword in confirmation_lower for keyword in positive_keywords):
        # Perguntar se quer criar demanda
        state_manager.set_state(phone, 'asking_create_demand', state_context, db)

        response = """Ótimo! 👍

Agora você pode escolher:

1️⃣ *Criar uma demanda* - Sua solicitação será registrada e outros cidadãos poderão apoiá-la
2️⃣ *Apenas conversar* - Vou te ajudar sem criar um registro oficial

O que você prefere?

Digite *"1"* para criar a demanda
Digite *"2"* para apenas conversar"""

        return response

    # Confirmação NEGATIVA - expandida com mais variações
    negative_keywords = [
        'não', 'nao', 'n', 'no', 'errado', 'incorreto', 'negativo',
        'não!', 'nao!', 'n!', 'não está', 'nao esta', '2'
    ]

    if any(keyword in confirmation_lower for keyword in negative_keywords):
        state_manager.clear_state(phone, db)

        response = """Sem problemas! 😊

Por favor, me conte novamente qual é o problema, com mais detalhes:

💡 Dica: Seja específico sobre:
- O que está acontecendo
- Onde está acontecendo
- Qual a urgência"""

        return response

    # Resposta não reconhecida
    else:
        response = """Desculpe, não entendi. 🤔

Por favor, confirme:

✅ Digite *"sim"* se entendi corretamente
❌ Digite *"não"* se preciso ajustar"""

        return response


async def handle_create_demand_decision(
    user_id: str,
    phone: str,
    decision_text: str,
    state_context: dict,
    db: Session
) -> str:
    """
    Processa a decisão de criar ou não a demanda.
    Se escolher criar → busca similares e oferece escolha
    Se escolher apenas conversar → oferece ajuda conversacional
    """

    from src.services.similarity_service import SimilarityService
    from src.services.embedding_service import EmbeddingService

    state_manager = ConversationStateManager()
    decision_lower = decision_text.lower().strip()

    # Opção 1: CRIAR DEMANDA
    if decision_lower in ['1', 'criar', 'demanda', 'criar demanda']:
        # Agora sim: gerar embedding e buscar similares
        demand_content = state_context['demand_content']
        classification = state_context['classification']
        scope_level = state_context['scope_level']
        user_location = state_context['user_location']

        embedding_service = EmbeddingService()
        similarity_service = SimilarityService()

        # Gerar embedding
        text_for_embedding = embedding_service.prepare_text_for_embedding(
            demand_content['title'],
            demand_content['description'],
            classification.get('theme', 'Outros')
        )
        embedding = await embedding_service.generate_embedding(text_for_embedding)

        # Buscar similares
        similar_demands = await similarity_service.find_similar_demands(
            embedding=embedding,
            theme=classification.get('theme', 'Outros'),
            scope_level=scope_level,
            user_location=user_location,
            db=db,
            similarity_threshold=0.80,
            max_results=3
        )

        # Se encontrou similares → oferecer escolha
        if similar_demands:
            logger.info(f"Found {len(similar_demands)} similar demands for user {user_id}")

            # Atualizar contexto com embedding e similares
            state_context['embedding'] = embedding
            state_context['similar_demands'] = [
                {
                    'id': d['id'],
                    'title': d['title'],
                    'similarity': d['similarity'],
                    'supporters_count': d['supporters_count']
                }
                for d in similar_demands
            ]
            state_manager.set_state(phone, 'choosing_similar_or_new', state_context, db)

            # Montar mensagem com opções
            response = "🔍 Encontrei demanda(s) similar(es) já criadas:\n\n"

            for i, demand in enumerate(similar_demands[:3], 1):
                similarity_pct = int(demand['similarity'] * 100)
                response += f"{i}. **{demand['title']}**\n"
                response += f"   👥 {demand['supporters_count']} apoiadores | "
                response += f"📊 {similarity_pct}% similar\n\n"

            response += "O que você prefere?\n\n"
            response += "📌 Digite o *número* para apoiar uma demanda existente\n"
            response += "🆕 Digite *'nova'* para criar sua própria demanda"

            return response

        # Não encontrou similares → criar nova diretamente
        else:
            logger.info(f"No similar demands found, creating new demand for user {user_id}")
            return await _create_new_demand(
                user_id=user_id,
                phone=phone,
                state_context=state_context,
                embedding=embedding,
                db=db
            )

    # Opção 2: APENAS CONVERSAR
    elif decision_lower in ['2', 'conversar', 'apenas conversar']:
        state_manager.clear_state(phone, db)

        response = """Entendido! 😊

Estou aqui para te ajudar. Você pode:

💬 Tirar dúvidas sobre leis e direitos
📍 Pedir orientações sobre serviços públicos
🤝 Conversar sobre questões da sua comunidade

Como posso te ajudar?"""

        return response

    # Resposta não reconhecida
    else:
        response = """Desculpe, não entendi. 🤔

Por favor, escolha uma opção:

1️⃣ Digite *"1"* para criar a demanda
2️⃣ Digite *"2"* para apenas conversar"""

        return response


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

    demand_content = state_context['demand_content']
    classification = state_context['classification']
    scope_level = state_context['scope_level']
    user_location = state_context['user_location']
    interaction_id = state_context.get('interaction_id')

    demand_location = user_location
    if classification.get('location_mentioned') and classification.get('location_text'):
        demand_location = {
            'text': classification['location_text'],
            'coordinates': None
        }

    # NOVO: Buscar PLs relacionados à demanda
    detective = DetectiveAgent()
    related_pls = await detective.find_related_pls(
        theme=classification.get('theme', 'outros'),
        keywords=classification.get('keywords', []),
        db=db
    )
    await detective.close()

    # Criar demanda
    demand = await demand_service.create_demand(
        creator_id=user_id,
        title=demand_content['title'],
        description=demand_content['description'],
        scope_level=scope_level,
        theme=classification.get('theme', 'Outros'),
        location=demand_location,
        affected_entity=demand_content.get('affected_entity'),
        urgency=classification.get('urgency', 'Média'),
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

    scope_emoji = {1: "📍", 2: "🏘️", 3: "🏙️"}

    # Se encontrou PLs, informar o usuário
    pl_info = ""
    if related_pls:
        pl_info = f"\n\n📋 **Já existe legislação sobre isso!**\n"
        pl_info += f"Encontrei {len(related_pls)} PL(s) relacionado(s):\n"
        for pl in related_pls[:2]:
            pl_info += f"• {pl['title']}\n"
        pl_info += "\n💡 Você pode apoiar esses PLs existentes!"

    response = f"""✅ Demanda criada com sucesso!

**{demand_content['title']}**

{scope_emoji.get(scope_level, "📍")} Escopo: Nível {scope_level}
📋 Tema: {classification.get('theme', 'Outros')}
🔹 Urgência: {classification.get('urgency', 'Média')}
👥 Apoiadores: 1 (você)

{demand_service.get_demand_link(demand.id)}{pl_info}

💡 Compartilhe para aumentar a pressão!"""

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

    choice_lower = choice_text.lower().strip()

    # Opção 1: Apoiar demanda existente
    if choice_lower.isdigit():
        choice_num = int(choice_lower)
        similar_demands = state_context.get('similar_demands', [])

        if 1 <= choice_num <= len(similar_demands):
            selected_demand = similar_demands[choice_num - 1]

            # Adicionar como apoiador
            was_added = await demand_service.add_supporter(
                demand_id=selected_demand['id'],
                user_id=user_id,
                db=db
            )

            if was_added:
                new_count = selected_demand['supporters_count'] + 1
                response = f"""✅ Você agora apoia esta demanda!

**{selected_demand['title']}**

👥 Total de apoiadores: {new_count}

💪 Quanto mais gente apoiar, maior a pressão!"""
            else:
                response = "⚠️ Você já apoia esta demanda!"

            # Limpar estado
            state_manager.clear_state(phone, db)
            return response
        else:
            return f"❌ Opção inválida. Digite um número de 1 a {len(similar_demands)}, ou 'nova' para criar sua própria demanda."

    # Opção 2: Criar nova demanda
    elif 'nova' in choice_lower or 'criar' in choice_lower:
        # Recuperar embedding do contexto
        embedding = state_context.get('embedding')

        # Criar nova demanda
        return await _create_new_demand(
            user_id=user_id,
            phone=phone,
            state_context=state_context,
            embedding=embedding,
            db=db
        )

    else:
        return "❌ Não entendi. Digite o número da demanda para apoiar, ou 'nova' para criar sua própria."