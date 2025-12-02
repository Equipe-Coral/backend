# Coral WhatsApp Bot

## Descrição

Bot de WhatsApp implementado com `whatsapp-web.js` para o projeto Coral.
Atua como interface entre o WhatsApp e o Backend FastAPI, com API REST para envio programático de mensagens.

## Pré-requisitos

- Node.js 18+
- NPM

## Instalação

```bash
npm install
```

## Configuração

Copie o arquivo `.env.example` para `.env` e ajuste as variáveis se necessário:

```bash
cp .env.example .env
```

Variáveis disponíveis:
- `BACKEND_URL`: URL do backend FastAPI (padrão: `http://localhost:8000`)
- `PORT`: Porta do servidor Express (padrão: `3000`)
- `ALLOWED_NUMBER`: Números permitidos separados por vírgula (opcional)

## Execução

```bash
npm start
```

Para desenvolvimento (com restart automático):

```bash
npm run dev
```

## Funcionalidades

- **Chatbot**: Conexão via QR Code, persistência de sessão
- **Webhook**: Envio de mensagens recebidas para o backend
- **API REST**: Endpoints para envio programático de mensagens

## API Endpoints

### Health Check

```
GET /status
```

Resposta:
```json
{
  "status": "ready",
  "timestamp": "2025-12-01T10:00:00.000Z"
}
```

### Enviar Mensagem

```
POST /send-message
Content-Type: application/json

{
  "phone": "5511999999999",
  "message": "Seu código de verificação é: 123456"
}
```

**Formato do telefone:** `55` (DDI Brasil) + `11` (DDD) + `999999999` (número)

Resposta sucesso:
```json
{
  "success": true,
  "message": "Message sent successfully"
}
```

Resposta erro:
```json
{
  "error": "WhatsApp client is not ready yet"
}
```

## Integração com Backend

O bot se comunica com o backend Python:

1. **Recebe mensagens** do WhatsApp → envia para `POST /webhook`
2. **Backend chama** `POST /send-message` → envia códigos de verificação

## Primeira Execução

Na primeira execução, será exibido um QR Code no terminal. Escaneie com o WhatsApp para autenticar.
A sessão será salva em `.wwebjs_auth/` para execuções futuras.

---

## 🔄 Fluxo de Criação de Demandas via WhatsApp

### Objetivo
Coletar todas as informações necessárias para criar uma demanda cívica através de conversa natural com o usuário.

### Dados Necessários para Criar uma Demanda

#### 1. **Informações do Usuário** (se não existir)
- ✅ `phone` - Já capturado automaticamente do WhatsApp
- 📝 `name` - Nome completo do usuário
- 📍 `location_primary` - Localização principal do usuário
  - `neighborhood` - Bairro
  - `city` - Cidade
  - `state` - Estado (UF)
  - `coordinates` - {lat, lng} (opcional)
  - `formatted_address` - Endereço formatado

#### 2. **Dados da Demanda** (obrigatórios)
- 📋 `title` - Título da demanda (gerado automaticamente do problema)
- 📝 `description` - Descrição detalhada do problema
- 🎯 `theme` - Categoria/tema da demanda
  - Opções: `mobilidade`, `saude`, `educacao`, `seguranca`, `meio_ambiente`, `infraestrutura`, `outros`
- 📍 `location` - Localização específica do problema (JSONB)
  - `address` - Endereço do problema
  - `city` - Cidade afetada
  - `state` - Estado (UF)
  - `neighborhood` - Bairro (opcional)
  - `coordinates` - {lat, lng} (opcional)
- 🔢 `scope_level` - Nível de abrangência
  - `1` - Hiper-local (rua, praça específica)
  - `2` - Serviço/região (linha de ônibus, UBS)
  - `3` - Cidade/estado (problema amplo)
- ⚠️ `urgency` - Urgência do problema
  - `baixa` - Pode esperar
  - `media` - Importante mas não crítico
  - `alta` - Precisa de atenção rápida
  - `critica` - Emergencial
- 🏢 `affected_entity` - Entidade/serviço afetado (opcional)
  - Exemplos: "Linha 123 de ônibus", "UBS Vila Maria", "Praça da República"

### Fluxo de Conversação Proposto

#### **Etapa 1: Identificação do Usuário** (se novo usuário)
```
Bot: Olá! 👋 Sou o assistente Coral. Vejo que é sua primeira vez aqui!
     Para começar, qual é o seu nome?

User: João Silva

Bot: Prazer, João! Em qual bairro e cidade você mora?

User: Vila Madalena, São Paulo

Bot: Perfeito! [✅ user.name, user.location_primary salvos]
```

#### **Etapa 2: Identificação do Tipo de Interação**
```
Bot: Como posso te ajudar hoje?
     • Relatar um problema na cidade
     • Tirar dúvidas sobre serviços públicos
     • Consultar leis e projetos

User: Quero relatar um problema

Bot: Entendi! Vou te ajudar a criar uma demanda cívica. 
     [🔄 Inicia fluxo de coleta de demanda]
```

#### **Etapa 3: Coleta do Problema**
```
Bot: Qual é o problema que você gostaria de relatar? 
     Descreva da forma mais detalhada possível.

User: A iluminação pública da Rua Augusta está queimada há 2 semanas, 
      deixando a via muito escura e perigosa à noite.

Bot: Entendi. [✅ description capturado]
     Esse problema está em qual endereço exato?

User: Rua Augusta, entre a Rua Oscar Freire e Alameda Lorena

Bot: E em qual bairro e cidade? [📍 Validação de localização]

User: Jardim Paulista, São Paulo - SP

Bot: Perfeito! [✅ location capturado]
```

#### **Etapa 4: Classificação Temática**
```
Bot: Agora preciso classificar seu relato. 
     Esse problema se enquadra em qual categoria?
     
     1. 🚦 Mobilidade (trânsito, transporte, sinalização)
     2. 🏥 Saúde (UBS, hospitais, atendimento)
     3. 📚 Educação (escolas, creches)
     4. 🚨 Segurança (policiamento, vigilância)
     5. 🌳 Meio Ambiente (lixo, poluição, árvores)
     6. 🏗️ Infraestrutura (iluminação, calçadas, buracos)
     7. 📋 Outros

User: 6

Bot: ✅ Classificado como "Infraestrutura"
```

#### **Etapa 5: Nível de Abrangência**
```
Bot: Qual é o alcance deste problema?
     
     1. 🎯 Localizado (um local específico - rua, praça)
     2. 🏘️ Regional (bairro, serviço específico)
     3. 🌆 Amplo (cidade inteira, múltiplas regiões)

User: 1

Bot: ✅ Marcado como problema localizado [scope_level = 1]
```

#### **Etapa 6: Urgência**
```
Bot: Como você classificaria a urgência deste problema?
     
     1. 🟢 Baixa - Pode aguardar
     2. 🟡 Média - Importante, mas não crítico
     3. 🟠 Alta - Precisa de atenção rápida
     4. 🔴 Crítica - Emergencial, risco à saúde/segurança

User: 3

Bot: ✅ Urgência definida como "Alta"
```

#### **Etapa 7: Confirmação e Criação**
```
Bot: Ótimo! Vou resumir sua demanda:
     
     📋 Problema: Iluminação pública queimada
     📍 Local: Rua Augusta, Jardim Paulista - São Paulo/SP
     🏗️ Categoria: Infraestrutura
     🎯 Abrangência: Localizada
     ⚠️ Urgência: Alta
     
     Confirma esses dados? (Sim/Não/Corrigir)

User: Sim

Bot: ✅ Demanda criada com sucesso! 
     
     🎉 Sua demanda foi registrada e já está disponível 
     para receber apoio da comunidade!
     
     📱 Acompanhe em: coral.app/demands/{id}
     🤝 Você é o apoiador nº 1!
     
     [✅ Demand criado no banco com status='active']
```

### Fluxo Técnico de Implementação

#### **1. Detecção de Estado da Conversa**
```python
# src/services/conversation_handler.py

estados_possiveis = [
    "AGUARDANDO_NOME",
    "AGUARDANDO_LOCALIZACAO_USUARIO",
    "AGUARDANDO_TIPO_INTERACAO",
    "AGUARDANDO_DESCRICAO_PROBLEMA",
    "AGUARDANDO_ENDERECO_PROBLEMA",
    "AGUARDANDO_CIDADE_PROBLEMA",
    "AGUARDANDO_TEMA",
    "AGUARDANDO_ABRANGENCIA",
    "AGUARDANDO_URGENCIA",
    "AGUARDANDO_CONFIRMACAO",
]
```

#### **2. Validações Necessárias**
- ✅ Nome: mínimo 2 palavras
- ✅ Localização: validar cidade/estado existentes
- ✅ Descrição: mínimo 20 caracteres
- ✅ Tema: opção válida (1-7)
- ✅ Scope: opção válida (1-3)
- ✅ Urgência: opção válida (1-4)

#### **3. Integração com Agentes IA**
- **RouterAgent**: Classifica tipo de mensagem (DEMANDA, DUVIDA, etc)
- **ProfilerAgent**: Gerencia dados do usuário
- **AnalystAgent**: Analisa similaridade com demandas existentes
- **WriterAgent**: Gera respostas conversacionais naturais
- **ValidatorAgent**: Valida completude dos dados antes de criar demanda

#### **4. Persistência de Estado**
```python
# Tabela: conversation_states
{
    "user_id": "uuid",
    "phone": "5511999999999",
    "current_state": "AGUARDANDO_TEMA",
    "collected_data": {
        "description": "Iluminação pública queimada...",
        "location": {
            "address": "Rua Augusta",
            "city": "São Paulo",
            "state": "SP"
        }
    },
    "last_interaction": "2025-12-01T10:30:00",
    "timeout": 1800  # 30 minutos
}
```

### Melhorias Futuras

- 🗺️ **Geocodificação automática**: Converter endereços em coordenadas
- 📸 **Suporte a imagens**: Permitir envio de fotos do problema
- 🤖 **IA para extração**: Usar Gemini para extrair dados estruturados da descrição livre
- 🔔 **Notificações**: Avisar sobre updates na demanda via WhatsApp
- 🏆 **Gamificação**: Sistema de pontos por demandas criadas/apoiadas
- 📊 **Analytics**: Estatísticas de engajamento do usuário
