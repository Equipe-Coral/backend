# ========================================
# Script para resetar APENAS os dados (mantém estrutura)
# ========================================
# Uso: .\reset-data.ps1

Write-Host "🔄 Conectando ao banco e limpando dados..." -ForegroundColor Yellow

# Executa SQL para truncar todas as tabelas
docker compose exec postgres psql -U coral_user -d coral_db -c "
TRUNCATE TABLE 
    conversation_states,
    interactions,
    demands,
    demand_supporters,
    legislative_items,
    pl_interactions,
    users
CASCADE;
"

Write-Host "✅ Dados limpos com sucesso!" -ForegroundColor Green
Write-Host "📝 As tabelas estão vazias mas a estrutura foi mantida" -ForegroundColor Cyan
