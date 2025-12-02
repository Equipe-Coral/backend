# 🌊 Coral Backend - Documentação Técnica

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Modelos de Dados](#modelos-de-dados)
- [APIs REST](#apis-rest)
- [Autenticação](#autenticação)
- [Serviços](#serviços)
- [Configuração](#configuração)
- [Instalação](#instalação)

---

## 🎯 Visão Geral

O backend do Coral é uma aplicação FastAPI que gerencia:
- **Chatbot via WhatsApp**: Sistema conversacional para engajamento cívico
- **API REST**: Interface web para autenticação e perfil de usuário
- **Blockchain**: Registro de demandas cívicas na blockchain

### Tecnologias

- **Framework**: FastAPI + Uvicorn
- **Banco de Dados**: PostgreSQL com pgvector
- **ORM**: SQLAlchemy
- **IA**: Google Gemini (agentes conversacionais) + Whisper (transcrição de áudio)
- **Autenticação**: JWT + bcrypt
- **Mensageria**: WhatsApp (whatsapp-web.js)

---

## 🏗️ Arquitetura

```
backend/
├── main.py                    # Aplicação FastAPI principal
├── sql/                       # Migrations SQL
│   ├── 000_reset_schema.sql
│   ├── 002_create_users.sql
│   ├── 007_add_auth_fields.sql
│   └── ...
├── src/
│   ├── agents/               # Agentes IA (Gemini)
│   │   ├── router.py        # Classificação de mensagens
│   │   ├── profiler.py      # Gerenciamento de usuários
│   │   ├── writer.py        # Geração de respostas
│   │   ├── analyst.py       # Análise de demandas
│   │   └── ...
│   ├── core/                # Configurações principais
│   │   ├── config.py        # Variáveis de ambiente
│   │   ├── database.py      # Conexão PostgreSQL
│   │   ├── gemini.py        # Cliente Gemini
│   │   └── state_manager.py # Gerenciamento de estado
│   ├── models/              # Modelos SQLAlchemy
│   │   ├── user.py
│   │   ├── verification_code.py
│   │   ├── demand.py
│   │   ├── interaction.py
│   │   ├── legislative_item.py
│   │   └── ...
│   ├── routes/              # Rotas API REST
│   │   ├── auth.py          # Autenticação
│   │   └── user.py          # Perfil de usuário
│   └── services/            # Lógica de negócio
│       ├── auth_service.py      # JWT, bcrypt, validações
│       ├── whatsapp_service.py  # Envio de mensagens
│       ├── demand_handler.py    # Gerenciamento de demandas
│       ├── onboarding_handler.py
│       └── ...
└── whatsapp-bot/            # Serviço Node.js (whatsapp-web.js)
    └── ...
```

---

## 📊 Modelos de Dados

### **User** (`src/models/user.py`)

Representa usuários do sistema (chatbot + web).

```python
class User:
    # Identificação
    id: UUID                          # Primary key
    phone: str                        # Telefone (11 dígitos) - UNIQUE
    
    # Autenticação Web (novos campos)
    name: str                         # Nome completo
    email: str                        # E-mail - UNIQUE
    cpf: str                          # CPF (11 dígitos) - UNIQUE
    password_hash: str                # Senha criptografada (bcrypt)
    is_verified: bool                 # Verificado via código WhatsApp
    
    # Localização
    uf: str                           # Estado (2 letras)
    city: str                         # Cidade
    address: str                      # Endereço
    number: str                       # Número do endereço
    location_primary: JSONB           # Localização do chatbot (legacy)
    
    # Perfil (novos campos)
    bio: str                          # Biografia (máximo 300 caracteres)
    avatar_url: str                   # URL da foto de perfil
    interests: List[str]              # Lista de interesses (ARRAY)
    
    # Metadata
    status: str                       # onboarding_incomplete, active, inactive
    first_contact_date: datetime
    created_at: datetime
    updated_at: datetime
    
    # Relacionamentos
    interactions: List[Interaction]
    demands: List[Demand]
    supported_demands: List[DemandSupporter]
```

**Status do Usuário:**
- `onboarding_incomplete`: Usuário iniciou conversa no chatbot mas não completou cadastro
- `active`: Usuário ativo (chatbot completo ou registro web verificado)
- `inactive`: Usuário desativado

### **VerificationCode** (`src/models/verification_code.py`)

Códigos de verificação temporários enviados por WhatsApp.

```python
class VerificationCode:
    id: int                           # Primary key (auto-increment)
    email: str                        # E-mail do usuário
    code: str                         # Código de 6 dígitos
    expires_at: datetime              # Expiração (10 minutos)
    created_at: datetime
```

### **Demand** (`src/models/demand.py`)

Demandas cívicas criadas pelos usuários.

```python
class Demand:
    id: UUID
    creator_id: UUID                  # FK -> User
    problem_description: str
    suggested_solution: str
    location: JSONB                   # {city, state, neighborhood, coordinates}
    category: str
    status: str                       # draft, published, blockchain_pending, on_blockchain
    blockchain_tx_hash: str           # Hash da transação na blockchain
    support_count: int
    created_at: datetime
    updated_at: datetime
    
    # Relacionamentos
    creator: User
    supporters: List[DemandSupporter]
```

### **Interaction** (`src/models/interaction.py`)

Histórico de interações do chatbot.

```python
class Interaction:
    id: UUID
    phone: str
    user_id: UUID                     # FK -> User (nullable)
    message_type: str                 # text, audio
    original_message: str             # Texto original (se text)
    transcription: str                # Transcrição (se audio)
    audio_duration_seconds: float
    classification: str               # ONBOARDING, DEMANDA, DUVIDA, OUTRO
    extracted_data: JSONB
    created_at: datetime
    
    # Relacionamento
    user: User
```

### **LegislativeItem** (`src/models/legislative_item.py`)

Itens legislativos (PLs, leis) para consulta com embeddings.

```python
class LegislativeItem:
    id: UUID
    title: str
    description: str
    full_text: str
    category: str
    uf: str
    city: str
    source_url: str
    embedding: Vector(1536)           # pgvector para busca semântica
    created_at: datetime
```

### Outros Modelos

- **ConversationState**: Estado da conversa multi-turno do chatbot
- **DemandSupporter**: Relacionamento many-to-many entre User e Demand (apoios)
- **PLInteraction**: Interações com itens legislativos

---

## 🔌 APIs REST

Base URL: `http://localhost:8000`

### 🔐 Autenticação (`/api/auth`)

#### **1. Login**

```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "usuario@example.com",
  "password": "senha123"
}
```

**Respostas:**

```json
// 200 OK
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "uuid-here",
    "name": "Nome do Usuário",
    "email": "usuario@example.com"
  }
}

// 401 Unauthorized
{
  "message": "Credenciais inválidas"
}
```

---

#### **2. Registro**

```http
POST /api/auth/register
Content-Type: application/json

{
  "name": "Nome Completo",
  "email": "usuario@example.com",
  "phone": "11999999999",
  "cpf": "12345678900",
  "password": "senha123",
  "uf": "SP",
  "city": "São Paulo",
  "address": "Rua Example, 123",
  "number": "123"
}
```

**Validações:**
- E-mail único e válido
- CPF único, 11 dígitos, válido
- Telefone 11 dígitos (DDD + número)
- Senha mínimo 6 caracteres
- UF 2 letras

**Respostas:**

```json
// 201 Created
{
  "message": "Código de verificação enviado para o WhatsApp",
  "email": "usuario@example.com"
}

// 400 Bad Request
{
  "message": "E-mail já cadastrado"
}
```

---

#### **3. Verificar Código**

```http
POST /api/auth/verify
Content-Type: application/json

{
  "email": "usuario@example.com",
  "code": "123456"
}
```

**Respostas:**

```json
// 200 OK (mesmo formato do login)
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "uuid-here",
    "name": "Nome do Usuário",
    "email": "usuario@example.com"
  }
}

// 400 Bad Request
{
  "message": "Código inválido ou expirado"
}
```

---

#### **4. Reenviar Código**

```http
POST /api/auth/resend-code
Content-Type: application/json

{
  "email": "usuario@example.com"
}
```

**Respostas:**

```json
// 200 OK
{
  "message": "Código reenviado com sucesso"
}

// 404 Not Found
{
  "message": "Usuário não encontrado"
}
```

---

### 👤 Usuário (`/api/user`)

**Autenticação obrigatória**: Header `Authorization: Bearer {token}`

#### **5. Obter Perfil**

```http
GET /api/user/profile
Authorization: Bearer {token}
```

**Respostas:**

```json
// 200 OK
{
  "id": "uuid-here",
  "name": "Nome do Usuário",
  "email": "usuario@example.com",
  "phone": "11999999999",
  "cpf": "12345678900",
  "uf": "SP",
  "city": "São Paulo",
  "address": "Rua Example, 123",
  "number": "123",
  "bio": "Minha biografia aqui",
  "avatar_url": "https://example.com/avatar.jpg",
  "interests": ["mobilidade", "educação", "saúde"],
  "stats": {
    "created": 5,      // Demandas criadas
    "supported": 12,   // Demandas apoiadas
    "active": 3,       // Demandas ativas (published/blockchain_pending)
    "completed": 2     // Demandas finalizadas (on_blockchain)
  },
  "activities": [
    {
      "id": "uuid-demand",
      "type": "demand_created",
      "text": "Criou demanda: Melhoria na iluminação",
      "time": "2024-01-15T10:30:00"
    }
  ],
  "demandsStatus": {
    "analysis": { "current": 2, "total": 5 },    // draft + published
    "waiting": { "current": 1, "total": 5 },    // blockchain_pending
    "completed": { "current": 2, "total": 5 }   // on_blockchain
  }
}

// 401 Unauthorized
{
  "message": "Token inválido ou expirado"
}
```

---

#### **6. Atualizar Perfil**

```http
PUT /api/user/profile
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Novo Nome",
  "phone": "11988888888",
  "address": "Nova Rua, 456",
  "number": "456",
  "uf": "SP",
  "city": "São Paulo",
  "bio": "Nova biografia aqui (máximo 300 caracteres)",
  "avatar_url": "https://example.com/new-avatar.jpg",
  "interests": ["mobilidade", "saúde pública"]
}
```

**Campos atualizáveis:** `name`, `phone`, `address`, `number`, `uf`, `city`, `bio` (max 300 chars), `avatar_url`, `interests` (todos opcionais)

**Respostas:**

```json
// 200 OK
{
  "message": "Perfil atualizado com sucesso",
  "user": {
    "id": "uuid-here",
    "name": "Novo Nome",
    "email": "usuario@example.com",
    "phone": "11988888888",
    "cpf": "12345678900",
    "uf": "SP",
    "city": "São Paulo",
    "address": "Nova Rua, 456",
    "number": "456",
    "bio": "Nova biografia",
    "avatar_url": "https://example.com/new-avatar.jpg",
    "interests": ["mobilidade", "saúde pública"],
    "stats": { /* ... */ },
    "activities": [ /* ... */ ],
    "demandsStatus": { /* ... */ }
  }
}

// 400 Bad Request
{
  "message": "Telefone já cadastrado por outro usuário"
}
// ou
{
  "message": "Bio deve ter no máximo 300 caracteres"
}
```

---

### 📋 Demandas (`/api/demands`)

#### **7. Listar Demandas**

```http
GET /api/demands?q=iluminação&city=São Paulo&category=mobilidade&status=published&page=1&pageSize=10
```

**Parâmetros de Query (todos opcionais):**
- `q`: Termo de busca (filtra por `problem_description` ou `location.city`)
- `city`: Filtrar por cidade
- `category`: Filtrar por categoria
- `status`: Filtrar por status (draft, published, blockchain_pending, on_blockchain)
- `page`: Página atual (padrão: 1)
- `pageSize`: Itens por página (padrão: 10, máximo: 100)

**Respostas:**

```json
// 200 OK
{
  "items": [
    {
      "id": "uuid-demand",
      "problem_description": "Falta de iluminação na praça",
      "suggested_solution": "Instalar postes de luz",
      "location": {
        "city": "São Paulo",
        "state": "SP",
        "neighborhood": "Vila Madalena"
      },
      "category": "mobilidade",
      "status": "published",
      "support_count": 25,
      "created_at": "2024-01-10T08:30:00",
      "creator": {
        "id": "uuid-user",
        "name": "João Silva",
        "avatar_url": "https://example.com/avatar.jpg"
      }
    }
  ],
  "page": 1,
  "pageSize": 10,
  "total": 45
}
```

---

#### **8. Obter Detalhe de Demanda**

```http
GET /api/demands/{demand_id}
Authorization: Bearer {token}  # Opcional (para verificar supportedByUser)
```

**Respostas:**

```json
// 200 OK
{
  "id": "uuid-demand",
  "problem_description": "Falta de iluminação na praça",
  "suggested_solution": "Instalar postes de luz",
  "location": {
    "city": "São Paulo",
    "state": "SP",
    "neighborhood": "Vila Madalena",
    "coordinates": { "lat": -23.5505, "lng": -46.6333 }
  },
  "category": "mobilidade",
  "status": "on_blockchain",
  "support_count": 125,
  "blockchain_tx_hash": "0x123abc...",
  "created_at": "2024-01-10T08:30:00",
  "creator": {
    "id": "uuid-user",
    "name": "João Silva",
    "avatar_url": "https://example.com/avatar.jpg"
  },
  "timeline": [
    {
      "stage": "created",
      "label": "Demanda Criada",
      "date": "2024-01-10T08:30:00",
      "completed": true
    },
    {
      "stage": "published",
      "label": "Publicada",
      "date": "2024-01-10T09:00:00",
      "completed": true
    },
    {
      "stage": "community_report",
      "label": "10 Apoios",
      "date": "2024-01-12T14:20:00",
      "completed": true
    },
    {
      "stage": "blockchain",
      "label": "Na Blockchain",
      "date": "2024-01-15T16:45:00",
      "completed": true
    }
  ],
  "communityReport": {
    "totalSupports": 125,
    "supportThreshold": 10,
    "message": "Esta demanda alcançou 125 apoios da comunidade!"
  },
  "relatedBills": [],
  "supportedByUser": true
}

// 404 Not Found
{
  "message": "Demanda não encontrada"
}
```

**Observações:**
- `communityReport` só aparece quando `support_count >= 10`
- `supportedByUser` é `true` se o usuário autenticado apoiou a demanda
- `timeline` mostra as etapas concluídas da demanda

---

#### **9. Apoiar Demanda**

```http
POST /api/demands/{demand_id}/support
Authorization: Bearer {token}
```

**Respostas:**

```json
// 200 OK
{
  "success": true,
  "message": "Apoio registrado com sucesso",
  "new_support_count": 26
}

// 400 Bad Request
{
  "message": "Você já apoia esta demanda"
}

// 404 Not Found
{
  "message": "Demanda não encontrada"
}

// 401 Unauthorized
{
  "message": "Token inválido ou expirado"
}
```

---

### 💬 Chatbot (`/webhook`)

Endpoint para integração com WhatsApp (usado pelo whatsapp-bot).

```http
POST /webhook
Content-Type: application/json  # ou multipart/form-data para áudio

# Texto
{
  "from": "5511999999999",
  "body": "Olá, gostaria de fazer uma denúncia",
  "message_type": "text"
}

# Áudio
multipart/form-data:
  - audio_file: File
  - from: "5511999999999"
```

---

## 🔒 Autenticação

### JWT (JSON Web Tokens)

**Geração:**
- Algoritmo: HS256
- Expiração: 7 dias (configurável via `JWT_EXPIRES_IN`)
- Payload: `user_id`, `email`, `exp`, `iat`

**Validação:**
- Header: `Authorization: Bearer {token}`
- Verificação de assinatura e expiração
- Extração de `user_id` para identificação

**Código:**
```python
# src/services/auth_service.py
token = AuthService.create_jwt_token(user_id, email)
payload = AuthService.verify_jwt_token(token)
```

### Senhas

**Hash:** bcrypt com salt automático
```python
password_hash = AuthService.hash_password("senha123")
is_valid = AuthService.verify_password("senha123", password_hash)
```

### Verificação de Conta

**Fluxo:**
1. Usuário se registra (`POST /api/auth/register`)
2. Sistema gera código de 6 dígitos
3. Código enviado via WhatsApp (válido por 10 minutos)
4. Usuário verifica (`POST /api/auth/verify`)
5. Conta ativada (`is_verified = true`)

---

## 🛠️ Serviços

### **AuthService** (`src/services/auth_service.py`)

Gerenciamento de autenticação e validações.

**Métodos:**
- `hash_password(password)`: Hash bcrypt
- `verify_password(plain, hashed)`: Verifica senha
- `create_jwt_token(user_id, email)`: Gera JWT
- `verify_jwt_token(token)`: Valida JWT
- `generate_verification_code()`: Código de 6 dígitos
- `create_verification_code(email, db)`: Cria e armazena código
- `verify_code(email, code, db)`: Valida código
- `validate_email(email)`: Valida formato de e-mail
- `validate_cpf(cpf)`: Valida CPF
- `validate_phone(phone)`: Valida telefone (11 dígitos)
- `validate_password(password)`: Valida senha (mínimo 6 caracteres)

---

### **WhatsAppService** (`src/services/whatsapp_service.py`)

Comunicação com serviço whatsapp-bot (Node.js).

**Métodos:**
- `send_verification_code(phone, code)`: Envia código via WhatsApp
- `check_whatsapp_connection()`: Verifica se bot está conectado

**Integração:**
```python
result = await WhatsAppService.send_verification_code("11999999999", "123456")
# result = {"success": True} ou {"success": False, "error": "..."}
```

**Requisitos:**
- Serviço whatsapp-bot rodando em `http://localhost:3000`
- Endpoint `/send-message` implementado
- WhatsApp autenticado via QR code

---

### **DemandInvestigationHandler** (`src/services/demand_investigation_handler.py`)

**NOVO:** Sistema de investigação contextualizada de demandas (seção 2.3 do `docs/fluxos.md`).

**Objetivo:**
Antes de apresentar opções ao usuário, o bot faz uma **investigação completa** buscando:
1. 📚 PLs/Leis relacionados (APIs legislativas)
2. 🏛️ Programas governamentais existentes
3. 👥 Demandas comunitárias similares (busca vetorial com pgvector)

**Fluxo:**
```
Usuário relata problema
    ↓
Sistema executa busca paralela (async)
    ↓
Identifica cenário (matriz de decisão 2x2)
    ↓
Apresenta contexto + opções personalizadas
```

**4 Cenários da Matriz de Decisão:**

| Cenário | PLs/Leis | Demandas Similares | Ação |
|---------|----------|-------------------|------|
| **1** | ❌ Não | ❌ Não | Usuário é protagonista: criar demanda OU criar ideia legislativa |
| **2** | ❌ Não | ✅ Sim | Apoiar demanda existente OU criar ideia legislativa |
| **3** | ✅ Sim | ❌ Não | Apoiar/comentar PL OU criar demanda local OU criar outra ideia |
| **4** | ✅ Sim | ✅ Sim | Apoiar demanda OU apoiar PL OU criar outra ideia |

**Exemplo de resposta (Cenário 2):**
```
🔍 Investigação completa:

Analisei sua solicitação e encontrei:
❌ Nenhum projeto de lei sobre esse tema ainda
✅ Outras pessoas com o mesmo problema!

━━━━━━━━━━━━━━━━
📌 Demanda existente:

*Iluminação precária na Praça XV*
👥 15 pessoas apoiando
📅 Criado há 3 dias
🏷️ Tema: mobilidade

💡 Por que apoiar?
• Sua voz se junta com outras 15 pessoas
• Quanto mais apoios, mais força para pressionar
• Com 20 apoios, fazemos denúncia institucional automática

━━━━━━━━━━━━━━━━
O que você gostaria de fazer?

1️⃣ Apoiar a demanda existente
   → Juntar sua voz e fortalecer a causa

2️⃣ Criar ideia legislativa
   → Se você acha que precisa de uma lei sobre isso

3️⃣ Cancelar

Digite o número da opção:
```

**Métodos principais:**
- `investigate_and_present_options()`: Orquestra todo o fluxo
- `_search_similar_demands()`: Busca vetorial com embeddings
- `_scenario_1_no_pl_no_demand()`: Gera resposta cenário 1
- `_scenario_2_no_pl_has_demand()`: Gera resposta cenário 2
- `_scenario_3_has_pl_no_demand()`: Gera resposta cenário 3
- `_scenario_4_has_pl_has_demand()`: Gera resposta cenário 4

**Integração:**
```python
# main.py - quando detecta DEMANDA
from src.services.demand_investigation_handler import investigation_handler

response_text = await investigation_handler.investigate_and_present_options(
    user_text=text,
    classification_result=classification_result,
    user_location=user.location_primary,
    db=db
)
```

---

### **LegislativeSearchService** (`src/services/legislative_search_service.py`)

**NOVO:** Busca em APIs legislativas oficiais.

**Fontes de dados:**
- 📚 **Câmara dos Deputados**: API Dados Abertos (`dadosabertos.camara.leg.br`)
- 📜 **Senado Federal**: API LegisWS (futuro)
- 🏛️ **Portal da Transparência**: Programas governamentais (futuro)
- 📰 **Querido Diário**: Atos municipais (futuro)

**Métodos principais:**

1. **`search_related_propositions(theme, keywords, max_results)`**
   - Busca PLs relacionados ao tema
   - Retorna: `{'found': bool, 'pls': [], 'total_count': int}`
   - Exemplo:
   ```python
   result = await legislative_service.search_related_propositions(
       theme='transporte',
       keywords=['ônibus', 'linha', 'atraso'],
       max_results=5
   )
   # {'found': True, 'pls': [{'id': 123, 'full_name': 'PL 1234/2024', ...}], 'total_count': 3}
   ```

2. **`get_proposition_details(pl_id, source)`**
   - Busca detalhes completos de um PL específico
   - Retorna: ementa, justificativa, autores, status de tramitação, última atualização
   - Exemplo:
   ```python
   pl = await legislative_service.get_proposition_details('2345678', 'camara')
   # {'id': '2345678', 'full_name': 'PL 1234/2024', 'ementa': '...', 'autores': ['Dep. X'], ...}
   ```

3. **`search_government_programs(theme, location)`**
   - Busca programas governamentais (placeholder - implementação futura)
   - Retorna: `{'found': bool, 'programs': [], 'total_count': int}`

**API da Câmara:**
- Base URL: `https://dadosabertos.camara.leg.br/api/v2`
- Endpoints:
  - `/proposicoes` - Busca de proposições
  - `/proposicoes/{id}` - Detalhes de proposição
  - `/proposicoes/{id}/autores` - Autores
  - `/proposicoes/{id}/tramitacoes` - Tramitação
- Timeout: 10 segundos
- Ordenação: Por ID DESC (mais recentes primeiro)

**Exemplo de uso:**
```python
from src.services.legislative_search_service import legislative_service

# Buscar PLs sobre saúde
pls = await legislative_service.search_related_propositions(
    theme='saude',
    keywords=['sus', 'hospital', 'atendimento'],
    max_results=5
)

if pls['found']:
    for pl in pls['pls']:
        print(f"{pl['full_name']}: {pl['ementa']}")
```

---

### **LawSearchService** (`src/services/law_search_service.py`)

**NOVO:** Busca de **leis vigentes** (não PLs) usando Google Gemini com prompt engineering avançado.

**Objetivo:**
Antes de sugerir criar demanda ou ideia legislativa, verificar se **já existe uma lei** que garante o direito do cidadão. Evita trabalho desnecessário e **educa sobre direitos existentes**.

**Exemplo:**
```
Problema: "Cinema não deixou eu entrar com lanche"
Sistema: "Seu direito JÁ É GARANTIDO! CDC Art. 39, inciso IX..."
```

**Técnicas de Prompt Engineering utilizadas:**

1. **Chain of Thought (CoT)**: Guia o LLM por etapas de raciocínio
   ```
   1. Análise do problema
   2. Busca na base de conhecimento
   3. Critério de relevância
   4. Formato estruturado
   ```

2. **Few-Shot Learning**: Fornece exemplos de respostas corretas
   ```python
   # Exemplo 1: Cinema e lanche (CDC)
   # Exemplo 2: Taxa de serviço (CDC)
   # Exemplo 3: Falta de médico (Constituição)
   ```

3. **Role Prompting**: Define papel específico
   ```
   "Você é um assistente jurídico especializado..."
   ```

4. **Structured Output**: Força resposta em JSON
   ```json
   {
     "found": true,
     "laws": [{
       "name": "Código de Defesa do Consumidor",
       "article": "Art. 39, IX",
       "simple_explanation": "...",
       "how_to_use": "...",
       "where_to_complain": "..."
     }]
   }
   ```

**Fontes de conhecimento do Gemini:**
- 📜 Constituição Federal (1988)
- 🛒 Código de Defesa do Consumidor (Lei 8.078/1990)
- 📋 Código Civil (Lei 10.406/2002)
- 👶 Estatuto da Criança e Adolescente (ECA)
- 👴 Estatuto do Idoso
- ♿ Lei de Acessibilidade (LBI)
- 🏛️ Leis estaduais e municipais (quando relevante)

**Método principal:**

```python
from src.services.law_search_service import law_search_service

# Buscar leis vigentes
result = await law_search_service.search_existing_laws(
    user_problem="Cinema não deixou eu entrar com lanche próprio",
    theme="consumidor",
    location={'city': 'São Paulo', 'state': 'SP'}
)

# Retorno:
{
  'found': True,
  'laws': [
    {
      'name': 'Código de Defesa do Consumidor (Lei 8.078/1990)',
      'article': 'Art. 39, inciso IX',
      'scope': 'federal',
      'simple_explanation': 'A lei proíbe que estabelecimentos comerciais OBRIGUEM você a comprar produtos deles...',
      'how_to_use': 'Você pode exigir sua entrada mesmo com lanche próprio. Peça o nome do responsável...',
      'where_to_complain': 'Procon, Reclame Aqui, ou Juizado Especial Cível'
    }
  ]
}
```

**Configurações Gemini:**
- Model: `gemini-2.0-flash-lite` (modelo leve e rápido)
- Temperature: `0.2` (baixa para respostas determinísticas)
- Top-p: `0.8`
- Top-k: `40`
- Max tokens: `2048`
- Retry: 2 tentativas com backoff exponencial

**Feedback ao usuário:**
Antes de iniciar a investigação, o sistema envia mensagem de aguarde:
```
🔍 Aguarde um momento...
Estou pesquisando leis, projetos e demandas relacionadas ao seu problema.
```

**Fallback local:**
Se o Gemini falhar (quota excedida, timeout, etc.), o sistema usa uma **base de conhecimento local** com os casos mais comuns:
- Cinema + lanche → CDC Art. 39, IX
- Taxa de serviço → CDC Art. 39, I
- Falta de médico UBS → CF Art. 196

**Importante:** Se não encontrar lei vigente, o sistema **NÃO informa ao usuário** que "não existe lei". Em vez disso, continua a busca por PLs e demandas comunitárias.

**Validação de resposta:**
- Parse JSON robusto (remove markdown code blocks)
- Validação de campos obrigatórios
- Fallback para `{'found': false}` em caso de erro

**Benefícios:**
✅ **Educação cívica**: Cidadão aprende seus direitos  
✅ **Economia de tempo**: Não cria demanda desnecessária  
✅ **Ação imediata**: Sabe onde/como reclamar  
✅ **Empoderamento**: "Você JÁ TEM esse direito!"  

---

### **SimilarityService** (`src/services/similarity_service.py`)

Busca demandas similares usando **busca vetorial** (pgvector).

**Algoritmo:**
1. Gera embedding do texto do usuário (768 dimensões - Gemini)
2. Busca no banco por similaridade cosseno (`<=>` operator)
3. Filtra por:
   - `theme` (mesmo tema)
   - `scope_level` (mesmo nível de escopo)
   - `status = 'active'`
   - Similaridade >= threshold (padrão: 0.80)
4. Para Nível 1 (hiper-local): aplica filtro geográfico adicional (raio de 2km)

**Métodos:**
- `find_similar_demands(embedding, theme, scope_level, user_location, db, similarity_threshold, max_results)`
- `_is_geographically_close(demand_location, user_location, max_distance_km)` - Fórmula de Haversine

**Exemplo:**
```python
from src.services.similarity_service import SimilarityService
from src.services.embedding_service import EmbeddingService

similarity_service = SimilarityService()
embedding_service = EmbeddingService()

# Gerar embedding
text = "Buraco na rua causando acidentes"
embedding = await embedding_service.generate_embedding(text)

# Buscar similares
similar = await similarity_service.find_similar_demands(
    embedding=embedding,
    theme='mobilidade',
    scope_level=1,  # hiper-local
    user_location={'coordinates': [-23.5505, -46.6333]},
    db=db,
    similarity_threshold=0.75,
    max_results=3
)

# [{'id': 'uuid', 'title': '...', 'similarity': 0.87, 'supporters_count': 15, ...}]
```

---

### **EmbeddingService** (`src/services/embedding_service.py`)

Gera embeddings usando **Google Gemini** (`text-embedding-004`).

**Métodos:**
- `generate_embedding(text)`: Retorna vetor de 768 dimensões
- `prepare_text_for_embedding(title, description, theme)`: Combina campos para embedding mais rico

**Exemplo:**
```python
from src.services.embedding_service import EmbeddingService

service = EmbeddingService()

# Gerar embedding
text = "Iluminação precária causando insegurança"
embedding = await service.generate_embedding(text)
# [0.123, -0.456, 0.789, ...] (768 valores)

# Embedding enriquecido
combined = service.prepare_text_for_embedding(
    title="Iluminação na Praça XV",
    description="Falta de postes de luz causando insegurança à noite",
    theme="segurança"
)
embedding = await service.generate_embedding(combined)
```

**Configuração:**
- Model: `models/text-embedding-004`
- Dimensões: 768
- Task type: `retrieval_document`
- Limite de texto: 2000 caracteres (truncado automaticamente)

---

### **Agentes IA** (`src/agents/`)

Sistema multi-agente com Google Gemini:

- **RouterAgent**: Classifica mensagens (ONBOARDING, DEMANDA, DUVIDA, OUTRO)
- **ProfilerAgent**: Gerencia perfil de usuário
- **WriterAgent**: Gera respostas conversacionais
- **AnalystAgent**: Analisa similaridade de demandas
- **DetectiveAgent**: Busca informações legislativas
- **ValidatorAgent**: Valida completude de dados

---

## ⚙️ Configuração

### Variáveis de Ambiente (`.env`)

```env
# Servidor
API_HOST=0.0.0.0
API_PORT=8000

# Banco de Dados
DATABASE_URL=postgresql://user:password@localhost:5432/coral

# IA
GOOGLE_GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL_FLASH=gemini-2.0-flash-lite
WHISPER_MODEL=base
WHISPER_DEVICE=cpu

# Autenticação
JWT_SECRET=seu_secret_key_aqui_min_32_chars
JWT_EXPIRES_IN=7d
JWT_ALGORITHM=HS256

# WhatsApp (opcional para desenvolvimento)
WHATSAPP_BOT_URL=http://localhost:3000
SKIP_WHATSAPP_IN_DEV=true
```

### CORS

Configurado para aceitar requisições de:
- `http://localhost:5173` (Vite)
- `http://localhost:3000` (alternativo)
- `http://127.0.0.1:5173`
- `http://127.0.0.1:3000`

**Código:** `main.py` - `CORSMiddleware`

---

## 📦 Instalação

### 1. Pré-requisitos

- Python 3.11+
- PostgreSQL 14+
- Node.js 18+ (para whatsapp-bot)

### 2. Instalar Dependências

```bash
# Backend Python
pip install -r requirements.txt

# WhatsApp Bot (Node.js)
cd whatsapp-bot
npm install
```

### 3. Configurar Banco de Dados

```bash
# Criar database
createdb coral

# Executar migrations em ordem
psql -d coral -f sql/000_reset_schema.sql
psql -d coral -f sql/002_create_users.sql
psql -d coral -f sql/003_create_conversation_states.sql
psql -d coral -f sql/004_create_demands.sql
psql -d coral -f sql/005_add_pgvector.sql
psql -d coral -f sql/006_create_legislative_items.sql
psql -d coral -f sql/007_add_auth_fields.sql

# Ou usar script PowerShell
.\db.ps1
```

### 4. Configurar `.env`

```bash
cp .env.example .env
# Editar .env com suas credenciais
```

### 5. Iniciar Serviços

```bash
# Backend FastAPI
python main.py

# WhatsApp Bot (em outro terminal)
cd whatsapp-bot
node index.js
# Escanear QR code na primeira execução
```

### 6. Testar

```bash
# Health check
curl http://localhost:8000/health

# Documentação interativa
# Acesse: http://localhost:8000/docs
```

---

## 📚 Dependências Principais

```
fastapi                 # Framework web
uvicorn[standard]       # ASGI server
sqlalchemy             # ORM
psycopg2-binary        # PostgreSQL driver
pydantic               # Validação de dados
pyjwt                  # JWT tokens
bcrypt                 # Hash de senhas
httpx                  # Cliente HTTP async
google-generativeai    # Google Gemini
faster-whisper         # Transcrição de áudio
pgvector               # Busca vetorial
python-multipart       # Upload de arquivos
pydub                  # Processamento de áudio
geopy                  # Geocodificação
```

---

## 📄 Migrations SQL

| Arquivo | Descrição |
|---------|-----------||
| `000_reset_schema.sql` | Reset completo do schema |
| `002_create_users.sql` | Criação da tabela users |
| `003_create_conversation_states.sql` | Estados de conversa |
| `004_create_demands.sql` | Tabela de demandas |
| `005_add_pgvector.sql` | Extensão pgvector |
| `006_create_legislative_items.sql` | Itens legislativos |
| `007_add_auth_fields.sql` | Campos de autenticação (email, cpf, password, uf, city) |
| `008_add_profile_fields.sql` | **NOVO** - Campos de perfil (bio, avatar_url, interests) |

---

## 🔄 Fluxo de Autenticação Web

```mermaid
sequenceDiagram
    participant Frontend
    participant Backend
    participant Database
    participant WhatsApp

    Frontend->>Backend: POST /api/auth/register
    Backend->>Database: Verificar email/cpf únicos
    Backend->>Database: Criar usuário (is_verified=false)
    Backend->>Database: Gerar código (6 dígitos)
    Backend->>WhatsApp: Enviar código via WhatsApp
    Backend->>Frontend: 201 Created

    Frontend->>Backend: POST /api/auth/verify
    Backend->>Database: Validar código + prazo
    Backend->>Database: Atualizar is_verified=true
    Backend->>Frontend: 200 OK + JWT token

    Frontend->>Backend: GET /api/user/profile (Header: Bearer token)
    Backend->>Backend: Validar JWT
    Backend->>Database: Buscar usuário
    Backend->>Frontend: 200 OK + dados do perfil
```

---

## 🚀 Próximos Passos

1. **Implementar whatsapp-bot em Node.js**
   - Endpoint `/send-message` para envio de códigos
   - Endpoint `/status` para health check

2. **Testes**
   - Testes unitários para AuthService
   - Testes de integração para APIs REST
   - Testes E2E do fluxo de autenticação

3. **Melhorias**
   - Rate limiting para envio de códigos
   - Logs estruturados (logging)
   - Monitoramento (Sentry, Prometheus)
   - Cache (Redis) para tokens e códigos

4. **Produção**
   - Docker Compose com todos os serviços
   - CI/CD (GitHub Actions)
   - Secrets management (AWS Secrets Manager)
   - Backup automático do banco de dados

---

## 🔍 Fluxo de Investigação de Demandas (NOVO)

### Visão Geral

Quando um usuário **ativo** (já cadastrado) relata um problema, o sistema não apresenta opções imediatamente. Em vez disso, executa uma **investigação contextualizada** para informar melhor a decisão do usuário.

### Arquitetura do Fluxo

```
┌─────────────────────────────────────────┐
│ Usuário: "Ônibus da linha 40 sempre    │
│          atrasado e lotado"             │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ RouterAgent: Classifica como DEMANDA   │
│ Extrai: theme=transporte,               │
│         keywords=[ônibus, linha, 40]    │
│         scope_level=2 (regional)        │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ DemandInvestigationHandler              │
│ investigate_and_present_options()       │
└────────────────┬────────────────────────┘
                 │
        ┌────────┴────────┐
        │ Busca Paralela  │
        │   (asyncio)     │
        └────────┬────────┘
                 │
    ┌────────────┼────────────┐
    ▼            ▼            ▼
┌────────┐  ┌────────┐  ┌────────┐
│ PLs    │  │Program.│  │Demandas│
│Câmara/ │  │Portal  │  │Similares│
│Senado  │  │Transp. │  │pgvector│
└───┬────┘  └───┬────┘  └───┬────┘
    │           │           │
    └───────────┼───────────┘
                ▼
    ┌──────────────────────┐
    │ Matriz de Decisão    │
    │ (4 cenários)         │
    └──────────┬───────────┘
               ▼
    ┌──────────────────────┐
    │ Mensagem             │
    │ Contextualizada      │
    │ + Opções             │
    └──────────────────────┘
```

### Investigação Paralela (async)

O sistema executa buscas em **ordem de prioridade**:

#### PRIORIDADE 1: Leis Vigentes (`LawSearchService`)
```python
# Busca com Gemini (prompt engineering avançado)
existing_laws = await law_search_service.search_existing_laws(
    user_problem="Cinema não deixou entrar com lanche",
    theme="consumidor",
    location={'city': 'São Paulo', 'state': 'SP'}
)

# Se encontrar, retorna IMEDIATAMENTE (não precisa buscar PLs)
if existing_laws['found']:
    return "🎯 Seu direito JÁ É GARANTIDO! CDC Art. 39, IX..."
```

#### PRIORIDADE 2: PLs, Programas e Demandas (paralelo)

Só executa se **não encontrou lei vigente**:

**1. Busca de PLs/Leis em tramitação (`LegislativeSearchService`)**
```python
# API Câmara dos Deputados
GET /api/v2/proposicoes?keywords=transporte+ônibus+linha

# Retorna:
{
  'found': True,
  'pls': [
    {
      'id': '2345678',
      'full_name': 'PL 1234/2024',
      'ementa': 'Dispõe sobre melhoria do transporte público...',
      'url': 'https://...'
    }
  ],
  'total_count': 2
}
```

#### 2. Busca de Programas Governamentais
```python
# Futuro: Portal da Transparência, Querido Diário
# Atualmente retorna: {'found': False, 'programs': []}
```

#### 3. Busca de Demandas Similares (`SimilarityService`)
```python
# Gera embedding do texto
embedding = await embedding_service.generate_embedding(text)

# Busca vetorial no PostgreSQL (pgvector)
SELECT id, title, description, 
       1 - (embedding <=> [0.123, -0.456, ...]) as similarity
FROM demands
WHERE theme = 'transporte'
  AND scope_level = 2
  AND status = 'active'
  AND 1 - (embedding <=> [0.123, -0.456, ...]) >= 0.75
ORDER BY similarity DESC
LIMIT 3;

# Retorna:
[
  {
    'id': 'uuid-123',
    'title': 'Linha 40 com atrasos constantes',
    'description': '...',
    'supporters_count': 18,
    'similarity': 0.89,
    'created_at': '2024-11-28T10:30:00'
  }
]
```

### Matriz de Decisão (5 Cenários)

| Cenário | Lei Vigente | PLs | Demandas | Mensagem | Opções |
|---------|-------------|-----|----------|----------|--------|
| **0** (NOVO) | ✅ | - | - | "Seu direito JÁ É GARANTIDO!" | 1️⃣ Criar demanda (mobilizar)<br>2️⃣ Orientação completa<br>3️⃣ Nada |
| **1** | ❌ | ❌ | ❌ | "Você pode ser o primeiro!" | 1️⃣ Criar demanda<br>2️⃣ Criar ideia legislativa<br>3️⃣ Cancelar |
| **2** | ❌ | ❌ | ✅ | "15 pessoas já reportaram!" | 1️⃣ Apoiar demanda<br>2️⃣ Criar ideia legislativa<br>3️⃣ Cancelar |
| **3** | ❌ | ✅ | ❌ | "Encontrei PL relacionado!" | 1️⃣ Apoiar/comentar PL<br>2️⃣ Criar demanda local<br>3️⃣ Criar ideia<br>4️⃣ Cancelar |
| **4** | ❌ | ✅ | ✅ | "Encontrei PL + demanda!" | 1️⃣ Apoiar demanda<br>2️⃣ Apoiar PL<br>3️⃣ Criar ideia<br>4️⃣ Cancelar |

### Exemplo Completo (Cenário 0 - Lei Vigente)

**Input do usuário:**
```
"Cinema não deixou eu entrar com lanche, mas eles vendem comida lá dentro"
```

**Classificação (RouterAgent):**
```json
{
  "classification": "DEMANDA",
  "theme": "consumidor",
  "keywords": ["cinema", "lanche", "comida", "entrada"],
  "scope_level": 3,
  "urgency": "media"
}
```

**Busca de lei vigente (LawSearchService + Gemini):**
```python
existing_laws = {
  'found': True,
  'laws': [{
    'name': 'Código de Defesa do Consumidor (Lei 8.078/1990)',
    'article': 'Art. 39, inciso IX',
    'scope': 'federal',
    'simple_explanation': 'A lei proíbe que estabelecimentos comerciais OBRIGUEM você a comprar produtos deles como condição para usar o serviço. O cinema não pode te forçar a comprar a pipoca deles para assistir o filme. Você tem o direito de levar seu próprio lanche.',
    'how_to_use': 'Você pode exigir sua entrada mesmo com lanche próprio. Se negarem, peça o nome do responsável e registre uma reclamação no Procon. Tire foto/vídeo se possível.',
    'where_to_complain': 'Procon, Reclame Aqui, ou Juizado Especial Cível'
  }]
}
```

**Mensagem gerada (Cenário 0):**
```
🎯 *Ótima notícia! Seu direito JÁ É GARANTIDO POR LEI!*

Encontrei uma lei que protege você:

━━━━━━━━━━━━━━━━
📜 *Código de Defesa do Consumidor (Lei 8.078/1990)*
📋 Art. 39, inciso IX

💡 *O que a lei diz (em português claro):*
A lei proíbe que estabelecimentos comerciais OBRIGUEM você a comprar 
produtos deles como condição para usar o serviço. O cinema não pode te 
forçar a comprar a pipoca deles para assistir o filme. Você tem o direito 
de levar seu próprio lanche.

━━━━━━━━━━━━━━━━
✅ *Como USAR esse direito na prática:*
Você pode exigir sua entrada mesmo com lanche próprio. Se negarem, peça 
o nome do responsável e registre uma reclamação no Procon. Tire foto/vídeo 
se possível.

━━━━━━━━━━━━━━━━
📢 *Onde denunciar/reclamar:*
Procon, Reclame Aqui, ou Juizado Especial Cível

💪 *Você quer fazer algo?*

1️⃣ *Criar demanda comunitária*
   → Mobilizar outras pessoas com o mesmo problema
   → Pressionar estabelecimentos a cumprirem a lei

2️⃣ *Orientação completa*
   → Ver passo a passo detalhado de como agir
   → Modelos de reclamação

3️⃣ *Nada por enquanto*
   → Já entendi meus direitos

Digite o número da opção:
```

---

### Exemplo Completo (Cenário 4 - PL + Demanda)

**Input do usuário:**
```
"Ônibus da linha 40 sempre lotado e atrasado, trabalho fica longe"
```

**Classificação (RouterAgent):**
```json
{
  "classification": "DEMANDA",
  "theme": "transporte",
  "keywords": ["ônibus", "linha 40", "lotado", "atraso"],
  "scope_level": 2,
  "urgency": "media",
  "affected_entity": "linha 40"
}
```

**Resultados da investigação:**
```python
# PLs encontrados
pls_result = {
  'found': True,
  'pls': [{
    'id': '2345678',
    'full_name': 'PL 5678/2024',
    'ementa': 'Melhoria da qualidade do transporte público municipal'
  }],
  'total_count': 1
}

# Demandas similares
similar_demands = [{
  'id': 'uuid-abc',
  'title': 'Linha 40 com atrasos frequentes',
  'supporters_count': 18,
  'created_at': datetime(2024, 11, 25),
  'theme': 'transporte',
  'similarity': 0.89
}]
```

**Mensagem gerada (Cenário 4):**
```
🔍 *Investigação completa:*

Analisei sua solicitação e encontrei *informações importantes!*

━━━━━━━━━━━━━━━━
📚 *PROJETO DE LEI RELACIONADO:*

*PL 5678/2024*
Melhoria da qualidade do transporte público municipal...

━━━━━━━━━━━━━━━━
📌 *DEMANDA COMUNITÁRIA EXISTENTE:*

*Linha 40 com atrasos frequentes*
👥 18 pessoas apoiando
📅 Criado há 7 dias

💡 *Você tem 2 caminhos:*
• Apoiar a mobilização local (demanda comunitária)
• Participar do processo legislativo (comentar no PL)

━━━━━━━━━━━━━━━━
*O que você gostaria de fazer?*

1️⃣ *Apoiar a demanda comunitária*
   → Juntar sua voz com outras 18 pessoas
   → Pressão local e mobilização

2️⃣ *Apoiar/comentar no PL*
   → Participar oficialmente do processo legislativo
   → Influenciar a lei que está sendo criada

3️⃣ *Criar outra ideia legislativa*
   → Se você acha que o PL não resolve bem

4️⃣ *Cancelar*

Digite o número da opção:
```

### Código de Integração

```python
# main.py
from src.services.demand_investigation_handler import investigation_handler

# Quando detecta DEMANDA
if classification == 'DEMANDA':
    logger.info(f"User mentioned a problem: {user.id}")
    
    # Executa investigação completa
    response_text = await investigation_handler.investigate_and_present_options(
        user_text=text,
        classification_result=classification_result,
        user_location=user.location_primary,
        db=db
    )
    
    # Salva contexto para processar resposta do usuário
    state_manager = ConversationStateManager()
    state_manager.set_state(
        phone, 
        'choosing_help_type', 
        {'original_text': text}, 
        db
    )
```

### Performance

**Tempo de resposta típico:**

**Cenário 0 (Lei Vigente - FAST PATH):**
- Busca com Gemini: ~800ms
- **Total**: ~1s (retorno imediato, não busca PLs/demandas)

**Outros Cenários (busca completa):**
- Busca de leis vigentes (Gemini): ~800ms (não encontrou)
- Busca de PLs (Câmara API): ~500ms
- Busca de programas: ~100ms (placeholder)
- Busca vetorial (pgvector): ~50ms
- **Total (paralelo)**: ~1.3s

**Otimizações:**
- `asyncio.gather()` para buscas paralelas (PLs + programas + demandas)
- Early return quando encontra lei vigente
- Timeout de 10s nas APIs externas
- Cache de resultados (futuro)
- Índice GIN no campo `embedding` (pgvector)

### Benefícios

✅ **Educação sobre direitos existentes**: Usuário aprende leis que já o protegem  
✅ **Ação imediata**: Sabe exatamente onde/como reclamar  
✅ **Contexto completo**: Usuário vê o panorama antes de decidir  
✅ **Educação cívica**: Explica o que significa cada opção  
✅ **Reduz duplicação**: Incentiva apoio a demandas existentes  
✅ **Engajamento legislativo**: Conecta com PLs em tramitação  
✅ **Protagonismo informado**: Quando não há nada, usuário pode criar  
✅ **Empoderamento**: "Você JÁ TEM esse direito!" (quando aplicável)  

---

## 📞 Suporte

Para dúvidas ou problemas:
1. Verifique os logs: `logs/app.log`
2. Consulte a documentação interativa: `http://localhost:8000/docs`
3. Revise as variáveis de ambiente no `.env`

---

**Última atualização**: Dezembro 2025
**Versão**: 1.0.0
