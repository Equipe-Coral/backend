"""
Fluxo V2 de Criação de Demandas - Step by Step
Coleta progressiva com mensagens fixas (sem desperdício de IA)
"""
from sqlalchemy.orm import Session
from src.core.state_manager import ConversationStateManager
from src.models.demand import Demand
from src.models.user import User
from src.services.demand_service import DemandService
from src.agents.writer import WriterAgent
import logging
import copy
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# ============================================================================
# MENSAGENS FIXAS (SEM IA) - Formatação Profissional
# ============================================================================

class DemandMessages:
    """Mensagens padronizadas para o fluxo de demandas"""
    
    @staticmethod
    def initial_prompt() -> str:
        return (
            "🎯 *Vamos criar sua demanda cívica!*\n\n"
            "Preciso coletar algumas informações para registrar corretamente.\n\n"
            "📝 *Passo 1/3: Descrição do Problema*\n\n"
            "Me conte: o que está acontecendo?\n"
            "Descreva com detalhes o problema que você quer relatar."
        )
    
    @staticmethod
    def ask_location() -> str:
        return (
            "📍 *Passo 2/3: Localização*\n\n"
            "Onde exatamente está acontecendo esse problema?\n\n"
            "Envie o endereço completo:\n"
            "• Rua/Avenida + número\n"
            "• Ou ponto de referência (ex: \"Em frente à Escola Municipal\")"
        )
    
    @staticmethod
    def ask_category() -> str:
        return (
            "🏷️ *Passo 3/3: Categoria*\n\n"
            "Em qual área esse problema se encaixa?\n\n"
            "*Escolha um número:*\n\n"
            "1️⃣ Infraestrutura (iluminação, calçadas, buracos)\n"
            "2️⃣ Transporte (ônibus, trânsito, sinalização)\n"
            "3️⃣ Saúde (UBS, hospitais, atendimento)\n"
            "4️⃣ Educação (escolas, creches)\n"
            "5️⃣ Segurança (policiamento, vigilância)\n"
            "6️⃣ Meio Ambiente (lixo, poluição, árvores)\n"
            "7️⃣ Outros"
        )
    
    @staticmethod
    def ask_urgency() -> str:
        # Não é mais solicitado ao usuário (definido internamente)
        return ""
    
    @staticmethod
    def ask_scope() -> str:
        # Não é mais solicitado ao usuário (definido internamente)
        return ""
    
    @staticmethod
    def confirmation_summary(data: Dict) -> str:
        category_map = {
            "1": "Infraestrutura", "2": "Transporte", "3": "Saúde",
            "4": "Educação", "5": "Segurança", "6": "Meio Ambiente", "7": "Outros",
            "infraestrutura": "Infraestrutura", "transporte": "Transporte",
            "saude": "Saúde", "educacao": "Educação", "seguranca": "Segurança",
            "meio_ambiente": "Meio Ambiente", "outros": "Outros"
        }
        
        urgency_map = {
            "1": "Baixa", "2": "Média", "3": "Alta", "4": "Crítica",
            "baixa": "Baixa", "media": "Média", "alta": "Alta", "critica": "Crítica"
        }
        
        scope_map = {
            "1": "Localizado", "2": "Regional", "3": "Amplo"
        }
        
        category = category_map.get(str(data.get('category', '7')), "Outros")
        urgency = urgency_map.get(str(data.get('urgency', '2')), "Média")
        scope = scope_map.get(str(data.get('scope_level', '1')), "Localizado")
        
        # Use AI-generated title and description if available
        title = data.get('ai_title', data.get('title', 'Sem título'))
        description = data.get('ai_description', data.get('description', ''))
        location = data.get('location', '')
        
        return (
            "✅ *Sua demanda foi estruturada:*\n\n"
            f"📌 *Título:*\n{title}\n\n"
            f"📝 *Descrição:*\n{description}\n\n"
            f"📍 *Local:* {location}\n"
            f"🏷️ *Categoria:* {category}\n"
            f"⏰ *Urgência:* {urgency}\n"
            f"📏 *Abrangência:* {scope}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "*Está tudo correto?*\n\n"
            "✅ Digite *SIM* para confirmar\n"
            "❌ Digite *NÃO* para cancelar\n"
            "✏️ Digite *CORRIGIR* para ajustar"
        )
    
    @staticmethod
    def success_message(demand_id: str, support_count: int = 1) -> str:
        return (
            "🎉 *Demanda criada com sucesso!*\n\n"
            "Sua demanda foi registrada e já está disponível "
            "para receber apoio da comunidade.\n\n"
            f"🤝 Você é o apoiador nº {support_count}!\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "*Próximos passos:*\n"
            "• Compartilhe com amigos e vizinhos\n"
            "• Acompanhe atualizações aqui no WhatsApp\n"
            "• Quando atingir 10 apoios, enviaremos relatório oficial\n\n"
            "💬 Precisa de algo mais? Estou aqui!"
        )
    
    @staticmethod
    def invalid_option() -> str:
        return (
            "❌ Opção inválida.\n\n"
            "Por favor, escolha um dos números apresentados."
        )
    
    @staticmethod
    def validation_error(field: str) -> str:
        errors = {
            "description": "A descrição precisa ter pelo menos 20 caracteres. Tente descrever melhor o problema.",
            "location": "Por favor, informe um endereço válido (rua + número ou ponto de referência).",
            "category": "Escolha uma opção de 1 a 7.",
            "urgency": "Escolha uma opção de 1 a 4.",
            "scope": "Escolha uma opção de 1 a 3."
        }
        return f"⚠️ {errors.get(field, 'Dado inválido. Tente novamente.')}"


# ============================================================================
# ESTADOS DO FLUXO
# ============================================================================

class DemandFlowStates:
    COLLECTING_DESCRIPTION = "collecting_description"
    COLLECTING_LOCATION = "collecting_location"
    COLLECTING_CATEGORY = "collecting_category"
    CONFIRMING = "confirming_demand"


# ============================================================================
# VALIDAÇÕES
# ============================================================================

class DemandValidators:
    """Validadores para cada campo"""
    
    @staticmethod
    def validate_description(text: str) -> tuple[bool, Optional[str]]:
        """Valida descrição (mínimo 20 caracteres)"""
        if len(text.strip()) < 20:
            return False, DemandMessages.validation_error("description")
        return True, None
    
    @staticmethod
    def validate_location(text: str) -> tuple[bool, Optional[str]]:
        """Valida localização (mínimo 5 caracteres)"""
        if len(text.strip()) < 5:
            return False, DemandMessages.validation_error("location")
        return True, None
    
    @staticmethod
    def validate_category(text: str) -> tuple[bool, Optional[str]]:
        """Valida categoria (1-7)"""
        if text.strip() not in ['1', '2', '3', '4', '5', '6', '7']:
            return False, DemandMessages.validation_error("category")
        return True, None
    
    @staticmethod
    def validate_urgency(text: str) -> tuple[bool, Optional[str]]:
        """Valida urgência (1-4)"""
        if text.strip() not in ['1', '2', '3', '4']:
            return False, DemandMessages.validation_error("urgency")
        return True, None
    
    @staticmethod
    def validate_scope(text: str) -> tuple[bool, Optional[str]]:
        """Valida abrangência (1-3)"""
        if text.strip() not in ['1', '2', '3']:
            return False, DemandMessages.validation_error("scope")
        return True, None


# ============================================================================
# HANDLER PRINCIPAL
# ============================================================================

async def start_demand_flow(phone: str, db: Session) -> str:
    """Inicia o fluxo de criação de demanda"""
    state_manager = ConversationStateManager()
    
    context = {
        'collected_data': {}
    }
    
    state_manager.set_state(phone, DemandFlowStates.COLLECTING_DESCRIPTION, context, db)
    logger.info(f"Started demand flow for {phone}")
    
    return DemandMessages.initial_prompt()


async def process_demand_step(
    phone: str,
    text: str,
    current_state: str,
    state_context: dict,
    db: Session
) -> str:
    """Processa cada etapa do fluxo"""
    
    state_manager = ConversationStateManager()
    # Deep copy to avoid reference issues with SQLAlchemy objects
    collected = copy.deepcopy(state_context.get('collected_data', {}))
    
    # ========================================================================
    # ETAPA 1: DESCRIÇÃO
    # ========================================================================
    if current_state == DemandFlowStates.COLLECTING_DESCRIPTION:
        valid, error = DemandValidators.validate_description(text)
        if not valid:
            return error
        
        collected['description'] = text.strip()
        new_context = {
            'collected_data': collected,
            'last_description': collected['description']
        }
        state_manager.set_state(phone, DemandFlowStates.COLLECTING_LOCATION, new_context, db)
        
        return DemandMessages.ask_location()
    
    # ========================================================================
    # ETAPA 2: LOCALIZAÇÃO
    # ========================================================================
    elif current_state == DemandFlowStates.COLLECTING_LOCATION:
        valid, error = DemandValidators.validate_location(text)
        if not valid:
            return error
        
        collected['location'] = text.strip()
        new_context = {
            'collected_data': collected,
            'last_description': state_context.get('last_description'),
            'last_location': collected['location']
        }
        state_manager.set_state(phone, DemandFlowStates.COLLECTING_CATEGORY, new_context, db)
        
        return DemandMessages.ask_category()
    
    # ========================================================================
    # ETAPA 3: CATEGORIA
    # ========================================================================
    elif current_state == DemandFlowStates.COLLECTING_CATEGORY:
        valid, error = DemandValidators.validate_category(text)
        if not valid:
            return error
        
        category_map = {
            '1': 'infraestrutura', '2': 'mobilidade', '3': 'saude',
            '4': 'educacao', '5': 'seguranca', '6': 'meio_ambiente', '7': 'outros'
        }
        collected['category'] = text.strip()
        collected['theme'] = category_map[text.strip()]

        # Definições internas (não perguntamos ao usuário)
        # Urgência padrão estimada (poderemos melhorar com heurísticas do Router futuramente)
        if 'urgency' not in collected:
            collected['urgency'] = 'media'
        # Abrangência padrão: Localizado (1) — geralmente problemas são pontuais
        if 'scope_level' not in collected:
            collected['scope_level'] = 1

        # Síntese com Gemini ANTES de mostrar resumo
        user = db.query(User).filter(User.phone == phone).first()
        writer = WriterAgent()
        
        category_label_map = {
            '1': 'Infraestrutura', '2': 'Transporte', '3': 'Saúde',
            '4': 'Educação', '5': 'Segurança', '6': 'Meio Ambiente', '7': 'Outros'
        }
        category_label = category_label_map.get(str(collected.get('category', '7')), 'Outros')
        scope_label = 'Localizado'
        urgency_value = collected.get('urgency', 'media')
        
        title_seed = collected.get('description', state_context.get('last_description', ''))
        location_seed = collected.get('location', state_context.get('last_location', ''))
        
        logger.info(f"🔄 Starting synthesis with: desc='{title_seed[:50]}...', loc='{location_seed}'")
        
        try:
            logger.info(f"🔄 Calling synthesize_demand with: desc='{title_seed[:80]}...', loc='{location_seed}'")
            synthesis = await writer.synthesize_demand(
                description=title_seed,
                location=location_seed,
                category_label=category_label,
                urgency=urgency_value,
                scope_label=scope_label
            )
            logger.info(f"📥 Synthesis raw result: {synthesis}")
            
            ai_title = synthesis.get('title') or (title_seed[:100] or 'Demanda da Comunidade')
            ai_desc = synthesis.get('description') or title_seed
            ai_affected = synthesis.get('affected_entity')
            
            logger.info(f"✅ Synthesis result - Title: '{ai_title[:80]}...'")
            logger.info(f"✅ Synthesis result - Desc: '{ai_desc[:120]}...'")
            logger.info(f"✅ Synthesis result - Affected: '{ai_affected}'")
            
            # Salvar síntese no contexto para usar na confirmação
            collected['ai_title'] = ai_title
            collected['ai_description'] = ai_desc
            collected['ai_affected_entity'] = ai_affected
            
            logger.info(f"💾 Saved to collected: ai_title={bool(collected.get('ai_title'))}, ai_desc={bool(collected.get('ai_description'))}")
        except Exception as e:
            logger.error(f"❌ Synthesis failed at summary with exception: {e}", exc_info=True)
            collected['ai_title'] = title_seed[:100] or 'Demanda da Comunidade'
            collected['ai_description'] = title_seed
            collected['ai_affected_entity'] = None
        
        # Salvar contexto com síntese - MANTENDO TODOS OS DADOS
        new_context = {
            'collected_data': collected,  # collected is now a deepcopy, so it's safe
            'last_description': state_context.get('last_description'),
            'last_location': state_context.get('last_location')
        }
        logger.info(f"💾 Context BEFORE saving - collected_data keys: {list(collected.keys())}")
        logger.info(f"💾 Context BEFORE saving - full collected: {collected}")
        
        state_manager.set_state(phone, DemandFlowStates.CONFIRMING, new_context, db)
        
        # Verificar o que foi salvo
        saved_state = state_manager.get_state(phone, db)
        if saved_state:
            logger.info(f"💾 Context AFTER saving - context_data keys: {list(saved_state.context_data.get('collected_data', {}).keys())}")
            logger.info(f"💾 Context AFTER saving - full context: {saved_state.context_data}")
        
        logger.info(f"Demand V2 summary with AI synthesis: {collected}")
        return DemandMessages.confirmation_summary(collected)
    
    # ========================================================================
    # ETAPA 4: URGÊNCIA
    # ========================================================================
    
    
    # ========================================================================
    # ETAPA 5: ABRANGÊNCIA
    # ========================================================================
    # Nenhuma coleta adicional; estados de urgência/escopo foram removidos
    
    # ========================================================================
    # ETAPA 6: CONFIRMAÇÃO
    # ========================================================================
    if current_state == DemandFlowStates.CONFIRMING:
        response = text.strip().lower()
        
        if response in ['sim', 's', 'yes', 'confirmar', 'ok']:
            # Normalizar telefone (remover @c.us se presente)
            normalized_phone = phone.replace('@c.us', '')
            
            # Criar demanda no banco
            user = db.query(User).filter(User.phone == normalized_phone).first()
            if not user:
                # Tentar variação com 9 adicional
                if len(normalized_phone) == 10 and normalized_phone[2] != '9':
                    alt_phone = normalized_phone[:2] + '9' + normalized_phone[2:]
                    user = db.query(User).filter(User.phone == alt_phone).first()
                
                if not user:
                    state_manager.clear_state(phone, db)
                    logger.error(f"User not found for phone: {normalized_phone}")
                    return "❌ Erro: usuário não encontrado."
            
            # PEGAR OS DADOS DO CONTEXTO SALVO (não do collected local que pode estar vazio)
            demand_data = collected.copy() if collected else {}
            
            logger.info(f"🔍 State context at confirmation: {state_context}")
            logger.info(f"🔍 Collected local keys: {list(collected.keys())}")
            logger.info(f"🔍 Demand data keys: {list(demand_data.keys())}")
            
            # Usar a síntese já gerada (salva no contexto) - PRIORIDADE ABSOLUTA para dados da IA
            ai_title = demand_data.get('ai_title')
            ai_desc = demand_data.get('ai_description')
            ai_affected = demand_data.get('ai_affected_entity')
            
            # Fallback APENAS se síntese falhou completamente (não deve acontecer)
            if not ai_title:
                logger.warning("⚠️ ai_title não encontrado! Usando fallback")
                logger.warning(f"⚠️ demand_data disponível: {demand_data}")
                ai_title = demand_data.get('description', '').strip()[:100] or 'Demanda da Comunidade'
            if not ai_desc:
                logger.warning("⚠️ ai_description não encontrado! Usando fallback")
                logger.warning(f"⚠️ demand_data disponível: {demand_data}")
                ai_desc = demand_data.get('description', '')
            
            logger.info(f"📝 Creating demand with AI synthesis:")
            logger.info(f"   Title: {ai_title}")
            logger.info(f"   Description: {ai_desc[:100]}...")
            logger.info(f"   Affected: {ai_affected}")
            
            location_payload = {
                'address': demand_data.get('location', ''),
                'city': user.location_primary.get('city') if user.location_primary else None,
                'state': user.location_primary.get('state') if user.location_primary else None
            }
            urgency_value = demand_data.get('urgency', 'media')
            scope_value = int(demand_data.get('scope_level', 1))

            demand_service = DemandService()
            demand = await demand_service.create_demand(
                creator_id=str(user.id),
                title=ai_title,
                description=ai_desc,
                scope_level=scope_value,
                theme=demand_data.get('theme', 'outros'),
                location=location_payload,
                affected_entity=ai_affected,
                urgency=urgency_value,
                db=db
            )
            
            state_manager.clear_state(phone, db)
            logger.info(f"✅ Demand created: {demand.id}")
            
            return DemandMessages.success_message(str(demand.id))
        
        elif response in ['nao', 'não', 'n', 'no', 'cancelar']:
            state_manager.clear_state(phone, db)
            return (
                "❌ *Criação cancelada.*\n\n"
                "Sem problemas! Quando quiser criar uma demanda, é só me chamar. 😊"
            )
        
        elif response in ['corrigir', 'editar', 'mudar']:
            # Reiniciar fluxo
            state_manager.clear_state(phone, db)
            return await start_demand_flow(phone, db)
        
        else:
            return (
                "❓ Não entendi sua resposta.\n\n"
                "Digite *SIM*, *NÃO* ou *CORRIGIR*"
            )
    
    return "❌ Estado inválido."
