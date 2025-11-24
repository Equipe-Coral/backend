# PowerShell aliases para facilitar o uso do Docker
# Para usar: . .\.docker-aliases.ps1

# Iniciar apenas banco de dados
function Start-DB { docker compose --profile db up -d }
Set-Alias dc-db Start-DB

# Iniciar backend (FastAPI + PostgreSQL)
function Start-Backend { docker compose --profile backend up -d }
Set-Alias dc-backend Start-Backend

# Iniciar blockchain (Blockchain Service + PostgreSQL Blockchain)
function Start-Blockchain { docker compose --profile blockchain up -d }
Set-Alias dc-blockchain Start-Blockchain

# Iniciar tudo
function Start-Full { docker compose --profile full up -d }
Set-Alias dc-full Start-Full

# Ver logs
function Show-Logs { docker compose logs -f $args }
Set-Alias dc-logs Show-Logs

# Parar tudo
function Stop-All { docker compose down }
Set-Alias dc-down Stop-All

# Rebuild backend
function Rebuild-Backend { docker compose --profile backend up -d --build }
Set-Alias dc-rebuild-backend Rebuild-Backend

# Rebuild blockchain
function Rebuild-Blockchain { docker compose --profile blockchain up -d --build }
Set-Alias dc-rebuild-blockchain Rebuild-Blockchain

# Status dos containers
function Show-Status { docker compose ps }
Set-Alias dc-ps Show-Status

# Limpar volumes e reiniciar
function Clean-Restart { docker compose down -v; docker compose --profile full up -d --build }
Set-Alias dc-clean Clean-Restart

Write-Host "Docker aliases carregados!" -ForegroundColor Green
Write-Host "Comandos disponíveis:" -ForegroundColor Cyan
Write-Host "  dc-db, dc-backend, dc-blockchain, dc-full" -ForegroundColor Yellow
Write-Host "  dc-logs, dc-down, dc-rebuild-backend, dc-rebuild-blockchain" -ForegroundColor Yellow
Write-Host "  dc-ps, dc-clean" -ForegroundColor Yellow
