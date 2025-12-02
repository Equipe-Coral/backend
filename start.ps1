# Script para iniciar o ambiente Coral Backend completo
# Para todos os containers, sobe PostgreSQL, executa migration e inicia backend

Write-Host "🌊 CORAL BACKEND - Iniciando Ambiente" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# 1. Parar todos os containers
Write-Host "🛑 Parando todos os containers Docker..." -ForegroundColor Yellow
docker compose --profile full down
Start-Sleep -Seconds 2
Write-Host "✅ Containers parados" -ForegroundColor Green
Write-Host ""

# 2. Iniciar apenas PostgreSQL
Write-Host "🐘 Iniciando PostgreSQL..." -ForegroundColor Yellow
docker compose up -d postgres
Write-Host "⏳ Aguardando PostgreSQL ficar pronto..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Verificar se está healthy
$maxAttempts = 30
$attempt = 0
$isHealthy = $false

while ($attempt -lt $maxAttempts -and -not $isHealthy) {
    $attempt++
    $status = docker inspect --format='{{.State.Health.Status}}' coral-postgres 2>$null
    
    if ($status -eq "healthy") {
        $isHealthy = $true
        Write-Host "✅ PostgreSQL está pronto!" -ForegroundColor Green
    } else {
        Write-Host "   Tentativa $attempt/$maxAttempts - Status: $status" -ForegroundColor Gray
        Start-Sleep -Seconds 2
    }
}

if (-not $isHealthy) {
    Write-Host "❌ PostgreSQL não ficou pronto. Abortando..." -ForegroundColor Red
    exit 1
}
Write-Host ""

# 3. Executar migration
Write-Host "📦 Executando migrations SQL..." -ForegroundColor Yellow
python run_migration.py

# 4. Verificar se há erro na migration
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "❌ Erro ao executar migration. Verifique os logs acima." -ForegroundColor Red
    exit 1
}
Write-Host ""

# 5. Iniciar backend (foreground para ver logs)
Write-Host "🚀 Iniciando Backend FastAPI..." -ForegroundColor Yellow
Write-Host "   API disponível em: http://localhost:8000" -ForegroundColor Cyan
Write-Host "   Documentação: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "📝 Logs do Backend:" -ForegroundColor Cyan
Write-Host "==================" -ForegroundColor Cyan
Write-Host ""

# Iniciar backend em foreground (mostra logs)
python main.py
