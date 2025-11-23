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
            # Map 'type' to 'message_type' if needed, or just use defaults
            # api-client.js sends 'type', WebhookMessage expects 'message_type'
            # We can manually construct the object
            
            phone = data.get("from")
            text = data.get("body")
            msg_type = data.get("message_type", "text")
            
            # Validate
            if not phone or not text:
                 raise HTTPException(status_code=400, detail="Missing from or body")
                 
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported Content-Type: {content_type}")

        # 2. Classify
        router = RouterAgent()
        classification_result = await router.classify_and_extract(text)
        logger.info(f"Classification: {classification_result}")

        # 3. Check user and conversation state
        profiler = ProfilerAgent()
        state_manager = ConversationStateManager()
        
        user = await profiler.check_user_exists(phone, db)
        current_state = state_manager.get_state(phone, db)
        
        # 4. Route based on user status and onboarding completion
        if not user or user.status == 'onboarding_incomplete':
            # User needs onboarding
            logger.info(f"Routing to onboarding for {phone}")
            response_text = await handle_onboarding(
                phone, text, classification_result,
                user, current_state, db
            )
            
            # Save interaction (without user_id if user not created yet)
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
            
            return {"response": response_text}
        
        # 5. User exists and onboarding complete - handle other flows
        # TODO: Implement demand, question, and other flows in future steps
        logger.info(f"User {user.id} already onboarded, processing message")
        
        # Save interaction with user_id
        interaction = Interaction(
            phone=phone,
            user_id=user.id,
            message_type=msg_type,
            original_message=text if msg_type == "text" else None,
            transcription=text if msg_type == "audio" else None,
            audio_duration_seconds=audio_duration,
            classification=classification_result.get("classification"),
            extracted_data=classification_result
        )
        db.add(interaction)
        db.commit()
        
        # 6. Response (temporary - will be replaced with specific handlers in next steps)
        classification = classification_result.get('classification', 'OUTRO')
        theme = classification_result.get('theme', 'outros')
        urgency = classification_result.get('urgency', 'baixa')
        
        # Mensagem amigável baseada na classificação
        if classification == 'DEMANDA':
            response_text = f"""✅ Recebi sua demanda sobre {theme}!

📋 Classificação: {classification}
🔹 Urgência: {urgency}
📍 Localização cadastrada: {user.location_primary.get('city', 'não especificada') if user.location_primary else 'não informada'}

💬 Você disse: "{text[:100]}{'...' if len(text) > 100 else ''}"

⚠️ **Sistema em desenvolvimento (Step 3)**
Em breve vou:
• Buscar demandas similares
• Encontrar Projetos de Lei relacionados
• Te conectar com outros cidadãos

Por enquanto, estou apenas registrando. Obrigado pela paciência! 🙏"""
        
        elif classification == 'DUVIDA':
            response_text = f"""✅ Recebi sua dúvida sobre {theme}!

📋 Classificação: {classification}
❓ Pergunta: "{text[:100]}{'...' if len(text) > 100 else ''}"

⚠️ **Sistema em desenvolvimento**
Em breve vou te ajudar com:
• Explicações sobre leis e PLs
• Análise de impacto na sua região
• Respostas pedagógicas

Por enquanto, estou apenas aprendendo! 📚"""
        
        else:
            response_text = f"""✅ Mensagem recebida!

📋 Tipo: {classification}
📍 Tema: {theme}

"{text[:100]}{'...' if len(text) > 100 else ''}"

⚠️ **Em desenvolvimento**
Funcionalidades completas chegando em breve! 🚀""" 
        
        if audio_duration:
            response_text += f"\n\n🎙️ Áudio de {audio_duration:.1f}s transcrito com sucesso"

        return {"response": response_text}

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"response": "Desculpe, ocorreu um erro ao processar sua mensagem."}

if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)
