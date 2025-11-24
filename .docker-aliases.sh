# Scripts auxiliares para facilitar o uso do Docker

# Iniciar apenas banco de dados
alias dc-db="docker compose --profile db up -d"

# Iniciar todo o backend
alias dc-backend="docker compose --profile backend up -d"

# Iniciar tudo
alias dc-full="docker compose --profile full up -d"

# Ver logs
alias dc-logs="docker compose logs -f"

# Parar tudo
alias dc-down="docker compose down"

# Rebuild e restart
alias dc-rebuild="docker compose --profile backend up -d --build"

# Status dos containers
alias dc-ps="docker compose ps"

# Limpar volumes e reiniciar
alias dc-clean="docker compose down -v && docker compose --profile backend up -d --build"
