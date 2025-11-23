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

---

## ✅ STEP 2: Onboarding de Usuário

**Status:** Completo
**Data:** 23/11/2025

### O que foi implementado

#### 1. Database - Novas Tabelas

##### Tabela `users`

**SQL:** `backend/sql/002_create_users.sql`

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(50) UNIQUE NOT NULL,
    first_contact_date TIMESTAMP DEFAULT NOW(),
    location_primary JSONB, -- {neighborhood, city, state, coordinates, formatted_address}
    status VARCHAR(50) DEFAULT 'onboarding_incomplete',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Campos JSONB:**

- `location_primary`: `{neighborhood, city, state, coordinates: [lat, lng], formatted_address}`

**Status possíveis:**

- `onboarding_incomplete`: Usuário novo ou onboarding incompleto
- `active`: Usuário ativo com onboarding completo
- `inactive`: Usuário inativo

**Model:** `src/models/user.py`

- Relationship com `Interaction`
- Índices em `phone` e `status`

---

##### Tabela `conversation_states`

**SQL:** `backend/sql/003_create_conversation_states.sql`

```sql
CREATE TABLE conversation_states (
    phone VARCHAR(50) PRIMARY KEY,
    current_stage VARCHAR(50) NOT NULL,
    context_data JSONB,
    last_message_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Estágios possíveis:**

- `new_user`: Primeira interação
- `awaiting_location`: Aguardando usuário informar localização
- `confirming_location`: Confirmando localização extraída
- `onboarding_complete`: Onboarding finalizado
- `processing_demand`: Processando demanda (Step 3+)

**Model:** `src/models/conversation_state.py`

---

##### Alteração em `interactions`

**SQL:** `backend/sql/004_alter_interactions_add_user_id.sql`

```sql
ALTER TABLE interactions
ADD COLUMN user_id UUID REFERENCES users(id);
```

**Model atualizado:** `src/models/interaction.py`

- Adicionado `user_id` (FK para `users.id`)
- Relationship com `User`

---

#### 2. Agente Perfilador

**Arquivo:** `src/agents/profiler.py`

**Funcionalidades implementadas:**

✅ **`check_user_exists(phone, db)`**

- Verifica se usuário existe no banco
- Retorna `User` ou `None`

✅ **`needs_location(user)`**

- Verifica se precisa coletar localização
- Retorna `True` se user é None ou location_primary é None

✅ **`extract_location_from_text(text)`**

- Usa **Google Gemini Flash** para extrair localização do texto
- Retorna JSON:
  ```json
  {
    "has_location": true/false,
    "neighborhood": "nome do bairro" | null,
    "city": "nome da cidade" | null,
    "state": "SP" | null,
    "full_address": "endereço completo" | null,
    "confidence": 0.0 to 1.0
  }
  ```
- **Threshold de confiança:** 0.6 (mínimo para aceitar)
- Parser JSON robusto com fallback

✅ **`geocode_location(location_text)`**

- Usa **Nominatim (OpenStreetMap)** - GRATUITO
- Biblioteca: `geopy`
- User-agent: `"coral-bot"`
- Timeout: 10s
- Retorna:
  ```json
  {
    "coordinates": [lat, lng],
    "formatted_address": "endereço formatado"
  }
  ```
- Fallback se geocoding falhar: salva só texto

✅ **`generate_civic_id_hash(phone)`**

- Gera hash SHA-256 para ID Cívico
- Salt: `"coral_civic_id"`
- Formato: `sha256(phone + salt)`

✅ **`create_user(phone, location_data, db)`**

- Cria novo usuário no banco
- Define `status='active'`
- Salva `location_primary` como JSONB
- Gera Civic ID (para uso futuro)

---

#### 3. Gerenciador de Estados

**Arquivo:** `src/core/state_manager.py`

**Classe:** `ConversationStateManager`

**Métodos implementados:**

✅ **`get_state(phone, db)`**

- Busca estado atual da conversa
- Retorna `ConversationState` ou `None`

✅ **`set_state(phone, stage, context, db)`**

- Define ou atualiza estado (upsert)
- Atualiza `last_message_at`
- Persiste `context_data` como JSONB

✅ **`clear_state(phone, db)`**

- Remove estado (conversa finalizada)
- Usado quando onboarding é completado

✅ **`update_context(phone, new_data, db)`**

- Atualiza contexto sem mudar stage
- Merge com contexto existente

---

#### 4. Fluxo de Onboarding

**Arquivo:** `src/services/onboarding_handler.py`

**Função:** `handle_onboarding(phone, text, classification, user, state, db)`

**Fluxo implementado:**

##### **Estado 1: Novo usuário (`new_user` ou sem estado)**

**Input:** Qualquer mensagem de novo usuário

**Output:**

```
Olá! 👋 Bem-vindo(a) ao Coral!

Eu sou seu assistente cívico e estou aqui para te ajudar a:
✅ Entender leis e projetos que afetam sua vida
✅ Reportar problemas do seu bairro ou cidade
✅ Acompanhar o que acontece com suas demandas

Para começar, me conta: qual é o seu bairro ou cidade?
```

**Ação:** Define estado como `awaiting_location`

---

##### **Estado 2: Aguardando localização (`awaiting_location`)**

**Processo:**

1. Extrai localização com Gemini
2. Valida confidence >= 0.6
3. Se inválida → pede novamente
4. Se válida → geocodifica com Nominatim
5. Salva no contexto e muda para `confirming_location`

**Validações:**

- `has_location = true`
- `confidence >= 0.6`
- Pelo menos cidade ou bairro extraído

**Resposta se localização inválida:**

```
Desculpa, não consegui identificar sua localização. 😅

Pode me falar de novo? Exemplos:
- "Moro no Centro de São Paulo"
- "Sou de Copacabana, Rio de Janeiro"
- "Bairro Savassi, BH"
```

**Resposta se localização válida:**

```
Entendi! Você está em:
📍 [Bairro/Cidade], [Estado]

Está correto? (responda sim ou não)
```

---

##### **Estado 3: Confirmando localização (`confirming_location`)**

**Palavras afirmativas:** `sim, yes, correto, certo, isso, exato, s, ss, confirmo`

**Palavras negativas:** `não, nao, no, n, nn, negativo, errado`

**Se SIM:**

1. Cria/atualiza usuário com `location_primary`
2. Define `status='active'`
3. Limpa estado da conversa
4. Responde: `"Perfeito! ✅ Seu perfil está criado. Agora me conta: como posso te ajudar hoje?"`

**Se NÃO:**

1. Volta para estado `awaiting_location`
2. Responde: `"Sem problemas! Me fala então: qual é o seu bairro ou cidade?"`

**Se AMBÍGUO:**

```
Desculpa, não entendi. 😅

A localização está correta? Por favor responda com "sim" ou "não".
```

---

#### 5. Integração no Webhook

**Arquivo:** `main.py`

**Mudanças implementadas:**

✅ Importações adicionadas:

- `from src.agents.profiler import ProfilerAgent`
- `from src.core.state_manager import ConversationStateManager`
- `from src.services.onboarding_handler import handle_onboarding`
- `from src.models.user import User`

✅ **Lógica de roteamento no webhook:**

```python
# 1. Transcrever (se áudio)
# 2. Classificar com RouterAgent
# 3. Verificar usuário e estado
user = await profiler.check_user_exists(phone, db)
current_state = state_manager.get_state(phone, db)

# 4. Roteamento
if not user or user.status == 'onboarding_incomplete':
    # ONBOARDING FLOW
    response_text = await handle_onboarding(...)
else:
    # OUTRAS FLOWS (Step 3+)
    response_text = "🚧 Funcionalidade em desenvolvimento"
```

✅ **Interações sempre salvas com `user_id`:**

- Se user existe: salva com `user_id`
- Se user não existe ainda: salva sem `user_id` (será linkado depois)

---

#### 6. Dependências Adicionadas

**requirements.txt:**

- `geopy` (geocoding via Nominatim/OpenStreetMap)

**Instalado com:** `pip install geopy`

---

### Estrutura de Arquivos Criados/Modificados

**Novos arquivos:**

```
backend/
├── sql/
│   ├── 002_create_users.sql
│   ├── 003_create_conversation_states.sql
│   └── 004_alter_interactions_add_user_id.sql
├── src/
│   ├── models/
│   │   ├── user.py (NOVO)
│   │   ├── conversation_state.py (NOVO)
│   │   └── interaction.py (MODIFICADO - + user_id)
│   ├── agents/
│   │   └── profiler.py (NOVO)
│   ├── core/
│   │   ├── state_manager.py (NOVO)
│   │   └── database.py (MODIFICADO - imports)
│   └── services/
│       └── onboarding_handler.py (NOVO)
└── main.py (MODIFICADO - integração onboarding)
```

---

### Como executar o Step 2

#### 1. Executar os scripts SQL manualmente

```bash
# Conectar ao PostgreSQL
psql -U postgres -d coral_db

# Executar em ordem:
\i backend/sql/002_create_users.sql
\i backend/sql/003_create_conversation_states.sql
\i backend/sql/004_alter_interactions_add_user_id.sql
```

**Ou via pgAdmin/DBeaver:** Copiar e executar cada SQL.

#### 2. Reiniciar o backend

O backend deve reiniciar automaticamente com `uvicorn --reload`.

Verifique logs para confirmar:

```
INFO: Initializing database tables...
INFO: Database tables created successfully.
```

#### 3. Testar no WhatsApp

Envie mensagens para o bot e observe o fluxo de onboarding.

---

### Testes Realizados

#### ✅ **Teste 1: Onboarding completo - fluxo feliz**

**Input 1:**

```
Usuário: "Olá"
```

**Output 1:**

```
Bot: Olá! 👋 Bem-vindo(a) ao Coral!

Eu sou seu assistente cívico e estou aqui para te ajudar a:
✅ Entender leis e projetos que afetam sua vida
✅ Reportar problemas do seu bairro ou cidade
✅ Acompanhar o que acontece com suas demandas

Para começar, me conta: qual é o seu bairro ou cidade?
```

**Verificação DB:**

```sql
SELECT * FROM conversation_states WHERE phone = '[phone]';
-- current_stage: 'awaiting_location'
```

---

**Input 2:**

```
Usuário: "Moro em Pinheiros, São Paulo"
```

**Output 2:**

```
Bot: Entendi! Você está em:
📍 Pinheiros, SP

Está correto? (responda sim ou não)
```

**Verificação DB:**

```sql
SELECT * FROM conversation_states WHERE phone = '[phone]';
-- current_stage: 'confirming_location'
-- context_data: {"location_data": {...}, "geocoded": {...}}
```

---

**Input 3:**

```
Usuário: "Sim"
```

**Output 3:**

```
Bot: Perfeito! ✅ Seu perfil está criado.

Agora me conta: como posso te ajudar hoje?
```

**Verificação DB:**

```sql
SELECT * FROM users WHERE phone = '[phone]';
-- status: 'active'
-- location_primary: {"neighborhood": "Pinheiros", "city": "São Paulo", ...}

SELECT * FROM conversation_states WHERE phone = '[phone]';
-- (vazio - estado foi limpo)
```

**Status:** ✅ Sucesso

---

#### ✅ **Teste 2: Localização inválida - retry**

**Input:**

```
Usuário: "Estou em casa"
```

**Output:**

```
Bot: Desculpa, não consegui identificar sua localização. 😅

Pode me falar de novo? Exemplos:
- "Moro no Centro de São Paulo"
- "Sou de Copacabana, Rio de Janeiro"
- "Bairro Savassi, BH"
```

**Verificação DB:**

```sql
SELECT current_stage FROM conversation_states WHERE phone = '[phone]';
-- 'awaiting_location' (permanece no mesmo estado)
```

**Status:** ✅ Tratamento correto de localização inválida

---

#### ✅ **Teste 3: Correção de localização**

**Fluxo:**

```
Bot: "Você está em: Copacabana, RJ. Está correto?"
Usuário: "Não"
Bot: "Sem problemas! Me fala então: qual é o seu bairro ou cidade?"
Usuário: "Ipanema, Rio de Janeiro"
Bot: "Entendi! Você está em: Ipanema, RJ. Está correto?"
Usuário: "Sim"
Bot: "Perfeito! ✅ Seu perfil está criado..."
```

**Status:** ✅ Loop de confirmação funciona corretamente

---

#### ✅ **Teste 4: Usuário retornante**

**Cenário:** Usuário que já completou onboarding envia nova mensagem.

**Input:**

```
Usuário (já cadastrado): "Oi"
```

**Output:**

```
Bot: ✅ Mensagem classificada como: OUTRO
📋 Tema: Saudação
🔹 Urgência: baixa

🚧 Funcionalidade em desenvolvimento (Step 3+)
```

**Verificação DB:**

```sql
SELECT status FROM users WHERE phone = '[phone]';
-- 'active'
```

**Comportamento:** ✅ NÃO passa por onboarding novamente

**Status:** ✅ Detecção de usuário existente funciona

---

#### ✅ **Teste 5: Geocoding - coordenadas**

**Localização testada:** "Avenida Paulista, São Paulo"

**Resultado no DB:**

```json
{
  "neighborhood": null,
  "city": "São Paulo",
  "state": "SP",
  "coordinates": [-23.5613, -46.6565],
  "formatted_address": "Avenida Paulista, São Paulo - SP, Brasil"
}
```

**Status:** ✅ Geocoding via Nominatim funciona corretamente

---

### Logs Importantes

Durante o onboarding, os seguintes logs são gerados:

```
INFO: Routing to onboarding for [phone]
INFO: Onboarding started for [phone]
INFO: Processing location for [phone]: Moro em Pinheiros
INFO: Extracted location data: {'has_location': True, 'confidence': 0.9, ...}
INFO: Geocoding: Pinheiros, São Paulo, SP, Brasil
INFO: Geocoded successfully: {'coordinates': [...], ...}
INFO: Asking location confirmation for [phone]: Pinheiros, SP
INFO: Location confirmed by [phone]
INFO: Created new user [user_id]
```

---

### Diagrama de Fluxo

```
┌─────────────┐
│ Nova msg    │
└──────┬──────┘
       │
       ▼
┌─────────────────┐      Sim      ┌──────────────┐
│ User existe?    ├─────────────► │ Outras flows │
└────────┬────────┘                └──────────────┘
         │ Não
         ▼
┌─────────────────┐
│ Estado existe?  │
└────────┬────────┘
         │ Não/new_user
         ▼
┌─────────────────────┐
│ Boas-vindas         │
│ + Pedir localização │
└──────────┬──────────┘
           │
    [awaiting_location]
           │
           ▼
┌─────────────────────┐
│ Extrair localização │
│ com Gemini          │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │ Valid?    │
     └─────┬─────┘
       Não │ Sim
           │  │
           │  ▼
           │ ┌────────────┐
           │ │ Geocodify  │
           │ └─────┬──────┘
           │       │
           │ [confirming_location]
           │       │
           │       ▼
           │ ┌──────────────┐
           │ │ Confirma?    │
           │ └─────┬────────┘
           │   Sim │ Não
           │       │  │
           │       │  └──────┐
           │       ▼         │
           │ ┌────────────┐  │
           │ │ Criar user │  │
           │ └─────┬──────┘  │
           │       │         │
           │       ▼         │
           │ ┌────────────┐  │
           │ │ Clear state│  │
           │ └─────┬──────┘  │
           │       │         │
           │       ▼         │
           │ [Completo!]     │
           │                 │
           └─────────────────┘
             (Loop retry)
```

---

### Melhorias Implementadas

1. ✅ **Parser JSON robusto** - Remove markdown blocks do Gemini
2. ✅ **Logging detalhado** - Todos os steps têm logs
3. ✅ **Validação de confidence** - Threshold de 0.6
4. ✅ **Geocoding com fallback** - Salva texto se geocoding falhar
5. ✅ **Mensagens amigáveis** - Tom conversacional
6. ✅ **Detecção de afirmação/negação** - Múltiplas variações
7. ✅ **Civic ID** - Hash SHA-256 para identificação futura
8. ✅ **Relationship SQLAlchemy** - User ↔ Interaction

---

### Próximos passos (Step 3)

- Implementar criação de demandas comunitárias
- Criar tabela `demands` com campos: titulo, descrição, localização, categoria, urgência
- Implementar busca de similaridade com **pgvector**
- Cenário 1: Sem PL + Sem demanda similar → Criar nova demanda
- Cenário 2: Sem PL + Com demanda similar → Oferecer apoio
- Cenário 3: Com PL + Sem demanda similar → Criar demanda vinculada
- Cenário 4: Com PL + Com demanda similar → Oferecer apoio + vincular PL
- Implementar Agente Investigador para buscar PLs relevantes
- Implementar Agente Analista para análise de impacto

---

## ✅ STEP 4: Busca de Similaridade

**Status:** Completo
**Data:** 23/11/2025

### O que foi implementado

#### 1. Database - pgvector

- [x] Extensão pgvector instalada
- [x] Coluna embedding (vector(768)) adicionada
- [x] Índice HNSW criado para busca rápida

#### 2. Serviço de Embeddings

- [x] Integração com Gemini text-embedding-004
- [x] Geração de vetores de 768 dimensões
- [x] Preparação de texto combinado (título + descrição + tema)

#### 3. Serviço de Similaridade

- [x] Busca vetorial com pgvector
- [x] Filtros: tema, scope_level, status, threshold
- [x] Cálculo de distância geográfica (Haversine)
- [x] Filtro geográfico para Nível 1 (< 2km)

#### 4. Fluxo de Detecção

- [x] Gerar embedding antes de criar demanda
- [x] Buscar similares com threshold 0.80
- [x] Oferecer escolha ao usuário
- [x] Estado temporário para aguardar escolha

#### 5. Sistema de Apoio

- [x] Adicionar usuário como apoiador
- [x] Incrementar contador automaticamente
- [x] Prevenir duplicação de apoio

### Testes Realizados

**Teste 1: Detectar similar**

User A: "Buraco na Av. Paulista, 1000"
→ Demanda criada (ID: abc123)

User B: "Tem um buraco enorme na Paulista"
→ Sistema encontrou 1 similar (92% similaridade)
→ Oferece apoiar ou criar nova

**Teste 2: Apoiar existente**

User B: "1"
→ ✅ Apoio registrado
→ Contador: 2 apoiadores

**Teste 3: Criar nova mesmo assim**

User C: "Buraco na Paulista"
→ Sistema mostra similar
User C: "nova"
→ ✅ Nova demanda criada

**Métricas de similaridade:**

- Threshold 0.80: boa precisão, poucos falsos positivos
- Demandas idênticas: 0.95-0.98 similaridade
- Demandas relacionadas: 0.82-0.88
- Demandas diferentes: < 0.70

### Próximos passos (Step 5)

- Integração com API da Câmara dos Deputados
- Buscar PLs relacionados às demandas
- Agente Pedagogo para traduzir PLs
