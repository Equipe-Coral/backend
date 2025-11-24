# Guia de Uso - Docker Compose

## 🚀 Comandos Principais

### Iniciar apenas Banco de Dados
```bash
docker compose --profile db up -d
```

### Iniciar Backend (FastAPI + PostgreSQL)
```bash
docker compose --profile backend up -d
```

### Iniciar Blockchain (Blockchain Service + PostgreSQL Blockchain)
```bash
docker compose --profile blockchain up -d
```

### Iniciar tudo (Backend + Blockchain)
```bash
docker compose --profile full up -d
```

---

## 📋 Comandos Básicos

### Ver logs do backend
```bash
docker compose logs -f backend
```

### Ver logs do banco de dados
```bash
docker compose logs -f postgres
```

### Ver logs de todos os serviços
```bash
docker compose logs -f
```

### Parar todos os serviços
```bash
docker compose down
```

### Reconstruir imagens (após mudanças no código)
```bash
docker compose --profile backend up -d --build
```

---

## 🏗️ Profiles Disponíveis

| Profile | Serviços Incluídos | Uso |
|---------|-------------------|-----|
| `db` | PostgreSQL principal | Apenas banco de dados |
| `backend` | PostgreSQL + Backend FastAPI | Backend da aplicação |
| `blockchain` | PostgreSQL Blockchain + Blockchain Service | Serviço blockchain |
| `full` | Todos os serviços | Backend + Blockchain completos |

**Exemplos:**
```bash
# Apenas banco de dados (para desenvolvimento local do backend fora do Docker)
docker compose --profile db up -d

# Backend FastAPI em container
docker compose --profile backend up -d

# Blockchain em container
docker compose --profile blockchain up -d

# Tudo junto
docker compose --profile full up -d

# Parar tudo
docker compose down
```

---

## 📦 Informações dos Containers

### Backend Stack
| Serviço | Container | Porta Host | URL |
|---------|-----------|------------|-----|
| Backend FastAPI | coral-backend | 8000 | http://localhost:8000 |
| PostgreSQL | coral-postgres | 5433 | localhost:5433 |

### Blockchain Stack
| Serviço | Container | Porta Host | URL |
|---------|-----------|------------|-----|
| Blockchain Service | coral-blockchain-service | 8001 | http://localhost:8001 |
| PostgreSQL Blockchain | coral-postgres-blockchain | 5434 | localhost:5434 |

---

## Credenciais do Banco de Dados

```
Host: localhost
Port: 5433
Database: coral_db
User: coral_user
Password: senha123
```

**Dentro do Docker (entre containers):**
```
Host: postgres
Port: 5432
```

---

## Troubleshooting

### Limpar volumes e reiniciar do zero
```bash
docker compose down -v
docker compose up -d --build
```

### Ver status de todos os containers
```bash
docker compose ps
```

### Acessar shell do container do backend
```bash
docker exec -it coral-backend bash
```

### Acessar PostgreSQL diretamente
```bash
docker exec -it coral-postgres psql -U coral_user -d coral_db
```
