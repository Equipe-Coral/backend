# ========================================
# Script para reconstruir o banco de dados
# ========================================
# Uso: .\rebuild-db.ps1

Write-Host "🔄 Parando containers..." -ForegroundColor Yellow
docker compose --profile backend down

Write-Host "🗑️  Removendo volume do banco de dados..." -ForegroundColor Yellow
docker volume rm backend_postgres_data -f

Write-Host "🚀 Recriando containers com banco novo..." -ForegroundColor Green
docker compose --profile backend up -d

Write-Host "✅ Banco de dados reconstruído com sucesso!" -ForegroundColor Green
Write-Host "📊 Para ver os logs: docker compose logs -f backend" -ForegroundColor Cyan
