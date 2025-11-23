from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from src.core.config import settings
from src.core.database import get_db
from src.models.interaction import Interaction
from src.models.user import User
from src.services import whisper_service
from src.agents.router import RouterAgent
from src.agents.profiler import ProfilerAgent
from src.core.state_manager import ConversationStateManager
from src.services.onboarding_handler import handle_onboarding
from src.services.demand_handler import handle_demand_creation
from src.models.demand import Demand
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

class WebhookMessage(BaseModel):
    from_: str = Field(..., alias="from")
    body: str
    timestamp: int
    message_type: str = "text"

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
                # Write file
                content = await audio_file.read()
                with open(temp_path, "wb") as f:
                    f.write(content)
                
                # Get duration
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
                
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
        elif "application/json" in content_type:
            logger.info("Processing application/json request")
            data = await request.json()
            
            phone = data.get("from")
            text = data.get("body")
            msg_type = data.get("message_type", "text")
            
            # Validate
            if not phone or not text:
                 raise HTTPException(status_code=400, detail="Missing from or body")
                 
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
        
        # 4. SALVAR INTERAÇÃO (LOG) - MOVIDO PARA ANTES DO ROTEAMENTO
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
            
            # Tratamento de ONBOARDING para usuário ativo
            if classification_result.get('classification') == 'ONBOARDING':
                logger.info(f"Active user greeting: {user.id}")
                response_text = "Oi! 👋 Já nos conhecemos 😊\n\nComo posso te ajudar hoje?\n\n💡 Dica: Você pode relatar problemas do seu bairro ou tirar dúvidas sobre leis!"

            # Verifica se existe um estado de conversa específico (ex: respondendo a uma pergunta do bot)
            # Se não houver estado, assume fluxo padrão de demanda
            elif current_state and current_state.current_stage != 'processing_demand':
                 # Se tivéssemos fluxos multi-turn para demandas complexas, trataríamos aqui
                 pass
                 # Fallback para demanda se não tiver handler específico
                 response_text = await handle_demand_creation(
                    user_id=str(user.id),
                    phone=phone,
                    text=text,
                    classification=classification_result,
                    user_location=user.location_primary,
                    interaction_id=str(interaction.id),
                    db=db
                )

            else:
                # Chama o Handler de Demandas (CRIAÇÃO DE DEMANDA ACONTECE AQUI)
                response_text = await handle_demand_creation(
                    user_id=str(user.id),
                    phone=phone,
                    text=text,
                    classification=classification_result,
                    user_location=user.location_primary,
                    interaction_id=str(interaction.id),
                    db=db
                )

        return WebhookResponse(response=response_text)

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        # Retorna erro genérico mas não derruba o webhook do whatsapp
        return WebhookResponse(response="Desculpe, tive um erro interno. Tente novamente mais tarde.")

if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)