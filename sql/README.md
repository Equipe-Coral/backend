# SQL Scripts - Manual Migrations

Este diretório contém scripts SQL para serem executados manualmente no PostgreSQL.

## ⚠️ Importante

**NÃO estamos usando Alembic** neste projeto. As migrations são manuais.

## 🔄 Reconstruir o Banco de Dados

### Opção 1: Reconstrução Completa (Recomendado)

Use o script `db.ps1` na raiz do projeto:

```powershell
# Reconstruir do zero (destrói e recria volume)
.\db.ps1 full

# Limpar apenas os dados (mantém estrutura)
.\db.ps1 data
```

### Opção 2: Comandos Manuais

```powershell
# Parar containers
docker compose --profile backend down

# Remover volume do banco
docker volume rm backend_postgres_data

# Recriar (vai executar todos os scripts SQL automaticamente)
docker compose --profile backend up -d
```

### Por que preciso reconstruir?

O PostgreSQL só executa os scripts em `/docker-entrypoint-initdb.d` na **primeira inicialização** do volume. Se você alterar os arquivos SQL depois, precisa remover o volume para que eles sejam executados novamente.

## Como executar

### Opção 1: Via psql (linha de comando)

```bash
# Conectar ao banco
psql -U postgres -d coral_db

# Executar scripts em ordem
\i backend/sql/002_create_users.sql
\i backend/sql/003_create_conversation_states.sql
\i backend/sql/004_alter_interactions_add_user_id.sql
```

### Opção 2: Via pgAdmin ou DBeaver

1. Abra o pgAdmin ou DBeaver
2. Conecte ao banco `coral_db`
3. Abra o Query Tool
4. Copie e cole o conteúdo de cada arquivo SQL em ordem
5. Execute (F5 ou botão Execute)

### Opção 3: Via docker-compose exec

```bash
docker-compose exec postgres psql -U postgres -d coral_db -f /path/to/script.sql
```

## Scripts disponíveis

### Step 2: Onboarding

- **002_create_users.sql**: Cria tabela `users`

  - Campos: id, phone, location_primary (JSONB), status
  - Índices em phone e status

- **003_create_conversation_states.sql**: Cria tabela `conversation_states`

  - Campos: phone, current_stage, context_data (JSONB)
  - Gerencia estados da conversa multi-turn

- **004_alter_interactions_add_user_id.sql**: Adiciona FK em `interactions`
  - Adiciona coluna `user_id` referenciando `users.id`
  - Cria índice em user_id

## Ordem de execução

Sempre execute na ordem numérica:

1. 002_create_users.sql
2. 003_create_conversation_states.sql
3. 004_alter_interactions_add_user_id.sql

## Verificar se foi criado corretamente

```sql
-- Listar todas as tabelas
\dt

-- Ver estrutura da tabela users
\d users

-- Ver estrutura da tabela conversation_states
\d conversation_states

-- Ver estrutura atualizada de interactions
\d interactions

-- Verificar índices
\di
```

## Rollback (se necessário)

Se precisar reverter as mudanças:

```sql
-- Remover FK de interactions
ALTER TABLE interactions DROP COLUMN user_id;

-- Remover tabelas
DROP TABLE conversation_states;
DROP TABLE users;
```

⚠️ **Atenção:** Isso apagará todos os dados dessas tabelas!
