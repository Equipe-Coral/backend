# Coral WhatsApp Bot

## Descrição

Bot de WhatsApp implementado com `whatsapp-web.js` para o projeto Coral.
Atua como interface entre o WhatsApp e o Backend FastAPI.

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

## Execução

```bash
npm start
```

Para desenvolvimento (com restart automático):

```bash
npm run dev
```

## Funcionalidades

- Conexão via QR Code
- Persistência de sessão
- Envio de mensagens recebidas para o backend via Webhook
- Recebimento de respostas do backend e envio para o usuário
