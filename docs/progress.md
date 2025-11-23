# Projeto Coral - Progresso de Implementação

## ✅ STEP 0: Setup Inicial do Ambiente

**Status:** Completo
**Data:** 23/11/2025

### O que foi implementado

- Bot WhatsApp (whatsapp-web.js)
- Backend (FastAPI)
- Database (PostgreSQL)
- Integração básica (Echo)

---

## ✅ STEP 1: Transcrição e Classificação Básica

**Status:** Completo
**Data:** 23/11/2025

### O que foi implementado

#### 1. Bot WhatsApp - Processamento de Áudio

- [x] Detectar mensagem de texto vs áudio
- [x] Baixar áudio do WhatsApp
- [x] Acelerar áudio para 1.25x usando ffmpeg
- [x] Enviar como multipart/form-data para FastAPI
- [x] Atualizar payload para incluir tipo de mensagem

**Arquivos modificados:**

- `whatsapp-bot/src/whatsapp-client.js`
- `whatsapp-bot/package.json` (+ fluent-ffmpeg)

**Dependências Node.js adicionadas:**

- fluent-ffmpeg (processamento de áudio)

---

#### 2. Backend - Transcrição com Faster-Whisper

- [x] Faster-Whisper instalado e configurado
- [x] Modelo carregado uma única vez (singleton)
- [x] Transcrição otimizada com VAD (Voice Activity Detection)
- [x] Suporte a áudios acelerados

**Arquivos criados:**

- `backend/src/services/whisper_service.py`
- `backend/src/core/whisper_model.py` (singleton)

**Configurações:**

- Modelo: base
- Device: CPU (int8)
- VAD: ativado

---

#### 3. Backend - Agente Porteiro (Classificador)

- [x] RouterAgent implementado
- [x] Integração com Google Gemini Flash
- [x] Prompt de classificação otimizado
- [x] Extração de: tema, localização, urgência, keywords
- [x] Parser JSON robusto com fallback

**Arquivos criados:**

- `backend/src/agents/router.py`
- `backend/src/core/gemini.py`

---

#### 4. Database - Tabela interactions

- [x] Model SQLAlchemy implementado (`src/models/interaction.py`)
- [x] Criação automática de tabelas via `init_db` (Substituindo Alembic por enquanto)
- [x] Índices otimizados

**Schema:**

```sql
interactions (
    id, phone, message_type, original_message,
    transcription, audio_duration_seconds,
    classification, extracted_data, created_at
)
```

---

#### 5. Backend - Webhook com suporte a multipart

- [x] Endpoint atualizado para aceitar JSON e multipart
- [x] Processamento de arquivos de áudio
- [x] Detecção de duração original do áudio
- [x] Limpeza de arquivos temporários
- [x] Resposta contextualizada com duração

---

### Como rodar o projeto (Step 1)

#### Pré-requisitos Adicionais

1.  **FFmpeg**: Deve estar instalado no sistema e acessível no PATH.
2.  **API Key do Gemini**: Adicionar `GOOGLE_GEMINI_API_KEY` no `.env` do backend.

#### Execução

1.  Backend: `uvicorn main:app --reload --host 0.0.0.0 --port 8000`
2.  Bot: `node index.js` (na pasta whatsapp-bot)

---

### Próximos passos (Step 2)

- Implementar fluxo de Onboarding completo
- Criar tabela `users` no PostgreSQL
- Implementar Agente Perfilador
- Coletar localização do usuário com geocoding
- Gerar ID Cívico
