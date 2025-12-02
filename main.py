from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from src.core.config import settings
from src.core.database import get_db
from src.models.interaction import Interaction
from src.models.user import User
from src.services import whisper_service
from src.agents.router import RouterAgent
from src.agents.profiler import ProfilerAgent
from src.agents.writer import WriterAgent
from src.core.state_manager import ConversationStateManager
from src.services.onboarding_handler import handle_onboarding
from src.services.demand_handler import handle_demand_creation
# Importação completa dos Handlers para o roteamento de estado
from src.services.demand_handler import handle_problem_confirmation, handle_create_demand_decision, handle_demand_choice, handle_demand_drafting 
from src.services.question_action_handler import handle_question_action_choice
from src.services.demand_support_handler import handle_demand_support_choice
from src.services.question_handler import handle_question
from src.services.demand_investigation_handler import investigation_handler
# Import V2 Flow (sem IA para textos simples)
from src.services.demand_flow_v2 import start_demand_flow, process_demand_step, DemandFlowStates
# Import routers
from src.routes.auth import router as auth_router
from src.routes.user import router as user_router
from src.routes.demands import router as demands_router
from src.routes.community import router as community_router
import uvicorn
import uuid
import os
import logging
from typing import Optional
from pydub import AudioSegment

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Coral Bot Backend")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default port
        "http://localhost:3000",  # Alternative frontend port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Standardize error responses to {"message": "..."}
@app.exception_handler(FastAPIHTTPException)
async def custom_http_exception_handler(request: Request, exc: FastAPIHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"message": exc.detail})

# Include routers
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(demands_router)
app.include_router(community_router)

class WebhookResponse(BaseModel):
    response: str

@app.on_event("startup")
def startup_event():
    from src.core.database import init_db
    logger.info("Initializing database tables...")
    init_db()
    logger.info("Database tables created successfully.")

@app.get("/health")
def health_check():
    return {"status": "ok", "database": "connected"}

@app.post("/webhook", response_model=WebhookResponse)
async def webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    text = None
    audio_duration = None
    phone = None
    msg_type = None
    writer = WriterAgent()
    
    try:
        content_type = request.headers.get("content-type", "")
        
        # 1. PROCESSAMENTO DE ENTRADA (Multipart/Audio ou JSON/Texto)
        if "multipart/form-data" in content_type:
            logger.info("Processing multipart/form-data request")
            form = await request.form()
            
            audio_file = form.get("audio_file")
            phone = form.get("from")
            msg_type = "audio"
            
            if not audio_file:
                raise HTTPException(status_code=400, detail="Missing audio_file")

            # Save temp file
            temp_filename = f"audio_{uuid.uuid4()}.ogg"
            temp_path = os.path.join("/tmp", temp_filename) if os.name != 'nt' else os.path.join(os.getenv('TEMP', '/tmp'), temp_filename)
            
            try:
                content = await audio_file.read()
                with open(temp_path, "wb") as f:
                    f.write(content)
                
                # Get duration (mantido do código original)
                try:
                    audio = AudioSegment.from_file(temp_path)
                    current_duration = len(audio) / 1000.0
                    audio_duration = current_duration * 1.25
                except Exception as e:
                    logger.warning(f"Could not determine audio duration: {e}")
                    audio_duration = 0.0
                
                # Transcribe
                text = await whisper_service.transcribe_audio(temp_path)
                logger.info(f"Transcription: {text}")

                # Edge Case 1: Empty Transcription
                if not text or not text.strip():
                    return WebhookResponse(response=await writer.empty_message_response(is_audio=True))
                
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
        elif "application/json" in content_type:
            logger.info("Processing application/json request")
            data = await request.json()
            
            phone = data.get("from")
            text = data.get("body")
            msg_type = data.get("message_type", "text")
            
            # Edge Case 2: Empty Text Message
            if not phone or not text or not text.strip():
                 return WebhookResponse(response=await writer.empty_message_response(is_audio=False))
                 
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported Content-Type: {content_type}")

        # 2. CLASSIFICAÇÃO (Agente Roteador)
        router = RouterAgent()
        classification_result = await router.classify_and_extract(text)
        logger.info(f"Classification: {classification_result}")

        # 3. VERIFICAÇÃO DE ESTADO E USUÁRIO (Profiler)
        profiler = ProfilerAgent()
        state_manager = ConversationStateManager()
        
        user = await profiler.check_user_exists(phone, db)
        current_state = state_manager.get_state(phone, db)
        
        # 4. SALVAR INTERAÇÃO (LOG)
        interaction = Interaction(
            phone=phone,
            user_id=user.id if user else None,
            message_type=msg_type,
            original_message=text if msg_type == "text" else None,
            transcription=text if msg_type == "audio" else None,
            audio_duration_seconds=audio_duration,
            classification=classification_result.get("classification"),
            extracted_data=classification_result
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)
        logger.info(f"Interaction saved: {interaction.id}")

        # 5. ROTEAMENTO DE FLUXO
        
        # FLUXO A: Usuário Novo ou Onboarding Incompleto
        if not user or user.status == 'onboarding_incomplete':
            logger.info(f"Routing to onboarding for {phone}")
            response_text = await handle_onboarding(
                phone, text, classification_result,
                user, current_state, db
            )
            
        # FLUXO B: Usuário Ativo (Já cadastrado)
        else:
            logger.info(f"Routing to Active/Demand Flow for {phone}")

            # --- PRIORIDADE 1: FLUXO DE ESTADO (MULTI-TURN) ---
            response_text = None
            
            if current_state:
                # NOVO FLUXO V2 (Step-by-step sem IA)
                v2_states = [
                    DemandFlowStates.COLLECTING_DESCRIPTION,
                    DemandFlowStates.COLLECTING_LOCATION,
                    DemandFlowStates.COLLECTING_CATEGORY,
                    DemandFlowStates.CONFIRMING
                ]
                
                if current_state.current_stage in v2_states:
                    logger.info(f"Handling V2 demand flow: {current_state.current_stage}")
                    response_text = await process_demand_step(
                        phone=phone,
                        text=text,
                        current_state=current_state.current_stage,
                        state_context=current_state.context_data,
                        db=db
                    )
                
                # Menu de escolha de tipo de ajuda
                elif current_state.current_stage == 'choosing_help_type':
                    choice = text.strip()
                    state_manager = ConversationStateManager()
                    
                    if choice == '1':
                        # Iniciar fluxo de criação de demanda
                        logger.info(f"User chose to create demand: {user.id}")
                        state_manager.clear_state(phone, db)
                        response_text = await start_demand_flow(phone, db)
                    
                    elif choice == '2':
                        # Ver demandas próximas (TODO: implementar busca por localização)
                        logger.info(f"User wants to see nearby demands: {user.id}")
                        state_manager.clear_state(phone, db)
                        response_text = (
                            "🔍 *Buscar demandas próximas*\n\n"
                            "Esta funcionalidade estará disponível em breve!\n\n"
                            "Por enquanto, você pode:\n"
                            "• Criar uma nova demanda (digite *1*)\n"
                            "• Tirar uma dúvida (digite *3*)"
                        )
                    
                    elif choice == '3':
                        # Tirar dúvida
                        logger.info(f"User wants to ask question: {user.id}")
                        state_manager.clear_state(phone, db)
                        response_text = (
                            "❓ *Tirar Dúvida*\n\n"
                            "Faça sua pergunta sobre:\n"
                            "• Leis municipais ou estaduais\n"
                            "• Projetos de lei em tramitação\n"
                            "• Serviços públicos\n"
                            "• Como funciona a Câmara/Assembleia\n\n"
                            "Digite sua pergunta:"
                        )
                        state_manager.set_state(phone, 'asking_question', {}, db)
                    
                    else:
                        response_text = (
                            "❌ Opção inválida.\n\n"
                            "Digite *1*, *2* ou *3*"
                        )
                
                # Estado quando encontrou lei vigente
                elif current_state.current_stage == 'law_found':
                    choice = text.strip()
                    state_manager = ConversationStateManager()
                    
                    if choice == '1':
                        # Criar demanda comunitária mesmo tendo lei
                        logger.info(f"User chose to create demand despite existing law: {user.id}")
                        state_manager.clear_state(phone, db)
                        response_text = await start_demand_flow(phone, db)
                    
                    elif choice == '2':
                        # Orientação completa
                        logger.info(f"User wants full guidance: {user.id}")
                        state_manager.clear_state(phone, db)
                        response_text = (
                            "📋 *Orientação Completa*\n\n"
                            "Em breve você terá acesso a:\n"
                            "• Passo a passo detalhado\n"
                            "• Modelos de reclamação\n"
                            "• Contatos dos órgãos\n"
                            "• Exemplos de sucesso\n\n"
                            "Por enquanto, use as informações que já te passei para exercer seu direito! 💪"
                        )
                    
                    elif choice == '3':
                        # Nada por enquanto
                        logger.info(f"User understood their rights: {user.id}")
                        state_manager.clear_state(phone, db)
                        response_text = (
                            "✅ Perfeito! Agora você conhece seus direitos.\n\n"
                            "Se precisar de ajuda no futuro, é só me chamar! 💙"
                        )
                    
                    else:
                        response_text = (
                            "❌ Opção inválida.\n\n"
                            "Digite *1*, *2* ou *3*"
                        )
                
                # Estado de pergunta ativa
                elif current_state.current_stage == 'asking_question':
                    logger.info(f"Processing user question: {user.id}")
                    state_manager = ConversationStateManager()
                    state_manager.clear_state(phone, db)
                    
                    # Chamar handler de dúvida
                    response_text = await handle_question(
                        user_id=str(user.id), 
                        phone=phone, 
                        text=text,
                        classification=classification_result, 
                        user_location=user.location_primary,
                        db=db
                    )
                
                # FLUXO V1 LEGADO (mantido para compatibilidade)
                else:
                    handler_map = {
                        'drafting_demand': handle_demand_drafting,
                        'confirming_problem': handle_problem_confirmation,
                        'asking_create_demand': handle_create_demand_decision,
                        'choosing_similar_or_new': handle_demand_choice,
                        'awaiting_demand_choice': handle_demand_choice, # Mantido por compatibilidade
                        'choosing_demand_action_after_question': handle_question_action_choice,
                        'choosing_demand_to_support': handle_demand_support_choice,
                    }
                    
                    handler = handler_map.get(current_state.current_stage)
                    
                    if handler:
                        logger.info(f"Handling state: {current_state.current_stage}")
                        
                        # Argumentos comuns para todos os handlers
                        common_args = {
                            "user_id": str(user.id),
                            "phone": phone,
                            "state_context": current_state.context_data,
                            "db": db
                        }
                        
                        # Chamada unificada baseada no tipo de input esperado
                        if current_state.current_stage in ['drafting_demand', 'choosing_similar_or_new', 'awaiting_demand_choice', 'choosing_demand_to_support']:
                            # Handlers que esperam o input principal como 'text' ou 'choice_text'
                            response_text = await handler(**common_args, text=text)
                        
                        elif current_state.current_stage == 'confirming_problem':
                            # Handler que espera 'confirmation_text'
                            response_text = await handler(**common_args, confirmation_text=text)

                        elif current_state.current_stage == 'asking_create_demand':
                            # Handler que espera 'decision_text'
                            response_text = await handler(**common_args, decision_text=text)

                        elif current_state.current_stage == 'choosing_demand_action_after_question':
                            # Handler que precisa de 'text' e 'user_location'
                            response_text = await handler(
                                **common_args,
                                text=text,
                                user_location=user.location_primary
                            )            # --- PRIORIDADE 2: SEM ESTADO ATIVO OU RESPOSTA PENDENTE ---
            
            if not response_text:
                
                classification = classification_result.get('classification')

                # Tratamento de ONBOARDING (Saudação) para usuário ativo
                if classification == 'ONBOARDING':
                    logger.info(f"Active user greeting: {user.id}")
                    response_text = await writer.welcome_message(is_new_user=False)

                # Tratamento de DEMANDA (mostra opções primeiro)
                elif classification == 'DEMANDA':
                    logger.info(f"User mentioned a problem: {user.id}")
                    
                    # Enviar feedback imediato ao usuário
                    feedback_message = "🔍 *Aguarde um momento...*\n\nEstou pesquisando leis, projetos e demandas relacionadas ao seu problema."
                    
                    # Tentar enviar feedback via WhatsApp (não bloqueia se falhar)
                    try:
                        from src.services.whatsapp_service import WhatsAppService
                        await WhatsAppService.send_message(phone.replace('@c.us', ''), feedback_message)
                    except Exception as e:
                        logger.warning(f"Could not send feedback message: {e}")
                    
                    # NOVO FLUXO: Investigação completa antes de apresentar opções
                    response_text = await investigation_handler.investigate_and_present_options(
                        user_text=text,
                        classification_result=classification_result,
                        user_location=user.location_primary,
                        db=db
                    )
                    
                    logger.info(f"Investigation result length: {len(response_text)} chars")
                    logger.info(f"Investigation result preview: {response_text[:200]}...")
                    logger.info(f"First char (repr): {repr(response_text[0])} | Starts with 🎯: {response_text.startswith('🎯')}")
                    
                    # IMPORTANTE: Salvar contexto SOMENTE se não encontrou lei vigente
                    # (Lei vigente tem opções diferentes: criar demanda, orientação, nada)
                    state_manager = ConversationStateManager()
                    
                    # Detectar se é resposta de lei vigente (começa com 🎯)
                    if response_text.startswith("🎯"):
                        logger.info("Found existing law - setting state: law_found")
                        state_manager.set_state(phone, 'law_found', {'original_text': text, 'response': response_text}, db)
                    else:
                        logger.info("No law found - setting state: choosing_help_type")
                        state_manager.set_state(phone, 'choosing_help_type', {'original_text': text}, db)

                # Tratamento de DUVIDA (perguntas sobre legislação)
                elif classification == 'DUVIDA':
                    response_text = await handle_question(
                        user_id=str(user.id), phone=phone, text=text,
                        classification=classification_result, user_location=user.location_primary,
                        db=db
                    )

                # Outros tipos de mensagem (OUTRO, interrupção de fluxo sem resposta)
                else:
                    logger.warning(f"Unrecognized classification or fallback for active user: {classification}")
                    # Fallback com opções
                    response_text = await writer.ask_for_help_options()

        return WebhookResponse(response=response_text)

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        # Retorna erro genérico usando WriterAgent
        return WebhookResponse(response=await writer.generic_error_response())

if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)