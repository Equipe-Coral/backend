# Setup do Banco de Dados (PostgreSQL)

## Visão Geral

O projeto utiliza PostgreSQL 16 rodando em um container Docker.

## Configuração

O arquivo `docker-compose.yml` na raiz do projeto define o serviço `postgres`.

### Variáveis de Ambiente

As credenciais padrão (para desenvolvimento) são:

- **User:** `coral_user`
- **Password:** `senha123`
- **Database:** `coral_db`
- **Port:** `5432`

Essas variáveis devem ser configuradas no arquivo `.env` do backend.

## Como Rodar

Para iniciar apenas o banco de dados:

```bash
docker-compose up -d postgres
```

Para verificar os logs:

```bash
docker-compose logs -f postgres
```

## Persistência

Os dados são persistidos no volume Docker `postgres_data`.
